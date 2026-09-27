-- data_sources.sql
-- Seeds the nine Tier-1 data source connectors required for MVP.
-- Run after alembic upgrade head.
-- Uses ON CONFLICT DO UPDATE so this script is safe to re-run.
--
-- IMPORTANT (arch §E.x): pricing, rate limits, and terms change without notice.
-- Re-verify each provider's current terms before production deployment.
-- Update terms_verified_at whenever you do.

INSERT INTO data_sources (
    source_key, name, source_type, base_url, auth_type,
    reliability, license_terms, terms_verified_at, coverage_notes,
    poll_interval_seconds, is_enabled, status, config
) VALUES

-- 1. OFAC Sanctions List Service
(
    'ofac_sls',
    'OFAC Sanctions List Service',
    'bulk_download',
    'https://sanctionslistservice.ofac.treas.gov',
    'none',
    'high',
    'US Government public domain — no restrictions on use or redistribution.',
    '2026-09-27',
    'Enumerate available lists via /sanctions-lists endpoint; never hardcode filenames — OFAC changes them without notice. Coverage: US designations globally (SDN + Consolidated non-SDN). SLS is a file-delivery service only; fuzzy matching and alias resolution are our responsibility.',
    21600,   -- 6 h
    true,
    'healthy',
    '{
        "list_endpoint": "/sanctions-lists",
        "formats": ["xml", "csv"],
        "delta_available": true
    }'::jsonb
),

-- 2. GLEIF LEI API
(
    'gleif',
    'GLEIF LEI API',
    'api',
    'https://api.gleif.org/api/v1',
    'none',
    'high',
    'CC0 1.0 Universal — free for any use including commercial. See https://www.gleif.org/en/about/open-data',
    '2026-09-27',
    '~3.4M legal entities with Level-2 corporate hierarchy (direct/ultimate parent + children). Primary backbone for entity resolution and graph seeding. Use Golden Copy bulk files for initial load; live API for enrichment and on-demand resolution.',
    86400,   -- nightly enrichment; on-demand queries are separate
    true,
    'healthy',
    '{
        "golden_copy_url": "https://www.gleif.org/en/lei-data/gleif-golden-copy",
        "level2_endpoint": "/lei-records/{lei}/direct-children",
        "search_endpoint": "/lei-records"
    }'::jsonb
),

-- 3. GDELT DOC 2.0 API
(
    'gdelt_doc',
    'GDELT DOC 2.0 API',
    'api',
    'https://api.gdeltproject.org/api/v2/doc/doc',
    'none',
    'medium',
    'GDELT returns metadata and links only. Publisher article text carries separate copyright. Store and display: URL, title, domain, seendate, language, sourcecountry only. Do NOT store or re-serve full article text.',
    '2026-09-27',
    'Rolling 3-month window only — no historical access beyond that. Rate limit: ~1 request per 5 seconds (hard). No published SLA. User-Agent header required. Coverage: worldwide news across 100+ languages.',
    1800,    -- 30 min for global material queries; 4 h for per-tenant supplier queries handled in task config
    true,
    'healthy',
    '{
        "min_interval_seconds": 6,
        "user_agent_env_var": "GDELT_USER_AGENT",
        "modes": ["ArtList", "TimelineVol"],
        "requires_user_agent": true
    }'::jsonb
),

-- 4. Federal Register API (US)
(
    'federal_register',
    'Federal Register API',
    'api',
    'https://www.federalregister.gov/api/v1',
    'none',
    'high',
    'US Government public domain.',
    '2026-09-27',
    'US rules, proposed rules, notices, presidential documents. Covers BIS export-control rules and Commerce trade actions. Published on business days ~06:00 ET.',
    3600,    -- 1 h
    true,
    'healthy',
    '{
        "relevant_agencies": ["commerce-department", "treasury-department", "state-department"],
        "relevant_types": ["RULE", "PRORULE", "NOTICE", "PRESDOCU"]
    }'::jsonb
),

