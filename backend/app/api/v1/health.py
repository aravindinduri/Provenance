"""
/health and /health/ready endpoints.

/health    — liveness: the process is alive (used by ECS/ALB health checks).
/health/ready — readiness: the process can serve traffic (DB + Redis reachable).
"""

import time
from typing import Any

import structlog
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])

# Module-level start time for uptime reporting
_START_TIME = time.time()


@router.get(
    "/health",
    summary="Liveness probe",
    response_description="Service is alive",
    status_code=status.HTTP_200_OK,
)
async def health_liveness() -> dict[str, Any]:
    """Always returns 200 while the process is running."""
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - _START_TIME, 1),
    }


@router.get(
    "/health/ready",
    summary="Readiness probe",
    response_description="Service can accept traffic",
)
async def health_readiness() -> JSONResponse:
    """
    Checks that the database and Redis are reachable.
    Returns 200 if ready, 503 if any dependency is unavailable.
    """
    checks: dict[str, str] = {}
    healthy = True

    # ── Database ────────────────────────────────────────────────────────────
    try:
        from app.db.session import check_db_connection

        await check_db_connection()
        checks["database"] = "ok"
    except Exception as exc:
        logger.warning("health_check_db_failed", error=str(exc))
        checks["database"] = "unavailable"
        healthy = False

    # ── Redis ────────────────────────────────────────────────────────────────
    try:
        from app.db.redis import check_redis_connection

        await check_redis_connection()
        checks["redis"] = "ok"
    except Exception as exc:
        logger.warning("health_check_redis_failed", error=str(exc))
        checks["redis"] = "unavailable"
        healthy = False

    http_status = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_status,
        content={
            "status": "ready" if healthy else "degraded",
            "checks": checks,
        },
    )
