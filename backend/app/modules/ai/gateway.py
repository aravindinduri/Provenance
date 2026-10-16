"""
app/modules/ai/gateway.py — LLMGateway (the single choke point for all AI calls).

Architecture reference: §C.5, §J.2, §J.3, §Q.7.
Responsibilities:
  - Model routing by task (entity_resolution, extraction, classification, explanation, investigation)
  - Pluggable provider resolution (Groq default, Gemini, Claude, OpenAI, Mock)
  - Content-hash response caching
  - Per-tenant monthly token budget enforcement (reject with BudgetExceededError)
  - Audit logging to `agent_runs` table with latency, cost, and Langfuse trace link
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, TypeVar

import structlog
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.modules.ai.models import AgentRun
from app.modules.ai.provider import BaseAIProvider, get_ai_provider

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class BudgetExceededError(Exception):
    """Raised when tenant's monthly token budget is exceeded (arch §C.5, §J.3, §21)."""

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

    # In-memory tenant token accumulator for fast checks across calls
    _shared_tenant_usage: dict[uuid.UUID, int] = {}
    _custom_tenant_budgets: dict[uuid.UUID, int] = {}

    def __init__(
        self,
        db: AsyncSession | None = None,
        provider: BaseAIProvider | None = None,
    ) -> None:
        self.db = db
        self.settings = get_settings()
        self.provider = provider or get_ai_provider()
        self._cache: dict[str, Any] = {}  # In-memory fast cache; Redis in prod

    def set_tenant_budget(self, org_id: uuid.UUID, budget: int) -> None:
        """Override monthly token budget for a specific tenant."""
        self._custom_tenant_budgets[org_id] = budget

    def get_tenant_budget(self, org_id: uuid.UUID) -> int:
        """Get effective monthly token budget for a tenant."""
        return self._custom_tenant_budgets.get(
            org_id, self.settings.default_monthly_token_budget
        )

    def get_tenant_usage(self, org_id: uuid.UUID) -> int:
        """Get accumulated monthly token usage for a tenant."""
        return self._shared_tenant_usage.get(org_id, 0)

    def reset_tenant_usage(self, org_id: uuid.UUID) -> None:
        """Reset usage counter (useful for test isolation)."""
        self._shared_tenant_usage.pop(org_id, None)

    async def check_budget(self, org_id: uuid.UUID, estimated_tokens: int = 1000) -> None:
        """
        Enforce tenant monthly token budget.
        Raises BudgetExceededError before calling any external model if exceeded.
        """
        budget = self.get_tenant_budget(org_id)
        used = self.get_tenant_usage(org_id)

        if self.db:
            try:
                start_of_month = datetime.now(timezone.utc).replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                stmt = select(
                    func.coalesce(
                        func.sum(AgentRun.prompt_tokens + AgentRun.completion_tokens), 0
                    )
                ).where(
                    AgentRun.org_id == org_id,
                    AgentRun.created_at >= start_of_month,
                )
                res = await self.db.execute(stmt)
                db_sum = res.scalar() or 0
                used = max(used, int(db_sum))
                self._shared_tenant_usage[org_id] = used
            except Exception as db_exc:
                logger.debug("budget_query_fallback_to_memory", error=str(db_exc))

        if used + estimated_tokens > budget:
            logger.warning(
                "token_budget_exceeded",
                org_id=str(org_id),
                budget=budget,
                used=used,
                requested=estimated_tokens,
            )
            raise BudgetExceededError(org_id=org_id, budget=budget, used=used)

    def resolve_model_for_task(self, task: str) -> str:
        """Route to appropriate model based on task type."""
        default_model = getattr(self.provider, "default_model", "openai/gpt-oss-120b")
        task_lower = task.lower()
        if "entity" in task_lower or "resolution" in task_lower:
            return self.settings.llm_model_entity_resolution or default_model
        elif "extract" in task_lower:
            return self.settings.llm_model_extraction or default_model
        elif "classif" in task_lower:
            return self.settings.llm_model_classification or default_model
        elif "explain" in task_lower:
            return self.settings.llm_model_explanation or default_model
        elif "investig" in task_lower:
            return self.settings.llm_model_investigation or default_model
        return self.settings.llm_model_extraction or default_model

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
        prompt_version: str = "v1",
    ) -> T:
        """
        Execute structured LLM completion with audit logging, budget enforcement,
        content-hash caching, and provider abstraction.
        """
        model = self.resolve_model_for_task(task)
        cache_key = self._compute_cache_key(prompt, task, model)

        # 1. Check Content-Hash Cache
        if use_cache and cache_key in self._cache:
            logger.debug("llm_gateway_cache_hit", task=task, key=cache_key)
            cached_val = self._cache[cache_key]
            if isinstance(cached_val, schema):
                return cached_val
            return schema.model_validate(cached_val)

        # 2. Estimate tokens and check monthly tenant budget
        est_prompt_tokens = max(1, len(prompt) // 4)
        if org_id is not None:
            await self.check_budget(org_id, estimated_tokens=est_prompt_tokens)

        start_time = time.monotonic()
        status = "success"
        error_msg: str | None = None
        result: T | None = None

        # Generate Langfuse trace ID if tracing configured
        langfuse_trace_id: str | None = None
        if self.settings.langfuse_public_key:
            langfuse_trace_id = f"trace-{uuid.uuid4()}"

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
            est_completion_tokens = max(1, len(str(result)) // 4) if result else 0
            # Approximate costs: Groq / GPT-OSS 120B ~$0.59/1M input, ~$0.79/1M output; Gemini Flash ~$0.10/$0.30
            if getattr(self.provider, "name", "") == "groq":
                cost_usd = (est_prompt_tokens * 0.00000059) + (est_completion_tokens * 0.00000079)
            else:
                cost_usd = (est_prompt_tokens * 0.0000001) + (est_completion_tokens * 0.0000003)

            # Record token usage for tenant
            if org_id is not None:
                total_used = est_prompt_tokens + est_completion_tokens
                self._shared_tenant_usage[org_id] = (
                    self._shared_tenant_usage.get(org_id, 0) + total_used
                )

            # Audit log to agent_runs
            if self.db:
                try:
                    run_record = AgentRun(
                        org_id=org_id,
                        agent_name=task,
                        workflow_run_id=workflow_run_id,
                        model=model,
                        prompt_version=prompt_version,
                        input_ref={"prompt_preview": prompt[:200]},
                        output_ref={"result_preview": str(result)[:200] if result else None},
                        prompt_tokens=est_prompt_tokens,
                        completion_tokens=est_completion_tokens,
                        cost_usd=cost_usd,
                        latency_ms=latency_ms,
                        status=status,
                        error=error_msg,
                        langfuse_trace_id=langfuse_trace_id,
                    )
                    self.db.add(run_record)
                    await self.db.flush()
                except Exception as log_exc:
                    logger.warning("failed_to_write_agent_run", error=str(log_exc))
