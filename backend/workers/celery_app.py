from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "hybridrag",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=600,
    task_time_limit=900,
    task_default_retry_delay=60,
    task_max_retries=3,
)

celery_app.autodiscover_tasks(["workers.tasks.ingestion"])

import workers.tasks.ingestion  # noqa: F401 — ensure tasks are registered
