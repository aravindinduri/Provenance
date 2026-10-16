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

# ── 9. Phase 1 — Procurement foundation ─────────────────────────────────────
from app.modules.items.models import Item  # noqa: F401
from app.modules.procurement.models import MaterialRequest, MaterialRequestItem  # noqa: F401
from app.modules.approvals.models import ApprovalRule, ApprovalWorkflow, ApprovalStep  # noqa: F401

# ── 10. Phase 2 — Sourcing ──────────────────────────────────────────────────
from app.modules.rfx.models import RFxEvent, RFxInvitation, RFxResponse  # noqa: F401

# ── 11. Phase 3 — Order-to-Receipt ──────────────────────────────────────────
from app.modules.goods_receipts.models import GoodsReceipt  # noqa: F401

__all__ = ["Base"]


