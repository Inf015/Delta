"""
Endpoints para RacingSessions (agrupaciones de vueltas).

POST  /api/v1/racing-sessions/          Crear sesión (vacía)
GET   /api/v1/racing-sessions/          Lista sesiones del usuario
GET   /api/v1/racing-sessions/{id}      Detalle con vueltas embebidas
PATCH /api/v1/racing-sessions/{id}      Editar campos
GET   /api/v1/racing-sessions/{id}/report  Reporte completo 11 secciones
POST  /api/v1/racing-sessions/compare   Comparación de dos sesiones
"""

import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.analysis import Analysis
from app.models.racing_session import RacingSession
from app.models.session import SessionType, Simulator, TelemetrySession
from app.models.track_info import TrackInfo
from app.models.user import User
from app.services.ai import claude_client
from app.services.analysis import session_report as sr
from app.services.parsers.csv_parser import parse_csv
from app.services.parsers.setup_parser import parse_setup
from app.services.reports.pdf_report import generate_report_pdf
from app.services.tracks import track_service
from app.services.tracks.track_normalizer import normalize_track_id
from app.utils.formatters import fmt_lap_time as _fmt

router = APIRouter(prefix="/racing-sessions", tags=["racing-sessions"])
logger = logging.getLogger(__name__)

# Bump this when the report schema changes (new sections/fields).
# Any cached report with a different version is automatically regenerated.
_REPORT_CACHE_VERSION = 2


def _generate_report(rs: RacingSession, db: Session) -> dict:
    """Genera el reporte completo (secciones 0-11) para una RacingSession.
    No guarda en caché — el caller es responsable de persistir rs.report_cache.
    """
    laps = (
        db.query(TelemetrySession)
        .filter_by(racing_session_id=rs.id)
        .order_by(TelemetrySession.lap_number)
        .all()
    )
    if not laps:
        raise HTTPException(status_code=422, detail="La sesión no tiene vueltas cargadas")

    analyses = db.query(Analysis).filter(
        Analysis.session_id.in_([l.id for l in laps])
    ).all()
    analysis_map = {a.session_id: a.pre_analysis for a in analyses if a.session_id and a.pre_analysis}

    laps_data = [
        {
            "lap_number": lap.lap_number,
            "lap_time":   lap.lap_time,
            "s1": lap.s1, "s2": lap.s2, "s3": lap.s3,
            "valid": lap.valid,
            "pre_analysis": analysis_map.get(lap.id),
        }
        for lap in laps
    ]

    track_info_dict = None
    if rs.track:
        best = min(laps_data, key=lambda l: l["lap_time"])
        track_length = (best.get("pre_analysis") or {}).get("track_length")
        try:
            track_info_dict = track_service.get_track_info(db, rs.track, track_length)
        except Exception:
            pass

    # Setup de la sesión anterior en la misma pista/auto para comparación
    prev_setup: dict | None = None
    if rs.setup_data and rs.track:
        prev_rs = (
            db.query(RacingSession)
            .filter(
                RacingSession.user_id == rs.user_id,
                RacingSession.track == rs.track,
                RacingSession.car == rs.car,
                RacingSession.id != rs.id,
                RacingSession.setup_data.isnot(None),
            )
            .order_by(RacingSession.created_at.desc())
            .first()
        )
        if prev_rs:
            prev_setup = prev_rs.setup_data

    report = sr.compute(laps_data, setup_data=rs.setup_data, track_info=track_info_dict)
    best_pre = min(laps_data, key=lambda l: l["lap_time"]).get("pre_analysis") or {}

    ai_sections, tok_in, tok_out = claude_client.analyze_session(
        session_summary=report.get("section_1_summary", {}),
        best_lap_pre=best_pre,
        setup_data=rs.setup_data,
        track_info=track_info_dict,
        prev_setup=prev_setup,
    )
    report.update(ai_sections)

    pilot_name = rs.user.name if rs.user and rs.user.name else "Piloto"
    report["meta"] = {
        "racing_session_id": str(rs.id),
        "name": rs.name,
        "track": rs.track,
        "car": rs.car,
        "simulator": rs.simulator.value if rs.simulator else None,
        "session_date": rs.session_date,
        "session_type": rs.session_type.value if rs.session_type else None,
        "pilot": pilot_name,
        "tyre_compound": laps[0].tyre_compound if laps else None,
        "tokens_used": tok_in + tok_out,
        "_cache_version": _REPORT_CACHE_VERSION,
    }
    return report


