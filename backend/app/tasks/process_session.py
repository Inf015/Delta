"""
Tarea Celery: procesa una TelemetrySession después del upload.

Flujo:
  1. Leer TelemetrySession de BD
  2. Parsear CSV del disco
  3. Generar PDF (11 secciones)
  4. Calcular pre-análisis (sin IA)
  5. Crear/actualizar registro Analysis(status=done)
  6. Marcar session.processed = True
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from celery.utils.log import get_task_logger

from app.core.celery_app import celery_app
from app.core.db import SessionLocal
from app.models.analysis import Analysis, AnalysisStatus
from app.models.session import TelemetrySession
from app.services.analysis import pre_analysis as pre
from app.services.parsers.csv_parser import parse_csv
from app.services.reports.pdf_generator import generate_pdf

logger = get_task_logger(__name__)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name="app.tasks.process_session.process_session",
)
def process_session(self, session_id: str) -> dict:
    """
    Procesa una sesión: parsea → PDF → pre-análisis → guarda en BD.
    Retorna un dict con el resultado para el backend de Celery.
    """
    db = SessionLocal()
    sid = uuid.UUID(session_id)

    # ── Buscar sesión ─────────────────────────────────────────────────────────
    session: TelemetrySession | None = db.get(TelemetrySession, sid)
    if session is None:
        db.close()
        raise ValueError(f"Session {session_id} not found")

    # ── Crear registro Analysis en estado processing ───────────────────────────
    analysis = Analysis(
        session_id=sid,
        user_id=session.user_id,
        status=AnalysisStatus.processing,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    try:
        # ── 1. Parsear CSV ────────────────────────────────────────────────────
        parsed = parse_csv(session.csv_path)
        if parsed is None:
            raise RuntimeError(f"No se pudo parsear el CSV: {session.csv_path}")

        # ── 2. Generar PDF ────────────────────────────────────────────────────
        logger.info("Generando PDF para sesión %s", session_id)
        pilot_name = session.user.name if session.user and session.user.name else "Piloto"
        pdf_path = generate_pdf(parsed, pilot_name=pilot_name)

        # Guardar ruta en sesión
        session.pdf_path = pdf_path
        session.processed = True

        # ── 3. Pre-análisis ───────────────────────────────────────────────────
        logger.info("Calculando pre-análisis para sesión %s", session_id)
        pre_result = pre.compute(parsed)

        # ── 4. Actualizar Analysis ────────────────────────────────────────────
        analysis.pre_analysis = pre_result
        analysis.status = AnalysisStatus.done
        analysis.completed_at = datetime.now(timezone.utc)

        db.commit()
        logger.info("Sesión %s procesada OK — PDF: %s", session_id, pdf_path)

        return {
            "session_id":  session_id,
            "pdf_path":    pdf_path,
            "weak_sector": pre_result.get("weak_sector"),
            "handling":    pre_result.get("handling"),
            "lap_time":    pre_result.get("lap_time"),
        }

    except Exception as exc:
        logger.error("Error procesando sesión %s: %s", session_id, exc)
        analysis.status = AnalysisStatus.failed
        analysis.error_message = str(exc)
        db.commit()
        raise self.retry(exc=exc)

    finally:
        db.close()
