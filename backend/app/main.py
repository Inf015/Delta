import logging
import re

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.api.admin.router import router as admin_router
from app.api.auth.router import router as auth_router
from app.api.teams.router import router as teams_router
from app.api.upload.router import router as upload_router
from app.api.sessions.router import router as sessions_router
from app.api.racing_sessions.router import router as racing_sessions_router

logger = logging.getLogger(__name__)

# Patterns that are always accepted when allow_ngrok=True
_NGROK_PATTERN = re.compile(
    r"^https?://[a-zA-Z0-9\-]+\.(ngrok-free\.app|ngrok\.io|ngrok\.app|ngrok\.dev)$"
)

_EXPLICIT_ORIGINS: set[str] = {
    o.strip() for o in settings.allowed_origins.split(",") if o.strip()
}

_ALLOWED_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
_ALLOWED_HEADERS = "Content-Type, Authorization, ngrok-skip-browser-warning"


def _origin_allowed(origin: str) -> bool:
    if origin in _EXPLICIT_ORIGINS:
        return True
    if settings.allow_ngrok and _NGROK_PATTERN.match(origin):
        return True
    return False


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    """
    CORS middleware that mirrors the request Origin header when the origin is
    in the allow-list (or matches ngrok patterns). This lets us use
    credentials=True with dynamic origins such as ngrok tunnels.
    """

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin", "")
        allowed = _origin_allowed(origin)

        # Preflight — respond immediately without hitting the app
        if request.method == "OPTIONS":
            response = Response(status_code=204)
            if allowed:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = _ALLOWED_METHODS
                response.headers["Access-Control-Allow-Headers"] = _ALLOWED_HEADERS
                response.headers["Access-Control-Max-Age"] = "600"
            return response

        response = await call_next(request)

        if allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = _ALLOWED_METHODS
            response.headers["Access-Control-Allow-Headers"] = _ALLOWED_HEADERS
            response.headers["Vary"] = "Origin"

        return response


app = FastAPI(
    title="SimTelemetry Pro",
    description="Plataforma de análisis de telemetría para sim racing",
    version="0.1.0",
    # No exponer docs en producción
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

app.add_middleware(DynamicCORSMiddleware)

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
