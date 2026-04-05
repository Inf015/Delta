import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.admin.router import router as admin_router
from app.api.auth.router import router as auth_router
from app.api.teams.router import router as teams_router
from app.api.upload.router import router as upload_router
from app.api.sessions.router import router as sessions_router
from app.api.racing_sessions.router import router as racing_sessions_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SimTelemetry Pro",
    description="Plataforma de análisis de telemetría para sim racing",
    version="0.1.0",
    # No exponer docs en producción
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "ngrok-skip-browser-warning"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(racing_sessions_router, prefix="/api/v1")
app.include_router(teams_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/health")
def health():
    """Liveness check — responde siempre que el proceso esté vivo."""
    return {"status": "ok", "version": "0.1.0"}


@app.get("/ready")
def ready():
    """Readiness check — verifica que DB y Redis estén disponibles."""
    from sqlalchemy import text
    from app.core.db import engine
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("DB not ready: %s", exc)
        from fastapi import Response
        return Response(content="db_unavailable", status_code=503)
    return {"status": "ready"}
