"""
POST /v1/webhooks/clerk — Clerk webhook receiver.

Handles organization and user membership lifecycle events from Clerk so the
internal organizations / organization_members tables stay in sync.

Supported event types:
  organization.created        → create organizations row
  organization.updated        → update name / metadata
  organization.deleted        → soft-delete
  organizationMembership.created  → upsert member
  organizationMembership.updated  → update role
  organizationMembership.deleted  → soft-delete member

Security: every request is verified against the Svix signing secret
(CLERK_WEBHOOK_SECRET). A missing or invalid signature returns 401.

Idempotency: all operations are upsert-style — replaying a webhook is safe.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import AuthenticationError
from app.auth.providers.clerk import verify_clerk_webhook
from app.db.session import get_db
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.schemas import OrganizationCreate
from app.modules.organizations.service import OrganizationService
from fastapi import Depends

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_ACTOR = "system:clerk_webhook"


@router.post(
    "/clerk",
    status_code=status.HTTP_200_OK,
    summary="Clerk webhook receiver",
    include_in_schema=False,  # not a public API
)
async def clerk_webhook(
    request: Request,
    svix_id: str = Header(..., alias="svix-id"),
    svix_timestamp: str = Header(..., alias="svix-timestamp"),
    svix_signature: str = Header(..., alias="svix-signature"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # ── 1. Verify signature ───────────────────────────────────────────────────
    body = await request.body()
    try:
        event = verify_clerk_webhook(body, svix_id, svix_timestamp, svix_signature)
    except AuthenticationError as exc:
        logger.warning("clerk_webhook_invalid_signature", error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid webhook signature"},
        )

    event_type: str = event.get("type", "")
    data: dict = event.get("data", {})

    logger.info("clerk_webhook_received", event_type=event_type)

    repo = OrganizationRepository(db)
    svc = OrganizationService(db)

    try:
        # ── 2. Dispatch ───────────────────────────────────────────────────────
        if event_type == "organization.created":
            await _handle_org_created(data, svc)

        elif event_type == "organization.updated":
            await _handle_org_updated(data, repo)

        elif event_type == "organization.deleted":
            await _handle_org_deleted(data, repo)

        elif event_type == "organizationMembership.created":
            await _handle_membership_created(data, svc)

        elif event_type == "organizationMembership.updated":
            await _handle_membership_updated(data, svc)

        elif event_type == "organizationMembership.deleted":
            await _handle_membership_deleted(data, repo)

        else:
            # Unknown event — acknowledge without processing
            logger.debug("clerk_webhook_unhandled_event", event_type=event_type)

        await db.commit()

    except Exception as exc:
        logger.exception("clerk_webhook_processing_error", event_type=event_type, error=str(exc))
        await db.rollback()
        # Return 200 so Clerk doesn't retry indefinitely for our internal errors
        # (Clerk interprets non-2xx as "please retry"). We log and alert separately.
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"detail": "Processed with errors — see application logs"},
        )

    return JSONResponse(status_code=status.HTTP_200_OK, content={"received": True})


# ---------------------------------------------------------------------------
# Handler helpers
# ---------------------------------------------------------------------------

async def _handle_org_created(data: dict, svc: OrganizationService) -> None:
    clerk_org_id = data.get("id", "")
    name = data.get("name", "")
    slug = data.get("slug") or name

    payload = OrganizationCreate(
        clerk_org_id=clerk_org_id,
        name=name,
        slug=slug,
    )
    org = await svc.create_from_webhook(payload, actor=_ACTOR)
    logger.info("clerk_webhook_org_created", org_id=str(org.id), clerk_org_id=clerk_org_id)


async def _handle_org_updated(data: dict, repo: OrganizationRepository) -> None:
    clerk_org_id = data.get("id", "")
    org = await repo.get_by_clerk_org_id(clerk_org_id)
    if org is None:
        logger.warning("clerk_webhook_org_not_found_on_update", clerk_org_id=clerk_org_id)
        return

    from app.modules.organizations.schemas import OrganizationUpdate

    update = OrganizationUpdate(name=data.get("name"))
    await repo.update(org, update, updated_by=_ACTOR)
    logger.info("clerk_webhook_org_updated", org_id=str(org.id))


async def _handle_org_deleted(data: dict, repo: OrganizationRepository) -> None:
    from datetime import datetime, timezone

    clerk_org_id = data.get("id", "")
    org = await repo.get_by_clerk_org_id(clerk_org_id)
    if org is None:
        return

    org.deleted_at = datetime.now(tz=timezone.utc)
    org.updated_by = _ACTOR
    logger.info("clerk_webhook_org_deleted", org_id=str(org.id))


async def _handle_membership_created(data: dict, svc: OrganizationService) -> None:
    organization = data.get("organization", {})
    public_user_data = data.get("public_user_data", {})

    clerk_org_id = organization.get("id", "")
    user_id = public_user_data.get("user_id", "")
    clerk_role = data.get("role", "org:member")

    member = await svc.upsert_member_from_webhook(clerk_org_id, user_id, clerk_role)
    if member:
        logger.info(
            "clerk_webhook_member_synced",
            user_id=user_id,
            clerk_org_id=clerk_org_id,
            role=member.role,
        )


async def _handle_membership_updated(data: dict, svc: OrganizationService) -> None:
    # Same shape as created — upsert handles both
    await _handle_membership_created(data, svc)


async def _handle_membership_deleted(
    data: dict, repo: OrganizationRepository
) -> None:
    from datetime import datetime, timezone

    organization = data.get("organization", {})
    public_user_data = data.get("public_user_data", {})

    clerk_org_id = organization.get("id", "")
    user_id = public_user_data.get("user_id", "")

    org = await repo.get_by_clerk_org_id(clerk_org_id)
    if org is None:
        return

    member = await repo.get_member(org.id, user_id)
    if member is None:
        return

    member.deleted_at = datetime.now(tz=timezone.utc)
    member.updated_by = _ACTOR
    logger.info(
        "clerk_webhook_member_removed",
        user_id=user_id,
        org_id=str(org.id),
    )
