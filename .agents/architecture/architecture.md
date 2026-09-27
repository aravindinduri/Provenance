# Provenance — Technical Specification & Implementation Blueprint

**Version:** 1.0
**Status:** Implementation-ready
**Audience:** AI coding agent + engineering team
**Purpose:** Single source of truth for building Provenance end to end.

---

# PART A — ANALYSIS OF EXISTING PROJECT CONTEXT

## A.1 The Business Problem (restated from context)

Manufacturers with multi-tier, multi-country supply chains learn about supply disruptions **reactively** — from a supplier email or a late shipment — days or weeks after the triggering event (an export ban, a quota, a sanction, a supplier's financial distress) became public.

Existing ERP and S2P platforms (SAP Ariba, JAGGAER, Coupa, Zycus, GEP, Ivalua) track unit cost, lead time, contracts, and supplier scorecards. They do **not** track country-of-origin risk at the material level, and their built-in AI (JAGGAER's JAI, Zycus's Merlin) is grounded in the customer's **internal** data and policies — not the open internet.

The gap Provenance fills: **connect an external event to internal exposure**, with a cited evidence chain from regulation → material/supplier → part → dollars, and surface it to the right role before the disruption lands.

## A.2 Primary Users (confirmed from context)

| Persona | Core question | Decision they make |
|---|---|---|
| **Supply Chain Risk Manager** | "What changed externally, and what does it threaten?" | Escalate / pre-qualify alternate / watch |
| **Category Manager** | "Given what changed, what do I do in my category?" | Resource / consolidate / hold |

Secondary (platform, not domain): **Org Admin**, **Platform Admin**.

Explicitly **not** targeted (validated in context — incumbents already serve these well): AP Specialist (JAGGAER autonomous AP is mature), tactical Buyer, Contract Manager.

## A.3 Core Entities

`Organization` (tenant + the modelled companies), `Company` (canonical entity — supplier, sub-supplier, parent), `SupplierRelationship` (edge), `Location`, `Product/Part`, `Material`, `BillOfMaterials`, `SourceRecord` (raw ingested item), `Event` (normalized), `RiskAssessment`, `Alert`, `Evidence/Citation`, `SpendRecord`, `Contract`, `SpendLeakageFinding`, `AgentRun`, `AuditLog`.

## A.4 Deterministic vs. AI — the single most important architectural split

**The default is deterministic.** An LLM is used only where the input is unstructured natural language and the output requires semantic judgment.

| Task | Implementation | Why |
|---|---|---|
| Graph traversal (which suppliers are exposed) | **Deterministic** — recursive SQL | Exact, fast, auditable, testable. An LLM here would be slower, costlier, and non-reproducible |
| Risk score arithmetic | **Deterministic** — weighted formula in Python | Scores must be reproducible and explainable. LLMs must never compute numbers that drive alerts |
| Spend leakage detection (duplicates, price variance, tail spend) | **Deterministic** — SQL + rules | These are exact comparisons against contract terms; no judgment needed |
| Deduplication of source records | **Deterministic** — content hashing + URL canonicalization | Idempotency requirement |
| Entity resolution: exact/identifier/domain match | **Deterministic** — indexed lookups | High precision, zero cost |
| Entity resolution: ambiguous band only | **AI-assisted** | Only the 5–15% of cases the deterministic cascade can't settle |
| Extracting structured event data from a news article / regulatory notice | **LLM** | Unstructured text → schema. Genuine NLP task |
| Classifying event type and severity | **LLM** with constrained output enum | Semantic judgment over prose |
| Parsing invoices/POs/contracts (PDF) | **LLM** (vision/text) | Layouts vary too much for templates |
| Writing the human-readable alert explanation | **LLM** | Natural-language generation, grounded in already-computed facts |
| Answering "why was X flagged?" | **LLM + RAG over the evidence chain** | Conversational retrieval |

**Rule enforced throughout:** the LLM never *decides* whether an alert fires. Deterministic code computes the score and the threshold; the LLM classifies inputs and explains outputs.

## A.5 Requirement Classification

### Confirmed (from project context)
- Two target personas with role-specific outputs
- External regulatory/geopolitical monitoring + financial-distress monitoring
- Exposure trace from event → material/supplier → part → dollars
- Document upload (PDF invoices, POs, contracts; CSV/Excel spend exports)
- Spend leakage detection (tail spend, duplicate payments, price variance, missed discounts)
- `regulatory_overlap` compound flag — leakage that coincides with live risk
- Every claim carries a citation with `live` vs `cached` source typing
- **No autonomous action** — recommend only, human decides
- Least-privilege tool scoping per agent
- Prompt-injection handling: all fetched content is untrusted data
- Confidence thresholds; below-threshold findings labelled "needs human judgment"

### Recommended (my additions, with reasoning)
- **Multi-tenancy from day one** — the context implies a product, not an internal tool; retrofitting tenant isolation is the single most expensive refactor in this class of system.
- **Canonical `Company` registry separate from tenant-scoped `SupplierRelationship`** — required to reuse entities across tenants without leaking who-supplies-whom (see §7, §12.6). The original context did not address this and it is a **hard privacy requirement**.
- **GLEIF LEI as the primary global entity identifier** — free, CC0, includes Level 2 parent/subsidiary relationships that seed the graph directly.
- **Deterministic risk scoring with LLM-classified inputs**, not an LLM-generated score.
- **A `needs_review` state for both entity resolution and document parsing** — nothing silently guessed into the model.
- **Digest-first notification default** — immediate email only above a severity threshold; prevents the alert fatigue that kills this category of product.

### Assumptions requiring validation before/during build
| # | Assumption | How to validate | Risk if wrong |
|---|---|---|---|
| A1 | Users will supply a supplier list at onboarding (CSV or manual) | 3 pilot onboardings | Cold-start: no graph, no alerts. Mitigation: GLEIF-seeded search + "add your top 20 suppliers" wizard |
| A2 | Users will **not** have clean BOM data at signup | Pilot interviews | Determines whether BOM-level tracing is MVP or Phase 2. **I assume they will not** — see A.6 |
| A3 | GDELT's 3-month rolling window and ~1 req/5s limit is sufficient for news coverage | Load test against 500-supplier tenant | May force a paid news provider earlier than planned |
| A4 | Supplier names in user uploads are messy but resolvable | Run ER cascade on pilot data, measure auto-resolve rate | If auto-resolve < 70%, review queue becomes unusable |
| A5 | No customer PII beyond business-contact data in uploaded invoices | Sample pilot documents | Changes DPDP/GDPR posture materially |

### Future enhancements (explicitly out of MVP)
Neo4j migration, streaming ingestion (Kafka), licensed commodity feeds (Fastmarkets, Benchmark Mineral Intelligence), live ERP connectors (SAP/Oracle APIs), action execution with approval workflow, mobile app, multi-language UI.

## A.6 Gaps, Risks, and Where I Am Changing the Original Concept

**Change 1 — BOM-level tracing moves from MVP to Phase 2.**
The context treats the material → BOM → part → supplier → dollars trace as the core differentiator. It is. But it requires BOM data that **almost no prospect will have in a clean, uploadable form on day one**. Building MVP around it guarantees an empty product at first login.

**Resolution:** MVP ships the **organization → supplier → sub-supplier → location** graph, which can be populated in minutes from a supplier list plus GLEIF enrichment. The event→exposure trace runs over *that* graph (supplier-level exposure, spend-level dollars from uploaded spend data). BOM depth is added in Phase 2 for tenants who have the data. The differentiator is preserved; the cold-start problem is solved.

**Change 2 — "Financial news" is scoped to structured distress signals, not general financial news.**
"Monitor financial news" is unbounded. What actually drives a procurement decision is a small set of discrete signals: insolvency/bankruptcy filings, credit-rating actions, going-concern disclosures, and material adverse events. MVP monitors these via targeted GDELT queries + regulatory filing sources, classified into a closed `financial_event_type` enum. General market/stock data is **optional and excluded from MVP** — share price movement is a weak, noisy predictor of supply disruption and would degrade precision.

**Change 3 — No dedicated graph database in MVP.** See §8. PostgreSQL recursive CTEs handle depth-3 traversal over realistic tenant sizes at sub-100ms. Neo4j is a Phase 3 decision gated on measured query latency, not an upfront choice.

**Change 4 — The five-agent design is reduced to four LLM-backed agents plus deterministic services.** The original v4 design had Document Ingestion, Regulatory Intelligence, Exposure Analysis, Spend Intelligence, Risk Escalation, Sourcing Recommendation. Of these, **Exposure Analysis and Spend Intelligence are deterministic** — they are SQL traversal and SQL rule evaluation. Making them "agents" adds LLM cost, latency, and non-determinism to tasks with exact answers. They become services. See §10.

**Risk register** is in §36.

---

# PART B — THE PRODUCT

## B.1 What the Application Does

Provenance is a multi-tenant SaaS platform that:
1. Lets an organization model its supply base as a graph (suppliers, sub-suppliers, parents, locations, and — Phase 2 — products and materials).
2. Continuously ingests external regulatory, trade, sanctions, and financial-distress signals from official sources.
3. Resolves entities mentioned in those signals against the canonical company registry.
4. Determines, deterministically, whether a resolved entity intersects a tenant's graph.
5. Scores business impact using a transparent weighted model.
6. Generates alerts with a full, inspectable evidence chain.
7. Notifies the right persona through the right channel at the right urgency.
8. Lets users interrogate any alert conversationally ("why was this flagged?") with cited answers.
9. Separately, ingests the tenant's own spend documents and flags leakage — tagging findings that coincide with live external risk.

## B.2 Core User Journeys

### J1 — Onboarding (first 15 minutes, the make-or-break journey)
```
Sign up (OIDC) → create Organization (tenant)
  → search & claim own company from GLEIF/registry  [entity resolution]
  → add suppliers: CSV upload OR typeahead search OR manual
      each name → ER cascade → auto-matched | review queue
  → GLEIF Level-2 enrichment auto-adds parents/subsidiaries as suggested nodes
  → user confirms/rejects suggestions
  → set criticality (1-5) + optional annual spend per supplier
  → backfill scan runs over last 30 days of events
  → first alerts appear within ~5 minutes
```
**Design requirement:** the user must see at least one real, relevant alert in the first session. The 30-day backfill exists specifically to guarantee this.

### J2 — Daily/weekly monitoring
```
Scheduled ingestion → normalize → dedupe → extract → resolve entities
  → graph intersection check → impact score → threshold
  → alert created → notification (immediate if ≥ HIGH, else digest)
  → user opens alert → reads evidence chain → marks Reviewed / Escalated / Dismissed
  → dismissal reason feeds false-positive metrics
```

### J3 — Investigation
```
User opens alert → "Why does this affect us?"
  → Investigation Agent, RAG over: this alert's evidence, the tenant's graph,
    prior related events
  → cited answer, every claim linked to a source_record or graph edge
```

### J4 — Spend intelligence
```
Upload invoices/POs/contracts/spend export → parse (agent) → normalize
  → deterministic leakage rules → findings
  → cross-check each finding against open RiskAssessments for the same supplier
  → regulatory_overlap = true → surfaced in both personas' views
```

## B.3 Feature Inventory

**Main:** supplier graph CRUD + visualization; continuous multi-source monitoring; entity resolution with review queue; deterministic impact scoring; evidence-chained alerts; role-scoped dashboards; conversational investigation; document ingestion; spend leakage detection; notifications (in-app, email, Slack/Teams).

**Secondary:** saved views/filters; alert assignment & workflow states; weekly digest; CSV/PDF export of an alert's evidence chain; watchlists (monitor a company not yet in the graph); supplier comparison.

**Admin (platform):** tenant management; data-source configuration & health; API credential rotation; prompt version management; model routing config; alert-rule thresholds; ER review queue oversight; failed-job replay; AI cost & token dashboards; full audit log search.

**AI capabilities:** event extraction & classification; ambiguous entity adjudication; alert explanation generation; conversational investigation (RAG); document parsing; recommendation drafting (role-scoped, never executing).

---

# PART C — TECHNOLOGY STACK (concrete choices)

## C.1 Frontend

| Layer | Choice | Reasoning |
|---|---|---|
| Framework | **Next.js 15 (App Router)** | SSR for fast first paint on data-heavy dashboards; mature auth middleware; single deployable; the ecosystem a coding agent knows best |
| Language | **TypeScript 5.x, `strict: true`** | Type safety across the API boundary via generated client |
| UI | **Tailwind CSS 4 + shadcn/ui (Radix primitives)** | Accessible primitives, owned source (no version-lock on a component vendor), fast to build dense enterprise UI |
| Server state | **TanStack Query v5** | Caching, background refetch, pagination — alert lists are polled and paginated constantly |
| Client state | **Zustand** | Small, for UI-only state (filters, panel open/closed). No Redux — unwarranted ceremony |
| Routing | Next.js App Router (file-based) | Built in |
| Forms | **React Hook Form + Zod** | Zod schemas shared with the generated API types; one validation definition |
| Graph viz | **Cytoscape.js** (via `react-cytoscapejs`) | Purpose-built for node-edge graphs; handles 1–5k nodes with `cose-bilkent`/`dagre` layouts; far better fit than D3-from-scratch or vis-network. **Not** react-flow — that is an editor for diagrams, not a graph-analysis renderer |
| Charts | **Recharts** | Sufficient for KPI trends; no need for D3 complexity |
| API client | **openapi-typescript + openapi-fetch**, generated from FastAPI's OpenAPI schema in CI | Eliminates hand-written client drift. Non-negotiable |
| Auth integration | Clerk Next.js SDK (`@clerk/nextjs`) | See C.3 |
| Error handling | React Error Boundaries per route segment + **Sentry** browser SDK | |
| Testing | **Vitest** (unit), **React Testing Library** (component), **Playwright** (E2E) | |

## C.2 Backend

| Layer | Choice | Reasoning |
|---|---|---|
| Language | **Python 3.12** | The AI/agent ecosystem (LangGraph, LiteLLM, instructor, pgvector clients) is Python-first. Splitting into a TS API + Python workers doubles the deployment surface for no gain |
| Framework | **FastAPI** | Native async, Pydantic v2 validation, automatic OpenAPI generation (which the frontend client is generated from), dependency-injection system that maps cleanly onto tenant scoping |
| API style | **REST + JSON**, OpenAPI 3.1 | GraphQL is rejected: the access patterns are known and few; GraphQL would add resolver-level authorization complexity — precisely where multi-tenant leaks happen |
| Structure | **Modular monolith**, package-per-domain, enforced import boundaries | Microservices at MVP would be a distributed-systems tax with one team. The module boundaries below are drawn so services can be extracted later without rewriting |
| ORM | **SQLAlchemy 2.0 (async) + Alembic** | Mature migrations; raw SQL escape hatch for the recursive CTEs |
| Validation | **Pydantic v2** everywhere — request, response, LLM structured output, config | One validation system end to end |
| Background jobs | **Celery 5 + Redis broker** | Mature, well-understood by coding agents, supports retries/backoff/DLQ natively, rate-limiting per task |
| Scheduling | **Celery Beat** with `django-celery-beat`-style DB scheduler (`celery-sqlalchemy-scheduler`) | Schedules configurable at runtime from the admin portal rather than baked into code |
| Rate limiting | **SlowAPI** (per-tenant + per-IP) backed by Redis | |
| Outbound HTTP | **httpx** async + **tenacity** for retry/backoff | |
| Errors | RFC 9457 `application/problem+json` | Machine-readable errors for the typed client |

## C.3 Authentication

**Choice: Clerk** for MVP, behind a `TokenVerifier` abstraction.

Reasoning: Clerk ships **organizations, org-scoped roles, invitations, MFA, and SAML SSO** as first-class primitives. Building these on Auth.js or raw OIDC is 3–5 weeks of work that is pure undifferentiated overhead. Enterprise procurement buyers *will* demand SAML SSO into their IdP; having it available by config rather than by project is decisive.

**Exit path (required, not optional):** all Clerk-specific code lives in `backend/app/auth/providers/clerk.py` implementing `TokenVerifier`. Application code consumes only `CurrentUser(user_id, org_id, role, permissions)`. Swapping to **Keycloak** (self-hosted, Phase 3, for customers who demand data residency) is one new provider implementation.

## C.4 Database

**Primary: PostgreSQL 16.** Single database, multiple schemas. Justification per requirement:

| Requirement | Mechanism | Why not a separate system |
|---|---|---|
| Relational core | Standard tables, FK constraints | — |
| Semi-structured payloads (raw API responses, LLM outputs) | **JSONB** columns with GIN indexes | Avoids a document DB. Postgres JSONB is faster than MongoDB for this access pattern and keeps transactional consistency with relational rows |
| Graph | **Adjacency table + recursive CTEs** | See §8 — full analysis |
| Full-text search | **Postgres FTS** (`tsvector` + GIN) for alerts/events; **pg_trgm** for fuzzy name matching | Elasticsearch is unjustified at MVP volume; adds a cluster to operate and a sync pipeline to keep consistent |
| Vector search | **pgvector 0.7+** with HNSW indexes | A dedicated vector DB (Pinecone/Weaviate/Qdrant) means a second datastore, a sync pipeline, and cross-store transactions. At MVP corpus size (low hundreds of thousands of chunks) pgvector's HNSW is more than adequate, and keeping embeddings in the same transaction as their source record is a correctness win |
| Caching / queue | **Redis 7** | Celery broker + response cache + rate-limit counters + dedupe bloom |
| Object storage | **S3** | Raw documents, raw API payload archives, generated exports |

**Explicitly rejected for MVP:** Neo4j, Elasticsearch, Pinecone, Kafka, MongoDB. Each is a defensible Phase 3 addition gated on a measured threshold (§33).

## C.5 AI / LLM Layer

| Concern | Choice | Reasoning |
|---|---|---|
| Provider abstraction | **LiteLLM** (Python SDK, not the proxy, for MVP) | One interface over Anthropic/OpenAI/Bedrock/Vertex. Model switch = config change. Satisfies the "keep AI providers replaceable" rule literally |
| Default models | **Claude Sonnet** class for extraction/classification/explanation; **Claude Haiku** class for high-volume cheap classification (severity pre-filter); escalate to **Opus** class only for the ER adjudication and investigation agent | Cost tiering by task. Configured in `model_routing.yaml`, not hardcoded |
| Structured output | **instructor** + Pydantic models, with `tool_use`/JSON-schema mode | Never parse free text. Validation failure → retry with error fed back → 2 retries → `needs_review` |
| Embeddings | **Voyage `voyage-3`** (or OpenAI `text-embedding-3-large`) via LiteLLM | Abstracted; dimension recorded per-row so a model change doesn't corrupt the index (see §14 `embeddings.model` + partial indexes) |
| Agent framework | **LangGraph** | Explicit state machine, checkpointing, conditional edges. Matches the pipeline shape and makes runs replayable — which the audit requirement demands |
| Prompt management | **Versioned files in `agents/prompts/`**, loaded by ID+version, recorded on every `AgentRun` | Prompts in the DB are unreviewable; prompts in code are versioned by Git. Admin portal can pin a version, not edit free text |
| Observability | **Langfuse** (self-hostable) | Traces every LLM call with cost, latency, prompt version, and input/output — needed for the cost and eval requirements |
| Evaluation | **promptfoo** for prompt-level regression + custom pytest eval harness over golden datasets | §30 |
| Guardrails | Structured output + allow-listed enums + citation-required validators + injection sentinels | §17.7 |
| Cost control | Per-tenant monthly token budget enforced in `LLMGateway`; cheap-model pre-filter before expensive calls; aggressive caching of identical extractions by content hash | §21 |

## C.6 Infrastructure

**Cloud: AWS** (single account for MVP, `ap-south-1` primary given the India context + a US/EU region when a customer requires residency).

| Component | Service | Sizing (MVP) |
|---|---|---|
| Compute — API | ECS Fargate, 2 tasks, 1 vCPU / 2 GB | Behind ALB |
| Compute — Workers | ECS Fargate, 2 tasks, 1 vCPU / 4 GB | Separate queues: `ingest`, `ai`, `notify` |
| Database | RDS PostgreSQL 16, `db.t4g.medium`, 100 GB gp3, single-AZ MVP → **Multi-AZ before first paying customer** | pgvector + pg_trgm extensions |
| Cache/Broker | ElastiCache Redis 7, `cache.t4g.micro` | |
| Object storage | S3, versioning on, SSE-KMS | Lifecycle: raw payloads → Glacier at 90d |
| Scheduler | Celery Beat in a dedicated single-task service | Not EventBridge — keeps scheduling logic in one place and runtime-configurable |
| Secrets | **AWS Secrets Manager**, injected as ECS task secrets | Never env-file-in-image |
| Container registry | ECR | |
| CDN/Frontend | **Vercel** for Next.js | Purpose-built; avoids hand-rolling Next.js on ECS. Accept the second vendor — the alternative costs weeks |
| Logs/Metrics | CloudWatch → **Grafana Cloud** (OTLP) | |
| Errors | **Sentry** (backend + frontend) | |
| LLM traces | **Langfuse** | |
| IaC | **Terraform** | |
| CI/CD | **GitHub Actions** | |
| Local dev | **Docker Compose** | §28 |

---

# PART D — SYSTEM ARCHITECTURE

## D.1 Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│  CLIENT                                                               │
│  Next.js 15 (Vercel) — Dashboard │ Graph │ Alerts │ Suppliers │      │
│                        Investigate │ Data │ Admin                     │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ HTTPS, Bearer JWT (Clerk)
┌───────────────────────────▼──────────────────────────────────────────┐
│  EDGE — AWS ALB → ECS Fargate (api)                                   │
│  FastAPI: CORS │ RateLimit │ AuthN │ TenantContext │ AuditMiddleware  │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────────┐
│  APPLICATION MODULES (modular monolith, one process)                  │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐      │
│  │ organizations│ companies    │ graph        │ events       │      │
│  │ (tenants,    │ (canonical   │ (edges,      │ (normalized  │      │
│  │  members)    │  registry,ER)│  traversal)  │  events)     │      │
│  ├──────────────┼──────────────┼──────────────┼──────────────┤      │
│  │ risk         │ alerts       │ spend        │ notifications│      │
│  │ (scoring —   │ (lifecycle,  │ (docs,       │ (channels,   │      │
│  │  DETERMINISTIC)│ evidence)  │  leakage)    │  prefs)      │      │
│  ├──────────────┴──────────────┴──────────────┴──────────────┤      │
│  │ ai (LLMGateway, agents, RAG)  │  admin  │  audit          │      │
│  └───────────────────────────────┴─────────┴─────────────────┘      │
└───────┬──────────────────────────────────────────┬──────────────────┘
        │                                          │
        │ enqueue                                  │ read/write
┌───────▼───────────────────────┐   ┌──────────────▼──────────────────┐
│  WORKERS (ECS, Celery)         │   │  DATA LAYER                     │
│  queues: ingest │ ai │ notify  │   │  PostgreSQL 16                  │
│  Celery Beat (schedules)       │   │   + pgvector + pg_trgm + FTS    │
└───────┬───────────────────────┘   │  Redis 7 (broker,cache,ratelimit)│
        │                            │  S3 (raw payloads, documents)   │
        │                            └─────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────────────────────────────┐
│  INGESTION PIPELINE (per-source connector → shared stages)            │
│                                                                       │
│  Connector ─► RawStore(S3+source_records) ─► Normalize ─► Dedupe      │
│      │                                                    │           │
│      │                                                    ▼           │
│      │                           Extract (LLM) ─► EntityResolve       │
│      │                                                    │           │
│      │                                                    ▼           │
│      │                          GraphIntersect (SQL, deterministic)   │
│      │                                                    │           │
│      │                                                    ▼           │
│      │                          RiskScore (deterministic formula)     │
│      │                                                    │           │
│      │                                                    ▼           │
│      │                     Threshold? ─► Alert ─► Explain (LLM)       │
│      │                                                    │           │
│      └────────────────────────────────────────────────────▼           │
│                                                    Notify (channels)  │
└──────────────────────────────────────────────────────────────────────┘
        ▲
        │
┌───────┴──────────────────────────────────────────────────────────────┐
│  EXTERNAL SOURCES                                                     │
│  OFAC SLS │ EU/UN/UK sanctions │ GLEIF │ GDELT DOC 2.0 │ Federal      │
│  Register │ EUR-Lex │ WTO EPING │ data.gov.in │ DGFT/CBIC (HTML)      │
└──────────────────────────────────────────────────────────────────────┘
```

## D.2 Component Contracts

For each module: responsibility, inputs, outputs, DB, auth, failure, scaling.

### organizations
- **Responsibility:** tenants, membership, roles, org settings, notification preferences.
- **In:** authenticated user context, org CRUD payloads. **Out:** org records, membership lists.
- **DB:** `organizations`, `organization_members`, `org_settings`.
- **Auth:** every read/write filtered by `org_id` from token; role ≥ `org_admin` for mutations.
- **Failure:** pure CRUD; standard 4xx/5xx. No external dependency.
- **Scaling:** stateless; read-through Redis cache on `org_settings` (TTL 60s).

### companies (canonical registry + entity resolution)
- **Responsibility:** the **global, cross-tenant** canonical company registry; ER cascade; review queue; GLEIF/registry enrichment.
- **In:** raw name strings (from user upload or event extraction), optional identifiers/domain/country. **Out:** `company_id` + `confidence` + `match_method`, or a `entity_resolution_reviews` row.
- **DB:** `companies`, `company_identifiers`, `company_aliases`, `company_name_norm` (trigram idx), `entity_resolution_reviews`.
- **Auth:** **critical** — `companies` is cross-tenant readable (it is public reference data). `supplier_relationships` is strictly tenant-scoped. No endpoint may ever join from a company to another tenant's relationships. Enforced by RLS (§12.6) *and* a repository-layer guard *and* a test.
- **Failure:** GLEIF unavailable → resolution proceeds on local data, `enrichment_status='pending'`, retried by a nightly job.
- **Scaling:** heaviest read path; trigram index + Redis cache keyed on normalized name.

### graph
- **Responsibility:** tenant-scoped edges; traversal queries; graph payload for visualization.
- **In:** `org_id`, root node, depth, edge-type filter. **Out:** node/edge sets with attributes.
- **DB:** `supplier_relationships`, `locations`, `company_locations`.
- **Auth:** hard `org_id` filter at the repository layer; RLS as defence in depth.
- **Failure:** depth cap (default 3, max 5) and node cap (5,000) enforced in SQL to prevent runaway recursion.
- **Scaling:** recursive CTE with `LIMIT`; materialized `graph_reachability` table refreshed on edge change (§8.5) once p95 traversal exceeds 200ms.

### events
- **Responsibility:** normalized event records + their linkage to source records and resolved entities.
- **In:** normalized payloads from ingestion. **Out:** `Event` rows.
- **DB:** `source_records`, `events`, `event_entities`, `event_materials`.
- **Auth:** events are **global** (not tenant-scoped) — the same export ban affects many tenants. Tenant scoping happens at `risk_assessments`/`alerts`. This is a deliberate normalization choice that prevents storing the same event N times.
- **Failure:** extraction failure → `events.status='extraction_failed'`, DLQ, admin-visible.

### risk (deterministic scoring)
- **Responsibility:** compute impact score per (event, org, supplier) triple. **Contains no LLM calls.**
- **In:** event (with classified severity + type), graph intersection result, supplier attributes. **Out:** `risk_assessments` rows with full score breakdown.
- **DB:** `risk_assessments`, `risk_model_versions`.
- **Failure:** missing inputs → score computed on available factors with `completeness` recorded; never guessed.
- **Scaling:** pure computation; batched per event.

### alerts
- **Responsibility:** alert lifecycle, evidence chain assembly, user workflow state.
- **In:** risk assessments above threshold. **Out:** `alerts` + `alert_evidence`.
- **DB:** `alerts`, `alert_evidence`, `alert_actions`.
- **Auth:** tenant-scoped, role-filtered (Category Manager sees own categories by default).

### spend
- **Responsibility:** document ingestion, normalization to spend/contract tables, deterministic leakage rules, overlap cross-check.
- **DB:** `uploaded_documents`, `spend_records`, `purchase_orders`, `contracts`, `spend_leakage_findings`.
- **Failure:** parse confidence < threshold → `parse_status='needs_review'`, never inserted into spend tables.

### notifications
- **Responsibility:** channel fan-out, preference evaluation, delivery tracking, retries, digests.
- **DB:** `notifications`, `notification_deliveries`, `notification_preferences`.
- **Failure:** provider failure → exponential retry ×5 → `failed` + admin alert. Idempotency key prevents double-send.

### ai
- **Responsibility:** `LLMGateway` (the only place any LLM is called), agent definitions, RAG retrieval, prompt loading, budget enforcement.
- **DB:** `agent_runs`, `documents`, `document_chunks`, `embeddings`.
- **Auth:** internal only; no direct external route except the investigation endpoint.
- **Failure:** provider error → retry with backoff → fallback model per routing config → hard fail recorded on `agent_runs`, surfaced as degraded, never silently fabricated.

### admin
- **Responsibility:** platform-admin-only operations (§20).
- **Auth:** `platform_admin` role only; every action written to `audit_logs`.

### audit
- **Responsibility:** append-only record of every state-changing action and every agent step.
- **DB:** `audit_logs` (append-only; `REVOKE UPDATE, DELETE` from the application role).


---

# PART E — EXTERNAL DATA SOURCES (§5, §15, §21, §37)

**Verification note:** the facts below were checked against current provider documentation at the time of writing. **Pricing and rate limits change without notice — the implementation must re-verify each provider's current terms before production deployment**, and the admin portal surfaces a per-source "terms last verified" date.

## E.1 Tier 1 — REQUIRED for MVP (all free, all official, all with documented access)

### 1. OFAC Sanctions List Service (SLS) — US Treasury
- **Provider:** U.S. Department of the Treasury, Office of Foreign Assets Control
- **Docs:** `https://ofac.treasury.gov/sanctions-list-service`
- **What:** SDN List + Consolidated (non-SDN) List — sanctioned individuals, entities, vessels, aircraft, with aliases, addresses, programs, IDs.
- **Access:** File-download REST endpoints, pattern `https://sanctionslistservice.ofac.treas.gov/api/download/{filename}`; a `/sanctions-lists` endpoint returns available list names programmatically. **Critical implementation note: OFAC can change file names without notice — always enumerate via `/sanctions-lists`, never hardcode a filename.**
- **Auth:** None. **Rate limit:** none published. **Cost:** free. **Format:** XML + CSV. Delta files published by year.
- **Important limitation:** SLS is a **file-delivery service, not a screening API**. It provides no fuzzy matching, scoring, or alias resolution. Parsing, normalization, indexing, and matching are our responsibility — this is a real engineering cost, budgeted in Phase 8/9.
- **Coverage:** global (US designations). **Reliability:** highest (authoritative primary source). **License:** US Government public domain.
- **Poll:** every 6 h (list updates are irregular and unscheduled — no fixed publication window).
- **Store:** `uid`, `name`, `type`, `programs[]`, `aliases[]`, `addresses[]`, `nationality`, `id_documents[]`, `list_name`, `published_date`, `raw_xml_s3_key`.
- **Production-suitable:** **Yes.**

### 2. GLEIF LEI API — Global Legal Entity Identifier Foundation
- **Provider:** GLEIF. **Base:** `https://api.gleif.org/api/v1` **Docs:** `https://www.gleif.org/en/lei-data/gleif-api`
- **What:** ~3.4M legal entities. Legal name, registration status, jurisdiction, legal form, registered + HQ address, BIC codes, **and Level 2 corporate relationship data (direct/ultimate parent and children)**.
- **Why this is the backbone of the system:** it is the only free, global, authoritative source that provides both **entity identity** (for entity resolution) and **corporate hierarchy** (to auto-seed the `owned_by` edges of the graph). Everything else is supplementary.
- **Auth:** none. **Rate limit:** none published; observed to tolerate high throughput; honour 429 with backoff regardless. **Cost:** free. **Format:** JSON:API. Updated multiple times daily.
- **License:** **CC0 1.0** — free to use and redistribute, including commercially. This is unusually permissive and is a major reason to anchor on it.
- **Poll:** on-demand for resolution/enrichment; nightly refresh job for entities in any tenant graph. For bulk, use GLEIF Golden Copy files rather than hammering the API.
- **Store:** `lei`, `legal_name`, `other_names[]`, `legal_jurisdiction`, `legal_form`, `entity_status`, `registration_status`, `next_renewal_date`, `legal_address`, `hq_address`, `direct_parent_lei`, `ultimate_parent_lei`, `bic[]`.
- **Production-suitable:** **Yes — primary.**

### 3. GDELT DOC 2.0 API
- **Provider:** The GDELT Project. **Endpoint:** `https://api.gdeltproject.org/api/v2/doc/doc`
- **What:** worldwide news article search across 100+ languages; modes `ArtList` (articles), `TimelineVol`, `TimelineTone`. Returns `url`, `title`, `seendate`, `domain`, `language`, `sourcecountry`, `socialimage`.
- **Auth:** **none** — the documentation defines no credential and no security scheme.
- **Rate limit:** **approximately one request per 5 seconds** — exceeding it returns HTTP 429 with a "limit requests to one every 5 seconds" message. **This is the single hardest constraint in the ingestion design.** Implementation: a dedicated Celery queue with `rate_limit='10/m'` and a Redis token bucket shared across all workers; conservative 6 s spacing. A `User-Agent` header must be set — requests without one have been rejected.
- **Coverage window:** **rolling 3 months only.** Anything older requires GDELT's separate bulk/BigQuery exports (out of MVP scope). This directly bounds the backfill depth in J1 to 30 days — well inside the window.
- **Cost:** free. **Webhooks:** none — polling only. **Updates:** ~every 15 minutes.
- **Reliability:** good, but **no published SLA and no guaranteed rate-limit schedule** — treat availability as best-effort and alert on staleness rather than assuming uptime.
- **Licensing caution:** GDELT returns **metadata and links**, not article text. Publisher headlines and article bodies carry separate copyright. **Store and display only: URL, title, domain, seendate, language, sourcecountry.** Do not store or re-serve full article text. If the extraction agent needs body text, fetch it at analysis time, use it transiently, persist only the extracted structured fields plus the source URL.
- **Poll:** per-tenant supplier-name queries batched; global material/commodity queries every 30 min; supplier-specific queries every 4 h (rate-limit bound).
- **Production-suitable:** **Yes, with the caveats above.** Plan for a paid news provider (E.3) if precision or latency proves insufficient.

### 4. Federal Register API (US)
- **Provider:** US National Archives / GPO. **Base:** `https://www.federalregister.gov/api/v1`
- **What:** US rules, proposed rules, notices, presidential documents — including BIS export-control rules and Commerce trade actions.
- **Auth:** none. **Cost:** free. **Format:** JSON. **Search:** by agency, document type, date, full text.
- **Poll:** hourly (published on business days ~06:00 ET).
- **Store:** `document_number`, `title`, `abstract`, `agencies[]`, `publication_date`, `effective_on`, `html_url`, `pdf_url`, `type`, `topics[]`.
- **License:** US Government public domain. **Production-suitable: Yes.**

### 5. EUR-Lex / EU Official Journal
- **Provider:** Publications Office of the EU. **Docs:** `https://eur-lex.europa.eu/content/help/data-reuse/webservice.html`
- **What:** EU regulations, decisions, and sanctions instruments — including CBAM, CRMA, and Regulation 833/2014 amendments.
- **Access:** SPARQL endpoint (Cellar) + web service; also per-topic RSS. **Auth:** registration required for the SOAP web service; SPARQL/RSS open.
- **Cost:** free. **License:** permissive EU reuse policy (Decision 2011/833/EU) with attribution.
- **Poll:** every 6 h. **Production-suitable: Yes.**

### 6. EU Consolidated Financial Sanctions List
- **Provider:** European Commission (FISMA). Published via the EU Sanctions Map / FSF.
- **What:** persons, groups, entities under EU asset freezes. **Note the documented scope limit:** Annex IV of Regulation 833/2014 entities are subject to specific economic prohibitions but **not** asset freezes, and are therefore **not** in the consolidated list. Anyone relying on this list alone will have a coverage gap — record this in `data_sources.coverage_notes` and surface it in the UI.
- **Format:** XML/CSV. **Auth:** free access token required for the official download endpoint. **Poll:** every 6 h.
- **Production-suitable: Yes.**

### 7. UN Security Council Consolidated List
- **Provider:** UN Security Council. **Access:** direct XML download from `un.org`.
- **Auth:** none. **Cost:** free. **Poll:** daily. **License:** UN public. **Production-suitable: Yes.**

### 8. UK Sanctions List (OFSI)
- **Provider:** UK HM Treasury / OFSI. **Access:** ODT/CSV/XML published on GOV.UK.
- **Auth:** none. **Cost:** free. **Poll:** daily. **License:** Open Government Licence v3.0. **Production-suitable: Yes.**

### 9. India — Open Government Data (OGD) Platform
- **Provider:** Government of India, NIC. **Base:** `https://api.data.gov.in/resource/{resource_id}`
- **Params:** `?api-key={key}&format=json&offset=&limit=` with server-side `filters[field]=value`.
- **Auth:** **free API key** (32-char hex) from registration at data.gov.in.
- **Rate limit:** per-key; honour `X-RateLimit-*` response headers where present and back off on 429.
- **What (relevant resources):** foreign-trade statistics, commodity/mandi prices, MCA company master data (CIN, ROC, capital, status, NIC industry — ~3.6M companies).
- **License:** **Government Open Data Licence — India (GODL)**. Attribution and redistribution terms vary by dataset — **check the licence on each specific dataset page before use**, and record it per-source in `data_sources.license_terms`.
- **Poll:** daily to weekly (these are reference datasets, not event feeds).
- **Production-suitable: Yes** for company reference data and trade statistics.

## E.2 Tier 2 — RECOMMENDED (official, but with access caveats)

### 10. WTO EPING / TBT-SPS Notifications
- **What:** member-state notifications of new technical barriers to trade and sanitary measures — an early-warning signal that precedes national regulation.
- **Access:** EPING alert system with email subscription + a notification search interface. **Poll:** daily.
- **Caveat:** verify current API/feed availability at implementation time; if only email alerts exist, ingest via a dedicated mailbox connector (see E.5 pattern).

### 11. India — DGFT (Directorate General of Foreign Trade)
- **What:** the single most important India-specific source: notifications, public notices, trade notices, and **ITC-HS import/export policy changes** (Free / Restricted / Prohibited status per tariff line). India changes export policy frequently and with immediate effect — exactly the event class Provenance exists to catch.
- **Access problem:** **DGFT publishes no documented public API and no official RSS feed.** Content is served from `dgft.gov.in` behind a portal.
- **Recommended approach, in order:**
  1. Check at implementation time whether any DGFT dataset has been published to `data.gov.in` (preferred — official, licensed, keyed).
  2. If not: **structured HTML monitoring** of the official DGFT notification listing pages, implemented as a polite, rate-limited, robots.txt-respecting connector that extracts **only the notification metadata and the link to the official PDF** — number, date, title, subject, PDF URL. Fetch the official PDF and extract from that, never from a third-party aggregator.
  3. Mark `source_type='html_monitor'` and `reliability='medium'` on every record so downstream alerts and the UI show the lower confidence.
- **This is the only HTML-monitoring source in the MVP and it is a deliberate, documented exception**, justified by the fact that no official machine-readable alternative exists for a source this central to the India use case. It must be re-evaluated quarterly. Aggregator sites (TaxGuru and similar) are **not** acceptable sources — they are copyrighted secondary commentary.
- **Never:** scrape behind a login, ignore robots.txt, or defeat a CAPTCHA.

### 12. India — CBIC (Central Board of Indirect Taxes and Customs)
- **What:** customs tariff notifications, duty changes, anti-dumping duties.
- **Access:** same situation as DGFT — official site, no documented API. Same treatment, same caveats.

### 13. India — MCA company data
- **Preferred:** via `data.gov.in` OGD resources (official, keyed, licensed — see E.1 #9).
- **Note:** the MCA V3 portal itself is interactive and CAPTCHA-protected; several commercial vendors (Surepass, Meon, and others) resell MCA lookups as paid APIs. **Do not scrape the MCA portal.** Use OGD for bulk reference data; if per-CIN real-time lookups become necessary, procure a licensed vendor — that is a Phase 2 purchasing decision, not an engineering workaround.

## E.3 Tier 3 — OPTIONAL / commercial (evaluate at Phase 2, not MVP)

### 14. OpenSanctions
- **What:** 460+ sources consolidated and de-duplicated into one entity graph (FollowTheMoney model) — OFAC, EU, UN, UK, PEPs, debarment registers. Offers `/match`, `/search`, `/entities` endpoints with per-feature match explanations.
- **⚠️ LICENSING — READ CAREFULLY:** the dataset is **CC BY-NC 4.0 — free for non-commercial use only. Commercial/business users must purchase a data licence or use the metered API.** Reported metering is on the order of **EUR 0.10 per query** (verify current pricing directly with the provider before any commercial use).
- **Implication:** Provenance is a commercial product. **OpenSanctions cannot be used for free.** It is therefore excluded from MVP; we ingest OFAC/EU/UN/UK **directly from the primary government sources** (E.1 #1, 6, 7, 8), which are public domain or OGL and carry no such restriction. OpenSanctions becomes attractive in Phase 2 *if* the cost of maintaining four separate parsers plus a matching engine exceeds the licence fee — a build-vs-buy decision to revisit with real numbers, not an assumption.

### 15. Commercial news APIs (NewsAPI.ai / Event Registry, Aylien, Bloomberg, Dow Jones Factiva)
- **When justified:** if GDELT's 5-second rate limit, 3-month window, or precision proves insufficient at scale.
- **Do not select one now.** Add a `NewsConnector` interface in Phase 8 so a paid provider is a new implementation, not a refactor. Obtain current pricing directly from providers at evaluation time.

### 16. Credit/financial distress providers (D&B, Creditsafe, CRISIL/ICRA for India)
- **When justified:** if GDELT-derived distress signals prove too noisy (measured by false-positive rate on `financial_distress` alerts).
- **MVP alternative:** targeted GDELT queries constrained to a closed vocabulary (insolvency, bankruptcy, liquidation, rating downgrade, going concern, receivership) + company-name match, classified by LLM into a closed enum. Lower recall than a paid feed, honestly labelled as such.

## E.4 Explicitly EXCLUDED from MVP, with reasons

| Source | Why excluded |
|---|---|
| Market/stock price APIs | Share price is a noisy, lagging proxy for supply risk. Would degrade alert precision. Not necessary for business-impact analysis |
| MOFCOM (China) | No documented API, no RSS, no verified reuse policy. Carried as **static cited snapshots** bundled in `data/regulatory_snapshots/`, `source_type='cached'`, never presented as live monitoring |
| DRC ARECOMS | Same as MOFCOM — static cited snapshot only |
| Panjiva / ImportGenius (trade data) | Paid; Phase 3 |
| Fastmarkets / Benchmark Mineral Intelligence | Paid commodity intelligence; Phase 3 |
| Any aggregator/secondary site | Copyrighted commentary, not a primary source |

## E.5 Source Cost Summary

| Provider | Purpose | Access | Auth | Free tier | Paid | Rate limit | MVP? |
|---|---|---|---|---|---|---|---|
| OFAC SLS | US sanctions | REST file download | None | Fully free | — | None published | **Required** |
| GLEIF | Entity identity + hierarchy | REST JSON:API | None | Fully free (CC0) | — | None published | **Required** |
| GDELT DOC 2.0 | News/geopolitical signal | REST | None | Fully free | — | ~1 req / 5 s | **Required** |
| Federal Register | US regulation | REST JSON | None | Fully free | — | Generous | **Required** |
| EUR-Lex | EU regulation | SPARQL/RSS/WS | Reg. for WS | Fully free | — | Fair use | **Required** |
| EU Consolidated List | EU sanctions | XML/CSV | Free token | Fully free | — | — | **Required** |
| UN Consolidated | UN sanctions | XML | None | Fully free | — | — | **Required** |
| UK OFSI | UK sanctions | CSV/XML | None | Fully free (OGL v3) | — | — | **Required** |
| data.gov.in | India trade + company data | REST | Free key | Free | — | Per-key | **Required** |
| WTO EPING | Trade-barrier early warning | Feed/email | Varies | Free | — | — | Recommended |
| DGFT | India trade policy | HTML monitor | None | Free | — | Self-imposed | Recommended |
| CBIC | India customs | HTML monitor | None | Free | — | Self-imposed | Recommended |
| OpenSanctions | Consolidated sanctions | REST | API key | **Non-commercial only** | Licence / ~EUR 0.10 per query (verify) | Per plan | Phase 2 |
| Commercial news | Higher-precision news | REST | API key | Varies | Verify at eval | Per plan | Phase 2 |
| D&B / Creditsafe / CRISIL | Financial distress | REST | API key | None typically | Verify at eval | Per plan | Phase 3 |

**LLM/infra costs** (verify current rates before deployment): LLM inference is the dominant variable cost. Control levers in §21/C.5: cheap-model pre-filter, content-hash caching of extractions, per-tenant token budgets, batch classification.


---

# PART F — DATA INGESTION ARCHITECTURE (§6)

## F.1 Pipeline

```
Schedule/Trigger
  → Connector.fetch()            [per-source, rate-limited, retried]
  → RawStore                     [S3 object + source_records row]
  → Normalize                    [source-specific → common schema]
  → Dedupe                       [content_hash + canonical_url]
  → Extract                      [LLM → EventExtraction schema]
  → EntityResolve                [cascade, §7]
  → GraphIntersect               [SQL, per affected tenant]
  → RiskScore                    [deterministic, §9]
  → Threshold → Alert
  → Explain                      [LLM, grounded]
  → Notify
```
Each stage is a separate Celery task. State is carried in the DB (not in task payloads), so any stage can be replayed independently from its predecessor's output.

## F.2 Connector Interface

Every source implements one interface — this is what makes providers replaceable (engineering rule 17).

```python
class SourceConnector(Protocol):
    source_id: str
    source_type: Literal["api", "bulk_download", "rss", "html_monitor", "cached_snapshot"]
    reliability: Literal["high", "medium", "low"]

    async def fetch(self, cursor: Cursor | None) -> FetchResult:
        """Returns raw items + next cursor. MUST NOT transform."""

    def normalize(self, raw: dict) -> NormalizedRecord:
        """Pure function, no I/O. Fully unit-testable."""

    def content_hash(self, raw: dict) -> str:
        """Stable hash over the identity-bearing fields only."""
```
`fetch` and `normalize` are separated deliberately: `normalize` being pure and I/O-free means every source's parsing logic is testable against stored fixtures with no network.

## F.3 Idempotency and Deduplication (hard requirement)

Three layers — the system must never create a duplicate event when the same article or record is retrieved again:

1. **Source-level idempotency key.** `source_records` has `UNIQUE (source_id, external_id)` where `external_id` is the provider's own identifier (OFAC `uid`, Federal Register `document_number`, GDELT canonicalized URL). Insert uses `ON CONFLICT DO UPDATE SET last_seen_at = now(), seen_count = seen_count + 1` — re-fetching updates, never duplicates.
2. **Content hash.** `content_hash = sha256(normalized identity fields)`. If the external ID is absent or unstable, the hash is the key. A changed hash for the same external ID means the record was **revised** → new `source_record_version` row, existing event flagged `superseded`, and a re-analysis triggered (this is how a corrected sanctions entry or an amended regulation propagates).
3. **Semantic dedupe across sources.** The same export ban is reported by 40 news outlets. After extraction, an `event_cluster_key` is computed from `(event_type, jurisdiction, normalized_materials, effective_date)`. Records with the same key within a 72-hour window attach to **one** `Event` as additional `source_records` (more corroboration = higher `Event.corroboration_count`, which feeds the risk score) rather than creating 40 events and 40 alerts. **This single mechanism is the difference between a usable product and alert spam.**

URL canonicalization before hashing: strip `utm_*`, `fbclid`, `gclid`, fragments; lowercase host; resolve one level of redirect; drop trailing slash.

## F.4 Scheduling, Retry, Backoff, DLQ

| Source | Frequency | Queue | Rate control |
|---|---|---|---|
| GDELT — global material queries | 30 min | `ingest_gdelt` | Redis token bucket, 1 per 6 s **globally** |
| GDELT — per-tenant supplier queries | 4 h, batched | `ingest_gdelt` | same bucket |
| OFAC SLS | 6 h | `ingest_bulk` | — |
| EU / UN / UK sanctions | 6 h / daily / daily | `ingest_bulk` | — |
| Federal Register | 1 h | `ingest_api` | — |
| EUR-Lex | 6 h | `ingest_api` | — |
| data.gov.in | daily | `ingest_api` | honour `X-RateLimit-*` |
| DGFT / CBIC HTML | 4 h | `ingest_html` | max 1 req / 10 s, robots-respecting |
| GLEIF enrichment | nightly + on-demand | `ingest_api` | honour 429 |

- **Retry:** tenacity, exponential backoff `2^n` with full jitter, base 2 s, max 5 attempts, cap 5 min.
- **Respect 429/`Retry-After`** always; for GDELT, **fail fast** on 429 rather than retrying into a still-closed cooldown, and re-enqueue after the cooldown.
- **Circuit breaker** per source: 5 consecutive failures → `data_sources.status='degraded'`, polling paused 30 min, admin notified. Prevents one dead source from starving the queue.
- **DLQ:** failed tasks after final retry → `dead_letter_queue` table with full payload + traceback; admin portal supports inspect + replay. Nothing is silently dropped.
- **Data versioning:** `source_record_versions` retains every revision; `events` reference the version they were extracted from, so an alert always shows the exact text it was based on even after the source changes.

## F.5 Source Reliability Propagation
Every `source_record` carries `reliability` from its connector. It flows into `Event.confidence` and into the risk score's evidence-quality factor, and is displayed on the alert. An alert derived from an HTML-monitored DGFT page is visibly weaker than one derived from the OFAC XML — the user sees that, always.

---

# PART G — ENTITY RESOLUTION (§7)

## G.1 The Cascade (deterministic first, LLM last)

Input: `{name, country?, domain?, identifiers?, address?}` → Output: `{company_id, confidence, match_method}` or a review-queue row.

```
Stage 0  Normalize
         lowercase; strip legal suffixes (inc, corp, corporation, ltd, limited,
         llc, gmbh, sa, bv, pvt, private limited, plc, co, company, holdings);
         unicode NFKC; collapse whitespace; transliterate non-Latin (unidecode)
         → name_norm, stored + trigram-indexed

Stage 1  IDENTIFIER MATCH                          confidence 1.00  [exact]
         LEI / CIN / DUNS / VAT / registration no.  → company_identifiers lookup
         Deterministic. Terminates immediately.

Stage 2  DOMAIN MATCH                              confidence 0.97
         registered web domain (eTLD+1, public-suffix-list aware)
         Reject free-mail domains (gmail, outlook, qq …) from ever matching.

Stage 3  EXACT NORMALIZED NAME + COUNTRY           confidence 0.95
         name_norm = ? AND country = ?

Stage 4  EXACT NORMALIZED NAME, NO COUNTRY         confidence 0.85
         unique hit only; multiple hits → Stage 6

Stage 5  FUZZY  pg_trgm similarity                 confidence = 0.60–0.90
         WHERE name_norm % ?  ORDER BY similarity DESC LIMIT 10
         + Jaro-Winkler rescore + token-set ratio
         + country/address/industry agreement boosts
         ≥ 0.90 → auto-accept; 0.60–0.90 → Stage 6; < 0.60 → Stage 7

Stage 6  AI ADJUDICATION  (only the ambiguous band)
         Input: candidate name + context + top-10 candidates with their
                attributes. Output: STRUCTURED
                {decision: match|no_match|uncertain, company_id?, confidence,
                 reasoning, evidence_fields[]}
         ≥ 0.85 and decision=match → accept, flagged ai_assisted
         otherwise → Stage 7

Stage 7  HUMAN REVIEW QUEUE
         entity_resolution_reviews row; blocks nothing else in the pipeline —
         the event still records an UNRESOLVED mention rather than a wrong one.

Stage 8  CREATE NEW
         Only when the user explicitly confirms "this is a new company", or
         when an authoritative source (GLEIF) returns a record with an
         identifier we do not have.
```

**Why the LLM sits at Stage 6 and nowhere else:** Stages 1–4 are exact and free. Stage 5 is cheap and covers most of the rest. Only the genuinely ambiguous band justifies an LLM call. Measured target: **≥ 80% of resolutions terminate before Stage 6.** If that metric drops, the normalization rules — not the model — need work.

## G.2 Worked Example
```
"Microsoft Corporation"     → Stage 3  name_norm="microsoft" + US  → 0.95
"Microsoft Corp."           → Stage 3  name_norm="microsoft" + US  → 0.95
"Microsoft"                 → Stage 4  unique                      → 0.85
"Microsoft Corporation Ltd" → Stage 5  sim 0.91 → auto-accept      → 0.91
"MSFT Ireland Operations"   → Stage 5  sim 0.42 → Stage 6 → LLM sees
                              GLEIF child-of relationship → match, 0.88
```

## G.3 Canonical Model — the multi-tenant privacy rule

**`companies` is a global, cross-tenant registry of public reference data.**
**`supplier_relationships` is strictly tenant-private.**

That Acme Corp exists is public. That *Tenant A buys from Acme* is Tenant A's confidential commercial information and **must never be visible to Tenant B**. This separation is the central privacy invariant of the product. It is enforced at three layers (RLS policy, repository guard, and an explicit test in the security suite) because a single-layer failure here is a business-ending incident.

Practical consequence: two tenants supplying from the same company share one `companies` row (deduplication achieved, storage saved, enrichment shared) with zero information leakage between them.

---

# PART H — THE GRAPH (§8)

## H.1 Recommended: PostgreSQL adjacency table + recursive CTEs. **Not Neo4j.**

### Reasoning
1. **Realistic scale is small.** A large tenant has 500–2,000 direct suppliers; depth-3 expansion reaches maybe 10–20k nodes. This is trivial for Postgres. Graph databases earn their keep at millions of edges with deep variable-length traversal — not here.
2. **One datastore, one transaction.** Alerts, risk scores, spend, and graph edges are written together. With Neo4j they would span two systems with no shared transaction, requiring a sync pipeline and introducing an entire class of consistency bugs.
3. **Multi-tenant RLS.** Postgres gives row-level security for free. Neo4j's tenant isolation would be hand-rolled in every query.
4. **Operational cost.** One managed RDS instance vs. RDS + a Neo4j cluster, with a second backup/DR/upgrade story.
5. **Team and agent familiarity.** SQL is universally understood; Cypher is not.

### Trade-offs honestly stated
Recursive CTEs get awkward past depth 4–5, and variable-length shortest-path queries are far less ergonomic than Cypher. If the product later needs multi-hop path-finding ("show every route by which we depend on Country X") over deep tiers, Neo4j becomes genuinely better.

### The migration trigger (decide on data, not taste)
Move to Neo4j **only when** p95 traversal latency exceeds 500 ms at depth 3 after the materialized reachability table (H.5) is in place, **or** a committed requirement needs traversal deeper than 5 hops. Both are measured by existing metrics. Until then, Neo4j is unjustified infrastructure.

### Why not Apache AGE (Postgres graph extension)
Tempting — Cypher inside Postgres. Rejected for MVP: RDS does not support it, so it would force self-managed Postgres, losing managed backups/failover. Not worth it for depth-3 queries that plain SQL handles.

## H.2 Node Types
`Organization` (tenant), `Company` (canonical: supplier/sub-supplier/parent), `Location`, `Product` (Phase 2), `Material` (Phase 2).

## H.3 Edge Types (`supplier_relationships.relationship_type`)
| Type | From → To | Attributes |
|---|---|---|
| `supplies_to` | Company → Organization | criticality 1–5, annual_spend_usd, category, single_source (bool), lead_time_days, contract_id |
| `sub_supplies_to` | Company → Company | tier, criticality, inherited_from_edge_id |
| `owned_by` | Company → Company | ownership_pct, is_ultimate_parent — auto-seeded from GLEIF Level 2 |
| `located_in` | Company → Location | site_type (hq/plant/warehouse), is_primary |
| `produces` (P2) | Company → Product | |
| `contains` (P2) | Product → Material | composition_pct |

## H.4 Shared Edge Attributes (every edge carries these — non-negotiable for explainability)
`confidence` (0–1), `source` (`user_declared` \| `gleif` \| `inferred` \| `document`), `source_record_id` (nullable), `valid_from`, `valid_to` (nullable — edges are **temporal**, never hard-deleted, so a historical alert still explains itself correctly), `created_by`, `verified_at`, `verified_by`.

## H.5 Traversal
Core query — "which of this org's suppliers are reachable from an affected company":
```sql
WITH RECURSIVE reach AS (
    SELECT r.from_company_id, r.to_company_id, r.to_org_id,
           r.relationship_type, 1 AS depth,
           ARRAY[r.from_company_id] AS path, r.confidence AS path_confidence
    FROM supplier_relationships r
    WHERE r.from_company_id = :affected_company_id
      AND r.org_id = :org_id
      AND r.valid_to IS NULL
  UNION ALL
    SELECT r.from_company_id, r.to_company_id, r.to_org_id,
           r.relationship_type, x.depth + 1,
           x.path || r.from_company_id,
           x.path_confidence * r.confidence
    FROM supplier_relationships r
    JOIN reach x ON r.from_company_id = x.to_company_id
    WHERE x.depth < :max_depth
      AND r.org_id = :org_id
      AND r.valid_to IS NULL
      AND NOT r.from_company_id = ANY(x.path)     -- cycle guard, mandatory
)
SELECT * FROM reach LIMIT 5000;
```
`path_confidence` (the product of edge confidences) degrades with depth automatically — a tier-3 inferred link is correctly treated as weaker evidence than a tier-1 declared one.

**Performance path (build when needed, not before):** a `graph_reachability` materialized table `(org_id, from_company_id, to_company_id, min_depth, best_path_confidence)` refreshed incrementally on edge change. Turns traversal into an indexed lookup.

## H.6 Visualization
Cytoscape.js. Server returns `{nodes, edges}` already filtered and capped (default 300 nodes; "expand" loads more on demand — never ship 5,000 nodes to a browser). Node colour = current risk level, size = spend, edge thickness = criticality, dashed edge = inferred/low-confidence. Layout `dagre` for tier hierarchy, `cose-bilkent` for cluster exploration.


---

# PART I — BUSINESS IMPACT & RISK ENGINE (§9)

## I.1 Design Principle
**The score is computed by deterministic code. The LLM classifies inputs and writes the explanation — it never produces the number.** A user challenging an alert must get the same score every time, with an arithmetic breakdown. An LLM-generated score cannot offer that.

## I.2 Flow
```
Event (classified) ─► for each org with a graph intersection:
     GraphIntersect (SQL) ─► affected supplier(s), depth, path, path_confidence
        ─► gather factors ─► weighted score ─► severity band
        ─► above threshold? ─► create Alert + evidence chain
        ─► Explanation Agent (grounded, cited)
```

## I.3 The Scoring Model

The formula in the brief (a flat sum of six factors) has two defects: it ignores that **relevance is multiplicative, not additive** (an event with zero relevance to a supplier should score zero regardless of how severe it is), and it has no term for evidence quality. Corrected model:

```
impact_score = 100
             × event_severity            (0–1)
             × dependency_strength       (0–1)   ← multiplicative gate
             × evidence_quality          (0–1)   ← multiplicative gate
             × (1 + urgency_multiplier)          (0–0.5)
             × exposure_multiplier               (0.8–1.5)
```

**Multiplicative gates.** `dependency_strength` near zero (a depth-3 supplier with 0.3 path confidence and no spend) drives the whole score toward zero even for a severe event — correct behaviour. An additive model would surface it as a mid-score alert, which is exactly how these systems become noise.

### Factor definitions (all deterministic)

**`event_severity` (0–1)** — from a lookup table by `event_type`, adjusted by LLM-classified `severity_signal`:
| event_type | base |
|---|---|
| `sanction_designation` (direct entity hit) | 1.00 |
| `export_prohibition` | 0.90 |
| `export_restriction` / licence requirement | 0.75 |
| `quota_imposition` | 0.70 |
| `insolvency_filing` | 0.90 |
| `credit_downgrade` | 0.55 |
| `tariff_change` | 0.50 |
| `facility_disruption` (fire/flood/strike) | 0.65 |
| `regulatory_proposal` (not yet in force) | 0.30 |

**`dependency_strength` (0–1)**
```
= path_confidence
× tier_decay[depth]                  # 1.0, 0.6, 0.35, 0.2, 0.1
× (0.5 + 0.5 × criticality/5)
× (1.3 if single_source else 1.0)    # capped at 1.0
```

**`evidence_quality` (0–1)**
```
= source_reliability      # high 1.0 | medium 0.75 | low 0.5
× entity_resolution_confidence
× min(1.0, 0.7 + 0.1 × corroboration_count)   # independent sources corroborating
```
This is why `corroboration_count` from the semantic-dedupe step (F.3) matters: 40 outlets reporting one ban produce one alert with *higher* confidence, not 40 alerts.

**`urgency_multiplier` (0–0.5)** — `effective_date` proximity: in force now 0.5; ≤7d 0.45; ≤30d 0.35; ≤90d 0.2; >90d 0.1; none 0.15.

**`exposure_multiplier` (0.8–1.5)** — annual spend on log scale, normalized within the tenant's own spend distribution (so it means the same thing for a $10M and a $10B company). No spend data → 1.0 and `completeness` flags the gap rather than assuming.

### Severity bands
`CRITICAL ≥ 75` · `HIGH 55–74` · `MEDIUM 35–54` · `LOW 15–34` · below 15 recorded, no alert.
Bands are per-tenant configurable; defaults calibrated against the labelled eval set (§30).

### Confidence vs. score — two different numbers, both shown
`impact_score` = how much this matters. `confidence` = how sure we are. A 90-score/0.4-confidence alert reads "potentially severe, weak evidence" and is labelled **"needs human judgment"** rather than force-ranked — directly implementing the confirmed requirement.

### Versioning
`risk_model_versions` stores weights and thresholds; every `risk_assessment` records `model_version`. Changing weights never silently rewrites history, and A/B comparison of models against the eval set is possible.

## I.4 What Every Alert Must Answer (enforced by schema, not convention)
| Question | Field |
|---|---|
| What happened? | `event.summary` + `event.event_type` |
| Which supplier? | `alert.company_id` → resolved entity |
| Why does it affect me? | `alert_evidence` rows of type `graph_path` — the literal edge chain |
| What relationship caused it? | serialized path with each edge's type, confidence, source |
| How severe? | `impact_score` + band + **factor-by-factor breakdown** |
| What evidence? | `alert_evidence` rows of type `source_record` with URL, retrieved_at, `source_type` live/cached |
| What should I consider? | `alert.recommendations[]` — role-scoped, **never executed** |

`alerts` has a DB-level `CHECK` that an alert cannot exist without at least one `alert_evidence` row. Engineering rule 9 is enforced by the database, not by discipline.

---

# PART J — AI AGENT ARCHITECTURE (§10)

## J.1 Agents That Exist (4) and Services That Replaced Proposed Agents

| Proposed | Verdict | Why |
|---|---|---|
| Research Agent | **Merged** into Investigation Agent | Same tools, same RAG; two agents would duplicate scope |
| Entity Resolution Agent | **Kept — narrow** | Only Stage 6 of the cascade |
| Impact Analysis Agent | **REPLACED by deterministic service** | Scoring must be reproducible; SQL + arithmetic |
| Regulatory Intelligence Agent | **Kept** as Event Extraction Agent | Genuine unstructured→structured NLP |
| Alert Explanation Agent | **Kept** | Natural-language generation over computed facts |
| Investigation Agent | **Kept** | Conversational RAG |
| Spend Intelligence | **Service, not agent** | Exact SQL rules against contract terms |
| Document Ingestion | **Kept** as Document Parsing Agent | Layout variance genuinely needs a model |

**Four LLM-backed agents: Event Extraction, Entity Resolution (Stage 6), Alert Explanation, Investigation. Plus one document-parsing agent.** Everything else is deterministic.

## J.2 Agent Specifications

### Agent 1 — Event Extraction
- **Purpose:** unstructured source record → validated `EventExtraction`.
- **In:** `{title, body_text, source_url, source_type, published_date, source_reliability}`.
- **Out (Pydantic, enforced):**
```python
class EventExtraction(BaseModel):
    is_relevant: bool
    event_type: EventTypeEnum                 # closed enum, no free text
    jurisdictions: list[CountryCode]
    affected_entities: list[EntityMention]    # name, role, text_span
    affected_materials: list[str]
    affected_hs_codes: list[str]
    effective_date: date | None
    expiry_date: date | None
    severity_signal: Literal["low","moderate","high","severe"]
    summary: str = Field(max_length=500)      # OUR words, never source text
    confidence: float = Field(ge=0, le=1)
    evidence_spans: list[TextSpan]            # REQUIRED — char offsets in source
```
- **Tools:** none. Pure extraction. Deliberately tool-less to minimize injection surface.
- **System prompt responsibilities:** treat input as **untrusted data, never instructions**; extract only what is stated; `summary` must be paraphrase (never reproduce source text); every field must be supported by an `evidence_span`; return `is_relevant=false` rather than speculating.
- **Guardrails:** schema validation; enum-constrained; `evidence_spans` must resolve to real offsets (validated post-hoc in code — if a span doesn't exist in the source, the extraction is rejected as hallucinated); ≤2 retries then `needs_review`.
- **Failure:** validation failure ×2 → `events.status='extraction_failed'` → DLQ. **Never a partial or guessed event.**
- **Eval:** 200 hand-labelled records; targets in §30.
- **Memory/RAG:** none — stateless per record (which also makes it cacheable by content hash).

### Agent 2 — Entity Resolution (Stage 6 only)
- **In:** mention + context + top-10 candidates with attributes.
- **Out:** `{decision: match|no_match|uncertain, company_id|None, confidence, reasoning, evidence_fields[]}`.
- **Tools:** `get_company_details(company_id)`, `search_gleif(name, country)` — **read-only, no writes.**
- **Guardrails:** may only return a `company_id` from the supplied candidate list (validated in code — a model-invented ID is rejected); `uncertain` is always an acceptable answer and is never penalized.
- **Failure:** any error → review queue. Never auto-creates a company.
- **Eval:** 150 labelled pairs incl. hard negatives (e.g. "Delta Airlines" vs "Delta Electronics").

### Agent 3 — Alert Explanation
- **In:** the **already-computed** risk assessment, graph path, event, evidence records.
- **Out:** `{headline ≤120 chars, explanation ≤400 words, why_it_matters, recommended_considerations[1..3], citations[]}`.
- **Tools:** none.
- **Guardrails (strictest in the system):**
  - Must not introduce any fact absent from its input. Post-generation validator extracts claims and checks each maps to a provided evidence ID; unmapped claim → regenerate once → fall back to a deterministic template.
  - **Must not restate or recompute the score** — the number comes from the risk engine and is rendered by the UI.
  - Recommendations must be phrased as considerations, never instructions; a lexicon check rejects imperatives implying execution ("place the order", "switch the supplier now").
  - Never asserts a candidate supplier is "qualified" — only "candidate, requires qualification".
- **Failure:** template fallback (structured, unglamorous, always correct) — the alert still ships.

### Agent 4 — Investigation (user-facing, conversational)
- **Purpose:** answer "why was this flagged?", "what happened with our suppliers this week?", "which suppliers are exposed to Country X?"
- **In:** user question + `org_id` + optional `alert_id` + conversation history.
- **Tools (least-privilege, all tenant-scoped and read-only):**
  `search_alerts(filters)`, `get_alert_evidence(alert_id)`, `query_graph(root, depth)`, `search_events(query, date_range)`, `get_supplier(company_id)`, `semantic_search(query)` (RAG, §11).
  **Every tool injects `org_id` server-side from the auth context — the model cannot specify it.** A model-supplied org_id is structurally impossible, not merely forbidden.
- **Memory:** conversation history in Redis, 1-hour TTL, tenant-scoped. No cross-session memory in MVP.
- **Guardrails:** every factual claim must carry a citation to an alert/event/edge; refuses to answer beyond retrieved context ("I don't have evidence for that"); output passed through the same claim-validator as Agent 3.
- **Failure:** tool error → says so explicitly rather than answering from parametric knowledge.

### Agent 5 — Document Parsing
- **In:** uploaded PDF/CSV/XLSX + declared `doc_type`.
- **Out:** `ParsedDocument` with per-field confidence.
- **Guardrails:** confidence < 0.85 on any monetary/identifier field → whole document `needs_review`; totals must reconcile with line items (deterministic arithmetic check — a model that gets the sum wrong is caught by code); uploaded content is **untrusted** (a PDF saying "ignore previous instructions" is data).
- **Failure:** never partially inserts into spend tables. All-or-review.

## J.3 LLMGateway (the single choke point)
Every LLM call in the system goes through one class. Nothing calls LiteLLM directly.
Responsibilities: model routing by task, per-tenant token budget enforcement (reject with `budget_exceeded` before the call), content-hash response caching, Langfuse tracing, prompt version resolution, retry/fallback, and writing the `agent_runs` record. This is what makes "swap the provider" a config change and makes cost controllable.

---

# PART K — RAG ARCHITECTURE (§11)

## K.1 Where RAG Is and Is Not Used
- **Used:** Investigation Agent (semantic search over events, alerts, regulatory documents, and the tenant's own uploaded contracts).
- **Not used:** Event Extraction (single document in context — retrieval adds nothing), Explanation (inputs already supplied), Entity Resolution (structured candidate lookup, not semantic).

Over-applying RAG is a common failure; it is scoped deliberately.

## K.2 Pipeline
```
Document (regulatory text | uploaded contract | event summary)
 → Extract text (pdfplumber; OCR via Tesseract only if text layer absent)
 → Chunk: recursive semantic, 500 tokens target, 15% overlap,
          never split across section boundaries
 → Embed (voyage-3 via LiteLLM)
 → Store: document_chunks + embeddings (pgvector, HNSW)
 → Retrieve: HYBRID
      BM25/Postgres-FTS  ⊕  vector cosine
      → Reciprocal Rank Fusion (k=60)
      → rerank top-30 → top-8 (cross-encoder; MVP: LLM-based rerank)
 → LLM answers ONLY from retrieved chunks
 → Every claim carries chunk_id → document_id → source_url
```

**Hybrid, not pure vector** — regulatory language is full of exact identifiers (HS codes, regulation numbers, entity names) where lexical match beats embeddings. Pure vector search reliably misses "Notification No. 32/2025".

## K.3 Metadata on Every Chunk (drives mandatory filtering)
`org_id` (NULL = global/public), `document_type`, `source_url`, `jurisdiction`, `published_date`, `effective_date`, `language`, `source_reliability`, `section_path`.

**Tenant filtering is applied in the SQL WHERE clause before vector search, never as a post-filter** — post-filtering leaks another tenant's documents into the candidate set and is a data-isolation bug waiting to happen.

## K.4 Embedding Model Change Safety
`embeddings` stores `model` and `dimensions` per row. Partial HNSW indexes per model. A model change writes new rows alongside old ones and flips a config pointer — no index corruption, no big-bang re-embed, instant rollback.

## K.5 Citation Contract
No claim ships without `chunk_id` → `document_id` → `source_url` + `retrieved_at` + `source_type` (live/cached). The UI renders cached-derived claims distinctly, so a cached MOFCOM/ARECOMS snapshot can never read as live monitoring — the confirmed requirement, enforced in the data model.


---

# PART L — AUTHENTICATION & AUTHORIZATION (§12)

## L.1 Authentication
- **Provider:** Clerk. **Protocol:** OIDC; frontend uses Clerk SDK, backend verifies JWT via JWKS (cached 1 h).
- **Methods:** email+password, Google/Microsoft OAuth, **SAML SSO** (enterprise tier).
- **MFA:** TOTP + backup codes. **Enforced for `org_admin` and `platform_admin`.**
- **Sessions:** short-lived access JWT (15 min) + refresh token rotation handled by Clerk. Backend is **stateless** — no server session store.
- **JWT claims consumed:** `sub` (user), `org_id`, `org_role`, `exp`, `iss`, `aud`. Signature, issuer, audience, and expiry all verified. `org_id` is **only ever** read from the verified token — never from a request body, query param, or header.
- **Service-to-service:** workers use a signed internal service token (short-lived, from Secrets Manager) with a dedicated `service` principal; distinct DB role with narrower grants.
- **API keys (Phase 2):** per-org, prefix + `argon2id` hash stored, shown once, scoped, revocable, rate-limited separately.

## L.2 Roles

| Role | Scope | Permissions |
|---|---|---|
| `platform_admin` | Global | All admin endpoints, all tenants (every access audited and alerted) |
| `org_admin` | Org | Manage members, org settings, data sources, alert rules, full alert access, billing |
| `analyst` | Org | Full read; create/edit suppliers & relationships; triage alerts; upload documents; run investigations |
| `org_user` | Org | Read alerts/suppliers/graph; acknowledge alerts; no graph mutation, no upload |
| `read_only` | Org | Read only; no state change of any kind |

Persona ≠ role. Risk Manager and Category Manager are typically both `analyst`; their differing views come from `user_preferences.persona` and category assignment, not from permissions. Keeping persona out of the permission model avoids a combinatorial RBAC mess.

## L.3 Enforcement — three layers, deliberately redundant
1. **Route-level:** FastAPI dependency `require_permission("alerts:write")`.
2. **Repository-level:** every tenant-scoped repository method takes `org_id` as a **required, non-defaulted** parameter. A base class raises if a query on a tenant-scoped table is issued without it.
3. **Database-level:** PostgreSQL **Row-Level Security** on every tenant-scoped table, using `current_setting('app.current_org_id')`, set per request/transaction.

Three layers because tenant leakage is the highest-severity failure mode in a multi-tenant product handling confidential supplier relationships. Any single layer can be defeated by one mistake; all three failing simultaneously requires deliberate effort.

```sql
ALTER TABLE supplier_relationships ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON supplier_relationships
  USING (org_id = current_setting('app.current_org_id')::uuid);
```

**`companies`, `events`, and `source_records` are intentionally NOT RLS-restricted** — they are shared public reference data. This is the deliberate design of G.3 and must be documented in code comments so nobody "fixes" it later.

---

# PART M — DATABASE SCHEMA (§14)

Conventions applied to every table: `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`; audit fields `created_at`, `updated_at` (trigger-maintained), `created_by`, `updated_by`; soft delete via `deleted_at TIMESTAMPTZ NULL` with partial indexes `WHERE deleted_at IS NULL`; all timestamps `TIMESTAMPTZ` in UTC; money as `NUMERIC(18,2)` + `currency CHAR(3)` (**never floats**).

## M.1 Core

```sql
-- TENANCY -----------------------------------------------------------------
organizations(
  id, clerk_org_id TEXT UNIQUE NOT NULL, name, slug UNIQUE,
  company_id UUID REFERENCES companies(id),      -- tenant's own canonical entity
  industry, country CHAR(2), subscription_tier, settings JSONB DEFAULT '{}',
  monthly_token_budget BIGINT DEFAULT 5000000,
  onboarding_completed_at, deleted_at, <audit>)

organization_members(
  id, org_id FK, user_id TEXT NOT NULL,          -- Clerk user id
  role TEXT CHECK (role IN ('org_admin','analyst','org_user','read_only')),
  persona TEXT CHECK (persona IN ('risk_manager','category_manager','other')),
  assigned_categories TEXT[] DEFAULT '{}',        -- category-manager scoping
  invited_at, joined_at, deleted_at, <audit>,
  UNIQUE (org_id, user_id))

-- CANONICAL REGISTRY (GLOBAL, NOT TENANT-SCOPED) --------------------------
companies(
  id, legal_name, name_norm TEXT NOT NULL,        -- normalized, trigram idx
  country CHAR(2), jurisdiction, legal_form, entity_status,
  primary_domain, industry_codes TEXT[],
  registered_address JSONB, hq_address JSONB,
  data_source TEXT,                                -- gleif|ogd_india|user|inferred
  enrichment_status TEXT DEFAULT 'pending',
  last_enriched_at, confidence NUMERIC(3,2) DEFAULT 1.0,
  is_verified BOOL DEFAULT false, deleted_at, <audit>)
  INDEX gin_trgm_ops ON name_norm;  INDEX (country);  INDEX (primary_domain);

company_identifiers(
  id, company_id FK,
  identifier_type TEXT CHECK (identifier_type IN
    ('lei','cin','duns','vat','tax_id','registration_number','ticker')),
  identifier_value TEXT NOT NULL, issuing_country CHAR(2), source, verified_at,
  UNIQUE (identifier_type, identifier_value))      -- global uniqueness = ER anchor

company_aliases(
  id, company_id FK, alias, alias_norm, alias_type, source, confidence,
  UNIQUE (company_id, alias_norm))

entity_resolution_reviews(
  id, org_id FK NULL,                              -- NULL = global resolution
  raw_name, context JSONB, candidates JSONB,       -- top-10 + scores
  suggested_company_id FK NULL, ai_confidence, ai_reasoning,
  status TEXT DEFAULT 'pending'                    -- pending|resolved|rejected|new_entity
  resolved_company_id FK NULL, resolved_by, resolved_at, <audit>)

-- GRAPH (TENANT-SCOPED) ---------------------------------------------------
supplier_relationships(
  id, org_id FK NOT NULL,
  from_company_id FK NOT NULL, to_company_id FK NULL, to_org_id FK NULL,
  relationship_type TEXT NOT NULL,
  tier SMALLINT, criticality SMALLINT CHECK (criticality BETWEEN 1 AND 5),
  annual_spend_usd NUMERIC(18,2), category TEXT, single_source BOOL DEFAULT false,
  lead_time_days INT,
  confidence NUMERIC(3,2) DEFAULT 1.0,
  source TEXT CHECK (source IN ('user_declared','gleif','inferred','document')),
  source_record_id FK NULL,
  valid_from DATE NOT NULL DEFAULT CURRENT_DATE, valid_to DATE NULL,
  verified_at, verified_by, deleted_at, <audit>,
  CHECK (to_company_id IS NOT NULL OR to_org_id IS NOT NULL))
  INDEX (org_id, from_company_id) WHERE valid_to IS NULL;
  INDEX (org_id, to_company_id)   WHERE valid_to IS NULL;
  RLS ENABLED

locations(id, country CHAR(2) NOT NULL, region, city, lat, lon, geohash)
company_locations(id, company_id FK, location_id FK, site_type, is_primary,
                  source, confidence, valid_from, valid_to)

-- INGESTION ---------------------------------------------------------------
data_sources(
  id, source_key TEXT UNIQUE,                      -- 'ofac_sls','gdelt_doc'
  name, source_type, base_url, auth_type,
  reliability TEXT CHECK (reliability IN ('high','medium','low')),
  license_terms TEXT, terms_verified_at DATE,      -- per E.x verification note
  coverage_notes TEXT,
  poll_interval_seconds INT, is_enabled BOOL DEFAULT true,
  status TEXT DEFAULT 'healthy',                   -- healthy|degraded|failed
  last_success_at, last_failure_at, consecutive_failures INT DEFAULT 0,
  config JSONB, <audit>)

source_records(
  id, source_id FK NOT NULL,
  external_id TEXT, content_hash TEXT NOT NULL,
  canonical_url TEXT, title TEXT, published_date, retrieved_at NOT NULL,
  raw_s3_key TEXT NOT NULL,                        -- full payload in S3
  normalized JSONB NOT NULL,
  source_type TEXT CHECK (source_type IN ('live','cached')),
  reliability TEXT, language CHAR(2),
  processing_status TEXT DEFAULT 'pending',
  seen_count INT DEFAULT 1, last_seen_at, <audit>,
  UNIQUE (source_id, external_id),                 -- idempotency layer 1
  UNIQUE (source_id, content_hash))                -- idempotency layer 2

source_record_versions(id, source_record_id FK, version INT, content_hash,
                       normalized JSONB, raw_s3_key, detected_at,
                       UNIQUE (source_record_id, version))

dead_letter_queue(id, task_name, payload JSONB, error, traceback,
                  retry_count, status, created_at, replayed_at, replayed_by)

-- EVENTS (GLOBAL) ---------------------------------------------------------
events(
  id, event_cluster_key TEXT NOT NULL,             -- semantic dedupe key
  event_type TEXT NOT NULL, jurisdictions CHAR(2)[],
  affected_materials TEXT[], affected_hs_codes TEXT[],
  effective_date, expiry_date, published_date,
  summary TEXT NOT NULL,                           -- OUR paraphrase
  severity_signal TEXT, confidence NUMERIC(3,2),
  corroboration_count INT DEFAULT 1,
  status TEXT DEFAULT 'active',                    -- active|superseded|extraction_failed
  superseded_by FK NULL,
  extracted_by_model TEXT, prompt_version TEXT, <audit>)
  INDEX (event_cluster_key);  INDEX GIN (jurisdictions);
  INDEX GIN (to_tsvector('english', summary));

event_source_records(event_id FK, source_record_id FK, PRIMARY KEY(both))
event_entities(
  id, event_id FK, company_id FK NULL, raw_mention TEXT NOT NULL,
  role TEXT,                                       -- subject|affected|issuer
  resolution_confidence, resolution_method,        -- identifier|domain|exact|fuzzy|ai|unresolved
  evidence_span JSONB)

-- RISK & ALERTS (TENANT-SCOPED) -------------------------------------------
risk_model_versions(id, version TEXT UNIQUE, weights JSONB, thresholds JSONB,
                    is_active BOOL, activated_at, <audit>)

risk_assessments(
  id, org_id FK NOT NULL, event_id FK NOT NULL, company_id FK NOT NULL,
  impact_score NUMERIC(5,2) NOT NULL, severity_band TEXT NOT NULL,
  confidence NUMERIC(3,2) NOT NULL,
  factors JSONB NOT NULL,                          -- FULL breakdown, every factor
  graph_path JSONB NOT NULL,                       -- the literal edge chain
  path_depth SMALLINT, path_confidence NUMERIC(3,2),
  completeness JSONB,                              -- which inputs were missing
  model_version TEXT NOT NULL, computed_at, <audit>,
  UNIQUE (org_id, event_id, company_id))           -- idempotent recompute
  RLS ENABLED

alerts(
  id, org_id FK NOT NULL, risk_assessment_id FK NOT NULL,
  event_id FK NOT NULL, company_id FK NOT NULL,
  headline TEXT NOT NULL, explanation TEXT, why_it_matters TEXT,
  recommendations JSONB DEFAULT '[]',
  severity_band TEXT NOT NULL, impact_score NUMERIC(5,2) NOT NULL,
  confidence NUMERIC(3,2) NOT NULL,
  needs_human_judgment BOOL DEFAULT false,
  target_personas TEXT[] DEFAULT '{risk_manager,category_manager}',
  category TEXT,
  status TEXT DEFAULT 'new',                       -- new|acknowledged|investigating
                                                   -- |escalated|dismissed|resolved
  dismissed_reason TEXT, assigned_to TEXT,
  explanation_model TEXT, explanation_prompt_version TEXT,
  first_notified_at, deleted_at, <audit>)
  INDEX (org_id, status, severity_band, created_at DESC);
  RLS ENABLED

alert_evidence(
  id, alert_id FK NOT NULL,
  evidence_type TEXT CHECK (evidence_type IN
    ('source_record','graph_path','spend_record','document_chunk','score_factor')),
  source_record_id FK NULL, chunk_id FK NULL,
  source_url TEXT, source_name TEXT,
  source_type TEXT CHECK (source_type IN ('live','cached')),
  retrieved_at, excerpt TEXT, payload JSONB, display_order INT)
-- ENFORCES engineering rule 9:
ALTER TABLE alerts ADD CONSTRAINT alert_must_have_evidence
  CHECK (id IN (SELECT alert_id FROM alert_evidence));  -- via deferred trigger

alert_actions(id, alert_id FK, user_id, action, note, created_at)

-- SPEND -------------------------------------------------------------------
uploaded_documents(
  id, org_id FK NOT NULL, doc_type, filename, s3_key, content_hash,
  file_size_bytes, mime_type,
  parse_status TEXT DEFAULT 'pending',             -- pending|parsed|needs_review|failed
  parse_confidence NUMERIC(3,2), parsed_payload JSONB, parse_errors JSONB,
  uploaded_by, virus_scan_status, deleted_at, <audit>,
  UNIQUE (org_id, content_hash))                   -- no duplicate uploads
  RLS ENABLED

contracts(id, org_id FK, company_id FK, contract_number, category,
          start_date, end_date, renewal_terms JSONB,
          agreed_unit_prices JSONB, payment_terms JSONB,
          source_document_id FK, deleted_at, <audit>)  RLS

purchase_orders(id, org_id FK, po_number, company_id FK, contract_id FK NULL,
                order_date, total_amount NUMERIC(18,2), currency,
                line_items JSONB, source_document_id FK, deleted_at, <audit>)
                UNIQUE (org_id, po_number)  RLS

spend_records(id, org_id FK, company_id FK, po_id FK NULL, contract_id FK NULL,
              invoice_number, amount NUMERIC(18,2), currency, spend_date,
              category, source_document_id FK, deleted_at, <audit>)
              UNIQUE (org_id, company_id, invoice_number)  RLS

spend_leakage_findings(
  id, org_id FK NOT NULL,
  finding_type TEXT CHECK (finding_type IN
    ('maverick_spend','duplicate_payment','price_variance','missed_discount')),
  company_id FK, category, amount_usd NUMERIC(18,2), confidence NUMERIC(3,2),
  regulatory_overlap BOOL DEFAULT false,           -- THE differentiator
  risk_assessment_id FK NULL, evidence JSONB NOT NULL,
  status TEXT DEFAULT 'open', <audit>)  RLS

-- AI / RAG ----------------------------------------------------------------
documents(id, org_id FK NULL, document_type, title, source_url,
          jurisdiction, published_date, effective_date, language,
          source_reliability, s3_key, content_hash, <audit>)

document_chunks(id, document_id FK, chunk_index, content TEXT NOT NULL,
                section_path TEXT, token_count, metadata JSONB)
                INDEX GIN (to_tsvector('english', content))

embeddings(id, chunk_id FK NOT NULL, model TEXT NOT NULL, dimensions INT NOT NULL,
           embedding vector(1024), created_at,
           UNIQUE (chunk_id, model))
           INDEX USING hnsw (embedding vector_cosine_ops) WHERE model = 'voyage-3'

agent_runs(
  id, org_id FK NULL, agent_name, workflow_run_id UUID,
  input_ref JSONB, output_ref JSONB,
  model TEXT, prompt_version TEXT,
  prompt_tokens INT, completion_tokens INT, cost_usd NUMERIC(10,6),
  latency_ms INT, status, error, langfuse_trace_id, created_at)
  INDEX (org_id, created_at DESC);  INDEX (agent_name, created_at DESC)

-- NOTIFICATIONS -----------------------------------------------------------
notification_preferences(id, org_id FK, user_id,
  channel TEXT, min_severity TEXT, digest_frequency TEXT,
  categories TEXT[], quiet_hours JSONB, is_enabled BOOL,
  UNIQUE (org_id, user_id, channel))  RLS

notifications(id, org_id FK, user_id, alert_id FK NULL, notification_type,
              title, body, link_url, read_at, created_at)  RLS

notification_deliveries(id, notification_id FK, channel, provider,
  idempotency_key TEXT UNIQUE NOT NULL,            -- prevents double-send
  status, provider_message_id, attempt_count INT DEFAULT 0,
  last_error, sent_at, delivered_at, opened_at)

-- AUDIT -------------------------------------------------------------------
audit_logs(id, org_id FK NULL, user_id, actor_type,      -- user|system|agent
  action TEXT NOT NULL, resource_type, resource_id,
  changes JSONB, ip_address INET, user_agent, request_id, created_at)
  -- APPEND-ONLY: REVOKE UPDATE, DELETE ON audit_logs FROM app_role;
  PARTITION BY RANGE (created_at);                 -- monthly partitions
```

## M.2 Key Relationships
- `organizations.company_id → companies.id` — the tenant is itself a canonical entity (so it can be a node in its own graph and be matched by ER).
- `supplier_relationships` is the **only** table encoding who-buys-from-whom and is the **only one** carrying `org_id` on the graph — this is the privacy boundary of G.3.
- `events` ← `event_source_records` → `source_records` is many-to-many by design: one event, many corroborating sources.
- `risk_assessments` has `UNIQUE (org_id, event_id, company_id)` so recomputation is idempotent — re-running the pipeline updates rather than duplicates.
- `alert_evidence` is the enforcement point for "no claim without evidence."


---

# PART N — API SPECIFICATION (§13)

## N.1 Conventions
- Base: `https://api.provenance.app/v1`. Auth: `Authorization: Bearer <JWT>` on everything except `/health`.
- **Pagination:** cursor-based (`?cursor=&limit=`, max 100). Offset pagination is rejected — alert lists change under the user constantly and offset produces skipped/duplicated rows.
- **Filtering:** `?status=new&severity=high,critical&from=&to=`. **Sorting:** `?sort=-created_at`.
- **Errors:** RFC 9457 `application/problem+json`.
- **Idempotency:** `Idempotency-Key` header required on all POSTs that create resources.
- **Rate limits:** 1000 req/h per user, 10k/h per org; `/ai/*` 60/h per user; `429` with `Retry-After`.
- **Every response** includes `X-Request-Id` (correlates to logs and traces).

## N.2 Endpoint Catalog

| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/auth/me` | any | current user + org + role + persona |
| GET/PATCH | `/organizations/{id}` | member / org_admin | |
| GET/POST/DELETE | `/organizations/{id}/members` | org_admin | invite/remove |
| GET | `/companies/search?q=&country=` | analyst | ER-backed typeahead over canonical registry |
| GET | `/companies/{id}` | analyst | enriched profile + identifiers + locations |
| POST | `/companies/resolve` | analyst | run ER cascade, return match or review |
| GET | `/suppliers` | org_user | tenant's suppliers + current risk |
| POST | `/suppliers` | analyst | add supplier (triggers ER) |
| POST | `/suppliers/bulk` | analyst | CSV bulk add — async, returns `job_id` |
| PATCH/DELETE | `/suppliers/{id}` | analyst | criticality/spend/soft-delete |
| GET/POST | `/relationships` | analyst | edges |
| GET | `/graph?root=&depth=&types=` | org_user | node/edge payload, capped |
| GET | `/graph/paths?from=&to=` | org_user | explain connection |
| GET | `/events` | org_user | global events, filtered |
| GET | `/events/{id}` | org_user | + source records + entities |
| GET | `/alerts` | org_user | **primary endpoint**; persona-filtered |
| GET | `/alerts/{id}` | org_user | full evidence chain |
| PATCH | `/alerts/{id}` | org_user | status/assignee/dismiss reason |
| GET | `/alerts/{id}/evidence` | org_user | ordered evidence records |
| GET | `/risks/summary` | org_user | dashboard aggregates |
| POST | `/ai/investigate` | analyst | conversational, SSE stream |
| GET | `/notifications` + `POST /{id}/read` | org_user | in-app |
| GET/PUT | `/notifications/preferences` | org_user | |
| POST | `/documents` | analyst | multipart upload → async parse |
| GET | `/documents/{id}` | analyst | parse status/results |
| GET | `/spend/findings` | analyst | leakage findings |
| GET | `/entity-reviews` + `POST /{id}/resolve` | analyst | ER review queue |
| GET | `/search?q=` | org_user | cross-entity search |
| GET | `/reports/exposure?format=pdf\|csv` | analyst | export with citations |
| GET | `/admin/data-sources` + `PATCH /{id}` | platform_admin | |
| GET | `/admin/dlq` + `POST /{id}/replay` | platform_admin | |
| GET | `/admin/ai-usage` | platform_admin | cost/tokens by tenant |
| GET | `/admin/audit-logs` | platform_admin | |
| GET | `/health` `/health/ready` | public | liveness / readiness |

## N.3 Example — the primary read path

**`GET /v1/alerts?status=new&severity=critical,high&limit=20`**
```json
{
  "data": [{
    "id": "a1b2c3d4-0000-4000-8000-000000000001",
    "headline": "Export licence requirement imposed on dysprosium affects Yixin Alloys",
    "severity_band": "CRITICAL",
    "impact_score": 82.4,
    "confidence": 0.88,
    "needs_human_judgment": false,
    "status": "new",
    "company": { "id": "…", "legal_name": "Henan Yixin Specialty Alloys Co., Ltd",
                 "country": "CN", "lei": "…" },
    "event": { "id": "…", "event_type": "export_restriction",
               "effective_date": "2026-11-10", "jurisdictions": ["CN"] },
    "factors": {
      "event_severity": 0.75, "dependency_strength": 0.82,
      "evidence_quality": 0.91, "urgency_multiplier": 0.35,
      "exposure_multiplier": 1.22
    },
    "graph_path": [
      { "from": "Henan Yixin Specialty Alloys", "type": "supplies_to",
        "to": "Acme Manufacturing", "depth": 1, "confidence": 1.0,
        "source": "user_declared" }
    ],
    "evidence_count": 4,
    "created_at": "2026-09-21T08:42:15Z"
  }],
  "pagination": { "next_cursor": "eyJpZCI6…", "has_more": true }
}
```

**`GET /v1/alerts/{id}/evidence`**
```json
{
  "data": [
    { "evidence_type": "source_record", "source_name": "Federal Register",
      "source_url": "https://www.federalregister.gov/documents/…",
      "source_type": "live", "retrieved_at": "2026-09-21T06:15:00Z",
      "excerpt": "…paraphrased summary of the operative provision…",
      "display_order": 1 },
    { "evidence_type": "graph_path",
      "payload": { "edges": [ { "from_company": "Henan Yixin Specialty Alloys",
                                "relationship_type": "supplies_to",
                                "to_org": "Acme Manufacturing",
                                "confidence": 1.0, "source": "user_declared",
                                "valid_from": "2024-01-15" } ] },
      "display_order": 2 },
    { "evidence_type": "score_factor",
      "payload": { "factor": "dependency_strength", "value": 0.82,
                   "inputs": { "path_confidence": 1.0, "tier_decay": 1.0,
                               "criticality": 4, "single_source": true } },
      "display_order": 3 }
  ]
}
```

**`POST /v1/ai/investigate`** (SSE)
```json
// request
{ "question": "Why is Henan Yixin flagged?", "alert_id": "a1b2c3d4-…" }
// streamed result
{ "answer": "…grounded explanation…",
  "citations": [ { "type": "alert_evidence", "id": "…",
                   "source_url": "https://…", "source_type": "live" } ],
  "tools_used": ["get_alert_evidence","query_graph"],
  "confidence": 0.86 }
```

**Error**
```json
{ "type": "https://api.provenance.app/errors/validation-error",
  "title": "Validation failed", "status": 422,
  "detail": "criticality must be between 1 and 5",
  "instance": "/v1/suppliers", "request_id": "req_01J…",
  "errors": [ { "field": "criticality", "code": "out_of_range" } ] }
```

---

# PART O — NOTIFICATIONS (§15)

**Channels:** in-app (always), email (**Resend** or AWS SES), Slack (incoming webhook/app), Microsoft Teams (**required** — the buyer persona lives in Teams far more than Slack). Push: **not in MVP** (no mobile app).

**Routing rules (defaults, per-user overridable):**
| Severity | Channel | Timing |
|---|---|---|
| CRITICAL | in-app + email + Slack/Teams | immediate |
| HIGH | in-app + email | immediate, **batched in a 15-min window** |
| MEDIUM | in-app + daily digest | 08:00 local |
| LOW | in-app only | weekly digest Monday 08:00 |

**Batching is deliberate:** one regulatory event can intersect 30 suppliers. Thirty emails destroys trust in the product permanently. The 15-minute window groups by `event_id` into one message: "1 event affects 30 of your suppliers."

**Every notification contains:** the headline, severity, affected supplier, impact score, **a deep link to the alert**, and the top evidence source with its live/cached tag.

**Delivery guarantees:** `idempotency_key = hash(notification_id, channel, user_id)` UNIQUE — double-send is structurally impossible. Retries: 5 attempts, exponential backoff, then `failed` + admin alert. Bounce/complaint webhooks disable the channel for that user and notify them in-app. Full lifecycle tracked (`sent_at`, `delivered_at`, `opened_at`).

**Quiet hours** respected for non-CRITICAL only.

---

# PART P — MONITORING & SCHEDULED JOBS (§16)

## P.1 Schedule
| Job | Frequency |
|---|---|
| GDELT global material/commodity queries | 30 min |
| GDELT per-tenant supplier queries (batched) | 4 h |
| Federal Register poll | 1 h |
| OFAC SLS / EU sanctions / EUR-Lex | 6 h |
| UN / UK sanctions | daily 02:00 |
| DGFT / CBIC HTML monitor | 4 h |
| data.gov.in reference refresh | daily 03:00 |
| GLEIF enrichment (graph entities) | nightly 01:00 |
| Risk recompute (time-decay, approaching effective dates) | daily 04:00 |
| Digest emails | daily 08:00 / weekly Mon 08:00 |
| Spend leakage re-scan | daily 05:00 |
| Data-freshness check → admin alert | 15 min |
| Embedding backfill for new documents | continuous |
| Partition maintenance / vacuum | weekly |

## P.2 Real-Time
Webhooks (none of the MVP sources offer them — noted honestly; webhook receiver infra is built in Phase 2 when a paid provider that supports them is added), user-triggered investigations, uploads.

## P.3 Admin Monitoring & Alert Thresholds
Per-source: availability, p95 latency, failure rate, rate-limit headroom, **data freshness** (`now() - last_success_at` vs. 3× poll interval → page). Pipeline: queue depth by queue, DLQ size (>0 → notify; >50 → page), processing lag. AI: token consumption vs. budget, cost/tenant/day, agent failure rate, schema-validation failure rate. Quality: alerts generated/day, **dismissal rate as false-positive proxy**, ER auto-resolve rate, review-queue depth.

---

# PART Q — SECURITY (§17)

**Transport:** TLS 1.3, HSTS preload, no TLS < 1.2. **At rest:** RDS/S3/ElastiCache encrypted with KMS CMKs; automated key rotation.

**Secrets:** AWS Secrets Manager, injected as ECS task secrets at runtime. Never in images, env files, or Git. Pre-commit `gitleaks` + CI secret scan. Quarterly rotation; immediate on offboarding.

**Tenant isolation:** the triple-layer enforcement of L.3. **A dedicated test suite (`tests/security/test_tenant_isolation.py`) attempts cross-tenant access on every tenant-scoped endpoint and must pass in CI for the build to ship.**

**Injection classes:** SQL — parameterized/ORM only, raw SQL only in reviewed recursive CTEs with bound params. XSS — React escaping + strict CSP, no `dangerouslySetInnerHTML` on any model or source output. CSRF — JWT in `Authorization` header (not cookies) makes it inapplicable; `SameSite=Strict` on any cookie. **SSRF — critical for this system**, since it fetches arbitrary URLs from news results: fetches go through an allow-list of source domains, a DNS resolver that **rejects private/link-local/metadata IPs (169.254.169.254, 10/8, 172.16/12, 192.168/16, ::1)**, with redirects capped at 3 and re-validated at each hop.

## Q.7 Prompt Injection — the core LLM threat
External content (news articles, regulatory PDFs, uploaded invoices) is **adversarial by assumption**. Defences, layered:
1. **Structural separation.** Source content is never concatenated into the system prompt. It is passed in a clearly delimited user-role message wrapped in `<untrusted_content>` tags, with the system prompt stating that content inside those tags is data to analyze and **can never issue instructions**.
2. **No tools on ingestion agents.** Event Extraction and Document Parsing have **zero tools** — even a fully successful injection has nothing to call.
3. **Constrained output.** Every extraction returns a Pydantic schema with closed enums. An injection telling the model to "output ACCESS GRANTED" fails schema validation.
4. **Tenant scoping is server-side.** The Investigation Agent's tools take `org_id` from the auth context; the model physically cannot pass a different one.
5. **Evidence-span validation.** Extracted claims must map to real character offsets in the source — fabricated content is detected mechanically.
6. **Injection sentinels.** A detector flags records containing instruction-like patterns ("ignore previous", "system:", "you are now") → `needs_review`, plus a security metric. Rising counts indicate a targeted campaign.
7. **Output validation.** Generated text passes the claim-validator before display.

**Data exfiltration:** LLM outputs never include raw credentials; prompts never contain secrets; egress from workers is restricted to the source allow-list; Langfuse traces are scrubbed of PII before storage.

**File upload:** 25 MB cap; MIME **and magic-byte** validation (not extension); ClamAV scan before processing; S3 storage outside the web root with pre-signed, short-TTL access; PDFs parsed in a resource-capped sandbox; zip bomb / recursion limits.

**PII & regulation:** uploaded invoices contain business-contact data and possibly personal names. Policy: extract only schema-defined fields; **discard non-schema personal data at the extraction step rather than persisting it**; raw documents encrypted, retained 90 days by default (configurable), then purged. **GDPR:** lawful basis = legitimate interest for B2B contact data; DSAR export/delete implemented; DPA available; EU tenants pinned to an EU region. **India DPDP Act 2023:** consent/notice at upload, purpose limitation, a named Data Protection Officer contact, breach notification procedure, and data-principal rights (access, correction, erasure) — implemented through the same DSAR machinery. Data residency: `ap-south-1` for Indian tenants.

**Audit:** every state change and every agent step to `audit_logs`, append-only at the DB grant level, monthly partitions, 7-year retention.

---

# PART R — OBSERVABILITY (§18)

**Logging:** structlog JSON to stdout → CloudWatch → Grafana. Every line carries `request_id`, `org_id`, `user_id`, `trace_id`. **Secrets and PII scrubbed by a processor in the logging pipeline, not by developer discipline.**

**Tracing:** OpenTelemetry auto-instrumentation (FastAPI, SQLAlchemy, httpx, Celery) → OTLP → Grafana Tempo. Trace context propagated into Celery tasks so an ingestion run is one trace end to end.

**Errors:** Sentry, both runtimes, releases tagged, source maps uploaded.

**AI observability:** Langfuse — every call traced with prompt version, model, tokens, cost, latency, and input/output.

**Metrics (Prometheus naming):**
```
provenance_events_ingested_total{source, status}
provenance_events_processed_total{stage, status}
provenance_events_failed_total{stage, error_type}
provenance_duplicate_records_total{source}
provenance_alerts_generated_total{org, severity}
provenance_alerts_sent_total{channel, status}
provenance_alert_dismissal_rate{org}               # false-positive proxy
provenance_entity_resolution_confidence{method}    # histogram
provenance_entity_resolution_stage_total{stage}    # ≥80% must be < stage 6
provenance_ai_latency_seconds{agent, model}        # histogram
provenance_ai_cost_usd_total{agent, model, org}
provenance_ai_schema_validation_failures_total{agent}
provenance_api_failure_rate{source}
provenance_data_freshness_seconds{source}          # gauge — critical
provenance_graph_traversal_seconds{depth}          # Neo4j migration trigger
provenance_queue_depth{queue}
provenance_dlq_size
provenance_prompt_injection_detected_total{source}
```

**Dashboards:** Pipeline Health, Data Source Health, AI Cost & Quality, Alert Quality, Tenant Activity, Infrastructure.

**SLOs:** API p95 < 500 ms; alert latency (event published → notification) p95 < 30 min for CRITICAL; data freshness within 3× poll interval for every source; 99.5% uptime MVP.


---

# PART S — FRONTEND UX (§19)

| Screen | Contents |
|---|---|
| **Dashboard** | KPI row (active alerts by severity, suppliers monitored, total spend exposed, data freshness); critical-alert feed; exposure-by-jurisdiction map; upcoming regulatory deadlines with day countdowns; **regulatory-overlap callout** (spend leakage ∩ live risk) styled distinctly; 30-day risk trend |
| **Alerts** | Filterable/sortable list; severity badges; bulk triage; each row expands to the evidence chain. Persona toggle reframes default filters, not permissions |
| **Alert Detail** | Headline, severity + score with **expandable factor-by-factor breakdown**, confidence, AI explanation with inline citation chips (live/cached tagged), the graph path rendered as a visual chain, all evidence sources, recommended considerations, action bar (Acknowledge / Escalate / Dismiss-with-reason / Export), **and an "Ask about this" box** opening the Investigation Agent scoped to this alert |
| **Suppliers** | Table + card views; risk level, criticality, spend, country, tier; add/bulk-upload; per-supplier drill-down |
| **Supplier Detail** | Profile + identifiers (LEI/CIN), locations, relationship to org, risk history timeline, related events, connected entities, spend summary |
| **Graph** | Cytoscape canvas; colour = risk, size = spend, dashed = inferred edge; filter by tier/country/risk; click-to-expand; click-node → detail panel; export PNG |
| **Investigate** | Full-page chat; suggested prompts; every answer's citations clickable to source |
| **Data** | Drag-drop upload; parse-status table (Parsed / Needs Review / Failed); field-mapping confirmation for ambiguous CSV columns; spend-leakage findings list |
| **Review Queue** | ER ambiguous cases: raw mention, candidates with scores and AI reasoning, one-click Match / New Entity / Reject |
| **Settings** | Org profile, members & roles, notification preferences, categories, alert thresholds |
| **Admin** (platform_admin) | §20 |

**Design rules:** no button anywhere says Approve/Execute/Send — actions are View Evidence, Mark Reviewed, Escalate, Export. Citation chips are visually distinct from body text. Cached-source claims are visibly marked. Low-confidence findings render with a "needs human judgment" badge instead of a rank.

**Accessibility:** WCAG 2.1 AA; never colour alone for severity (icon + text label always).

---

# PART T — ADMIN PORTAL (§20)

Users & orgs (list, impersonate **with audit + banner**, suspend); data sources (enable/disable, interval, credentials via Secrets Manager references only — **never displayed**, health, last success, coverage notes, terms-verified date); agent config (model routing per task, prompt version pinning, temperature, token caps — **prompts are selected from Git-versioned files, never free-text edited**); alert rules (thresholds, severity bands, per-tenant overrides); system health (queues, DLQ with replay, failed jobs, source status); ER review oversight; AI usage & cost by tenant/agent/model with budget alerts; audit-log search; feature flags.

---

# PART U — ENVIRONMENT VARIABLES (§22)

```env
# ── Core ──────────────────────────────────────────────────────────────
ENVIRONMENT=                      # local|staging|production
LOG_LEVEL=INFO
API_BASE_URL=
FRONTEND_URL=
SECRET_KEY=                       # app signing; Secrets Manager

# ── Database ─ RDS endpoint; Secrets Manager (rotated) ───────────────
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/provenance
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# ── Redis ─ ElastiCache endpoint ─────────────────────────────────────
REDIS_URL=redis://host:6379/0
CELERY_BROKER_URL=redis://host:6379/1
CELERY_RESULT_BACKEND=redis://host:6379/2

# ── Auth ─ Clerk dashboard ───────────────────────────────────────────
CLERK_SECRET_KEY=                 # backend JWT verification
CLERK_PUBLISHABLE_KEY=            # frontend (public, safe to expose)
CLERK_JWKS_URL=
CLERK_WEBHOOK_SECRET=             # user/org sync webhooks
AUTH_ISSUER=
AUTH_AUDIENCE=

# ── LLM ─ provider consoles; LiteLLM routes on these ─────────────────
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=
OPENAI_API_KEY=                   # fallback route only
LLM_MODEL_EXTRACTION=
LLM_MODEL_CLASSIFICATION=
LLM_MODEL_EXPLANATION=
LLM_MODEL_INVESTIGATION=
LLM_MAX_RETRIES=2
LLM_TIMEOUT_SECONDS=60
DEFAULT_MONTHLY_TOKEN_BUDGET=5000000

EMBEDDING_PROVIDER=voyage
EMBEDDING_API_KEY=
EMBEDDING_MODEL=voyage-3
EMBEDDING_DIMENSIONS=1024

LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=

# ── External data sources ────────────────────────────────────────────
DATA_GOV_IN_API_KEY=              # register at data.gov.in (free)
GDELT_USER_AGENT=                 # REQUIRED — GDELT rejects blank UA
GDELT_MIN_REQUEST_INTERVAL_SECONDS=6
OFAC_SLS_BASE_URL=https://sanctionslistservice.ofac.treas.gov
FEDERAL_REGISTER_BASE_URL=https://www.federalregister.gov/api/v1
GLEIF_BASE_URL=https://api.gleif.org/api/v1
EU_SANCTIONS_TOKEN=               # free token from EU FSF
EURLEX_WS_USERNAME=
EURLEX_WS_PASSWORD=
# OPENSANCTIONS_API_KEY=          # Phase 2 ONLY — commercial licence required

# ── Storage ─ AWS ────────────────────────────────────────────────────
AWS_REGION=ap-south-1
S3_BUCKET_DOCUMENTS=
S3_BUCKET_RAW_PAYLOADS=
S3_BUCKET_EXPORTS=

# ── Email / chat ─────────────────────────────────────────────────────
EMAIL_PROVIDER=resend
EMAIL_PROVIDER_API_KEY=
EMAIL_FROM_ADDRESS=
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=
TEAMS_APP_ID=
TEAMS_APP_PASSWORD=

# ── Observability ────────────────────────────────────────────────────
SENTRY_DSN=
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_SERVICE_NAME=provenance-api

# ── Security ─────────────────────────────────────────────────────────
ENCRYPTION_KEY=                   # KMS-backed, field-level encryption
ALLOWED_ORIGINS=
RATE_LIMIT_PER_USER_HOUR=1000
MAX_UPLOAD_SIZE_MB=25
CLAMAV_HOST=
```
**Rules:** `.env.example` is committed with keys and comments and **no values**. Production values live only in Secrets Manager and are injected as ECS task secrets. Only `CLERK_PUBLISHABLE_KEY` and `NEXT_PUBLIC_*` are ever exposed to the browser.

---

# PART V — REPOSITORY STRUCTURE (§23)

```
provenance/
├── frontend/                     # Next.js 15
│   ├── src/app/                  # routes: (auth) (dashboard) admin
│   ├── src/components/           # ui/ (shadcn) alerts/ graph/ suppliers/
│   ├── src/lib/api/              # GENERATED client — do not hand-edit
│   ├── src/lib/hooks/            # TanStack Query hooks
│   └── tests/                    # vitest + playwright
├── backend/
│   └── app/
│       ├── main.py               # FastAPI app factory
│       ├── config.py             # Pydantic Settings — the ONLY env reader
│       ├── api/v1/               # routers, one per resource
│       ├── core/                 # deps, security, pagination, errors, rls
│       ├── auth/providers/       # clerk.py implements TokenVerifier
│       ├── modules/              # DOMAIN MODULES — see D.2
│       │   ├── organizations/    # each: router, service, repository,
│       │   ├── companies/        #       models, schemas, tests
│       │   ├── graph/
│       │   ├── events/
│       │   ├── risk/             # scoring.py — DETERMINISTIC, no LLM import
│       │   ├── alerts/
│       │   ├── spend/
│       │   ├── notifications/
│       │   └── admin/
│       └── db/                   # session, base, rls.py
├── ingestion/
│   ├── connectors/               # one file per source, SourceConnector impl
│   │   ├── ofac.py gleif.py gdelt.py federal_register.py eurlex.py
│   │   ├── eu_sanctions.py un_sanctions.py uk_ofsi.py data_gov_in.py
│   │   ├── dgft_html.py cbic_html.py        # HTML monitors, documented
│   │   └── cached_snapshots.py              # MOFCOM/ARECOMS, source_type=cached
│   ├── pipeline/                 # normalize, dedupe, extract, resolve, score
│   └── fixtures/                 # RECORDED real responses for offline tests
├── agents/
│   ├── graphs/                   # LangGraph definitions
│   ├── prompts/                  # VERSIONED: event_extraction/v1.md, v2.md …
│   ├── schemas/                  # Pydantic structured-output models
│   ├── tools/                    # tool impls; org_id injected server-side
│   ├── gateway.py                # LLMGateway — the ONLY LiteLLM caller
│   └── rag/                      # chunking, embedding, hybrid retrieval
├── workers/                      # celery_app.py, tasks/, schedules.py
├── database/
│   ├── migrations/               # Alembic
│   └── seeds/                    # data_sources rows, risk model v1
├── infrastructure/
│   ├── terraform/                # modules/ environments/{staging,production}
│   └── docker/                   # Dockerfile.api .worker .frontend
├── tests/                        # unit/ integration/ e2e/ security/ evals/
│   ├── security/test_tenant_isolation.py   # BLOCKING in CI
│   └── evals/datasets/           # golden sets for AI evaluation
├── docs/                         # architecture.md data_sources.md runbooks/
├── scripts/                      # seed_dev_data.py backfill.py verify_sources.py
├── .env.example
├── docker-compose.yml
└── README.md
```

---

# PART W — DEPLOYMENT & CI/CD (§24)

**Local:** `docker compose up` → postgres (pgvector image) + redis + api + worker + beat + frontend + mailhog + localstack (S3). `scripts/seed_dev_data.py` creates two tenants, a supplier graph, and recorded source fixtures so the full pipeline runs offline with **zero external API calls**.

**Staging:** own AWS account, own Clerk instance, own database, real source connectors at reduced frequency, synthetic tenants only. **Never production data.**

**Production:** ALB + TLS 1.3 (ACM); ECS Fargate api (2–10 tasks, target-tracking autoscale on CPU 70% + ALB req/target) and workers (2–20, autoscale on queue depth via custom CloudWatch metric); RDS Multi-AZ with PITR, automated backups 30 days, monthly restore drill; ElastiCache Multi-AZ; S3 versioned + cross-region replication; WAF (rate rules + managed rulesets); Secrets Manager with rotation. **DR:** RPO 1 h, RTO 4 h, documented and **tested quarterly** — an untested DR plan is not a DR plan.

**CI/CD (GitHub Actions):**
```
push/PR
 → lint (ruff, mypy --strict, eslint, tsc --noEmit)
 → unit tests (pytest, vitest) — coverage gate ≥80% on modules/, ≥95% on risk/
 → integration tests (ephemeral postgres+redis services)
 → SECURITY: gitleaks, pip-audit, npm audit, Trivy image scan,
             tests/security/test_tenant_isolation.py         [BLOCKING]
 → AI evals (golden datasets, thresholds in §30)             [BLOCKING]
 → build + push to ECR, generate OpenAPI → regenerate FE client → fail on drift
 → deploy staging (auto on main)
 → smoke tests (Playwright critical paths)
 → MANUAL APPROVAL
 → deploy production (blue/green via ECS CodeDeploy, auto-rollback on alarm)
 → post-deploy smoke + Sentry release marker
```
Migrations run as a one-off ECS task **before** the new task set takes traffic; **expand/contract pattern only** — every migration must be backward-compatible with the previous app version so blue/green never breaks mid-deploy.

---

# PART X — TESTING STRATEGY (§25, §35)

**Unit** — scoring arithmetic (every factor, boundary values, missing inputs); ER normalization and each cascade stage; connector `normalize()` against recorded fixtures; validation schemas; permission logic. *Coverage: ≥95% on `modules/risk/` and `ingestion/pipeline/` — these encode the product's correctness.*

**Integration** — repository tenant scoping; RLS actually blocking cross-tenant reads; recursive CTE correctness including cycles; Celery retry/DLQ; idempotent re-ingestion (**ingest the same payload 3× → exactly 1 event**); notification idempotency; auth flows.

**E2E (Playwright)** — the full journey: login → create org → add supplier (ER resolves) → ingest fixture event → pipeline runs → alert appears → evidence chain renders → notification recorded → investigate returns cited answer.

**AI evaluation (blocking in CI)** — golden datasets in `tests/evals/datasets/`:

| Eval | Dataset | Acceptance criteria |
|---|---|---|
| Event extraction | 200 labelled records | event_type accuracy ≥90%; date extraction ≥95%; **hallucinated-span rate = 0%**; schema validity ≥99% |
| Relevance classification | 200 (100 relevant / 100 not) | precision ≥85%, recall ≥80% |
| Entity resolution | 150 pairs incl. hard negatives | precision ≥95% (**false merges are the costly error**), recall ≥85%, auto-resolve before Stage 6 ≥80% |
| Impact scoring | 100 scenarios, expert-labelled bands | band agreement ≥80%; **determinism: identical input → identical score, 100%** |
| Alert explanation | 100 assessments | every claim maps to supplied evidence = 100%; no unsupported facts = 100%; no imperative/execution language = 100% |
| Source attribution | 100 investigation answers | citation present ≥98%; citation actually supports claim ≥95% |
| **Prompt injection** | 50 adversarial payloads | instruction-following rate **0%**; all either extract correctly or route to `needs_review` |
| Document parsing | 50 real-format invoices/POs | field accuracy ≥95% on monetary fields; totals reconcile 100%; low-confidence → `needs_review` |

Evals run on every PR touching `agents/`; regression below threshold blocks merge.

**Load** — 100 concurrent users, 10k alerts/tenant, 2k-supplier graph at depth 3; assert API p95 < 500 ms and traversal p95 < 200 ms.


---

# PART Y — MVP vs PHASE 2 vs PHASE 3 (§26, §32, §33)

## MVP — prove one thing: *an external event reaches the right person, with evidence, before the disruption*

**In:** Clerk auth + orgs + RBAC · supplier graph (org→supplier→sub-supplier→parent→location) via CSV/manual/typeahead · ER cascade + review queue · GLEIF enrichment · 9 Tier-1 connectors · dedupe + idempotency · event extraction + classification · deterministic graph intersection + risk scoring · alerts with full evidence chains · explanation agent · in-app + email notifications with digest batching · Cytoscape graph view · investigation agent + RAG · document upload + parsing + deterministic leakage rules + `regulatory_overlap` · **category-level should-cost & price-claim check (Part AD, Layer 1: FRED/ECB/World Bank indices, category→index mapping, Cost Driver Agent, deterministic claim verification)** · admin portal (sources, DLQ, AI cost, audit) · full observability · tenant-isolation test suite.

**Why price intelligence moved into MVP:** the founding requirement was "let users add their own data and get intelligence on it" — spend-leakage detection and should-cost/price-claim checking are two answers to that same requirement, not a core feature plus a later add-on. Shipping only spend-leakage in MVP would tell a Category Manager "here's what you're overspending" without "here's whether the price you're being asked to pay is even justified" — half the promise. **Layer 2 (part/BOM-level should-cost, Part AD.1) stays in Phase 3** alongside BOM-level exposure tracing, since both are genuinely gated on BOM data most tenants won't have at signup — that scope line hasn't moved, only the category-level layer has.

**Out:** BOM/material depth (exposure tracing **and** should-cost) · Slack/Teams (email covers MVP) · commercial data providers · OpenSanctions · licensed LME/resin feeds · Neo4j · Elasticsearch · Kafka · live ERP connectors · mobile · approval/execution workflow · API keys for customers · multi-language UI.

**Success criteria:** 3 pilot tenants onboard in <30 min each; ≥1 relevant alert per tenant per week; **alert dismissal rate <30%** (the number that decides whether this product is trusted); ER auto-resolve ≥80%; zero cross-tenant leakage; CRITICAL alert latency p95 <30 min.

## Phase 2 — depth and reach
BOM/material modelling and the full material→part→supplier→dollars trace (the original differentiator, now on real customer data) · Slack + Teams · webhook receiver infra · commercial news provider behind `NewsConnector` · OpenSanctions **if** the build-vs-buy maths favours it · customer API keys · saved views/watchlists · scheduled PDF reports · materialized `graph_reachability` · reranking model upgrade · per-tenant risk-model tuning · SOC 2 Type I readiness.

## Phase 3 — scale and enterprise
Neo4j **only if** the H.1 trigger fires · Elasticsearch **only if** Postgres FTS p95 >1 s · Kafka **only if** sustained ingestion >10k records/min · live ERP connectors (SAP/Oracle) · approval workflow + action execution (the deliberate reversal of "no action" once there is a UI and audit trail to gate against) · multi-region residency · white-label · predictive risk modelling · mobile · **Part AD Layer 2: part/BOM-level should-cost using real material composition, plus licensed LME/resin feeds if metals/plastics-heavy tenants justify the cost — gated on the same BOM-data availability as part/BOM-level exposure tracing.**

**Every Phase 3 infrastructure item is gated on a measured metric, not on ambition.**

---

# PART Z — IMPLEMENTATION PLAN FOR THE CODING AGENT (§27, §34)

Each phase: objective · build · APIs · DB · env · deps · tests · **acceptance criteria (verify before proceeding)**.

### Phase 1 — Project setup
**Objective:** reproducible dev environment, CI skeleton.
**Build:** repo per Part V; `docker-compose.yml` (postgres+pgvector, redis, api, worker, beat, frontend, mailhog, localstack); Dockerfiles; `config.py` (Pydantic Settings — the only place env is read); `.env.example`; ruff/mypy/eslint/prettier configs; GH Actions lint+test skeleton; `/health`.
**Env:** `ENVIRONMENT, DATABASE_URL, REDIS_URL, LOG_LEVEL`.
**Deps:** fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, celery[redis], structlog, pytest, pytest-asyncio, httpx; next, typescript, tailwind, shadcn.
**Accept:** `docker compose up` → all healthy; `GET /health` 200; `pytest` and `npm test` run green; CI passes on a trivial PR.

### Phase 2 — Database
**Objective:** full schema, migrations, RLS.
**Build:** all Part M models; Alembic initial migration; `CREATE EXTENSION vector, pg_trgm, pg_stat_statements`; RLS policies + `app.current_org_id` session setter; audit triggers; `audit_logs` partitioning; seed `data_sources` + `risk_model_versions` v1; `scripts/seed_dev_data.py`.
**Tests:** migration up/down; RLS blocks cross-tenant; constraints reject bad data; trigram index used (EXPLAIN).
**Accept:** `alembic upgrade head` clean from empty; **a query for org A's `supplier_relationships` while session is org B returns 0 rows**; seed script produces 2 tenants with graphs.

### Phase 3 — Authentication
**Objective:** working authn/authz, tenant context on every request.
**Build:** `TokenVerifier` protocol + `ClerkVerifier`; JWKS cache; `get_current_user` dependency; `require_permission`; `TenantContextMiddleware` (sets `app.current_org_id`); Clerk webhooks → sync users/orgs; frontend Clerk provider + protected routes.
**APIs:** `/auth/me`, `/organizations/*`, `/organizations/{id}/members`.
**Env:** `CLERK_*, AUTH_ISSUER, AUTH_AUDIENCE`.
**Tests:** expired/invalid/wrong-audience tokens rejected; each role's matrix; **`tests/security/test_tenant_isolation.py` first version**.
**Accept:** login E2E works; a valid token for org A cannot read org B on any implemented endpoint; role matrix passes.

### Phase 4 — Backend APIs (core CRUD)
**Objective:** organizations, companies, suppliers, relationships.
**Build:** `modules/organizations`, `modules/companies` (no ER yet — exact match only), `modules/graph`; cursor pagination; RFC 9457 errors; SlowAPI rate limiting; OpenAPI generation.
**APIs:** `/companies/search`, `/companies/{id}`, `/suppliers` CRUD, `/relationships` CRUD.
**Tests:** CRUD + validation + pagination + rate limits + tenant scoping on each.
**Accept:** OpenAPI schema generates; every endpoint enforces role + org; pagination stable under concurrent insert.

### Phase 5 — Frontend foundation
**Build:** app shell, nav, auth-guarded layout; **generated API client from OpenAPI** (+ CI drift check); TanStack Query setup; shadcn components; error boundaries; Sentry.
**Accept:** login → dashboard shell; client regeneration produces no diff in CI; 401 redirects cleanly.

### Phase 6 — Organization & supplier management
**Build:** onboarding wizard (claim own company → add suppliers → criticality/spend); CSV bulk upload (async job + progress); supplier list/detail; settings.
**APIs:** `/suppliers/bulk`, `/organizations/{id}` PATCH.
**Accept:** **a new user reaches a populated supplier list in under 10 minutes** (this is journey J1 and is the product's riskiest UX moment); 500-row CSV imports without timeout.

### Phase 7 — Graph
**Build:** recursive CTE traversal with depth/node caps and cycle guard; `/graph` and `/graph/paths`; Cytoscape view with filters, expand-on-click, detail panel.
**Tests:** correctness at depths 1–5; **cycle A→B→C→A terminates**; caps enforced; perf at 2k nodes.
**Accept:** traversal p95 <200 ms on the 2k-supplier seed; graph renders 300 nodes smoothly; path explanation matches DB truth.

### Phase 8 — Data ingestion
**Build:** `SourceConnector` protocol; the 9 Tier-1 connectors; `RawStore` (S3 + `source_records`); normalize/dedupe stages; Celery queues, Beat schedules, retry/backoff, circuit breaker, DLQ; **GDELT global token bucket at 6 s**; recorded fixtures for every connector.
**Env:** all source vars incl. `GDELT_USER_AGENT`.
**Tests:** each `normalize()` against fixtures; **ingest same payload 3× → 1 record, `seen_count`=3**; 429 handling; circuit breaker opens/closes; DLQ capture + replay.
**Accept:** all 9 sources fetch live at least once; **re-running a full poll cycle creates zero duplicates**; rate limits never exceeded under load (verify GDELT spacing ≥5 s in logs); DLQ replay works.

### Phase 9 — Entity resolution
**Build:** normalization; Stages 1–5 deterministic; Stage 6 agent; review queue + UI; GLEIF enrichment job seeding `owned_by` edges.
**APIs:** `/companies/resolve`, `/entity-reviews`, `/entity-reviews/{id}/resolve`.
**Tests:** the 150-pair eval; stage-distribution metric; **hard negatives must not merge**.
**Accept:** precision ≥95%, recall ≥85%, **≥80% resolved before Stage 6**; review queue usable; GLEIF adds parent edges with `source='gleif'`.

### Phase 10 — AI analysis
**Build:** `LLMGateway` (routing, budget, cache, Langfuse, `agent_runs`); Event Extraction agent + prompts v1; `<untrusted_content>` wrapping; evidence-span validator; injection sentinel; semantic clustering (`event_cluster_key`); RAG (chunk/embed/hybrid retrieve).
**Env:** all LLM/embedding/Langfuse vars.
**Tests:** extraction eval (200); **injection suite (50) — 0% instruction-following**; schema-failure → `needs_review` not a bad event; cache hit on identical content.
**Accept:** extraction thresholds met; **zero injection successes**; 40 articles about one ban produce **one** event with `corroboration_count`≈40; budget rejection works.

### Phase 11 — Risk engine
**Build:** `modules/risk/scoring.py` — pure functions, **no LLM import allowed in this package** (enforced by an import-linter rule in CI); graph intersection; `risk_assessments` with full factor breakdown; recompute job.
**Tests:** every factor unit-tested at boundaries; **determinism test: same input 100× → identical score**; the 100-scenario band eval; missing-input `completeness` behaviour.
**Accept:** band agreement ≥80%; determinism 100%; `factors` JSONB reconstructs the score exactly; no LLM call occurs during scoring (asserted).

### Phase 12 — Alerts
**Build:** threshold → alert creation; evidence-chain assembly; Explanation agent + claim-validator + template fallback; alert list/detail UI with factor breakdown and citation chips; triage workflow.
**APIs:** `/alerts*`, `/risks/summary`.
**Tests:** explanation eval (100); **alert cannot be created without evidence** (constraint test); dismissal reasons recorded.
**Accept:** every alert renders a complete chain to primary sources; 100% of claims map to evidence; no imperative language; `needs_human_judgment` shown below threshold.

### Phase 13 — Notifications
**Build:** preferences; severity routing; **15-min batching by event**; digests; Resend/SES integration; templates with deep links + top evidence; delivery tracking; bounce webhooks.
**Tests:** batching (1 event × 30 suppliers → 1 email); **idempotency (same key twice → 1 send)**; retry to failure; quiet hours skip non-CRITICAL only.
**Accept:** CRITICAL arrives <5 min; digests correct; no duplicates; every email deep-links to the alert.

### Phase 14 — Document ingestion & spend
**Build:** upload (validation, ClamAV, S3); Document Parsing agent; normalization to contracts/POs/spend; deterministic leakage rules; `regulatory_overlap` cross-check; Data tab UI.
**Tests:** parsing eval (50); totals reconciliation; low-confidence → `needs_review` and **not** inserted; overlap correctness.
**Accept:** ≥95% monetary-field accuracy; nothing partially inserted; overlap flag verified against known fixtures.

### Phase 14b — Should-cost & price-claim check (Part AD, Layer 1)
**Objective:** category-level should-cost and supplier price-claim verification, moved into MVP.
**Build:** `modules/price_intelligence/` (new domain module, same pattern as `modules/spend/`); connectors for FRED, ECB FX, World Bank Pink Sheet (`ingestion/connectors/fred.py`, `ecb_fx.py`, `world_bank_commodities.py`), each a `SourceConnector` implementation per Part F.2; `price_index_sync` Celery schedule (daily/monthly per source); `price_indices` + `price_index_observations` + `category_index_mappings` tables; Cost Driver Agent (Part AD.5) with its prompt in `agents/prompts/cost_driver_extraction/`; **deterministic** `modules/price_intelligence/verify.py` computing verified magnitude and verdict — under the same import-linter rule as `modules/risk/scoring.py` (no `agents` import permitted); `supplier_price_claims` + `claim_assessments` tables with the same evidence-required constraint pattern as `alert_evidence`; negotiation-brief generation via the existing Explanation-agent pattern; Sourcing UI addition: claim submission form + assessment view with driver-by-driver breakdown.
**APIs:** `/price-indices`, `/price-indices/{id}/observations`, `/categories/{category}/index-mapping`, `/price-claims`, `/price-claims/{id}`, `/price-claims/{id}/negotiation-brief`.
**Env:** `FRED_API_KEY`, `ECB_FX_BASE_URL` (no key), `WORLD_BANK_API_BASE_URL` (no key).
**Deps:** none new beyond existing HTTP/Celery stack.
**Tests:** connector `normalize()` against recorded FRED/ECB/World Bank fixtures; Cost Driver Agent eval (100 labelled claim letters, ≥85% driver accuracy, 0% hallucinated magnitudes per AD.5); verify.py unit tests at boundary values (zero claimed magnitude, missing index mapping, category with no default template); **determinism test: identical claim + identical index data → identical verdict, 100%**; constraint test that a `claim_assessment` cannot exist without `evidence`.
**Accept:** all three index sources sync on schedule with zero duplicate observations (same idempotency pattern as Part F.3, keyed on `(price_index_id, observation_date)`); a submitted claim returns a driver-by-driver verdict referencing the real index value and date; **no LLM call occurs during verification** (asserted, same as Phase 11's risk-engine check); a category with no configured index mapping returns "unverifiable," never a guessed number.

### Phase 15 — Admin & observability
**Build:** admin portal (Part T); OTel instrumentation; all Part R metrics; Grafana dashboards; alert rules; Langfuse wiring.
**Accept:** all metrics emit; killing a source triggers the freshness alert within 3× its interval; DLQ replay works from the UI; cost dashboard attributes spend per tenant.

### Phase 16 — Security hardening
**Build:** SSRF-safe fetcher (private-IP rejection, redirect cap); CSP; WAF; secret scanning; DSAR export/delete; retention jobs; pen-test fixes.
**Tests:** full tenant-isolation suite across **every** endpoint; SSRF attempts against metadata IP blocked; upload of a disguised executable rejected.
**Accept:** security suite green; no criticals in Trivy/pip-audit/npm audit; SSRF blocked; DSAR round-trips.

### Phase 17 — Testing completion
Fill coverage gaps to targets; full E2E journey; load test; DR restore drill.
**Accept:** coverage gates met; E2E green; p95 targets met under load; a restore from backup succeeds in staging.

### Phase 18 — Deployment
Terraform staging + production; blue/green; migration task; runbooks; on-call alerts; production smoke.
**Accept:** deploy from clean state reproducibly; rollback tested; DR drill documented; on-call alerts fire correctly.

---

# PART AA — KEY RISKS & MITIGATIONS (§36)

| # | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| R1 | **Alert fatigue / poor precision** — the #1 killer of this product category | Fatal | High | Multiplicative gates; semantic clustering into one event; 15-min batching; dismissal-rate metric as a first-class KPI; thresholds tuned on a labelled set before launch |
| R2 | **Cold start** — empty graph = no alerts = churn in week 1 | Fatal | High | GLEIF-seeded typeahead; CSV import; auto-parent enrichment; **30-day backfill guaranteeing a real alert in session 1** |
| R3 | **GDELT rate limit / no SLA** bottlenecks ingestion | High | Medium | Global token bucket; prioritized query scheduling; `NewsConnector` interface ready for a paid provider; freshness alerting so degradation is visible, not silent |
| R4 | **Entity resolution false merges** — merging two real companies corrupts a tenant's graph and its alerts | High | Medium | Precision-weighted thresholds (95% target); LLM constrained to supplied candidates; review queue; **merges are reversible and audited** |
| R5 | **Prompt injection via ingested content** | High | Medium | Seven-layer defence (Q.7); tool-less ingestion agents; 50-case adversarial eval blocking in CI |
| R6 | **Cross-tenant data leakage** | Fatal (business-ending) | Low | Triple-layer isolation; blocking CI security suite; `companies`/`supplier_relationships` separation |
| R7 | **LLM cost overrun** | Medium | Medium | Per-tenant budgets enforced pre-call; cheap-model pre-filter; content-hash caching; per-tenant cost dashboard |
| R8 | **DGFT/CBIC HTML monitors break on site change** | Medium | High | Structural-change detection → admin alert + source marked degraded (never silent); quarterly re-check for an official API; metadata+PDF only |
| R9 | **OpenSanctions licence misuse** | High (legal) | Low | Excluded from MVP by policy; primary government sources used instead; licence status recorded in `data_sources.license_terms` |
| R10 | **Copyright — storing article text** | Medium (legal) | Medium | Store metadata + URL only; body text used transiently at extraction; summaries are our own paraphrase, enforced in the prompt and spot-audited |
| R11 | **BOM data unavailable**, undermining the original differentiator | Medium | High | Already mitigated by the A.6 scope change: supplier-level exposure in MVP, BOM depth in Phase 2 |
| R12 | **Postgres graph outgrows recursive CTEs** | Medium | Low | Measured trigger (H.1); materialized reachability first; Neo4j only if the metric demands it |
| R13 | **Source terms change without notice** | Medium | Medium | `terms_verified_at` per source, surfaced in admin; quarterly verification task; `scripts/verify_sources.py` |
| R14 | **Clerk vendor lock / enterprise SSO demands** | Medium | Medium | `TokenVerifier` abstraction from Phase 3; Keycloak is one implementation away |
| R17 | **Pulling Part AD Layer 1 into MVP widens scope right as R1/R2 (precision, cold-start) most need focus** | Medium | Medium | Built as an independent module (AD.7) sharing infrastructure, not the risk engine's logic or its team's attention; its own eval gate (Phase 14b) and success criteria are separate from the regulatory-alert success criteria, so one cannot mask the other's problems |

---

# PART AB — ENGINEERING RULES (§28) — MAPPED TO ENFORCEMENT

Rules are only real if something enforces them. Every rule below names its enforcement mechanism.

| # | Rule | Enforced by |
|---|---|---|
| 1,2 | No hard-coded external data / suppliers | `data_sources` + `companies` are DB-seeded; a CI grep test fails on hard-coded company names in `modules/` |
| 3,4 | No fabricated API responses or invented APIs | All connectors tested against **recorded real fixtures**; every source in Part E carries an official URL |
| 5,6 | Prefer official sources; third-party only when necessary | Part E tiering; Tier 3 requires explicit justification in `data_sources.coverage_notes` |
| 7,8 | External content untrusted; never overrides instructions | `<untrusted_content>` wrapping; tool-less ingestion agents; injection eval blocking in CI |
| 9 | Every AI business conclusion has evidence | `alert_must_have_evidence` DB constraint + claim-validator |
| 10 | Every source traceable | `source_records.raw_s3_key` + `canonical_url` + `retrieved_at` on every record |
| 11 | Ingestion idempotent | Two UNIQUE constraints + content hashing; integration test ingests 3×, asserts 1 |
| 12 | Secrets stored securely | Secrets Manager; gitleaks pre-commit + CI |
| 13 | Structured LLM outputs | `instructor` + Pydantic; free-text responses rejected at the gateway |
| 14 | No LLM where deterministic code suffices | Import-linter rule: `modules/risk` and `ingestion/pipeline/dedupe` **cannot import** `agents` |
| 15 | Multi-tenant from the beginning | `org_id` on every tenant table from the first migration + RLS |
| 16 | AI providers replaceable | Everything routes through `LLMGateway`; a test asserts no module imports `litellm` directly |
| 17 | Data providers replaceable | `SourceConnector` protocol; a test asserts every connector implements it |
| 18 | Don't over-engineer MVP | Part Y exclusions with measured Phase 3 triggers |
| 19 | Observability from the start | Phase 1 ships structured logging; metrics land in Phase 15 but instrumentation points are added as each module is built |
| 20 | Every major feature has tests | Coverage gates in CI; acceptance criteria per phase |

---

# PART AC — EXECUTIVE SUMMARY

**Provenance** is a multi-tenant SaaS platform that watches official regulatory, trade, sanctions, and financial-distress sources; resolves the companies named in those events against a canonical registry; determines deterministically whether they touch a customer's supply graph; scores the business impact with a reproducible model; and delivers a cited, evidence-backed alert to a Supply Chain Risk Manager or Category Manager. It recommends; a human decides.

**The technical core is four decisions:**
1. **Deterministic where it matters.** Graph traversal, risk scoring, deduplication, and leakage detection are SQL and arithmetic. LLMs handle only unstructured→structured extraction, ambiguous entity adjudication, and natural-language explanation. Scores are reproducible; alerts are defensible.
2. **PostgreSQL does almost everything.** Relational core, JSONB, graph via recursive CTEs, full-text search, fuzzy matching via pg_trgm, and vectors via pgvector — one datastore, one transaction, one backup story. Neo4j, Elasticsearch, and Kafka are each gated on a measured threshold rather than adopted upfront.
3. **Evidence is a schema constraint, not a convention.** An alert cannot exist in the database without evidence rows. Every claim traces to a primary source with a live/cached tag.
4. **Multi-tenant isolation is triple-enforced** and tested as a blocking CI gate, because the product stores confidential supplier relationships and a single leak would end it.

**Two honest scope changes from the original concept:** BOM-level material tracing moves to Phase 2 (customers won't have clean BOM data at signup, and building MVP around it guarantees an empty product); and "financial news" is narrowed to a closed set of distress signals rather than general market data, which would add noise without adding decisions.

**One scope addition, made deliberately mid-spec rather than assumed upfront:** category-level should-cost and supplier price-claim checking (Part AD) moved into MVP. The founding requirement — let users add their own data and get intelligence on it — has two equally valid answers: spend-leakage detection (already MVP) and should-cost verification (originally phased later, now pulled forward). Shipping only the first would leave the product answering "what are you overspending on" without "is the price you're being asked to pay even justified." It ships as an independent module reusing existing infrastructure (tenancy, `LLMGateway`, the evidence-chain pattern) rather than as a fork of the risk engine, specifically so widening scope here doesn't dilute the two metrics that actually decide whether the core product works: alert precision and cold-start time.

**The riskiest parts are not technical.** They are alert precision and the cold-start problem — a system that cries wolf or shows an empty dashboard fails regardless of how well it is engineered. Both have specific, measured mitigations (R1, R2) and both are surfaced as first-class KPIs rather than left to be discovered after launch.

**All external sources in the MVP are official, free, and documented.** OpenSanctions is deliberately excluded because its CC BY-NC licence prohibits commercial use without a paid licence; the same data is ingested directly from OFAC, EU, UN, and UK primary sources, which carry no such restriction. **Pricing, rate limits, and terms for every provider must be re-verified against official documentation before production deployment.**

---

# PART AD — SHOULD-COST & PRICE INTELLIGENCE MODULE (new, ivoflow-inspired)

## AD.1 Why This Module, and Why It Doesn't Compete With Part I

Part I (Business Impact & Risk Engine) answers *"is this supplier about to become a problem?"* This module answers a different, complementary question the Category Manager asks constantly and Provenance currently has no answer for: **"is the price I'm being asked to pay actually justified by what's happened in the underlying material market?"**

This is the core capability of ivoflow (now part of JAGGAER) — connecting a manufacturer's own spend/price data to external commodity and market indices, and using that gap to drive negotiation. It is a genuinely different data problem from regulatory/sanctions monitoring (Part E): the sources here are **economic time series**, not event feeds, so the ingestion, storage, and reasoning shapes are all different from the rest of the pipeline. It reuses the platform's existing tenancy, spend tables (Part M.1 `spend_records`/`contracts`/`purchase_orders`), and agent infrastructure (`LLMGateway`) rather than duplicating them.

**Scope decision:** like the BOM-tracing decision in A.6, this module ships in two layers. **Layer 1 (MVP-adjacent, ships in Phase 2 alongside BOM depth)** works at the **category/commodity level** — no per-part material composition required, matching what a real customer can supply on day one. **Layer 2 (Phase 3)** works at the **part/BOM level** once a tenant has usable BOM data, which is where ivoflow's own "price developments at parts-list level" sits. This mirrors the reasoning in A.6 exactly: don't gate a real capability on data most prospects won't have yet.

## AD.2 New Data Sources — Commodity & Economic Indices

Unlike Part E's event feeds, this data is **time-series**, official, and — critically — **free at the aggregator level**, which changes the sourcing story favourably.

### Tier 1 — REQUIRED, free, official

**1. FRED (Federal Reserve Economic Data) — Federal Reserve Bank of St. Louis**
- **Base:** `https://api.stlouisfed.org/fred` **Docs:** `https://fred.stlouisfed.org/docs/api/fred/`
- **What:** 800,000+ economic time series aggregated from 100+ primary sources (BLS, BEA, OECD, World Bank, Eurostat, IMF, Census). For this module the relevant series families are: **Producer Price Index by Commodity** (steel mill products, hot/cold-rolled steel, iron & steel scrap, aluminum — base scrap, secondary, mill shapes, sheet/strip — copper and copper products, and equivalents for plastics/resins), and the **IMF Global Price Index of All Commodities** and **Global Price of Industrial Materials Index**, both republished on FRED under IMF permission.
- **Auth:** free API key (register at `fredaccount.stlouisfed.org`). **Format:** JSON/XML, CSV/Excel for observations. **Cost:** free. **Update frequency:** monthly for most PPI series (BLS release schedule); some series weekly. **Reliability:** high — primary-source government/IMF data, not a scrape.
- **Why this is the anchor, exactly like GLEIF was for the graph:** one free, authoritative, well-documented API replaces what would otherwise require separate licensed feeds per commodity family.
- **Store:** `series_id`, `title`, `units`, `frequency`, `observation_date`, `value`, `source_organization`, `last_updated`.
- **Production-suitable: Yes.**

**2. ECB Statistical Data Warehouse / European Central Bank FX Reference Rates**
- **What:** daily EUR reference rates against all major currencies — the **currency-effect factor** in a should-cost model (a supplier claiming a price increase driven by FX movement needs this checked against the real rate, not their assertion).
- **Auth:** none. **Cost:** free. **Format:** XML/CSV/JSON via the SDMX-based API. **Update:** daily, ~16:00 CET. **Production-suitable: Yes.**

**3. World Bank Commodity Markets ("Pink Sheet") data**
- **What:** monthly commodity price data across energy, metals, agriculture — the same underlying data FRED republishes for some series, plus broader coverage (crude oil, natural gas, fertilizers, agricultural inputs relevant to plastics/packaging feedstock).
- **Access:** World Bank Open Data API (free, no key) or direct Pink Sheet Excel download.
- **Cost:** free. **Update:** monthly. **Production-suitable: Yes**, as a supplementary/cross-check source to FRED.

### Tier 2 — RECOMMENDED but licensed (evaluate at Phase 2/3, not MVP)

**4. LME (London Metal Exchange) real-time/settlement prices**
- **What:** the actual reference price the metals industry itself negotiates against (copper, aluminum, zinc, nickel, lead, tin) — the single most credible source for a metals-heavy manufacturer's should-cost model.
- **⚠️ Licensing:** LME data is **commercially licensed**, distributed through market-data vendors (Refinitiv, Bloomberg, Fastmarkets) rather than a free public API. **Not free — verify current commercial terms directly with LME or a licensed redistributor before committing to it.**
- **MVP alternative:** FRED's PPI-by-commodity series (Tier 1) is a reasonable free proxy for *directional* trend and *magnitude of change*, even though it isn't the identical benchmark a metals trader would quote. This is disclosed to the user exactly the way the DGFT HTML-monitor limitation is disclosed in Part E — the should-cost estimate is labelled with which index it was built from, and a metals-heavy tenant is told plainly that a licensed LME feed would sharpen precision.

**5. Plastics/resin indices (e.g. published polymer price benchmarks)**
- Similar situation to LME — the sharpest benchmarks are commercially published. FRED carries some BLS PPI plastics-material series as a free proxy; evaluate a licensed feed in Phase 2 if resin-heavy tenants demand it.

### Explicitly excluded from this module's MVP
Live LME/Fastmarkets/Bloomberg feeds (licensing cost, Phase 2/3 decision); freight-rate indices (a real should-cost factor for landed cost, but a distinct data problem — Phase 3); labor-cost indices by country (Phase 3, needed only once should-cost goes to true bottom-up costing rather than index-driven price-movement checking).

## AD.3 New Capability: Supplier Price-Claim Check (the flagship feature, matched deliberately against ivoflow's own)

This is the concrete, decision-grade capability a Category Manager gets, mirroring ivoflow's own highest-signal feature described in their materials.

### Journey
```
Supplier sends a price-increase request (email/portal/manual entry)
  → user enters or uploads the claim: {company_id, category, current_price,
                                        requested_price, effective_date,
                                        stated_reason (free text)}
  → Cost Driver Agent (LLM) extracts the CLAIMED drivers from the free text
      into a closed taxonomy: {material_cost, energy_cost, labor_cost,
                                fx_movement, logistics, regulatory, other}
      with a claimed magnitude per driver where stated
  → DETERMINISTIC check against real data:
      material_cost   → % change in the matched FRED/World Bank index
                          over the claim period, weighted by the category's
                          configured material composition (category-level
                          default until BOM data — see AD.1 Layer 2)
      fx_movement     → actual ECB rate change over the same period
      other drivers   → no independent index exists → flagged
                          "unverifiable from current data sources", NOT
                          accepted or rejected — an honest gap, not a guess
  → produces a JUSTIFIED / PARTIALLY JUSTIFIED / UNSUPPORTED split of the
    claimed increase, with the arithmetic shown
  → Explanation agent drafts the negotiation brief in plain language
  → Category Manager takes it into the actual negotiation — Provenance
    never contacts the supplier or accepts/rejects the claim itself
```

### Why the split between LLM and deterministic code matters here exactly as much as it does in Part I
The **claim extraction** (turning a supplier's prose justification into structured driver categories) is a genuine NLP task — LLM territory. The **verification** (did steel actually move 8% in this window, per an official index) is **arithmetic against a stored time series** — it must be deterministic for the same reason risk scores must be: a Category Manager walking into a negotiation needs a number that doesn't change if they ask the tool twice, and needs to be able to show the supplier the actual index, not an AI's paraphrase of it.

## AD.4 New Data Model

```sql
price_indices(
  id, source TEXT CHECK (source IN ('fred','ecb','world_bank')),
  external_series_id TEXT NOT NULL,           -- e.g. FRED 'WPU1017'
  name, category TEXT,                        -- steel|aluminum|copper|resin|fx_eur_usd…
  unit, frequency, reliability TEXT DEFAULT 'high',
  license_terms, terms_verified_at DATE, <audit>,
  UNIQUE (source, external_series_id))

price_index_observations(
  id, price_index_id FK NOT NULL, observation_date DATE NOT NULL,
  value NUMERIC(18,6) NOT NULL, retrieved_at, is_revised BOOL DEFAULT false,
  UNIQUE (price_index_id, observation_date))

category_index_mappings(                       -- category → which index(es) drive its cost
  id, org_id FK NOT NULL, category TEXT NOT NULL,
  price_index_id FK NOT NULL, weight NUMERIC(3,2) NOT NULL,  -- composition weight
  source TEXT CHECK (source IN ('user_declared','default_template')),
  valid_from, valid_to, <audit>)  RLS ENABLED

supplier_price_claims(
  id, org_id FK NOT NULL, company_id FK NOT NULL, category TEXT,
  current_price NUMERIC(18,4), requested_price NUMERIC(18,4), currency CHAR(3),
  effective_date DATE, stated_reason TEXT,          -- supplier's own words, stored verbatim
  claimed_drivers JSONB,                            -- extracted, structured
  status TEXT DEFAULT 'submitted', <audit>)  RLS ENABLED

claim_assessments(
  id, claim_id FK NOT NULL,
  driver TEXT NOT NULL,                             -- material_cost|fx_movement|…
  claimed_magnitude_pct NUMERIC(5,2),
  verified_magnitude_pct NUMERIC(5,2),               -- NULL if unverifiable
  verdict TEXT CHECK (verdict IN
    ('justified','partially_justified','unsupported','unverifiable')),
  supporting_index_id FK NULL, evidence JSONB NOT NULL,   -- same evidence
                                                           -- contract as alert_evidence
  computed_at, model_version, <audit>)
-- same evidence discipline as alerts: a claim_assessment without evidence is invalid
```

## AD.5 New Agent — Cost Driver Agent

| | |
|---|---|
| **Purpose** | Extract structured claimed cost drivers from a supplier's free-text price-increase justification |
| **In** | `stated_reason` free text + claim metadata |
| **Out** | `{drivers: [{type, claimed_magnitude_pct?, evidence_span}], confidence}` — same schema discipline as Event Extraction (Part J.2, Agent 1): closed enum, evidence spans required, no tools, treats the supplier's text as **untrusted input** (a claim letter is exactly the kind of external content Part Q.7's injection defence already covers — no new threat model needed, same wrapping and validation) |
| **Does NOT do** | Compute the verified magnitude, decide the verdict, or draft acceptance/rejection language — those are deterministic (AD.3) and the Explanation agent respectively |
| **Eval** | 100 hand-labelled real-format supplier claim letters; driver-classification accuracy ≥85%; hallucinated-magnitude rate (claiming a number wasn't in the text) = 0% |

The **verdict computation itself is a deterministic service** (`modules/price_intelligence/verify.py`), under the same import-linter rule as `modules/risk/scoring.py` (Part AB, rule 14): **no LLM import permitted in this package.**

## AD.6 API Additions

| Method | Path | Notes |
|---|---|---|
| GET | `/price-indices` | list available indices + coverage |
| GET | `/price-indices/{id}/observations` | time series, filterable by date range |
| GET/POST | `/categories/{category}/index-mapping` | configure which indices drive a category's cost |
| POST | `/price-claims` | submit a supplier claim (manual or uploaded letter) |
| GET | `/price-claims/{id}` | claim + full driver-by-driver assessment |
| GET | `/price-claims/{id}/negotiation-brief` | the drafted, cited negotiation brief |

## AD.7 Where This Sits in the Existing Architecture
No new pipeline, no new queue types beyond a `price_index_sync` schedule (daily/monthly per source, same Celery pattern as Part F). No change to the risk engine. The module reuses: tenancy, RLS, `LLMGateway`, the evidence-chain pattern, and the existing spend tables. It is a **new domain module** (`modules/price_intelligence/`) exactly like `modules/spend/`, not a fork of the architecture.

## AD.8 Updated MVP/Phase Placement (revising Part Y) — **REVISED: Layer 1 moved into MVP**
- **MVP (revised):** category-level price index ingestion (FRED, ECB, World Bank) and the Supplier Price-Claim Check at category granularity now ship in MVP, as Phase 14b of the implementation plan. Rationale: "let users add their own data and get intelligence on it" is the founding requirement behind both spend-leakage detection *and* should-cost checking — shipping only the former would answer "what are you overspending on" without "is the price you're being asked to pay even justified," which is half the promise. This does **not** reopen the R1/R2 priority (alert precision and cold-start on the regulatory side are still the first things validated) — it runs as a parallel, independently-testable module (AD.7) that shares infrastructure but not risk-engine logic.
- **Phase 2 (alongside BOM depth):** no change to this layer's timing — it was already Phase 3-gated; restated here for clarity given the MVP change above.
- **Phase 3 (alongside part/BOM-level exposure tracing):** part-level should-cost using real BOM composition; licensed LME/resin feeds if metals/plastics-heavy tenants justify the cost; freight and labor-cost factors for full bottom-up costing. **This boundary has not moved** — it remains gated on the same BOM-data availability as part/BOM-level exposure tracing (A.6), for the same reason: promising bottom-up costing before tenants have clean BOM data would repeat the original MVP-scoping mistake this spec was written to avoid.

## AD.9 Risk Register Addition
| # | Risk | Mitigation |
|---|---|---|
| R15 | Category-level index mapping is a weak proxy for a specific part's actual material mix, and could produce a wrong "unsupported" verdict | Every assessment discloses which index and weighting was used; verdicts below a confidence threshold render as "needs review" exactly like risk alerts; Phase 3 BOM-level costing is the real fix, not promised early |
| R16 | LME/resin licensing cost is unknown until negotiated | No LME dependency in the scoped MVP of this module; FRED proxy is disclosed as a proxy, not presented as the industry benchmark |