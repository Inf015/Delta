"""
GET /api/v1/sessions/          — lista de sesiones del usuario placeholder
GET /api/v1/sessions/{id}      — detalle de sesión
GET /api/v1/sessions/{id}/analysis — análisis de la sesión
GET /api/v1/sessions/{id}/pdf  — descarga del PDF
"""

import math
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.session import TelemetrySession
from app.models.analysis import Analysis
from app.models.user import User
from app.utils.formatters import fmt_lap_time as _fmt

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _session_dict(s: TelemetrySession) -> dict:
    return {
        "session_id": str(s.id),
        "simulator": s.simulator.value,
        "track": s.track,
        "car": s.car,
        "lap_time": s.lap_time,
        "lap_time_fmt": _fmt(s.lap_time),
        "s1": s.s1,
        "s2": s.s2,
        "s3": s.s3,
        "tyre_compound": s.tyre_compound,
        "track_length": s.track_length,
        "session_type": s.session_type.value,
        "lap_number": s.lap_number,
        "valid": s.valid,
        "pdf_path": s.pdf_path,
        "session_date": s.session_date,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _analysis_dict(a: Analysis) -> dict:
    return {
        "id": str(a.id),
        "status": a.status.value,
        "pre_analysis": a.pre_analysis,
        "ai_result": a.ai_result,
        "tokens_input": a.tokens_input,
        "tokens_output": a.tokens_output,
        "error_message": a.error_message,
        "completed_at": a.completed_at.isoformat() if a.completed_at else None,
    }


@router.get("/")
def list_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sessions = (
        db.query(TelemetrySession)
        .filter(TelemetrySession.user_id == current_user.id)
        .order_by(TelemetrySession.created_at.desc())
        .all()
    )
    return [_session_dict(s) for s in sessions]


@router.get("/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")

    s = db.query(TelemetrySession).filter(
        TelemetrySession.id == sid,
        TelemetrySession.user_id == current_user.id,
    ).first()

    if not s:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    return _session_dict(s)


@router.get("/{session_id}/analysis")
def get_analysis(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")

    # Verificar que la sesión pertenece al usuario
    s = db.query(TelemetrySession).filter(
        TelemetrySession.id == sid,
        TelemetrySession.user_id == current_user.id,
    ).first()

    if not s:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    a = db.query(Analysis).filter(Analysis.session_id == sid).first()

    if not a:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")

    return _analysis_dict(a)


@router.get("/{session_id}/pdf")
def download_pdf(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")

    s = db.query(TelemetrySession).filter(
        TelemetrySession.id == sid,
        TelemetrySession.user_id == current_user.id,
    ).first()

    if not s:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if not s.pdf_path:
        raise HTTPException(status_code=404, detail="PDF no disponible aún")

    pdf_path = Path(s.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Archivo PDF no encontrado en disco")

    safe_track = re.sub(r"[^\w\-]", "_", s.track or "session")[:40]
    filename = f"delta_{safe_track}_{_fmt(s.lap_time)}.pdf".replace(":", "-")
    return FileResponse(path=str(pdf_path), media_type="application/pdf", filename=filename)
