"""
Celery Beat schedules — all ingestion and maintenance jobs.
Populated in Phase 8 onwards. Stub here so Beat starts cleanly.
"""

from celery.schedules import crontab

# ponytail: empty for Phase 1; filled in as connectors are added (Phase 8+)
CELERYBEAT_SCHEDULE: dict = {}
