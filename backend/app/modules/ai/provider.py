"""
app/modules/ai/provider.py — Vendor-neutral, interchangeable AI provider abstractions.

Architecture reference: §C.5, §J.2, §J.3.
Enables instant switching between Google Gemini, Anthropic Claude, OpenAI, or Mock
via configuration (settings.llm_provider) without vendor lock-in.
"""

from __future__ import annotations

import abc
import json
import re
import time
from typing import Any, TypeVar

import httpx
import structlog
from pydantic import BaseModel

from app.config import get_settings

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class AIProviderError(Exception):
    """Raised when an AI provider call fails."""

    def __init__(self, message: str, status_code: int | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class BaseAIProvider(abc.ABC):
    """Abstract base class for interchangeable AI providers."""

    name: str

    @abc.abstractmethod
    async def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        """Generate freeform text."""
        ...

    @abc.abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> T:
        """Generate structured data conforming to a Pydantic schema."""
        ...

    async def generate_embeddings(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        """Optional embedding generation."""
        raise NotImplementedError(f"{self.name} does not implement generate_embeddings")


class GeminiProvider(BaseAIProvider):
    """
    Google Gemini provider implementation via Gemini REST API.
    Default provider for Provenance AI services.
    """

    name = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "gemini-1.5-flash",
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.base_url = (base_url or settings.gemini_base_url).rstrip("/")
        self.default_model = default_model

    async def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        target_model = model or self.default_model
        if "/" in target_model:
            target_model = target_model.split("/")[-1]

        endpoint = f"{self.base_url}/v1beta/models/{target_model}:generateContent"
        params = {"key": self.api_key} if self.api_key else {}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-goog-api-key"] = self.api_key

        contents: list[dict[str, Any]] = []
        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"SYSTEM INSTRUCTION: {system_prompt}"}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Understood. I will strictly follow these instructions."}]
            })

        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(endpoint, params=params, headers=headers, json=payload)
            if resp.status_code != 200:
                raise AIProviderError(
                    f"Gemini API returned error {resp.status_code}: {resp.text}",
                    status_code=resp.status_code,
                    details=resp.text,
                )
            data = resp.json()

        try:
            candidates = data.get("candidates", [])
            if not candidates:
                raise AIProviderError("Gemini returned no candidates", details=data)
            parts = candidates[0].get("content", {}).get("parts", [])
            return parts[0].get("text", "").strip()
        except (IndexError, KeyError, AttributeError) as exc:
            raise AIProviderError(f"Failed to parse Gemini response: {exc}", details=data) from exc

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> T:
        target_model = model or self.default_model
        if "/" in target_model:
            target_model = target_model.split("/")[-1]

        endpoint = f"{self.base_url}/v1beta/models/{target_model}:generateContent"
        params = {"key": self.api_key} if self.api_key else {}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-goog-api-key"] = self.api_key

        schema_json = json.dumps(schema.model_json_schema())
        instruction = (
            f"{system_prompt or ''}\n\n"
            f"You MUST output valid, raw JSON matching this JSON schema exactly:\n{schema_json}\n"
            "Do NOT include markdown formatting (like ```json). Return raw JSON only."
        ).strip()

        contents: list[dict[str, Any]] = [
            {"role": "user", "parts": [{"text": f"{instruction}\n\nInput Context:\n{prompt}"}]}
        ]

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "response_mime_type": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(endpoint, params=params, headers=headers, json=payload)
            if resp.status_code != 200:
                raise AIProviderError(
                    f"Gemini API returned error {resp.status_code}: {resp.text}",
                    status_code=resp.status_code,
                    details=resp.text,
                )
            data = resp.json()

        try:
            candidates = data.get("candidates", [])
            if not candidates:
                raise AIProviderError("Gemini returned no candidates", details=data)
            parts = candidates[0].get("content", {}).get("parts", [])
            raw_text = parts[0].get("text", "").strip()
            raw_text = re.sub(r"^```json\s*", "", raw_text)
            raw_text = re.sub(r"^```\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text).strip()
            parsed = json.loads(raw_text)
            return schema.model_validate(parsed)
        except Exception as exc:
            raise AIProviderError(f"Failed to parse structured Gemini output: {exc}", details=data) from exc


class ClaudeProvider(BaseAIProvider):
    """
    Anthropic Claude provider implementation via Messages API.
    Interchangeable drop-in.
    """

    name = "anthropic"

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "claude-3-5-sonnet-20241022",
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.anthropic_api_key
        self.default_model = default_model

    async def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body: dict[str, Any] = {
            "model": model or self.default_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            body["system"] = system_prompt

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
            if resp.status_code != 200:
                raise AIProviderError(f"Claude API error {resp.status_code}: {resp.text}", status_code=resp.status_code)
            data = resp.json()

        content = data.get("content", [])
        if not content:
            raise AIProviderError("Claude returned empty content", details=data)
        return content[0].get("text", "").strip()

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> T:
        schema_json = json.dumps(schema.model_json_schema())
        full_system = (
            f"{system_prompt or ''}\n"
            f"You MUST reply with ONLY a JSON object that satisfies this schema:\n{schema_json}"
        )
        text = await self.generate_text(
            prompt,
            system_prompt=full_system,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        clean = re.sub(r"^```(?:json)?\s*", "", text)
        clean = re.sub(r"\s*```$", "", clean).strip()
        parsed = json.loads(clean)
        return schema.model_validate(parsed)


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI provider implementation via Chat Completions API.
    Interchangeable drop-in.
    """

    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "gpt-4o-mini",
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.default_model = default_model

    async def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body)
            if resp.status_code != 200:
                raise AIProviderError(f"OpenAI API error {resp.status_code}: {resp.text}", status_code=resp.status_code)
            data = resp.json()

        choices = data.get("choices", [])
        if not choices:
            raise AIProviderError("OpenAI returned no choices", details=data)
        return choices[0].get("message", {}).get("content", "").strip()

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> T:
        schema_json = json.dumps(schema.model_json_schema())
        full_system = (
            f"{system_prompt or ''}\n"
            f"You MUST output raw JSON conforming to this schema:\n{schema_json}"
        )
        text = await self.generate_text(
            prompt,
            system_prompt=full_system,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        clean = re.sub(r"^```(?:json)?\s*", "", text)
        clean = re.sub(r"\s*```$", "", clean).strip()
        parsed = json.loads(clean)
        return schema.model_validate(parsed)


class MockProvider(BaseAIProvider):
    """
    Mock AI Provider for deterministic testing, offline environments, and CI.
    Can be loaded with deterministic scripted responses or generate default mock payloads.
    """

    name = "mock"

    def __init__(self) -> None:
        self.scripted_responses: list[Any] = []
        self.last_prompt: str | None = None
        self.call_count: int = 0

    def add_response(self, response: Any) -> None:
        self.scripted_responses.append(response)

    async def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        self.last_prompt = prompt
        self.call_count += 1
        if self.scripted_responses:
            res = self.scripted_responses.pop(0)
            if isinstance(res, str):
                return res
            return json.dumps(res)
        return "Mock AI response for prompt."

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> T:
        self.last_prompt = prompt
        self.call_count += 1
        if self.scripted_responses:
            res = self.scripted_responses.pop(0)
            if isinstance(res, schema):
                return res
            if isinstance(res, dict):
                return schema.model_validate(res)
            if isinstance(res, str):
                return schema.model_validate_json(res)

        # Build reasonable mock instance from schema fields
        mock_data: dict[str, Any] = {}
        fields = schema.model_fields
        for field_name, field_info in fields.items():
            ann = field_info.annotation
            ann_str = str(ann).lower()
            if "bool" in ann_str:
                mock_data[field_name] = True
            elif "float" in ann_str:
                mock_data[field_name] = 0.90
            elif "int" in ann_str:
                mock_data[field_name] = 1
            elif "list" in ann_str:
                mock_data[field_name] = []
            elif "dict" in ann_str:
                mock_data[field_name] = {}
            elif "decision" in field_name:
                mock_data[field_name] = "match"
            else:
                mock_data[field_name] = f"Mock {field_name}"
        return schema.model_validate(mock_data)


def get_ai_provider(provider_name: str | None = None) -> BaseAIProvider:
    """
    Factory function to get an interchangeable AI Provider.
    Defaults to Gemini (from settings.llm_provider = "gemini").
    """
    settings = get_settings()
    choice = (provider_name or settings.llm_provider or "gemini").lower()

    if choice in ("gemini", "google", "vertex"):
        return GeminiProvider()
    elif choice in ("anthropic", "claude"):
        return ClaudeProvider()
    elif choice in ("openai", "gpt"):
        return OpenAIProvider()
    elif choice in ("mock", "test"):
        return MockProvider()
    else:
        logger.warning("unknown_ai_provider_fallback", requested=choice, fallback="gemini")
        return GeminiProvider()
