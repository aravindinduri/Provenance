"""
Central model registry.

Import this module (or any subset of its imports) wherever you need
SQLAlchemy's metadata to include all tables — specifically in:
  - database/migrations/env.py  (for Alembic autogenerate)
  - tests                       (so create_all works on a test DB)

Order matters: tables with no FKs first, then dependents.
"""

# Shared base (must come first)
from app.db.base import Base  # noqa: F401

# ── 1. Global reference data (no org_id) ─────────────────────────────────────
from app.modules.companies.models import (  # noqa: F401
    Company,
    CompanyAlias,
    CompanyIdentifier,
    EntityResolutionReview,
)
from app.modules.graph.models import (  # noqa: F401
    CompanyLocation,
    Location,
    SupplierRelationship,
)

# ── 2. Tenancy ────────────────────────────────────────────────────────────────
from app.modules.organizations.models import (  # noqa: F401
    Organization,
    OrganizationMember,
)

# ── 3. Ingestion + events (global) ───────────────────────────────────────────
from app.modules.events.models import (  # noqa: F401
    DataSource,
    DeadLetterQueue,
    Event,
    EventEntity,
    EventSourceRecord,
    SourceRecord,
    SourceRecordVersion,
)

# ── 4. Risk + alerts (tenant-scoped) ─────────────────────────────────────────
from app.modules.risk.models import RiskAssessment, RiskModelVersion  # noqa: F401
from app.modules.alerts.models import Alert, AlertAction, AlertEvidence  # noqa: F401

# ── 5. Spend (tenant-scoped) ──────────────────────────────────────────────────
from app.modules.spend.models import (  # noqa: F401
    Contract,
    PurchaseOrder,
    SpendLeakageFinding,
    SpendRecord,
    UploadedDocument,
)

# ── 6. AI / RAG ───────────────────────────────────────────────────────────────
from app.modules.ai.models import (  # noqa: F401
    AgentRun,
    Document,
    DocumentChunk,
    Embedding,
)

# ── 7. Notifications (tenant-scoped) ─────────────────────────────────────────
from app.modules.notifications.models import (  # noqa: F401
    Notification,
    NotificationDelivery,
    NotificationPreference,
)

# ── 8. Audit (append-only) ───────────────────────────────────────────────────
from app.modules.admin.models import AuditLog  # noqa: F401

__all__ = ["Base"]
