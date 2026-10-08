"""
app/modules/ai/investigation/schemas.py — Schemas for AI Investigation Agent (Agent 4).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InvestigationQueryRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000, description="Natural language question for investigation")
    alert_id: uuid.UUID | None = Field(default=None, description="Optional alert being investigated")
    company_id: uuid.UUID | None = Field(default=None, description="Optional target company in focus")
    conversation_history: list[ConversationMessage] = Field(default_factory=list)


class InvestigationCitation(BaseModel):
    id: str
    citation_type: Literal["supplier", "company", "event", "graph_edge", "document"]
    title: str
    details: str
    country: str | None = None
    confidence: float = 1.0
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class InvestigationTraceStep(BaseModel):
    step_id: str
    name: str
    action: str
    status: Literal["completed", "executing", "skipped", "failed"] = "completed"
    details: str | None = None
    duration_ms: int = 0


class InvestigationSynthesisOutput(BaseModel):
    """Structured output expected from the LLM via Gemini/LLMGateway."""
    summary: str
    detailed_analysis: str
    risk_level: Literal["critical", "high", "medium", "low", "informational"] = "medium"
    recommended_actions: list[str] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)


class InvestigationResponse(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    query: str
    summary: str
    detailed_analysis: str
    risk_level: Literal["critical", "high", "medium", "low", "informational"]
    recommended_actions: list[str] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    citations: list[InvestigationCitation] = Field(default_factory=list)
    execution_trace: list[InvestigationTraceStep] = Field(default_factory=list)
    model: str
    provider: str
    latency_ms: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InvestigationSuggestion(BaseModel):
    id: str
    title: str
    prompt: str
    category: Literal["exposure", "disruption", "concentration", "deep_tier"]
    icon: str
