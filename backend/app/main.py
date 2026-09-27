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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
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

    # ── CORS ────────────────────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ─────────────────────────────────────────────────────────────
    from app.api.v1.health import router as health_router

    application.include_router(health_router)

    return application


app = create_app()
