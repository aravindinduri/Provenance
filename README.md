# Provenance

Supply-chain risk intelligence platform. Monitors regulatory, sanctions, and geopolitical signals; resolves them against your supplier graph; scores business impact deterministically; and delivers cited, evidence-backed alerts to Supply Chain Risk Managers and Category Managers.

## Architecture

See [`.agents/architecture/architecture.md`](.agents/architecture/architecture.md) for the full technical specification.

**Stack:** Next.js 15 · FastAPI · PostgreSQL 16 (pgvector + pg_trgm) · Redis 7 · Celery · LangGraph · LiteLLM · Clerk · AWS (ECS Fargate + RDS + S3)

## Quickstart (local dev)

### Prerequisites

- Docker Desktop (with Compose v2)
- Python 3.12
- Node.js 20

### 1. Clone and configure

```bash
git clone <repo>
cd Provenance
cp .env.example .env
# Edit .env — at minimum set CLERK_SECRET_KEY and CLERK_PUBLISHABLE_KEY
# All other values have working local defaults via Docker Compose
```

### 2. Start services

```bash
docker compose up
```

This starts:
| Service | URL |
|---|---|
| FastAPI backend | http://localhost:8000 |
| Next.js frontend | http://localhost:3000 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |
| MailHog (email) | http://localhost:8025 |
| LocalStack (S3) | http://localhost:4566 |

### 3. Run migrations

```bash
cd backend
pip install -e ".[dev]"
alembic upgrade head
```

### 4. Seed dev data

```bash
python scripts/seed_dev_data.py
```

Creates two tenants with a supplier graph and recorded source fixtures so the pipeline runs fully offline.

### 5. Verify

```bash
# Liveness
curl http://localhost:8000/health
# → {"status":"ok","uptime_seconds":...}

# API docs (local only)
open http://localhost:8000/docs
```

## Running tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test

# E2E (requires running stack)
cd frontend
npx playwright test
```

## Project structure

```
provenance/
├── frontend/          Next.js 15 app
├── backend/           FastAPI modular monolith
│   └── app/
│       ├── api/v1/    Route handlers
│       ├── core/      Shared middleware, logging, deps
│       ├── auth/      TokenVerifier + Clerk provider
│       ├── modules/   Domain modules (organizations, companies, graph, …)
│       └── db/        Session, Redis, base model
├── ingestion/         Source connectors + pipeline stages
├── agents/            LangGraph agents, prompts, RAG
├── workers/           Celery app + task modules + Beat schedules
├── database/          Alembic migrations + seeds
├── infrastructure/    Dockerfiles + Terraform
├── tests/             unit / integration / e2e / security / evals
└── scripts/           seed_dev_data.py, verify_sources.py
```

## Implementation phases

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Complete | Project setup, Docker Compose, `/health`, CI |
| 2 | Pending | Full DB schema + Alembic migrations + RLS |
| 3 | Pending | Clerk auth, tenant context, RBAC |
| 4 | Pending | Backend CRUD APIs (orgs, companies, suppliers, relationships) |
| 5 | Pending | Frontend shell + generated API client |
| 6 | Pending | Onboarding wizard + CSV bulk upload |
| 7 | Pending | Graph traversal + Cytoscape visualization |
| 8 | Pending | Data ingestion (9 Tier-1 connectors) |
| 9 | Pending | Entity resolution cascade + review queue |
| 10 | Pending | AI analysis (event extraction, RAG, semantic dedupe) |
| 11 | Pending | Deterministic risk scoring engine |
| 12 | Pending | Alerts with evidence chains + explanation agent |
| 13 | Pending | Notifications (email + in-app + digest batching) |
| 14 | Pending | Document ingestion + spend leakage detection |
| 14b | Pending | Should-cost & price-claim check (FRED/ECB/World Bank) |
| 15 | Pending | Admin portal + full observability |
| 16 | Pending | Security hardening |
| 17 | Pending | Test completion + load testing |
| 18 | Pending | Terraform deployment + CI/CD to production |

## Engineering rules enforced by tooling

| Rule | Enforcement |
|---|---|
| `modules/risk` cannot import `agents` (LLM) | import-linter in CI |
| `ingestion/pipeline` cannot import `agents` | import-linter in CI |
| No module imports `litellm` directly | import-linter in CI |
| Every alert requires evidence | DB `CHECK` constraint |
| Secrets never in code | gitleaks pre-commit + CI |
| Tenant isolation | RLS + repository guard + blocking CI security suite |

## Licence

Private. All rights reserved.
