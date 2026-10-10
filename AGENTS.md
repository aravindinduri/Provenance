# Provenance AI Agent Guidelines & Rules

## 🚫 MANDATORY RULE: ZERO DUMMY / MOCK DATA POLICY
**Must and Should Follow Rule for All AI Coding Agents:**

1. **NO DUMMY / MOCK / FAKE DATA**:
   - Under no circumstances should the codebase contain hardcoded dummy records, mock entity arrays, fake fallback topologies, fabricated metrics, or placeholder datasets in runtime application code or frontend UI.
   - Never use mock arrays as "offline fallbacks" or "disconnected fallbacks".

2. **ALL DATA MUST BE FETCHED VIA LIVE API OR USER INPUT**:
   - Every metric, table, card, chart, graph node, relationship, citation, alert, and entity displayed in the UI must come from a live backend API call or explicit user input.
   - If a backend service returns empty data, render an authentic empty state (e.g., *"No items found. Click 'Add' or upload documents to get started."*).
   - When loading, use genuine loading skeletons or spinners.

3. **TRUTHFUL ERROR HANDLING**:
   - If an API request fails or is unreachable, the application must present a clear, truthful error message or retry alert banner.
   - Never silently swallow errors and substitute fake records to make the UI look populated.

4. **DYNAMIC COMPUTED METRICS**:
   - Dashboard KPIs, percentages, counts, and spend numbers must be computed dynamically from actual API responses and live database records, never hardcoded static literals.

---

For design, antislop, and simplicity guidelines, refer to:
- `.agents/rules/antislop.md`
- `.agents/rules/ponytail.md`
- `.agents/skills/antislop/SKILL.md`
