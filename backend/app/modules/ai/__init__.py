"""
AI Module — Interchangeable AI Providers & LLMGateway.
"""

from app.modules.ai.gateway import LLMGateway
from app.modules.ai.models import AgentRun, Document, DocumentChunk, Embedding
from app.modules.ai.provider import (
    BaseAIProvider,
    ClaudeProvider,
    GeminiProvider,
    MockProvider,
    OpenAIProvider,
    get_ai_provider,
)

__all__ = [
    "AgentRun",
    "BaseAIProvider",
    "ClaudeProvider",
    "Document",
    "DocumentChunk",
    "Embedding",
    "GeminiProvider",
    "LLMGateway",
    "MockProvider",
    "OpenAIProvider",
    "get_ai_provider",
]
