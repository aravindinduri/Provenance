"""
main.py — FastAPI application factory.

Import and call `create_app()` to get the configured ASGI application.
`app` at module level is what uvicorn/gunicorn targets.
"""

import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

# Ensure repo root is on sys.path so ingestion / workers packages are resolvable
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.base import AuthenticationError, AuthorizationError
from app.config import get_settings
from app.core.errors import (
    authentication_error_handler,
    authorization_error_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "provenance_api_starting",
        environment=settings.environment,
        version=application.version,
    )
    yield
    logger.info("provenance_api_stopping")


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title="Provenance API",
        description="Supply-chain risk intelligence platform.",
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request ID middleware ─────────────────────────────────────────────────
    from app.core.middleware import RequestIdMiddleware
    application.add_middleware(RequestIdMiddleware)

    # ── Rate limiting ────────────────────────────────────────────────────────
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from app.core.limiter import limiter
    from app.core.errors import rate_limit_exceeded_handler

    application.state.limiter = limiter
    application.add_middleware(SlowAPIMiddleware)

    # ── Exception handlers ────────────────────────────────────────────────────
    from app.modules.ai.provider import AIProviderError
    from app.core.errors import ai_provider_error_handler

    application.add_exception_handler(AuthenticationError, authentication_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(AuthorizationError, authorization_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    application.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]
    application.add_exception_handler(AIProviderError, ai_provider_error_handler)  # type: ignore[arg-type]

    # ── Routers ───────────────────────────────────────────────────────────────
    from app.api.v1.health import router as health_router
    from app.api.v1.auth import router as auth_router
    from app.api.v1.organizations import router as orgs_router
    from app.api.v1.webhooks import router as webhooks_router
    from app.api.v1.companies import router as companies_router
    from app.api.v1.suppliers import router as suppliers_router
    from app.api.v1.relationships import router as relationships_router
    from app.api.v1.graph import router as graph_router
    from app.api.v1.admin import router as admin_router
    from app.api.v1.entity_reviews import router as entity_reviews_router
    from app.api.v1.investigate import router as investigate_router
    from app.api.v1.alerts import router as alerts_router
    from app.api.v1.events import router as events_router
    from app.api.v1.risks import router as risks_router
    # Phase 1 — Procurement foundation
    from app.api.v1.items import router as items_router
    from app.api.v1.material_requests import router as material_requests_router
    from app.api.v1.approvals import router as approvals_router
    # Phase 2 — Sourcing
    from app.api.v1.rfx import router as rfx_router
    from app.api.v1.supplier_quotations import router as supplier_quotations_router
    # Phase 3 — Order-to-Receipt
    from app.api.v1.purchase_orders import router as purchase_orders_router
    from app.api.v1.goods_receipts import router as goods_receipts_router
    # Phase 4 — Invoices & 3-Way Matching
    from app.api.v1.invoices import router as invoices_router

    api_prefix = "/v1"
    application.include_router(health_router)
    application.include_router(auth_router, prefix=api_prefix)
    application.include_router(orgs_router, prefix=api_prefix)
    application.include_router(webhooks_router, prefix=api_prefix)
    application.include_router(companies_router, prefix=api_prefix)
    application.include_router(entity_reviews_router, prefix=api_prefix)
    application.include_router(investigate_router, prefix=api_prefix)
    application.include_router(alerts_router, prefix=api_prefix)
    application.include_router(events_router, prefix=api_prefix)
    application.include_router(risks_router, prefix=api_prefix)
    application.include_router(suppliers_router, prefix=api_prefix)
    application.include_router(relationships_router, prefix=api_prefix)
    application.include_router(graph_router, prefix=api_prefix)
    application.include_router(admin_router, prefix=api_prefix)
    # Phase 1 routers
    application.include_router(items_router, prefix=api_prefix)
    application.include_router(material_requests_router, prefix=api_prefix)
    application.include_router(approvals_router, prefix=api_prefix)
    # Phase 2 routers
    application.include_router(rfx_router, prefix=api_prefix)
    application.include_router(supplier_quotations_router, prefix=api_prefix)
    # Phase 3 routers
    application.include_router(purchase_orders_router, prefix=api_prefix)
    application.include_router(goods_receipts_router, prefix=api_prefix)
    # Phase 4 routers
    application.include_router(invoices_router, prefix=api_prefix)

    return application



app = create_app()
