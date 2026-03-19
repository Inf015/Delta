"""
POST /api/v1/upload/
Recibe un CSV de telemetría, lo guarda en disco, lo parsea y crea un TelemetrySession.
"""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_db
from app.models.session import SessionType, Simulator, SourceType, TelemetrySession
from app.schemas.session import SessionOut
from app.services.parsers.csv_parser import is_valid_lap, parse_csv
from app.tasks.process_session import process_session

router = APIRouter(prefix="/upload", tags=["upload"])


def _fmt(lap_time: float) -> str:
    if lap_time <= 0:
        return "—"
    m = int(lap_time // 60)
    s = lap_time - m * 60
    return f"{m}:{s:06.3f}"


@router.post("/", response_model=SessionOut, status_code=201)
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # ── Validar extensión ────────────────────────────────────────────────────
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .csv")

    # ── Parsear en memoria para detectar simulador antes de guardar ──────────
    tmp_path = Path("/tmp") / f"{uuid.uuid4()}.csv"
    try:
        with tmp_path.open("wb") as buf:
            shutil.copyfileobj(file.file, buf)
    finally:
        await file.close()

    parsed = parse_csv(tmp_path)

    if parsed is None:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="El archivo no es un CSV de telemetría válido")

    if not is_valid_lap(parsed):
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422,
            detail="Vuelta inválida (pit lap, marcada como inválida o tiempo demasiado bajo)",
        )

    meta = parsed.meta

    # ── Determinar simulador y directorio destino ────────────────────────────
    sim_str = meta.simulator.upper()
    if sim_str.startswith("AC"):
        sim_enum = Simulator.ac
        sub_dir = "ac"
    elif sim_str.startswith("R3E"):
        sim_enum = Simulator.r3e
        sub_dir = "r3e"
    else:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Simulador no reconocido: {sim_str}")

    # ── Guardar CSV en destino definitivo ────────────────────────────────────
    dest_dir = Path(settings.csv_data_path) / sub_dir
    dest_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file.filename).name
    dest_path = dest_dir / f"{uuid.uuid4()}_{safe_name}"
    shutil.move(str(tmp_path), dest_path)

    # ── Mapear session_type ──────────────────────────────────────────────────
    event_lower = meta.event.lower()
    if "qualify" in event_lower or "qual" in event_lower:
        session_type = SessionType.qualify
    elif "race" in event_lower:
        session_type = SessionType.race
    else:
        session_type = SessionType.practice

    # ── Crear registro en BD ────────────────────────────────────────────────
    # TODO PASO 7: user_id vendrá del token JWT. Por ahora placeholder.
    PLACEHOLDER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

    session_record = TelemetrySession(
        user_id=PLACEHOLDER_USER_ID,
        simulator=sim_enum,
        track=meta.track,
        car=meta.car,
        session_type=session_type,
        lap_number=meta.lap_number,
        lap_time=meta.lap_time,
        s1=meta.s1,
        s2=meta.s2,
        s3=meta.s3,
        tyre_compound=meta.tyre_compound,
        track_temp=meta.track_temp,
        ambient_temp=meta.ambient_temp,
        track_length=meta.track_length,
        valid=meta.valid,
        source=SourceType.upload,
        csv_path=str(dest_path),
        session_date=meta.date,
    )

    db.add(session_record)
    db.commit()
    db.refresh(session_record)

    # Disparar tarea de procesamiento en background (PDF + pre-análisis)
    process_session.delay(str(session_record.id))

    return SessionOut(
        session_id=session_record.id,
        simulator=session_record.simulator.value,
        track=session_record.track,
        car=session_record.car,
        lap_time=session_record.lap_time,
        lap_time_fmt=_fmt(session_record.lap_time),
        s1=session_record.s1,
        s2=session_record.s2,
        s3=session_record.s3,
        tyre_compound=session_record.tyre_compound,
        track_length=session_record.track_length,
        session_type=session_record.session_type.value,
        lap_number=session_record.lap_number,
        valid=session_record.valid,
    )
