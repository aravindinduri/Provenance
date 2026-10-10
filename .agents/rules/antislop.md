# Anti Slop: Rules for AI Coding Agents

Anti Slop is a filter, not a style guide: it stops generic AI slop in generated UI, copy, and code, without prescribing aesthetics.

For UI, copy, accessibility, mobile layout, or code comments work, load the matching antislop skill:
- **Core filter (always active)**: `.agents/skills/antislop/SKILL.md`
- **UI / visual**: `.agents/skills/antislop-ui/SKILL.md`
- **Copy & text**: `.agents/skills/antislop-copywriting/SKILL.md`
- **Accessibility & human**: `.agents/skills/antislop-human/SKILL.md`
- **Mobile & responsive**: `.agents/skills/antislop-layoutmobile/SKILL.md`
- **Code comments**: `.agents/skills/antislop-code/SKILL.md`

## Usage Modes
Before starting, follow the core's "Two Usage Modes" section: explicit session instruction first, then global preference, then ask. For a resolved mode, announce `antislop active: <mode> (session override).` or `antislop active: <mode> (global preference).` once, using the actual mode and source. Ask only when no mode is resolved.

---

## 🚫 ZERO DUMMY / MOCK DATA POLICY (MANDATORY MUST & SHOULD RULE)

**THIS RULE IS ABSOLUTE, NON-NEGOTIABLE, AND MUST BE FOLLOWED BY ALL CODING AGENTS AT ALL TIMES.**

### 1. No Dummy / Mock / Placeholder Data in Application Code
- **NEVER** introduce or leave hardcoded dummy arrays, mock objects, simulated topologies, fake metrics, synthetic alerts, placeholder items, or demo fallbacks in application components or code.
- **NEVER** use mock data arrays as "offline fallbacks" or "disconnected mode fallbacks" (e.g. `setSuppliers(DEMO_MOCK_SUPPLIERS)` or `nodes = DEMO_GRAPH_NODES`).

### 2. All Data Must Be Fetched via Live API or User Input
- Every single entity, metric card, table row, graph node, relationship edge, citation, and suggestion displayed in the UI **MUST** be fetched from a live backend API endpoint or created directly by the user / database.
- If data has not yet been added to the system, render an **authentic empty state** (e.g., *"No suppliers found. Click 'Add Supplier' or upload documents to start building your supply network."*).
- If an operation is in progress, render authentic loading skeletons or spinners.

### 3. Truthful Error Handling — Never Mask Failures with Fakes
- If an API endpoint fails, is offline, or returns an error (4xx/5xx/network drop), the application **MUST** present an explicit, informative error state or alert banner with retry capability.
- **NEVER** silently swallow errors and substitute fake / dummy records to make the UI look populated.

### 4. Dynamic Computed Metrics Only
- KPI statistics, spend totals, jurisdiction exposure percentages, and supplier counts **MUST** be computed dynamically from actual API responses and live database records, never hardcoded static literals.

### 5. Scope
- This rule applies across all frontend code (`frontend/src/**`), backend application logic (`backend/app/**`), workers, and ingestion pipelines.
- Only automated unit/integration tests running under pytest/vitest may use isolated test mocks; all runtime application code must remain 100% free of dummy and mock datasets.

