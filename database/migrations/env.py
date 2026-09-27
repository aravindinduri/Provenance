"""
Alembic migration environment.

Uses a synchronous psycopg2 URL (converted from the asyncpg DATABASE_URL)
so Alembic's DDL operations run synchronously, which is the standard pattern.
"""

import os
import re
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Make backend/ importable when running `alembic` from the repo root ────────
# alembic.ini sets script_location = ../database/migrations which means the
# working directory when running `alembic upgrade head` from backend/ is fine,
# but running from the repo root needs backend/ on the path.
_backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, os.path.abspath(_backend_dir))

# Alembic Config object — gives access to alembic.ini values
config = context.config

# Standard logging setup from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import all models so Alembic autogenerate can detect them ─────────────────
# app.db.models re-exports every ORM class and registers them with Base.metadata.
import app.db.models  # noqa: F401, E402 — side-effect import registers all mappers

from app.db.base import Base  # noqa: E402

target_metadata = Base.metadata


# ── Resolve DATABASE_URL ──────────────────────────────────────────────────────
# Alembic needs a synchronous URL; our app uses asyncpg.
# Convert postgresql+asyncpg:// → postgresql+psycopg2://
def _get_sync_url() -> str:
    # Allow override via env (useful in CI)
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        from app.config import get_settings
        url = get_settings().database_url
    # Replace async driver with sync driver for Alembic
    return re.sub(r"^postgresql\+asyncpg", "postgresql+psycopg2", url)


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (useful for generating SQL scripts)."""
    url = _get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        # Render AS NULL for nullable columns (cleaner diffs)
        render_as_batch=False,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _get_sync_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
