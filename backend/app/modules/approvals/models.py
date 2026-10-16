"""
app/modules/approvals/models.py — Generic approval workflow engine.

Three tables:
  - approval_rules    DoA rules per document_type + amount range
  - approval_workflows  Active workflow per document
  - approval_steps    Individual step decisions
RLS ENABLED on all three.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base


class ApprovalRule(AuditMixin, Base):
    """
    Delegation of authority rule. Evaluated in order of `priority` (ascending).
    If amount is within [min_amount, max_amount], required_role must approve.
    auto_approve_below: if amount < this threshold, auto-approve (no human needed).
    """

    __tablename__ = "approval_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    min_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    max_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    required_role: Mapped[str] = mapped_column(String(50), nullable=False)
    auto_approve_below: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="10")

    def __repr__(self) -> str:
        return f"<ApprovalRule {self.document_type} {self.required_role}>"


class ApprovalWorkflow(AuditMixin, Base):
    """
    Active approval workflow for a single document. One per document.
    """

    __tablename__ = "approval_workflows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    initiated_by: Mapped[str | None] = mapped_column(String, nullable=True)
    initiated_at: Mapped[object | None] = mapped_column(
        __import__("sqlalchemy").DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[object | None] = mapped_column(
        __import__("sqlalchemy").DateTime(timezone=True), nullable=True
    )

    steps: Mapped[list["ApprovalStep"]] = relationship(
        "ApprovalStep",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="ApprovalStep.step_number",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ApprovalWorkflow {self.document_type}/{self.document_id} {self.status}>"


class ApprovalStep(AuditMixin, Base):
    """Individual step in an approval chain. One row per approver per step."""

    __tablename__ = "approval_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    approver_id: Mapped[str | None] = mapped_column(String, nullable=True)
    approver_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    decision_at: Mapped[object | None] = mapped_column(
        __import__("sqlalchemy").DateTime(timezone=True), nullable=True
    )
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    delegated_to: Mapped[str | None] = mapped_column(String, nullable=True)

    workflow: Mapped["ApprovalWorkflow"] = relationship("ApprovalWorkflow", back_populates="steps")
