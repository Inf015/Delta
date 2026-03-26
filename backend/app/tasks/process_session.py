"""
Tarea Celery: procesa una TelemetrySession después del upload.

Flujo completo:
  1. Leer TelemetrySession de BD
  2. Parsear CSV del disco
  3. Generar PDF (11 secciones)
  4. Calcular pre-análisis (sin IA)
  5. Buscar/crear KnowledgeProfile y actualizarlo
  6. Llamar Claude Haiku con pre-análisis + perfil histórico
  7. Guardar ai_result + Recommendations en BD
  8. Marcar Analysis(status=done) + session.processed=True
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from celery.utils.log import get_task_logger

from app.core.celery_app import celery_app
from app.core.db import SessionLocal
from app.models.analysis import Analysis, AnalysisStatus
from app.models.knowledge import Recommendation
from app.models.session import TelemetrySession
from sqlalchemy import desc
from app.services.analysis import pre_analysis as pre
from app.services.ai import claude_client
from app.services.knowledge import kb_service
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
    """Procesa una sesión de punta a punta."""
    db = SessionLocal()
    sid = uuid.UUID(session_id)

    session: TelemetrySession | None = db.get(TelemetrySession, sid)
    if session is None:
        db.close()
        raise ValueError(f"Session {session_id} not found")

    # Cargar relación user antes de cerrar la sesión ORM
    pilot_name = session.user.name if session.user and session.user.name else "Piloto"

    # Buscar Analysis existente (puede ser un retry) o crear uno nuevo
    analysis = db.query(Analysis).filter_by(session_id=sid).first()
    if analysis is None:
        analysis = Analysis(
            session_id=sid,
            user_id=session.user_id,
            status=AnalysisStatus.processing,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
    else:
        analysis.status = AnalysisStatus.processing
        analysis.error_message = None
        db.commit()

    try:
        # ── 1. Parsear CSV ────────────────────────────────────────────────────
        parsed = parse_csv(session.csv_path)
        if parsed is None:
            raise RuntimeError(f"No se pudo parsear el CSV: {session.csv_path}")

        # ── 2. Generar PDF ────────────────────────────────────────────────────
        logger.info("Generando PDF para sesión %s", session_id)
        pdf_path = generate_pdf(parsed, pilot_name=pilot_name)
        session.pdf_path  = pdf_path
        session.processed = True

        # ── 3. Pre-análisis ───────────────────────────────────────────────────
        logger.info("Pre-análisis para sesión %s", session_id)
        pre_result = pre.compute(parsed)
        analysis.pre_analysis = pre_result

        # ── 4. Knowledge Base — actualizar perfil (0 tokens) ──────────────────
        profile = kb_service.get_or_create_profile(db, session.user_id, session)
        kb_service.update_profile(db, profile, session, pre_result)

        # Commit parcial: PDF + pre-análisis + KB quedan guardados aunque Claude falle
        analysis.status = AnalysisStatus.processing
        db.commit()

        # ── 5. Análisis con Claude ────────────────────────────────────────────
        # Cargar recomendaciones previas testeadas para cerrar el ciclo
        prev_recs = (
            db.query(Recommendation)
            .filter_by(profile_id=profile.id, tested=True)
            .order_by(desc(Recommendation.created_at))
            .limit(5)
            .all()
        )

        # Buscar la mejor vuelta procesada de la misma racing_session para comparación
        best_lap_pre: dict | None = None
        if session.racing_session_id:
            from app.models.analysis import Analysis as AnalysisModel
            best_session = (
                db.query(TelemetrySession)
                .filter(
                    TelemetrySession.racing_session_id == session.racing_session_id,
                    TelemetrySession.processed == True,
                    TelemetrySession.id != sid,
                )
                .order_by(TelemetrySession.lap_time)
                .first()
            )
            if best_session:
                best_analysis = db.query(AnalysisModel).filter_by(session_id=best_session.id).first()
                if best_analysis and best_analysis.pre_analysis:
                    best_lap_pre = best_analysis.pre_analysis

        logger.info("Llamando Claude para sesión %s", session_id)
        ai_result, tok_in, tok_out = claude_client.analyze(
            pre_result, profile, prev_recs, best_lap_pre=best_lap_pre
        )

        analysis.ai_result     = ai_result
        analysis.tokens_input  = tok_in
        analysis.tokens_output = tok_out
        analysis.status        = AnalysisStatus.done
        analysis.completed_at  = datetime.now(timezone.utc)

        # Invalidar report_cache de la racing_session — puede haberse generado
        # antes de que este análisis completara, dejando datos vacíos en gomas/frenos
        if session.racing_session_id:
            from app.models.racing_session import RacingSession
            rs = db.get(RacingSession, session.racing_session_id)
            if rs:
                rs.report_cache = None

        # ── 6. Cerrar ciclo KB + guardar Recommendations ──────────────────────
        kb_service.update_after_ai(db, profile, ai_result, session.lap_time)

        for rec_data in ai_result.get("recommendations", []):
            text = rec_data.get("text", "")
            if not text:
                continue
            db.add(Recommendation(
                analysis_id=analysis.id,
                profile_id=profile.id,
                text=text,
                zone=rec_data.get("zone"),
            ))

        db.commit()
        logger.info(
            "Sesión %s OK — tokens: %d/%d — PDF: %s",
            session_id, tok_in, tok_out, pdf_path,
        )

        return {
            "session_id":  session_id,
            "pdf_path":    pdf_path,
            "weak_sector": pre_result.get("weak_sector"),
            "handling":    pre_result.get("handling"),
            "lap_time":    pre_result.get("lap_time"),
            "tokens":      tok_in + tok_out,
        }

    except Exception as exc:
        logger.error("Error en sesión %s: %s", session_id, exc)
        analysis.status        = AnalysisStatus.failed
        analysis.error_message = str(exc)
        db.commit()
        raise self.retry(exc=exc)

    finally:
        db.close()
