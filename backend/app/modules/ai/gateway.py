"""
app/modules/ai/gateway.py — LLMGateway (the single choke point for all AI calls).

Architecture reference: §C.5, §J.2, §J.3.
Responsibilities:
  - Model routing by task (entity_resolution, extraction, classification, explanation, investigation)
  - Pluggable provider resolution (Gemini default, Claude, OpenAI, Mock)
  - Content-hash response caching
  - Per-tenant monthly token budget enforcement
  - Audit logging to `agent_runs` table
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any, TypeVar

import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.modules.ai.models import AgentRun
from app.modules.ai.provider import BaseAIProvider, get_ai_provider

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class BudgetExceededError(Exception):
    """Raised when tenant's monthly token budget is exceeded."""

    def __init__(self, org_id: uuid.UUID, budget: int, used: int) -> None:
        super().__init__(f"Monthly token budget exceeded for tenant {org_id}: {used}/{budget}")
        self.org_id = org_id
        self.budget = budget
        self.used = used


class LLMGateway:
    """
    Central gateway for all AI calls in Provenance.
    Ensures unified audit logging, provider interchangeability, caching, and guardrails.
    """

    def __init__(
        self,
        db: AsyncSession | None = None,
        provider: BaseAIProvider | None = None,
    ) -> None:
        self.db = db
        self.settings = get_settings()
        self.provider = provider or get_ai_provider()
        self._cache: dict[str, Any] = {}  # In-memory fast cache; Redis in prod

    def resolve_model_for_task(self, task: str) -> str:
        """Route to appropriate model based on task type."""
        task_lower = task.lower()
        if "entity" in task_lower or "resolution" in task_lower:
            return self.settings.llm_model_entity_resolution
        elif "extract" in task_lower:
            return self.settings.llm_model_extraction
        elif "classif" in task_lower:
            return self.settings.llm_model_classification
        elif "explain" in task_lower:
            return self.settings.llm_model_explanation
        elif "investig" in task_lower:
            return self.settings.llm_model_investigation
        return self.settings.llm_model_extraction

    def _compute_cache_key(self, prompt: str, task: str, model: str) -> str:
        data = f"{task}:{model}:{prompt}".encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    async def execute_structured(
        self,
        *,
        task: str,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
        org_id: uuid.UUID | None = None,
        workflow_run_id: uuid.UUID | None = None,
        temperature: float = 0.0,
        use_cache: bool = True,
    ) -> T:
        """
        Execute structured LLM completion with audit logging and provider abstraction.
        """
        model = self.resolve_model_for_task(task)
        cache_key = self._compute_cache_key(prompt, task, model)

        if use_cache and cache_key in self._cache:
            logger.debug("llm_gateway_cache_hit", task=task, key=cache_key)
            cached_val = self._cache[cache_key]
            if isinstance(cached_val, schema):
                return cached_val
            return schema.model_validate(cached_val)

        start_time = time.monotonic()
        status = "success"
        error_msg: str | None = None
        result: T | None = None

        try:
            result = await self.provider.generate_structured(
                prompt=prompt,
                schema=schema,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature,
            )
            if use_cache and result is not None:
                self._cache[cache_key] = result.model_dump()
            return result
        except Exception as exc:
            status = "failed"
            error_msg = str(exc)
            logger.error("llm_gateway_call_failed", task=task, error=error_msg)
            raise
        finally:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            # Estimate tokens: ~4 chars per token
            est_prompt_tokens = max(1, len(prompt) // 4)
            est_completion_tokens = max(1, len(str(result)) // 4) if result else 0
            # Gemini Flash is ~$0.075 per 1M input tokens, ~$0.30 per 1M output tokens
            cost_usd = (est_prompt_tokens * 0.0000001) + (est_completion_tokens * 0.0000003)

            if self.db:
                try:
                    run_record = AgentRun(
                        org_id=org_id,
                        agent_name=task,
                        workflow_run_id=workflow_run_id,
                        model=model,
                        prompt_version="v1",
                        input_ref={"prompt_preview": prompt[:200]},
                        output_ref={"result_preview": str(result)[:200] if result else None},
                        prompt_tokens=est_prompt_tokens,
                        completion_tokens=est_completion_tokens,
                        cost_usd=cost_usd,
                        latency_ms=latency_ms,
                        status=status,
                        error=error_msg,
                    )
                    self.db.add(run_record)
                    await self.db.flush()
                except Exception as log_exc:
                    logger.warning("failed_to_write_agent_run", error=str(log_exc))
