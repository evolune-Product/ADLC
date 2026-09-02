from celery import Celery
from app.config import settings

celery_app = Celery(
    "agentic_sdlc",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.run_tasks", "app.tasks.memory_tasks", "app.tasks.simulation_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # NOT gevent. Every DB call in this codebase goes through synchronous
    # psycopg2 (via SQLAlchemy), and every external call (httpx, PyGithub, the
    # Anthropic SDK) is blocking, plain-socket I/O too — none of it is
    # gevent-monkey-patched. Under gevent's cooperative scheduler, psycopg2's
    # blocking C-level socket read never yields, so the greenlet — and with it
    # the whole worker — hangs forever on the very first query any task makes.
    # Confirmed live: a task would log "received" and then nothing, ever,
    # regardless of how fresh the worker process was. prefork (real OS
    # processes) has none of this cooperative-scheduling gotcha and is
    # Celery's own default for exactly this kind of synchronous workload.
    worker_pool="prefork",
    # Data-retention enforcement: a documented policy nobody executes is an
    # audit finding, so the pruner runs on a schedule rather than on request.
    beat_schedule={
        "prune-retention-nightly": {
            "task": "memory_tasks.prune_retention",
            "schedule": 24 * 60 * 60,
        },
    },
)
