"""
POST /api/v1/upload/preview   — parsea CSV y devuelve metadata sin guardar
POST /api/v1/upload/          — sube 1+ CSVs a una RacingSession existente
                                Auto-completa track/car/sim/fecha si la sesión está vacía
"""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_db
from app.models.session import SessionType, Simulator, SourceType, TelemetrySession
from app.models.racing_session import RacingSession
from app.schemas.session import SessionOut
from app.services.parsers.csv_parser import is_valid_lap, parse_csv
from app.tasks.process_session import process_session

router = APIRouter(prefix="/upload", tags=["upload"])

PLACEHOLDER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _fmt(lap_time: float) -> str:
    if lap_time <= 0:
        return "—"
    m = int(lap_time // 60)
    s = lap_time - m * 60
    return f"{m}:{s:06.3f}"


def _sim_enum(sim_str: str) -> tuple[Simulator, str]:
    s = sim_str.upper()
    if s.startswith("AC"):
        return Simulator.ac, "ac"
    if s.startswith("R3E"):
        return Simulator.r3e, "r3e"
    raise HTTPException(status_code=422, detail=f"Simulador no reconocido: {sim_str}")


def _session_type(event: str) -> SessionType:
    e = event.lower()
    if "qualify" in e or "qual" in e:
        return SessionType.qualify
    if "race" in e:
        return SessionType.race
    return SessionType.practice


async def _save_tmp(file: UploadFile) -> Path:
    tmp = Path("/tmp") / f"{uuid.uuid4()}.csv"
    try:
        with tmp.open("wb") as buf:
            shutil.copyfileobj(file.file, buf)
    finally:
        await file.close()
    return tmp


# ── Preview ──────────────────────────────────────────────────────────────────

class PreviewOut(BaseModel):
    track: str
    car: str
    simulator: str
    session_date: str
    session_type: str
    lap_time: float
    lap_time_fmt: str
    s1: float
    s2: float
    s3: float
    tyre_compound: str
    track_length: float
    lap_number: int


@router.post("/preview", response_model=PreviewOut)
async def preview_csv(file: UploadFile = File(...)):
    """Parsea el CSV y devuelve su metadata sin persistir nada."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .csv")

    tmp = await _save_tmp(file)
    parsed = parse_csv(tmp)
    tmp.unlink(missing_ok=True)

    if parsed is None:
        raise HTTPException(status_code=422, detail="El archivo no es un CSV de telemetría válido")
    if parsed.meta.lap_time < 5.0:
        raise HTTPException(status_code=422, detail="Tiempo de vuelta inválido (<5s)")

    m = parsed.meta
    st = _session_type(m.event)
    sim_enum, _ = _sim_enum(m.simulator)

    return PreviewOut(
        track=m.track,
        car=m.car,
        simulator=sim_enum.value,
        session_date=m.date,
        session_type=st.value,
        lap_time=m.lap_time,
        lap_time_fmt=_fmt(m.lap_time),
        s1=m.s1,
        s2=m.s2,
        s3=m.s3,
        tyre_compound=m.tyre_compound,
        track_length=m.track_length,
        lap_number=m.lap_number,
    )


# ── Upload vueltas a sesión existente ────────────────────────────────────────

class UploadResult(BaseModel):
    racing_session_id: uuid.UUID
    laps_uploaded: int
    laps_skipped: int
    laps_duplicate: int
    sessions: list[SessionOut]


@router.post("/", response_model=UploadResult, status_code=201)
async def upload_csv(
    files: list[UploadFile] = File(...),
    racing_session_id: uuid.UUID = Form(...),
    db: Session = Depends(get_db),
):
    if not files:
        raise HTTPException(status_code=400, detail="Se requiere al menos un archivo")

    rs = db.query(RacingSession).filter_by(
        id=racing_session_id, user_id=PLACEHOLDER_USER_ID
    ).first()
    if not rs:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    created_sessions: list[SessionOut] = []
    skipped = 0
    duplicates = 0
    session_meta_filled = False  # solo auto-llenamos una vez

    for file in files:
        if not file.filename or not file.filename.lower().endswith(".csv"):
            skipped += 1
            continue

        tmp = await _save_tmp(file)
        parsed = parse_csv(tmp)

        if parsed is None:
            tmp.unlink(missing_ok=True)
            skipped += 1
            continue

        # Solo rechazar si el tiempo es absurdo (<5s) — pit laps e inválidas se aceptan
        if parsed.meta.lap_time < 5.0:
            tmp.unlink(missing_ok=True)
            skipped += 1
            continue

        # Deduplicación: misma sesión + mismo lap_time (redondeado a 3 decimales)
        existing = db.query(TelemetrySession).filter_by(
            racing_session_id=racing_session_id,
            lap_number=parsed.meta.lap_number,
        ).filter(
            TelemetrySession.lap_time.between(
                parsed.meta.lap_time - 0.001,
                parsed.meta.lap_time + 0.001,
            )
        ).first()
        if existing:
            tmp.unlink(missing_ok=True)
            duplicates += 1
            continue

        m = parsed.meta
        sim_enum, sub_dir = _sim_enum(m.simulator)

        # Auto-llenar sesión con datos del primer CSV válido
        if not session_meta_filled and rs.track is None:
            rs.track = m.track
            rs.car = m.car
            rs.simulator = sim_enum
            rs.session_date = m.date
            rs.session_type = _session_type(m.event)
            db.flush()
            session_meta_filled = True

        dest_dir = Path(settings.csv_data_path) / sub_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file.filename).name
        dest_path = dest_dir / f"{uuid.uuid4()}_{safe_name}"
        shutil.move(str(tmp), dest_path)

        lap = TelemetrySession(
            user_id=PLACEHOLDER_USER_ID,
            racing_session_id=rs.id,
            simulator=sim_enum,
            track=rs.track or m.track,
            car=rs.car or m.car,
            session_type=rs.session_type or _session_type(m.event),
            lap_number=m.lap_number,
            lap_time=m.lap_time,
            s1=m.s1,
            s2=m.s2,
            s3=m.s3,
            tyre_compound=m.tyre_compound,
            track_temp=m.track_temp,
            ambient_temp=m.ambient_temp,
            track_length=m.track_length,
            valid=m.valid,
            source=SourceType.upload,
            csv_path=str(dest_path),
            session_date=rs.session_date or m.date,
        )

        db.add(lap)
        db.flush()
        db.refresh(lap)

        # Invalidar caché del reporte al agregar nuevas vueltas
        rs.report_cache = None

        process_session.delay(str(lap.id))

        created_sessions.append(SessionOut(
            session_id=lap.id,
            simulator=lap.simulator.value,
            track=lap.track,
            car=lap.car,
            lap_time=lap.lap_time,
            lap_time_fmt=_fmt(lap.lap_time),
            s1=lap.s1,
            s2=lap.s2,
            s3=lap.s3,
            tyre_compound=lap.tyre_compound,
            track_length=lap.track_length,
            session_type=lap.session_type.value,
            lap_number=lap.lap_number,
            valid=lap.valid,
            racing_session_id=rs.id,
        ))

    db.commit()

    if not created_sessions and duplicates == 0:
        raise HTTPException(
            status_code=422,
            detail="Ningún archivo era un CSV de telemetría válido",
        )

    return UploadResult(
        racing_session_id=rs.id,
        laps_uploaded=len(created_sessions),
        laps_skipped=skipped,
        laps_duplicate=duplicates,
        sessions=created_sessions,
    )
