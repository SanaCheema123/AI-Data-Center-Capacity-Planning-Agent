from celery import Celery

from app.core.config import settings

celery_app = Celery("capacity_agent", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "sync-real-data-sources": {
            "task": "data_sources.sync_all",
            "schedule": settings.collector_sync_minutes * 60.0,
        },
    },
)
