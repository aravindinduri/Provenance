"""
AI module models.

Tables: documents, document_chunks, embeddings, agent_runs

`documents` and `document_chunks` are the corpus for RAG retrieval.
`embeddings` stores pgvector vectors with model + dimension recorded per row
so a model change doesn't corrupt the HNSW index — arch §K.4.

`agent_runs` is the audit trail for every LLM call routed through LLMGateway.

org_id is nullable on documents (NULL = global/public regulatory documents).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base


class Document(AuditMixin, Base):
    """
    A source document that has been chunked and embedded for RAG.

    org_id = NULL for global regulatory/public documents shared across tenants.
    org_id = <uuid> for tenant-uploaded contracts (scoped in retrieval queries).

    Tenant filtering in retrieval is applied in the SQL WHERE clause before
    the vector search — never as a post-filter (arch §K.3).
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    document_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(2), nullable=True)
    published_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    effective_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    language: Mapped[str | None] = mapped_column(String(5), nullable=True)
    source_reliability: Mapped[str | None] = mapped_column(String(10), nullable=True)
    s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} type={self.document_type!r}>"


class DocumentChunk(Base):
    """
    A text chunk from a document, ready for embedding.

    `section_path` records e.g. "Part II / Section 3 / Paragraph 1" for citation.
    Full-text GIN index on content enables hybrid BM25+vector retrieval (arch §K.2).
    """

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    section_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    embeddings: Mapped[list["Embedding"]] = relationship(
        "Embedding", back_populates="chunk", passive_deletes=True
    )


# GIN full-text index on chunk content — enables lexical side of hybrid retrieval
Index(
    "ix_document_chunks_content_fts",
    text("to_tsvector('english', content)"),
    postgresql_using="gin",
)


class Embedding(Base):
    """
    A vector embedding for a document chunk.

    UNIQUE (chunk_id, model) — one embedding per (chunk, model) pair.
    Storing `model` and `dimensions` per row means a model upgrade writes new
    rows alongside old ones and flips a config pointer — no index corruption,
    instant rollback (arch §K.4).

    The HNSW index is a partial index on model='voyage-3' (created in the
    migration with a WHERE clause) so switching models doesn't break the index.

    The `embedding` column uses pgvector's `Vector` type. Because SQLAlchemy
    doesn't ship a native Vector type, we declare it as a custom type in the
    migration and use a Text placeholder here for model discovery purposes.
    The actual column DDL in the migration uses `vector(1024)`.
    """

    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", "model", name="uq_embedding_chunk_model"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    # Actual column type is vector(1024) — overridden in migration DDL.
    # Declared as Text here so Alembic autogenerate sees the column exists.
    # The migration sets the correct type with op.execute() + ALTER COLUMN.
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )

    chunk: Mapped["DocumentChunk"] = relationship(
        "DocumentChunk", back_populates="embeddings"
    )


class AgentRun(Base):
    """
    Audit record for every LLM call routed through LLMGateway.

    Every call writes one row here before returning to the caller.
    `langfuse_trace_id` links to the full trace with prompt+response in Langfuse.
    org_id is nullable for system-level runs (e.g. global entity resolution).
    """

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    # Lightweight references to the inputs/outputs (full payloads are in Langfuse)
    input_ref: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_ref: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    langfuse_trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()"), index=True
    )

    def __repr__(self) -> str:
        return (
            f"<AgentRun id={self.id} agent={self.agent_name!r} "
            f"status={self.status!r}>"
        )
