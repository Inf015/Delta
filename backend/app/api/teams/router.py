"""
Endpoints para equipos de técnicos.

POST   /api/v1/teams/                        Crear equipo (técnico)
GET    /api/v1/teams/my                      Mi equipo con lista de pilotos
POST   /api/v1/teams/my/members              Agregar piloto por email
DELETE /api/v1/teams/my/members/{pilot_id}   Quitar piloto del equipo
GET    /api/v1/teams/my/sessions             Todas las sesiones de mis pilotos
GET    /api/v1/teams/my/pilots/{pilot_id}/sessions  Sesiones de un piloto específico
GET    /api/v1/teams/my/pilots/{pilot_id}/sessions/{session_id}/report  Reporte de sesión
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, get_technician_user
from app.models.racing_session import RacingSession
from app.models.session import TelemetrySession
from app.models.team import Team, TeamMember
from app.models.user import User
from app.utils.formatters import fmt_lap_time as _fmt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/teams", tags=["teams"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class AddPilotRequest(BaseModel):
    email: str


class PilotOut(BaseModel):
    id: str
    email: str
    name: str
    plan: str
    racing_sessions: int


class TeamOut(BaseModel):
    id: str
    name: str
    owner_id: str
    pilots: list[PilotOut]


class SessionSummary(BaseModel):
    id: str
    pilot_email: str
    pilot_name: str
    name: str | None
    track: str | None
    car: str | None
    session_date: str | None
    lap_count: int
    best_lap_fmt: str
    has_report: bool


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_my_team(db: Session, owner_id) -> Team:
    team = db.query(Team).filter(Team.owner_id == owner_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="No tienes un equipo creado todavía")
    return team


def _sessions_for_pilot(db: Session, pilot: User) -> list[dict]:
    rows = (
        db.query(
            RacingSession,
            func.count(TelemetrySession.id).label("lap_count"),
            func.min(TelemetrySession.lap_time).label("best_lap"),
        )
        .outerjoin(TelemetrySession, TelemetrySession.racing_session_id == RacingSession.id)
        .filter(RacingSession.user_id == pilot.id)
        .group_by(RacingSession.id)
        .order_by(RacingSession.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(rs.id),
            "pilot_email": pilot.email,
            "pilot_name": pilot.name or pilot.email,
            "name": rs.name,
            "track": rs.track,
            "car": rs.car,
            "session_date": rs.session_date,
            "lap_count": lap_count or 0,
            "best_lap_fmt": _fmt(best_lap) if best_lap else "—",
            "has_report": bool(rs.report_cache),
        }
        for rs, lap_count, best_lap in rows
    ]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
def create_team(
    body: TeamCreate,
    current_user: User = Depends(get_technician_user),
    db: Session = Depends(get_db),
):
    existing = db.query(Team).filter(Team.owner_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ya tienes un equipo. Solo puedes tener uno.")
    team = Team(name=body.name, owner_id=current_user.id)
    db.add(team)
    db.commit()
    db.refresh(team)
    return {"id": str(team.id), "name": team.name, "owner_id": str(team.owner_id), "pilots": []}


@router.get("/my")
def get_my_team(
    current_user: User = Depends(get_technician_user),
    db: Session = Depends(get_db),
) -> Any:
    team = _get_my_team(db, current_user.id)
    members = (
        db.query(TeamMember, User)
        .join(User, User.id == TeamMember.user_id)
        .filter(TeamMember.team_id == team.id)
        .all()
    )
    pilots = []
    for _, pilot in members:
        rs_count = db.query(RacingSession).filter(RacingSession.user_id == pilot.id).count()
        pilots.append({
            "id": str(pilot.id),
            "email": pilot.email,
            "name": pilot.name or "",
            "plan": pilot.plan.value,
            "racing_sessions": rs_count,
        })
    return {"id": str(team.id), "name": team.name, "owner_id": str(team.owner_id), "pilots": pilots}


@router.post("/my/members", status_code=201)
def add_pilot(
    body: AddPilotRequest,
    current_user: User = Depends(get_technician_user),
    db: Session = Depends(get_db),
):
    team = _get_my_team(db, current_user.id)

    pilot = db.query(User).filter(User.email == body.email).first()
    if not pilot:
        raise HTTPException(status_code=404, detail="No existe ningún usuario con ese email")
    if str(pilot.id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="No puedes agregarte a ti mismo")

    already = db.query(TeamMember).filter(
        TeamMember.team_id == team.id,
        TeamMember.user_id == pilot.id,
    ).first()
    if already:
        raise HTTPException(status_code=409, detail="El piloto ya está en el equipo")

    member = TeamMember(team_id=team.id, user_id=pilot.id)
    db.add(member)
    db.commit()
    rs_count = db.query(RacingSession).filter(RacingSession.user_id == pilot.id).count()
    return {
        "id": str(pilot.id),
        "email": pilot.email,
        "name": pilot.name or "",
        "plan": pilot.plan.value,
        "racing_sessions": rs_count,
    }


@router.delete("/my/members/{pilot_id}", status_code=204)
def remove_pilot(
    pilot_id: str,
    current_user: User = Depends(get_technician_user),
    db: Session = Depends(get_db),
):
    team = _get_my_team(db, current_user.id)
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team.id,
        TeamMember.user_id == pilot_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="El piloto no pertenece a este equipo")
    db.delete(member)
    db.commit()


@router.get("/my/sessions")
def get_team_sessions(
    current_user: User = Depends(get_technician_user),
    db: Session = Depends(get_db),
) -> Any:
    team = _get_my_team(db, current_user.id)
    members = (
        db.query(TeamMember, User)
        .join(User, User.id == TeamMember.user_id)
        .filter(TeamMember.team_id == team.id)
        .all()
    )
    result = []
    for _, pilot in members:
        result.extend(_sessions_for_pilot(db, pilot))
    result.sort(key=lambda x: x["session_date"] or "", reverse=True)
    return result


@router.get("/my/pilots/{pilot_id}/sessions")
def get_pilot_sessions(
    pilot_id: str,
    current_user: User = Depends(get_technician_user),
    db: Session = Depends(get_db),
) -> Any:
    team = _get_my_team(db, current_user.id)
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team.id,
        TeamMember.user_id == pilot_id,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="El piloto no pertenece a tu equipo")

    pilot = db.query(User).filter(User.id == pilot_id).first()
    return _sessions_for_pilot(db, pilot)


@router.get("/my/pilots/{pilot_id}/sessions/{session_id}/report")
def get_pilot_session_report(
    pilot_id: str,
    session_id: str,
    current_user: User = Depends(get_technician_user),
    db: Session = Depends(get_db),
) -> Any:
    team = _get_my_team(db, current_user.id)
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team.id,
        TeamMember.user_id == pilot_id,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="El piloto no pertenece a tu equipo")

    session = db.query(RacingSession).filter(
        RacingSession.id == session_id,
        RacingSession.user_id == pilot_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if not session.report_cache:
        raise HTTPException(status_code=404, detail="Esta sesión aún no tiene reporte generado")

    return session.report_cache
