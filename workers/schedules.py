"""
Celery Beat schedules — all ingestion and maintenance jobs.
Architecture reference: §F.4.
"""

from celery.schedules import crontab

CELERYBEAT_SCHEDULE: dict = {
    # ── GDELT News Ingestion ───────────────────────────────────────────────────
    # Global material / trade restriction queries every 30 minutes
    "ingest-gdelt-global-materials": {
        "task": "workers.tasks.ingest.poll_source_task",
        "schedule": 1800.0,  # 30 min
        "args": ["gdelt_doc"],
        "options": {"queue": "ingest_gdelt"},
    },
    # ── Bulk Sanctions Download Sources ────────────────────────────────────────
    # OFAC SLS every 6 hours
    "ingest-ofac-sls": {
        "task": "workers.tasks.ingest.poll_source_task",
        "schedule": 21600.0,  # 6 h
        "args": ["ofac_sls"],
        "options": {"queue": "ingest_bulk"},
    },
    # EU Consolidated Sanctions every 6 hours
    "ingest-eu-sanctions": {
        "task": "workers.tasks.ingest.poll_source_task",
        "schedule": 21600.0,  # 6 h
        "args": ["eu_sanctions"],
        "options": {"queue": "ingest_bulk"},
    },
    # UN Security Council Sanctions: daily at 02:00 UTC
    "ingest-un-sanctions": {
        "task": "workers.tasks.ingest.poll_source_task",
        "schedule": crontab(hour=2, minute=0),
        "args": ["un_sanctions"],
        "options": {"queue": "ingest_bulk"},
    },
    # UK OFSI Sanctions: daily at 03:00 UTC
    "ingest-uk-ofsi": {
        "task": "workers.tasks.ingest.poll_source_task",
        "schedule": crontab(hour=3, minute=0),
        "args": ["uk_ofsi"],
        "options": {"queue": "ingest_bulk"},
    },
    # ── Regulatory and Government APIs ────────────────────────────────────────
    # Federal Register: hourly (published on US business days ~06:00 ET)
    "ingest-federal-register": {
        "task": "workers.tasks.ingest.poll_source_task",
        "schedule": 3600.0,  # 1 h
        "args": ["federal_register"],
        "options": {"queue": "ingest_api"},
    },
    # EUR-Lex: every 6 hours
    "ingest-eurlex": {
        "task": "workers.tasks.ingest.poll_source_task",
        "schedule": 21600.0,  # 6 h
        "args": ["eurlex"],
        "options": {"queue": "ingest_api"},
    },
    # India OGD (data.gov.in): daily at 04:00 UTC
    "ingest-data-gov-in": {
        "task": "workers.tasks.ingest.poll_source_task",
        "schedule": crontab(hour=4, minute=0),
        "args": ["data_gov_in"],
        "options": {"queue": "ingest_api"},
    },
    # GLEIF Nightly Corporate Hierarchy Enrichment: daily at 01:00 UTC
    "ingest-gleif-nightly": {
        "task": "workers.tasks.ingest.poll_source_task",
        "schedule": crontab(hour=1, minute=0),
        "args": ["gleif"],
        "options": {"queue": "ingest_api"},
    },
    # ── HTML Monitors ─────────────────────────────────────────────────────────
    # DGFT Notifications: every 4 hours
    "ingest-dgft-html": {
        "task": "workers.tasks.ingest.poll_source_task",
        "schedule": 14400.0,  # 4 h
        "args": ["dgft_html"],
        "options": {"queue": "ingest_html"},
    },
    # CBIC Customs Tariff: every 4 hours
    "ingest-cbic-html": {
        "task": "workers.tasks.ingest.poll_source_task",
        "schedule": 14400.0,  # 4 h
        "args": ["cbic_html"],
        "options": {"queue": "ingest_html"},
    },
}
