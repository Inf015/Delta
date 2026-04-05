from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "simtelemetry",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.process_session"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,   # una tarea a la vez por worker (PDFs son pesados)
    # Timeouts: matar tareas que se cuelguen (Claude timeout = 90s, damos margen)
    task_soft_time_limit=600,       # 10 min: warning, tarea puede limpiar
    task_time_limit=660,            # 11 min: kill forzado
    # Evitar pérdida de tareas si Redis cae momentáneamente
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)