-- 5. EUR-Lex / EU Official Journal
(
    'eurlex',
    'EUR-Lex / EU Official Journal',
    'api',
    'https://eur-lex.europa.eu',
    'registration',
    'high',
    'EU reuse policy — Decision 2011/833/EU. Attribution required. See https://eur-lex.europa.eu/content/help/data-reuse/reuse-policy.html',
    '2026-09-27',
    'EU regulations, decisions, sanctions instruments including CBAM, CRMA, and Reg 833/2014 amendments. SPARQL/RSS open; SOAP web service requires registration. Use SPARQL Cellar endpoint for structured queries.',
    21600,   -- 6 h
    true,
    'healthy',
    '{
        "sparql_endpoint": "https://publications.europa.eu/webapi/rdf/sparql",
        "rss_feeds": ["https://eur-lex.europa.eu/RSSONE.do?ihmlang=en"],
        "auth_env_vars": ["EURLEX_WS_USERNAME", "EURLEX_WS_PASSWORD"]
    }'::jsonb
),

-- 6. EU Consolidated Financial Sanctions List
(
    'eu_sanctions',
    'EU Consolidated Financial Sanctions List',
    'bulk_download',
    'https://webgate.ec.europa.eu/fsd/fsf',
    'token',
    'high',
    'EU public — permissive reuse. Free access token required from EU FSF.',
    '2026-09-27',
    'Persons, groups, entities under EU asset freezes. COVERAGE GAP: Annex IV of Regulation 833/2014 entities (specific economic prohibitions but NOT asset freezes) are NOT in this list. Record this gap in alerts derived from this source.',
    21600,   -- 6 h
    true,
    'healthy',
    '{
        "formats": ["xml", "csv"],
        "auth_env_var": "EU_SANCTIONS_TOKEN"
    }'::jsonb
),

-- 7. UN Security Council Consolidated List
(
    'un_sanctions',
    'UN Security Council Consolidated List',
    'bulk_download',
    'https://www.un.org/securitycouncil/content/un-sc-consolidated-list',
    'none',
    'high',
    'UN public domain.',
    '2026-09-27',
    'UN SC consolidated sanctions list — XML download. Daily updates.',
    86400,   -- daily
    true,
    'healthy',
    '{
        "xml_url": "https://scsanctions.un.org/resources/xml/en/consolidated.xml",
        "format": "xml"
    }'::jsonb
),

-- 8. UK Sanctions List (OFSI)
(
    'uk_ofsi',
    'UK OFSI Sanctions List',
    'bulk_download',
    'https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file',
    'none',
    'high',
    'Open Government Licence v3.0 — free to use and adapt with attribution. See https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/',
    '2026-09-27',
    'UK HM Treasury / OFSI consolidated sanctions list. Available as ODT/CSV/XML from GOV.UK. Check current download URL at implementation time — file paths change.',
    86400,   -- daily
    true,
    'healthy',
    '{
        "format": "csv",
        "gov_uk_page": "https://www.gov.uk/government/publications/financial-sanctions-consolidated-list-of-targets"
    }'::jsonb
),

-- 9. India Open Government Data Platform
(
    'data_gov_in',
    'India Open Government Data (OGD) Platform',
    'api',
    'https://api.data.gov.in/resource',
    'api_key',
    'high',
    'Government Open Data Licence — India (GODL). Terms vary per dataset — verify per dataset page before use. Record per-source in coverage_notes.',
    '2026-09-27',
    'Foreign trade statistics, commodity/mandi prices, MCA company master data (~3.6M companies with CIN, ROC, capital, status, NIC industry codes). Free API key from data.gov.in registration.',
    86400,   -- daily
    true,
    'healthy',
    '{
        "auth_env_var": "DATA_GOV_IN_API_KEY",
        "resource_ids": {
            "mca_company_master": "verify-at-implementation",
            "foreign_trade_stats": "verify-at-implementation"
        },
        "rate_limit_headers": ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
    }'::jsonb
)

ON CONFLICT (source_key) DO UPDATE SET
    name                  = EXCLUDED.name,
    source_type           = EXCLUDED.source_type,
    base_url              = EXCLUDED.base_url,
    auth_type             = EXCLUDED.auth_type,
    reliability           = EXCLUDED.reliability,
    license_terms         = EXCLUDED.license_terms,
    coverage_notes        = EXCLUDED.coverage_notes,
    poll_interval_seconds = EXCLUDED.poll_interval_seconds,
    config                = EXCLUDED.config,
    updated_at            = NOW();
