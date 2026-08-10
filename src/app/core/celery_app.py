from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "rag_multidoc_system",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.infrastructure.celery.tasks"],
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
    task_time_limit=60 * 15,
    task_soft_time_limit=60 * 12,
)
