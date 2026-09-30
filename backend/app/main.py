"""
main.py — FastAPI application factory.

Import and call `create_app()` to get the configured ASGI application.
`app` at module level is what uvicorn/gunicorn targets.
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

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
    application.add_exception_handler(AuthenticationError, authentication_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(AuthorizationError, authorization_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    application.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # ── Routers ───────────────────────────────────────────────────────────────
    from app.api.v1.health import router as health_router
    from app.api.v1.auth import router as auth_router
    from app.api.v1.organizations import router as orgs_router
    from app.api.v1.webhooks import router as webhooks_router
    from app.api.v1.companies import router as companies_router
    from app.api.v1.suppliers import router as suppliers_router
    from app.api.v1.relationships import router as relationships_router

    api_prefix = "/v1"
    application.include_router(health_router)
    application.include_router(auth_router, prefix=api_prefix)
    application.include_router(orgs_router, prefix=api_prefix)
    application.include_router(webhooks_router, prefix=api_prefix)
    application.include_router(companies_router, prefix=api_prefix)
    application.include_router(suppliers_router, prefix=api_prefix)
    application.include_router(relationships_router, prefix=api_prefix)

    return application


app = create_app()
