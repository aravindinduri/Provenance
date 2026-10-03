"""
Celery application factory.

All task modules are autodiscovered from workers/tasks/.
Schedules are defined in workers/schedules.py and loaded by Celery Beat.
"""

from celery import Celery

from app.config import get_settings


def create_celery_app() -> Celery:
    settings = get_settings()

    from workers.schedules import CELERYBEAT_SCHEDULE

    app = Celery("provenance")
    app.config_from_object(
        {
            "broker_url": settings.celery_broker_url,
            "result_backend": settings.celery_result_backend,
            "task_serializer": "json",
            "result_serializer": "json",
            "accept_content": ["json"],
            "timezone": "UTC",
            "enable_utc": True,
            # Queues: ingest (data sources), ai (LLM tasks), notify (channels)
            "task_routes": {
                "workers.tasks.ingest.*": {"queue": "ingest"},
                "workers.tasks.ai.*": {"queue": "ai"},
                "workers.tasks.notify.*": {"queue": "notify"},
            },
            # Celery Beat schedules
            "beat_schedule": CELERYBEAT_SCHEDULE,
            # Retry defaults — individual tasks can override
            "task_acks_late": True,
            "task_reject_on_worker_lost": True,
            "task_default_retry_delay": 2,
            "task_max_retries": 5,
        }
    )

    # Autodiscover tasks from workers/tasks/
    app.autodiscover_tasks(["workers.tasks"])

    return app


celery_app = create_celery_app()
