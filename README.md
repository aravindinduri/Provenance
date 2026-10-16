# Provenance

![Provenance Platform](frontend/public/image.png)

**Autonomous AI Procurement & Supply-Chain Risk Intelligence Platform.**

Provenance combines an end-to-end transactional **Procure-to-Pay (P2P)** operational backbone with real-time **Supply-Chain Risk Intelligence**. It unifies requisitioning, sourcing (RFx), quotation comparison, purchase orders, goods receipts, and multi-tier approval workflows with deterministic supplier graph risk scoring, entity resolution, and an autonomous conversational copilot—**Agent Trace**.

---

## Key Highlights

- **Autonomous Procurement Copilot (Agent Trace):** Natural-language execution for purchasing actions—create material requests, launch RFQs, invite suppliers, compare bid matrices, issue purchase orders, and record goods receipts with full trace observability and citation chains.
- **Complete Procure-to-Pay (P2P) Lifecycle:**
  - **Material Requests (Requisitions):** Sequential numbering (`MR-YYYY-NNNN`), urgency levels, multi-item specifications, and automated approval routing.
  - **Item Master Catalog:** Standardized SKU catalog, unit pricing, lead times, minimum order quantities (MOQ), and preferred vendor links.
  - **Sourcing & RFx Events:** Multi-step RFQ/RFP/RFI wizard, supplier invitation tracking, submission deadlines, and multi-criteria weighted scoring (Price, Quality, Delivery, Risk).
  - **Supplier Quotations & Bid Comparison:** Structured quotation management with side-by-side bid comparison matrices and best-offer identification.
  - **Purchase Orders (PO):** Comprehensive PO management with sequential numbering (`PO-YYYY-NNNN`), multi-line item tracking, payment/delivery terms, and full lifecycle states (`draft` &rarr; `approved` &rarr; `sent` &rarr; `acknowledged` &rarr; `received` &rarr; `closed`).
  - **Purchase Receipts (Goods Receipt Notes - GRN):** Inward delivery inspection (`GRN-YYYY-NNNN`), partial/complete receipts, inspection notes, and accepted vs. rejected quantity tracking against PO lines.
  - **Approvals & Delegation of Authority (DoA):** Configurable multi-tier approval rules based on role and amount thresholds, backed by an auditable approval queue.
- **Supply-Chain Risk Intelligence:**
  - Multi-stage Entity Resolution Cascade (Exact LEI/Tax ID &rarr; Trigram fuzzy matching &rarr; `pgvector` semantic embeddings &rarr; LLM disambiguation) with a human-in-the-loop review queue.
  - Deterministic multi-dimensional risk scoring (regulatory, sanctions, geopolitical, and financial).
  - Interactive multi-tier supply chain graph visualizer (Cytoscape.js) with layout algorithms (`cose`, `concentric`, `breadthfirst`) and sub-tier risk propagation.
  - Evidence-backed alerts with direct source citations and impact radius computations.
- **Strict Zero-Mock / Live Data Architecture:** Every metric card, graph node, table row, and entity is fetched via live API endpoints or direct user input. Operates with authentic loading skeletons and truthful empty states—zero placeholder arrays or fake fallback datasets in runtime code.

---

## Technical Architecture

See [`.agents/architecture.md`](.agents/architecture.md) for the detailed procurement agent specification and architectural roadmap.

### Core Stack