def _best_lap_with_csv_and_data(racing_session_id: uuid.UUID, db: Session) -> dict | None:
    """
    Returns resampled telemetry points for the best lap of a racing session.
    Returns None if no CSV is available or parsing fails.
    """
    N = 400
    lap = (
        db.query(TelemetrySession)
        .filter(
            TelemetrySession.racing_session_id == racing_session_id,
            TelemetrySession.csv_path.isnot(None),
        )
        .order_by(TelemetrySession.lap_time)
        .first()
    )
    if not lap:
        return None

    parsed = parse_csv(lap.csv_path)
    if parsed is None:
        return None

    df = parsed.telemetry
    required = {"x", "z", "lap_distance", "speed"}
    if required - set(df.columns):
        return None

    optional = {"throttle", "brake", "gear"}
    cols = list(required | (optional & set(df.columns)))
    df = df[cols].dropna(subset=list(required))
    df = df.sort_values("lap_distance").reset_index(drop=True)
    if df.empty or df["lap_distance"].max() <= 0:
        return None

    d_norm    = (df["lap_distance"] / df["lap_distance"].max()).values
    d_uniform = np.linspace(0.0, 1.0, N)

    def _interp(col: str, default: float = 0.0) -> np.ndarray:
        if col in df.columns:
            return np.interp(d_uniform, d_norm, df[col].values)
        return np.full(N, default)

    x_v  = _interp("x")
    z_v  = _interp("z")
    sp_v = _interp("speed")
    th_v = _interp("throttle")
    br_v = _interp("brake")
    ge_v = _interp("gear")

    points = [
        {
            "d":        float(d_uniform[i]),
            "x":        float(x_v[i]),
            "z":        float(z_v[i]),
            "speed":    float(sp_v[i]),
            "throttle": float(th_v[i]),
            "brake":    float(br_v[i]),
            "gear":     int(round(float(np.clip(ge_v[i], 0, 8)))),
        }
        for i in range(N)
    ]

    return {
        "points":       points,
        "lap_time":     lap.lap_time,
        "lap_time_fmt": _fmt(lap.lap_time),
    }


# ── Schemas de respuesta ────────────────────────────────────────────────────

class RacingSessionCreate(BaseModel):
    name: str | None = Field(None, max_length=200)
    track: str | None = Field(None, max_length=150)
    car: str | None = Field(None, max_length=150)
    simulator: str | None = Field(None, max_length=10)
    session_date: str | None = Field(None, max_length=20)
    session_type: str | None = Field(None, max_length=20)


class RacingSessionUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    track: str | None = Field(None, max_length=150)
    car: str | None = Field(None, max_length=150)
    simulator: str | None = Field(None, max_length=10)
    session_date: str | None = Field(None, max_length=20)
    session_type: str | None = Field(None, max_length=20)


class IncidentOut(BaseModel):
    type: str
    dist_m: float | None
    detail: str
    severity: str


class LapOut(BaseModel):
    session_id: uuid.UUID
    lap_number: int
    lap_time: float
    lap_time_fmt: str
    s1: float
    s2: float
    s3: float
    tyre_compound: str
    valid: bool
    processed: bool
    incidents: list[IncidentOut] = []

    model_config = {"from_attributes": True}


class RacingSessionOut(BaseModel):
    id: uuid.UUID
    name: str | None
    track: str | None
    car: str | None
    simulator: str | None
    session_date: str | None
    session_type: str | None
    lap_count: int
    best_lap: float | None
    best_lap_fmt: str

    model_config = {"from_attributes": True}


