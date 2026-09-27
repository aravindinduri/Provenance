-- init.sql — runs once on first postgres container start (docker-entrypoint-initdb.d)
-- Enables the extensions required by the schema.
-- Alembic migrations handle all table creation; this file only sets up extensions.

CREATE EXTENSION IF NOT EXISTS vector;        -- pgvector
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- fuzzy name matching
CREATE EXTENSION IF NOT EXISTS pg_stat_statements; -- query performance
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- gen_random_uuid() fallback