| Layer | Technologies |
|---|---|
| **Frontend** | [Next.js 15](https://nextjs.org/) (App Router), [React 19](https://react.dev/), [TypeScript](https://www.typescriptlang.org/), [Tailwind CSS](https://tailwindcss.com/), [Zustand](https://zustand-demo.pmnd.rs/), [Cytoscape.js](https://js.cytoscape.org/), [Lucide Icons](https://lucide.dev/) |
| **Backend API** | [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12), [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (AsyncIO + asyncpg), [Pydantic v2](https://docs.pydantic.dev/), [Alembic](https://alembic.sqlalchemy.org/), [Structlog](https://www.structlog.org/) |
| **Database & Cache** | [PostgreSQL 16](https://www.postgresql.org/) (`pgvector` for vector embeddings + `pg_trgm` for fuzzy search), [Redis 7](https://redis.io/) |
| **Asynchronous Workers** | [Celery](https://docs.celeryq.dev/) with Celery Beat scheduler |
| **AI & Agentic Framework** | [LangGraph](https://www.langchain.com/langgraph), [LiteLLM](https://github.com/BerriAI/litellm) / Multi-provider gateway (Gemini 2.5 Flash, Claude 3.5 Sonnet, OpenAI GPT-4o), deterministic procurement tool registry |
| **Authentication & Tenancy** | [Clerk](https://clerk.com/) Auth with multi-tenant Row Level Security (RLS) context |
| **Infrastructure & Local Services** | Docker Compose v2, [LocalStack](https://localstack.cloud/) (S3), [MailHog](https://github.com/mailhog/MailHog) (SMTP) |

---

## Quickstart (Local Development)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (with Docker Compose v2)
- [Node.js 20+](https://nodejs.org/)
- [Python 3.12+](https://www.python.org/)

### 1. Clone and Configure

```bash
git clone <repo-url>
cd Provenance
cp .env.example .env
```

Configure your `.env` file. Minimum required variables for local authentication:
```ini
CLERK_SECRET_KEY=sk_test_...
CLERK_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
```
*(All database, redis, and service URLs have operational defaults pre-configured for Docker Compose).*

### 2. Start Services via Docker Compose

```bash
docker compose up -d
```

#### Services Map:
| Service | URL | Description |
|---|---|---|
| **FastAPI Backend** | `http://localhost:8000` | REST API & Interactive OpenAPI Docs (`/docs`) |
| **Next.js Frontend** | `http://localhost:3000` | Web application |
| **PostgreSQL** | `localhost:5432` | Relational store with `pgvector` & `pg_trgm` |
| **Redis** | `localhost:6379` | Cache & Celery message broker |
| **MailHog** | `http://localhost:8025` | Local SMTP capture web interface |
| **LocalStack** | `http://localhost:4566` | Emulated AWS S3 storage |

### 3. Run Database Migrations

Apply Alembic database migrations up to the latest revision (including Phase 1-3 procurement schemas):

```bash
cd backend
pip install -e ".[dev]"
alembic upgrade head
```

### 4. Ingest Authentic Data

Populate the database with authentic enterprise entities, suppliers, catalog items, requisition workflows, approval chains, and supply chain graph relationships:

```bash
# Ingest comprehensive real-world supplier, catalog, and P2P data:
python scripts/ingest_real_world_data.py

# Or seed offline test fixtures:
python scripts/seed_dev_data.py
```

### 5. Verify Health

```bash
curl http://localhost:8000/health
# Response: {"status":"ok","uptime_seconds":...}
```

Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

---

## Project Structure

```
Provenance/
├── frontend/                     # Next.js 15 App Router Frontend
│   └── src/
│       ├── app/
│       │   ├── (auth)/           # Clerk sign-in / sign-up routes
│       │   ├── (dashboard)/
│       │   │   ├── trace/        # Agent Trace Conversational Copilot
│       │   │   ├── dashboard/    # Operational & risk KPI dashboard
│       │   │   ├── material-requests/ # Material Request (MR) list & details
│       │   │   ├── rfx/          # RFQ/RFP creation wizard & bid comparison
│       │   │   ├── quotations/   # Supplier quotations list
│       │   │   ├── purchase-orders/ # Purchase order list & detail views
│       │   │   ├── receipts/     # Goods receipt (GRN) tracking
│       │   │   ├── approvals/    # Approval queue & DoA workflow actions
│       │   │   ├── items/        # Material master item catalog
│       │   │   ├── suppliers/    # Supplier directory & management
│       │   │   ├── alerts/       # Supply chain risk alerts & evidence
│       │   │   ├── graph/        # Cytoscape interactive graph visualizer
│       │   │   └── admin/        # Platform administration & audit
│       ├── components/           # UI, shell, procurement, and graph components
│       └── lib/                  # Stores (Zustand), API client, auth adapters
├── backend/                      # FastAPI Modular Monolith
│   ├── app/
│   │   ├── api/v1/               # Version 1 REST route controllers
│   │   │   ├── material_requests.py
│   │   │   ├── rfx.py
│   │   │   ├── supplier_quotations.py
│   │   │   ├── purchase_orders.py
│   │   │   ├── goods_receipts.py
│   │   │   ├── approvals.py
│   │   │   ├── items.py
│   │   │   ├── investigate.py
│   │   │   ├── suppliers.py
│   │   │   ├── graph.py
│   │   │   └── alerts.py
│   │   ├── modules/              # Domain modules (models, schemas, repo, service)
│   │   │   ├── procurement/      # Material requests & requisitioning
│   │   │   ├── rfx/              # Sourcing lifecycle & bid evaluation
│   │   │   ├── purchase_orders/  # PO lifecycle & line-item tracking
│   │   │   ├── goods_receipts/   # GRN inspection & receipt management
│   │   │   ├── items/            # Items / material master
│   │   │   ├── approvals/        # DoA approval engine & rules
│   │   │   ├── ai/               # Investigation agent & procurement tools
│   │   │   ├── risk/             # Deterministic risk engine
│   │   │   └── spend/            # Spend records, contracts & leakage models
│   │   ├── auth/                 # Clerk JWT verification & tenancy guards
│   │   ├── core/                 # Logging, middleware, error handlers, rate limiting
│   │   └── db/                   # Async session factory, Base model, RLS context
├── database/                     # Migrations & database seeds
│   └── migrations/versions/      # Alembic migration revisions (0001 - 0004)
├── ingestion/                    # Regulatory & news ingestion pipelines
├── workers/                      # Celery application, task queues, and Beat schedules
├── infrastructure/               # Dockerfiles (api, worker, frontend) & deployment configs
├── tests/                        # Pytest unit, integration, and security test suites
└── scripts/                      # Data ingestion, dev seeding, and utility scripts
```

---

## Agent Trace: Autonomous Procurement Copilot

Provenance features **Agent Trace**, an autonomous AI copilot embedded directly into the procurement workflow:

- **Conversational Action Execution:** Users can trigger transactional actions in natural language:
  - *"I need 500 units of stainless steel sheet 304 for the plant by next month."* &rarr; Checks item catalog, identifies preferred suppliers, evaluates supplier risk, creates Material Request `MR-YYYY-NNNN`, and routes for approval.
  - *"Create an RFQ for that requisition and invite our top steel suppliers."* &rarr; Creates `RFQ-YYYY-NNNN`, attaches specifications, and sends invitations.
  - *"Compare the quotations received for RFQ-2026-0001."* &rarr; Produces side-by-side bid analysis with weighted scoring across pricing, delivery terms, quality, and risk.
  - *"Generate Purchase Order for the winning supplier."* &rarr; Validates approved requisition/quotation and issues `PO-YYYY-NNNN`.
  - *"Record arrival of 490 units on PO-2026-0001 with 10 units rejected."* &rarr; Creates Goods Receipt Note `GRN-YYYY-NNNN` with inspection notes.
- **Trace Observability:** Every reasoning step, tool call parameter, and result is rendered in real time.
- **Conversation Management:** Chat sessions are saved with title summarization, multi-chat navigation, and deletion controls.

---

## Implementation Roadmap & Status

### Core & Risk Intelligence Platform

| Phase | Milestone | Status | Description |
|---|---|---|---|
| 1 | Platform Setup | ✅ Complete | Docker Compose stack, FastAPI factory, `/health`, CI |
| 2 | Core Database Schema | ✅ Complete | PostgreSQL schema, Alembic migration `0001`, RLS policies |
| 3 | Auth & Multi-Tenancy | ✅ Complete | Clerk authentication, user store, tenant context & RBAC |
| 4 | Core Master Data APIs | ✅ Complete | CRUD endpoints for organizations, companies, suppliers, relationships |
| 5 | Modern Frontend Shell | ✅ Complete | Next.js 15 App Router, responsive collapsible sidebar, theme tokens |
| 6 | Supplier Directory & Bulk | ✅ Complete | Supplier directory, CSV bulk import, supplier details |
| 7 | Graph Visualizer | ✅ Complete | Cytoscape interactive graph, tier traversal, layout algorithms |
| 8 | Event Ingestion | ✅ Complete | External event ingestion pipeline with deduplication & circuit breakers |
| 9 | Entity Resolution | ✅ Complete | 4-stage resolution cascade (Exact, Trigram, Vector, LLM) + Review Queue |
| 10 | AI Investigation Engine | ✅ Complete | Multi-tool investigation agent, vector search, streaming traces |
| 11 | Deterministic Risk Scoring | ✅ Complete | Composite scoring across regulatory, sanctions, and network graph |
| 12 | Evidence-Backed Alerts | ✅ Complete | Real-time alert feed with citations, impact analysis, and notifications |
| 13 | Notifications | ✅ Complete | In-app notification bell, unread counts, and email handlers |

### Procurement (P2P) Backbone

| Phase | Milestone | Status | Description |
|---|---|---|---|
| **P1** | **Procurement Foundation** | ✅ Complete | Item Master Catalog (`items`), Material Requests (`material_requests`), DoA Rules & Approval Engine (`approvals`), Alembic migration `0002` |
| **P2** | **Sourcing & Quotations** | ✅ Complete | RFx events (`rfx_events`), supplier invitations, quotation submissions (`rfx_responses`), side-by-side bid comparison, Alembic migration `0003` |
| **P3** | **Order-to-Receipt** | ✅ Complete | Purchase Orders (`purchase_orders`), PO lifecycle states, Goods Receipts (`goods_receipts`), Alembic migration `0004` |
| **P4** | **Invoicing & 3-Way Matching** | 🗓️ Planned | Invoice processing (`invoices`), deterministic 2-way/3-way matching engine against PO and GRN, price/quantity variance exceptions |
| **P5** | **Analytics & Scorecards** | 🗓️ Planned | Spend cube aggregations, category breakdowns, savings tracking, and automated supplier scorecards |
| **P6** | **Integrations & Automation** | 🗓️ Planned | Automated end-to-end P2P pipeline, webhooks, and ERP sync |

---

## Running Tests

### Frontend Test Suite (Vitest & Testing Library)

```bash
cd frontend
npm test
```

Runs all component, shell, and user store tests in Vitest.

### Backend Test Suite (Pytest)

```bash
# Inside the backend environment or Docker container:
cd backend
pytest tests/
```

### End-to-End Tests (Playwright)

```bash
cd frontend
npx playwright test
```

---

## Architecture Guarantees & Enforcement

The codebase strictly enforces the following engineering constraints:

| Rule | Description | Enforcement |
|---|---|---|
| **Zero Mock Data** | No hardcoded dummy arrays, mock topologies, or fake fallback metrics in runtime code. All UI data originates from live APIs or user input. | Automated test suites & code review |
| **Clean Headers & Navigation** | No artificial live-feed badges, pulsing count pills, or fabricated source counters anywhere in the UI. | System design guidelines |
| **Deterministic Risk Engine** | `modules/risk` is deterministic and cannot import LLM agent modules. | `import-linter` in CI |
| **Ingestion Pipeline Isolation** | `ingestion/pipeline` deduplication cannot import LLM agent modules. | `import-linter` in CI |
| **AI Provider Abstraction** | No domain module imports `litellm` directly; all calls route through the AI provider gateway. | `import-linter` in CI |
| **Tenant Isolation** | Strict PostgreSQL Row Level Security (RLS) and tenant-context middleware. | Security test suite (`tests/security/`) |

---

## License

Private. All rights reserved.
