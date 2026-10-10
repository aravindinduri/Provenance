"""
app/api/v1/auth.py — Authentication endpoints: register, login, me.
Zero dummy/mock tokens. Issues and verifies cryptographically signed JWTs.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.auth.security import create_access_token, hash_password, verify_password
from app.config import get_settings
from app.core.deps import get_current_user
from app.core.errors import bad_request
from app.db.session import get_db
from app.modules.organizations.models import Organization, OrganizationMember, User
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.schemas import MeOut, OrganizationOut

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255, description="Valid email address")
    password: str = Field(min_length=6, description="Password must be at least 6 characters")
    full_name: str = Field(min_length=2, max_length=255)
    org_name: str = Field(min_length=2, max_length=255, description="Organization or company name")


class LoginRequest(BaseModel):
    email: str
    password: str


class UserSummary(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    persona: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary
    organization: OrganizationOut | None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user and organization",
)
async def register_user(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """
    Registers a real user and provisions their organization tenant.
    Issues a cryptographically signed JWT access token.
    """
    normalized_email = payload.email.strip().lower()

    # 1. Check if user already exists
    existing_user_query = await db.execute(
        text("SELECT id FROM users WHERE email = :email AND deleted_at IS NULL"),
        {"email": normalized_email},
    )
    if existing_user_query.fetchone():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in.",
        )

    # 2. Create User record
    user_id = uuid.uuid4()
    hashed_pwd = hash_password(payload.password)
    user = User(
        id=user_id,
        email=normalized_email,
        hashed_password=hashed_pwd,
        full_name=payload.full_name.strip(),
        is_active=True,
    )
    db.add(user)

    # 3. Resolve or Create Organization
    org_name = payload.org_name.strip()
    slug = re.sub(r"[^a-z0-9]+", "-", org_name.lower()).strip("-") or "org"

    # Check if an organization with this slug already exists
    org_query = await db.execute(
        text("SELECT id FROM organizations WHERE slug = :slug AND deleted_at IS NULL"),
        {"slug": slug},
    )
    existing_org = org_query.fetchone()

    if existing_org:
        org_id = existing_org[0]
        org_repo = OrganizationRepository(db)
        org = await org_repo.get_by_id(org_id)
    else:
        org_id = uuid.uuid4()
        clerk_org_id = f"org_{slug}_{uuid.uuid4().hex[:8]}"
        org = Organization(
            id=org_id,
            clerk_org_id=clerk_org_id,
            name=org_name,
            slug=slug,
            country="US",
            settings={},
            monthly_token_budget=get_settings().default_monthly_token_budget,
        )
        db.add(org)

    # 4. Create Organization Member
    member = OrganizationMember(
        id=uuid.uuid4(),
        org_id=org_id,
        user_id=str(user_id),
        role="org_admin",
        persona="risk_manager",
        assigned_categories=[],
    )
    db.add(member)

    await db.commit()

    # 5. Issue JWT
    token_claims = {
        "sub": str(user_id),
        "email": normalized_email,
        "org_id": str(org_id),
        "clerk_org_id": org.clerk_org_id if org else f"org_{slug}",
        "role": "org_admin",
        "persona": "risk_manager",
    }
    access_token = create_access_token(token_claims)

    org_out = OrganizationOut.model_validate(org) if org else None
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserSummary(
            id=str(user_id),
            email=normalized_email,
            full_name=payload.full_name.strip(),
            role="org_admin",
            persona="risk_manager",
        ),
        organization=org_out,
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in with email and password",
)
async def login_user(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """
    Authenticates an existing user and returns a cryptographically signed JWT token.
    """
    normalized_email = payload.email.strip().lower()

    # 1. Query user by email
    user_query = await db.execute(
        text(
            "SELECT id, email, hashed_password, full_name, is_active FROM users "
            "WHERE email = :email AND deleted_at IS NULL LIMIT 1"
        ),
        {"email": normalized_email},
    )
    user_record = user_query.fetchone()

    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id, email, hashed_pwd, full_name, is_active = user_record

    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact your administrator.",
        )

    # 2. Verify password hash
    if not verify_password(payload.password, hashed_pwd):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Query member role & organization
    member_query = await db.execute(
        text(
            """
            SELECT om.org_id, om.role, om.persona, o.id, o.clerk_org_id, o.name, o.slug, o.country
            FROM organization_members om
            JOIN organizations o ON o.id = om.org_id
            WHERE (om.user_id = :uid OR om.user_id = :email) AND om.deleted_at IS NULL AND o.deleted_at IS NULL
            ORDER BY om.created_at ASC LIMIT 1
            """
        ),
        {"uid": str(user_id), "email": normalized_email},
    )
    member_record = member_query.fetchone()

    if not member_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is not associated with any organization.",
        )

    org_id, role, persona = member_record[0], member_record[1], member_record[2]
    org_repo = OrganizationRepository(db)
    org = await org_repo.get_by_id(org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated organization could not be found.",
        )

    # 4. Generate JWT
    token_claims = {
        "sub": str(user_id),
        "email": normalized_email,
        "org_id": str(org.id),
        "clerk_org_id": org.clerk_org_id,
        "role": role,
        "persona": persona or "risk_manager",
    }
    access_token = create_access_token(token_claims)

    org_out = OrganizationOut.model_validate(org)
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserSummary(
            id=str(user_id),
            email=normalized_email,
            full_name=full_name,
            role=role,
            persona=persona or "risk_manager",
        ),
        organization=org_out,
    )


@router.get(
    "/me",
    response_model=MeOut,
    summary="Current authenticated user + org context",
)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeOut:
    """
    Returns the resolved CurrentUser and their organization record from verified JWT.
    """
    org_out = None
    if current_user.org_id:
        repo = OrganizationRepository(db)
        org = await repo.get_by_id(uuid.UUID(current_user.org_id))
        if org is not None:
            org_out = OrganizationOut.model_validate(org)

    return MeOut(
        user_id=current_user.user_id,
        email=current_user.email,
        org_id=current_user.org_id,
        clerk_org_id=current_user.clerk_org_id,
        role=current_user.role,
        persona=current_user.persona,
        assigned_categories=current_user.assigned_categories,
        organization=org_out,
    )
