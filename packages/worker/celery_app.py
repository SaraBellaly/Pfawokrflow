"""Configuration Celery avec Redis comme broker."""

from __future__ import annotations

from celery import Celery

from api.config import REDIS_URL

celery = Celery("funding_worker", broker=REDIS_URL, backend=REDIS_URL)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery.autodiscover_tasks(["worker"])