class RacingSessionDetail(BaseModel):
    id: uuid.UUID
    name: str | None
    track: str | None
    car: str | None
    simulator: str | None
    session_date: str | None
    session_type: str | None
    laps: list[LapOut]
    setup_data: dict | None = None

    model_config = {"from_attributes": True}


class CompareRequest(BaseModel):
    session_a_id: uuid.UUID
    session_b_id: uuid.UUID


# ── Helpers ─────────────────────────────────────────────────────────────────

def _rs_out(rs: RacingSession, lap_count: int, best_lap: float | None) -> RacingSessionOut:
    return RacingSessionOut(
        id=rs.id,
        name=rs.name,
        track=rs.track,
        car=rs.car,
        simulator=rs.simulator.value if rs.simulator else None,
        session_date=rs.session_date,
        session_type=rs.session_type.value if rs.session_type else None,
        lap_count=lap_count,
        best_lap=best_lap,
        best_lap_fmt=_fmt(best_lap) if best_lap else "—",
    )


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/", response_model=RacingSessionOut, status_code=201)
def create_racing_session(body: RacingSessionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sim = None
    if body.simulator:
        try:
            sim = Simulator(body.simulator.upper())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Simulador inválido: {body.simulator}")

    st = None
    if body.session_type:
        try:
            st = SessionType(body.session_type)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Tipo de sesión inválido: {body.session_type}")

    rs = RacingSession(
        user_id=current_user.id,
        name=body.name,
        track=body.track.strip() if body.track else None,
        car=body.car.strip() if body.car else None,
        simulator=sim,
        session_date=body.session_date.strip() if body.session_date else None,
        session_type=st,
    )
    db.add(rs)
    db.commit()
    db.refresh(rs)

    return _rs_out(rs, lap_count=0, best_lap=None)


@router.patch("/{racing_session_id}", response_model=RacingSessionOut)
def update_racing_session(
    racing_session_id: uuid.UUID,
    body: RacingSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rs = db.query(RacingSession).filter_by(id=racing_session_id, user_id=current_user.id).first()
    if not rs:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if body.name is not None:
        rs.name = body.name
    if body.track is not None:
        rs.track = body.track.strip()
    if body.car is not None:
        rs.car = body.car.strip()
    if body.session_date is not None:
        rs.session_date = body.session_date.strip()
    if body.simulator is not None:
        try:
            rs.simulator = Simulator(body.simulator.upper())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Simulador inválido: {body.simulator}")
    if body.session_type is not None:
        try:
            rs.session_type = SessionType(body.session_type)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Tipo de sesión inválido: {body.session_type}")


    rs.report_cache = None  # invalidar caché al editar
    db.commit()
    db.refresh(rs)

    lap_count, best_lap = db.query(
        func.count(TelemetrySession.id),
        func.min(TelemetrySession.lap_time),
    ).filter_by(racing_session_id=rs.id).one()

    return _rs_out(rs, lap_count=lap_count or 0, best_lap=best_lap)


@router.delete("/{racing_session_id}", status_code=204)
def delete_racing_session(racing_session_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rs = db.query(RacingSession).filter_by(id=racing_session_id, user_id=current_user.id).first()
    if not rs:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    # Recopilar paths de CSV antes de borrar para limpiar el disco
    laps = db.query(TelemetrySession).filter_by(racing_session_id=racing_session_id).all()
    csv_paths = [Path(l.csv_path) for l in laps if l.csv_path]

    db.delete(rs)  # cascade elimina TelemetrySessions y sus Analysis
    db.commit()

    for p in csv_paths:
        p.unlink(missing_ok=True)


@router.get("/", response_model=list[RacingSessionOut])
def list_racing_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(
            RacingSession,
            func.count(TelemetrySession.id).label("lap_count"),
            func.min(TelemetrySession.lap_time).label("best_lap"),
        )
        .outerjoin(TelemetrySession, TelemetrySession.racing_session_id == RacingSession.id)
        .filter(RacingSession.user_id == current_user.id)
        .group_by(RacingSession.id)
        .order_by(RacingSession.created_at.desc())
        .all()
    )

    return [_rs_out(rs, lap_count or 0, best_lap) for rs, lap_count, best_lap in rows]


@router.get("/{racing_session_id}", response_model=RacingSessionDetail)
def get_racing_session(racing_session_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rs = db.query(RacingSession).filter_by(id=racing_session_id, user_id=current_user.id).first()
    if not rs:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    laps = (
        db.query(TelemetrySession)
        .filter_by(racing_session_id=racing_session_id)
        .order_by(TelemetrySession.lap_number)
        .all()
    )

    # Cargar pre_analysis para extraer incidentes
    analyses = db.query(Analysis).filter(
        Analysis.session_id.in_([l.id for l in laps])
    ).all()
    incidents_map: dict[uuid.UUID, list] = {
        a.session_id: (a.pre_analysis or {}).get("incidents", [])
        for a in analyses
        if a.session_id
    }

    return RacingSessionDetail(
        id=rs.id,
        name=rs.name,
        track=rs.track,
        car=rs.car,
        simulator=rs.simulator.value if rs.simulator else None,
        session_date=rs.session_date,
        session_type=rs.session_type.value if rs.session_type else None,
        setup_data=rs.setup_data,
        laps=[
            LapOut(
                session_id=lap.id,
                lap_number=lap.lap_number,
                lap_time=lap.lap_time,
                lap_time_fmt=_fmt(lap.lap_time),
                s1=lap.s1,
                s2=lap.s2,
                s3=lap.s3,
                tyre_compound=lap.tyre_compound,
                valid=lap.valid,
                processed=lap.processed,
                incidents=[
                    IncidentOut(**inc)
                    for inc in incidents_map.get(lap.id, [])
                    if isinstance(inc, dict)
                ],
            )
            for lap in laps
        ],
    )


@router.get("/{racing_session_id}/report")
def get_session_report(racing_session_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    """
    Devuelve el reporte de 11 secciones. Usa caché guardado en BD si existe.
    Se regenera solo si no hay caché (nueva sesión o fue invalidado).
    """
    rs = db.query(RacingSession).filter_by(id=racing_session_id, user_id=current_user.id).first()
    if not rs:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if rs.report_cache and rs.report_cache.get("meta", {}).get("_cache_version") == _REPORT_CACHE_VERSION:
        return rs.report_cache

    report = _generate_report(rs, db)
    rs.report_cache = report
    db.commit()
    return report


@router.get("/{racing_session_id}/pdf")
def download_session_pdf(racing_session_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Genera y descarga el PDF desde el reporte cacheado (mismo contenido que la web).
    Si no hay caché, genera el reporte primero.
    """
    rs = db.query(RacingSession).filter_by(id=racing_session_id, user_id=current_user.id).first()
    if not rs:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    report = rs.report_cache
    if not report or report.get("meta", {}).get("_cache_version") != _REPORT_CACHE_VERSION:
        report = _generate_report(rs, db)
        rs.report_cache = report
        db.commit()

    # Inject telemetry points for charts (not cached — computed on demand)
    try:
        lap_telem = _best_lap_with_csv_and_data(racing_session_id, db)
        if lap_telem:
            report = dict(report)  # shallow copy so cache is not mutated
            report["section_telemetry_points"] = lap_telem["points"]
            report["section_telemetry_lap_fmt"] = lap_telem["lap_time_fmt"]
    except Exception:
        pass

    out_dir = Path(settings.pdf_data_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    track = (report.get("meta") or {}).get("track") or "session"
    best_fmt = (report.get("section_1_summary") or {}).get("best_lap_fmt", "").replace(":", "-")
    safe_track = track.replace(" ", "_").replace("/", "-")[:30]
    pdf_path = out_dir / f"delta_{safe_track}_{best_fmt}.pdf"

    try:
        generate_report_pdf(report, pdf_path)
    except Exception as exc:
        logger.error("Error generando PDF para sesión %s: %s", racing_session_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Error generando el PDF. Intenta de nuevo.")

    filename = f"delta_{safe_track}_{best_fmt}.pdf"
    return FileResponse(path=str(pdf_path), media_type="application/pdf", filename=filename)


@router.post("/{racing_session_id}/setup", status_code=200)
async def upload_setup(
    racing_session_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Sube un archivo .ini de setup de AC a una RacingSession.
    Parsea el archivo, guarda el dict en setup_data e invalida el report_cache.
    """
    rs = db.query(RacingSession).filter_by(id=racing_session_id, user_id=current_user.id).first()
    if not rs:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if not file.filename or not file.filename.lower().endswith(".ini"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .ini")

    content = await file.read()
    if len(content) > _MAX_SETUP_SIZE:
        raise HTTPException(status_code=400, detail="El archivo es demasiado grande (máx 2MB)")

    tmp = Path("/tmp") / f"{uuid.uuid4()}.ini"
    tmp.write_bytes(content)

    setup = parse_setup(tmp)
    tmp.unlink(missing_ok=True)

    if setup is None:
        raise HTTPException(status_code=422, detail="El archivo no es un setup de AC válido")

    rs.setup_data = setup
    rs.report_cache = None  # invalidar reporte para que incluya el setup
    db.commit()

    return {"ok": True, "sections": list(setup.keys())}


_TRACK_MAP_DIR = Path(settings.track_maps_path)
_ALLOWED_MAP_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
_MAX_MAP_SIZE = 5 * 1024 * 1024    # 5MB
_MAX_SETUP_SIZE = 2 * 1024 * 1024  # 2MB


@router.post("/{racing_session_id}/track-map", status_code=200)
async def upload_track_map(
    racing_session_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Sube el mapa del circuito (PNG/JPG/SVG) a una RacingSession.
    El mapa se guarda en disco y se asocia al TrackInfo del circuito
    (es reutilizable entre todas las sesiones del mismo circuito).
    """
    rs = db.query(RacingSession).filter_by(id=racing_session_id, user_id=current_user.id).first()
    if not rs:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if not rs.track:
        raise HTTPException(status_code=422, detail="La sesión no tiene circuito asignado")

    fname = file.filename or ""
    ext = Path(fname).suffix.lower()
    if ext not in _ALLOWED_MAP_EXTS:
        raise HTTPException(status_code=400, detail=f"Formato no soportado. Usa: {', '.join(_ALLOWED_MAP_EXTS)}")

    content = await file.read()
    if len(content) > _MAX_MAP_SIZE:
        raise HTTPException(status_code=400, detail="El archivo es demasiado grande (máx 5MB)")

    from app.services.tracks.track_normalizer import normalize_track_id
    normalized = normalize_track_id(rs.track)

    _TRACK_MAP_DIR.mkdir(parents=True, exist_ok=True)
    map_path = _TRACK_MAP_DIR / f"{normalized}{ext}"
    map_path.write_bytes(content)

    # Guardar en TrackInfo
    ti = db.get(TrackInfo, normalized)
    if ti is None:
        ti = TrackInfo(track_id=normalized, source="unknown", display_name=rs.track)
        db.add(ti)
    ti.map_path = str(map_path)
    rs.report_cache = None  # invalidar caché (map_path ahora existe, cambia has_map)
    db.commit()

    return {"ok": True, "map_path": str(map_path), "track_id": normalized}


@router.get("/{racing_session_id}/track-map")
def get_track_map(racing_session_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Descarga el mapa del circuito asociado a la sesión.
    """
    rs = db.query(RacingSession).filter_by(id=racing_session_id, user_id=current_user.id).first()
    if not rs:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if not rs.track:
        raise HTTPException(status_code=404, detail="Sin circuito asignado")

    normalized = normalize_track_id(rs.track)

    ti = db.get(TrackInfo, normalized)
    if not ti or not ti.map_path:
        raise HTTPException(status_code=404, detail="No hay mapa para este circuito")

    map_file = Path(ti.map_path)
    if not map_file.exists():
        raise HTTPException(status_code=404, detail="Archivo de mapa no encontrado en disco")

    ext = map_file.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
    }
    return FileResponse(
        path=str(map_file),
        media_type=media_types.get(ext, "application/octet-stream"),
        filename=map_file.name,
    )


@router.post("/compare")
def compare_sessions(body: CompareRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    # Cargar ambas sesiones
    rs_a = db.query(RacingSession).filter_by(id=body.session_a_id, user_id=current_user.id).first()
    rs_b = db.query(RacingSession).filter_by(id=body.session_b_id, user_id=current_user.id).first()

    if not rs_a or not rs_b:
        raise HTTPException(status_code=404, detail="Una o ambas sesiones no encontradas")

    if rs_a.track != rs_b.track:
        raise HTTPException(
            status_code=400,
            detail=f"Las sesiones deben ser del mismo circuito ({rs_a.track} vs {rs_b.track})",
        )

    # Best lap de cada sesión (vuelta procesada con menor tiempo)
    def _best_lap(rs_id: uuid.UUID) -> TelemetrySession | None:
        return (
            db.query(TelemetrySession)
            .filter_by(racing_session_id=rs_id, processed=True)
            .order_by(TelemetrySession.lap_time)
            .first()
        )

    best_a = _best_lap(body.session_a_id)
    best_b = _best_lap(body.session_b_id)

    if not best_a or not best_b:
        raise HTTPException(
            status_code=422,
            detail="Ambas sesiones deben tener al menos una vuelta procesada",
        )

    # Cargar pre_analysis de cada best lap
    analysis_a = db.query(Analysis).filter_by(session_id=best_a.id).first()
    analysis_b = db.query(Analysis).filter_by(session_id=best_b.id).first()

    pre_a = analysis_a.pre_analysis if analysis_a else {}
    pre_b = analysis_b.pre_analysis if analysis_b else {}

    # Calcular deltas (B - A)
    delta_s1 = (best_b.s1 or 0) - (best_a.s1 or 0)
    delta_s2 = (best_b.s2 or 0) - (best_a.s2 or 0)
    delta_s3 = (best_b.s3 or 0) - (best_a.s3 or 0)
    delta_total = best_b.lap_time - best_a.lap_time

    meta_a = {"car": rs_a.car, "simulator": rs_a.simulator.value if rs_a.simulator else None, "track": rs_a.track}
    meta_b = {"car": rs_b.car, "simulator": rs_b.simulator.value if rs_b.simulator else None, "track": rs_b.track}

    # Llamar Claude para comparación
    ai_comparison, cmp_tok_in, cmp_tok_out = claude_client.compare(
        pre_a=pre_a or {},
        meta_a=meta_a,
        pre_b=pre_b or {},
        meta_b=meta_b,
        delta_s1=delta_s1,
        delta_s2=delta_s2,
        delta_s3=delta_s3,
        delta_total=delta_total,
    )
    logging.getLogger(__name__).info(
        "Compare Claude call — %s vs %s — tokens: %d in / %d out",
        body.session_a_id, body.session_b_id, cmp_tok_in, cmp_tok_out,
    )

    def _metrics(lap: TelemetrySession, pre: dict) -> dict:
        return {
            "max_speed": pre.get("max_speed_kmh"),
            "avg_throttle_pct": pre.get("avg_throttle_pct"),
            "g_lat_max": pre.get("g_lat_max"),
            "g_lon_brake": pre.get("g_lon_brake_max"),
        }

    return {
        "track": rs_a.track,
        "session_a": {"id": str(rs_a.id), "car": rs_a.car, "simulator": rs_a.simulator.value},
        "session_b": {"id": str(rs_b.id), "car": rs_b.car, "simulator": rs_b.simulator.value},
        "best_lap_a": {
            "lap_time": best_a.lap_time,
            "lap_time_fmt": _fmt(best_a.lap_time),
            "s1": best_a.s1,
            "s2": best_a.s2,
            "s3": best_a.s3,
        },
        "best_lap_b": {
            "lap_time": best_b.lap_time,
            "lap_time_fmt": _fmt(best_b.lap_time),
            "s1": best_b.s1,
            "s2": best_b.s2,
            "s3": best_b.s3,
        },
        "delta_s1": delta_s1,
        "delta_s2": delta_s2,
        "delta_s3": delta_s3,
        "delta_total": delta_total,
        "metrics_a": _metrics(best_a, pre_a),
        "metrics_b": _metrics(best_b, pre_b),
        "ai_comparison": ai_comparison,
    }


@router.get("/{racing_session_id}/delta-map")
def get_delta_map(
    racing_session_id: uuid.UUID,
    ref: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Genera el mapa de delta de velocidad entre la mejor vuelta de esta sesión (A)
    y la mejor vuelta de la sesión de referencia (B).

    Returns 300 puntos con coordenadas X/Z y delta de velocidad normalizado.
    """
    N = 300

    # ── Cargar sesiones ──────────────────────────────────────────────────────
    rs_a = db.query(RacingSession).filter_by(id=racing_session_id, user_id=current_user.id).first()
    if not rs_a:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    rs_b = db.query(RacingSession).filter_by(id=ref, user_id=current_user.id).first()
    if not rs_b:
        raise HTTPException(status_code=404, detail="Sesión de referencia no encontrada")

    # ── Validar mismo circuito ───────────────────────────────────────────────
    if rs_a.track != rs_b.track:
        raise HTTPException(
            status_code=400,
            detail=f"Las sesiones deben ser del mismo circuito ({rs_a.track} vs {rs_b.track})",
        )

    # ── Best lap con csv_path para cada sesión ───────────────────────────────
    def _best_lap_with_csv(rs_id: uuid.UUID) -> TelemetrySession | None:
        return (
            db.query(TelemetrySession)
            .filter(
                TelemetrySession.racing_session_id == rs_id,
                TelemetrySession.csv_path.isnot(None),
            )
            .order_by(TelemetrySession.lap_time)
            .first()
        )

    lap_a = _best_lap_with_csv(racing_session_id)
    lap_b = _best_lap_with_csv(ref)

    if not lap_a:
        raise HTTPException(status_code=404, detail="La sesión A no tiene vueltas con telemetría CSV")
    if not lap_b:
        raise HTTPException(status_code=404, detail="La sesión de referencia no tiene vueltas con telemetría CSV")

    # ── Parsear CSVs ─────────────────────────────────────────────────────────
    parsed_a = parse_csv(lap_a.csv_path)
    parsed_b = parse_csv(lap_b.csv_path)

    if parsed_a is None:
        raise HTTPException(status_code=422, detail="No se pudo parsear el CSV de la sesión A")
    if parsed_b is None:
        raise HTTPException(status_code=422, detail="No se pudo parsear el CSV de la sesión de referencia")

    # ── Preparar DataFrames ──────────────────────────────────────────────────
    def _prepare_df(df):
        required = {"x", "z", "lap_distance", "speed"}
        missing = required - set(df.columns)
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"El CSV no contiene las columnas requeridas: {missing}",
            )
        df = df[["x", "z", "lap_distance", "speed"]].dropna()
        df = df.sort_values("lap_distance").reset_index(drop=True)
        if df.empty or df["lap_distance"].max() <= 0:
            raise HTTPException(status_code=422, detail="El CSV no tiene datos de posición válidos")
        df["d"] = df["lap_distance"] / df["lap_distance"].max()
        return df

    df_a = _prepare_df(parsed_a.telemetry)
    df_b = _prepare_df(parsed_b.telemetry)

    # ── Resamplear a N puntos equiespaciados ─────────────────────────────────
    d_uniform = np.linspace(0.0, 1.0, N)

    x_a      = np.interp(d_uniform, df_a["d"].values, df_a["x"].values)
    z_a      = np.interp(d_uniform, df_a["d"].values, df_a["z"].values)
    speed_a  = np.interp(d_uniform, df_a["d"].values, df_a["speed"].values)

    x_b      = np.interp(d_uniform, df_b["d"].values, df_b["x"].values)  # noqa: F841
    z_b      = np.interp(d_uniform, df_b["d"].values, df_b["z"].values)  # noqa: F841
    speed_b  = np.interp(d_uniform, df_b["d"].values, df_b["speed"].values)

    # ── Calcular delta ───────────────────────────────────────────────────────
    delta = speed_a - speed_b  # positivo = A más rápido

    max_abs = float(np.abs(delta).max())
    if max_abs < 1.0:
        max_abs = 1.0
    delta_norm = np.clip(delta / max_abs, -1.0, 1.0)

    # ── Serializar puntos ────────────────────────────────────────────────────
    points = [
        {
            "x":          float(x_a[i]),
            "z":          float(z_a[i]),
            "delta":      float(delta[i]),
            "delta_norm": float(delta_norm[i]),
            "speed_a":    float(speed_a[i]),
            "speed_b":    float(speed_b[i]),
        }
        for i in range(N)
    ]

    return {
        "points": points,
        "session_a": {
            "id":           str(rs_a.id),
            "track":        rs_a.track,
            "best_lap_fmt": _fmt(lap_a.lap_time),
            "lap_time":     lap_a.lap_time,
        },
        "session_b": {
            "id":           str(rs_b.id),
            "track":        rs_b.track,
            "best_lap_fmt": _fmt(lap_b.lap_time),
            "lap_time":     lap_b.lap_time,
        },
        "delta_total": lap_a.lap_time - lap_b.lap_time,
    }


@router.get("/{racing_session_id}/lap-telemetry")
def get_lap_telemetry(
    racing_session_id: uuid.UUID,
    n: int = 500,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Retorna los datos de telemetría de la mejor vuelta de la sesión,
    resampleados a N puntos equiespaciados por distancia.
    Incluye: x, z, speed, throttle, brake, gear.
    """
    rs = db.query(RacingSession).filter_by(id=racing_session_id, user_id=current_user.id).first()
    if not rs:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    lap = (
        db.query(TelemetrySession)
        .filter(
            TelemetrySession.racing_session_id == racing_session_id,
            TelemetrySession.csv_path.isnot(None),
        )
        .order_by(TelemetrySession.lap_time)
        .first()
    )
    if not lap:
        raise HTTPException(status_code=404, detail="No hay vueltas con telemetría CSV")

    parsed = parse_csv(lap.csv_path)
    if parsed is None:
        raise HTTPException(status_code=422, detail="No se pudo parsear el CSV")

    df = parsed.telemetry
    required = {"x", "z", "lap_distance", "speed"}
    missing = required - set(df.columns)
    if missing:
        raise HTTPException(status_code=422, detail=f"Columnas faltantes: {missing}")

    optional = {"throttle", "brake", "gear"}
    cols = list(required | (optional & set(df.columns)))
    df = df[cols].dropna(subset=list(required))
    df = df.sort_values("lap_distance").reset_index(drop=True)
    if df.empty or df["lap_distance"].max() <= 0:
        raise HTTPException(status_code=422, detail="Datos de posición inválidos")

    d_norm = df["lap_distance"] / df["lap_distance"].max()
    d_uniform = np.linspace(0.0, 1.0, n)

    def interp(col: str, default: float = 0.0) -> list[float]:
        if col in df.columns:
            return np.interp(d_uniform, d_norm.values, df[col].values).tolist()
        return [default] * n

    x_vals      = interp("x")
    z_vals      = interp("z")
    speed_vals  = interp("speed")
    throttle_v  = interp("throttle")
    brake_v     = interp("brake")
    gear_raw    = interp("gear")

    points = [
        {
            "d":        float(d_uniform[i]),
            "x":        x_vals[i],
            "z":        z_vals[i],
            "speed":    speed_vals[i],
            "throttle": throttle_v[i],
            "brake":    brake_v[i],
            "gear":     int(round(max(0, min(8, gear_raw[i])))),
        }
        for i in range(n)
    ]

    return {
        "lap_time":     lap.lap_time,
        "lap_time_fmt": _fmt(lap.lap_time),
        "lap_number":   lap.lap_number,
        "points":       points,
    }
