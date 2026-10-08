"""
app/api/v1/investigate.py — AI Investigation Agent API endpoints.
Architecture Reference: §J.2 Agent 4, §10, §11, §12.
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.core.deps import require_permission
from app.core.errors import bad_request
from app.db.session import get_db
from app.modules.ai.investigation.schemas import (
    InvestigationQueryRequest,
    InvestigationResponse,
    InvestigationSuggestion,
)
from app.modules.ai.investigation.service import InvestigationAgentService

router = APIRouter(prefix="/investigate", tags=["Investigation Agent"])


@router.post(
    "/query",
    response_model=InvestigationResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute conversational investigation over supplier graph and signals",
)
async def query_investigation_agent(
    request: InvestigationQueryRequest,
    current_user: CurrentUser = Depends(require_permission("ai:use")),
    db: AsyncSession = Depends(get_db),
) -> InvestigationResponse:
    """
    Agent 4 (Investigation Agent): Answers natural language questions regarding
    supply chain disruptions, geopolitical exposure, and risk evidence chains.
    Enforces tenant scoping server-side using current_user.org_id.
    """
    if not current_user.org_id:
        raise bad_request("Tenant organization scope (org_id) is required to run investigation.")

    service = InvestigationAgentService(db=db)
    return await service.investigate(
        request,
        org_id=current_user.org_id,
        user_id=current_user.user_id,
    )


@router.get(
    "/suggestions",
    response_model=list[InvestigationSuggestion],
    status_code=status.HTTP_200_OK,
    summary="Get context-aware investigation starter queries",
)
async def get_investigation_suggestions(
    current_user: CurrentUser = Depends(require_permission("ai:use")),
    db: AsyncSession = Depends(get_db),
) -> list[InvestigationSuggestion]:
    """
    Returns starter investigation queries tailored to the tenant's supplier base.
    """
    if not current_user.org_id:
        raise bad_request("Tenant organization scope (org_id) is required.")

    service = InvestigationAgentService(db=db)
    return await service.get_suggestions(org_id=current_user.org_id)
