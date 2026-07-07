"""Celery worker entrypoint.

Run with:
    celery -A app.queue.worker worker --loglevel=info --concurrency=2 -Q tickets
"""
from app.queue.tasks import celery_app  # noqa: F401 — re-export for celery CLI

__all__ = ["celery_app"]
