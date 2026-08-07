from celery import Celery
from app.config import settings

celery_app = Celery(
    "agentic_sdlc",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.run_tasks", "app.tasks.memory_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_pool="gevent",
    # Data-retention enforcement: a documented policy nobody executes is an
    # audit finding, so the pruner runs on a schedule rather than on request.
    beat_schedule={
        "prune-retention-nightly": {
            "task": "memory_tasks.prune_retention",
            "schedule": 24 * 60 * 60,
        },
    },
)
