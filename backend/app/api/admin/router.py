"""
Back office — solo accesible a usuarios con is_admin=True.

GET  /api/v1/admin/stats              Estadísticas globales de la plataforma
GET  /api/v1/admin/users              Lista todos los usuarios con sus stats
POST /api/v1/admin/users              Crea un usuario nuevo
PATCH /api/v1/admin/users/{id}        Edita usuario (plan, is_active, is_admin, name)
GET  /api/v1/admin/users/{id}/sessions  Sesiones de un piloto específico
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_admin_user, get_db
from app.core.security import hash_password
from app.models.analysis import Analysis
from app.models.racing_session import RacingSession
from app.models.session import TelemetrySession
from app.models.user import Plan, User, UserRole
from app.utils.formatters import fmt_lap_time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class UserAdminOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    plan: str
    role: str
    is_active: bool
    is_admin: bool
    analyses_used: int
    analyses_limit: int
    racing_sessions: int
    laps_total: int
    tokens_used: int
    created_at: str


class StatsOut(BaseModel):
    total_users: int
    active_users: int
    total_racing_sessions: int
    total_laps: int
    total_tokens: int
    users_by_plan: dict[str, int]


class CreateUserIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(default="", max_length=100)
    plan: str = Field(default="free")
    is_admin: bool = False
    role: str = "pilot"


class UpdateUserIn(BaseModel):
    name: str | None = Field(None, max_length=100)
    plan: str | None = None
    role: str | None = None
    is_active: bool | None = None
    is_admin: bool | None = None
    password: str | None = Field(None, min_length=8)


class SessionAdminOut(BaseModel):
    id: uuid.UUID
    name: str | None
    track: str | None
    car: str | None
    simulator: str | None
    session_type: str | None
    session_date: str | None
    lap_count: int
    best_lap_fmt: str
    created_at: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsOut)
def get_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """Estadísticas globales de la plataforma."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
    total_rs = db.query(func.count(RacingSession.id)).scalar() or 0
    total_laps = db.query(func.count(TelemetrySession.id)).scalar() or 0
    total_tokens = db.query(
        func.coalesce(func.sum(Analysis.tokens_input + Analysis.tokens_output), 0)
    ).scalar() or 0

    plans = db.query(User.plan, func.count(User.id)).group_by(User.plan).all()
    users_by_plan = {p.value: c for p, c in plans}

    return StatsOut(
        total_users=total_users,
        active_users=active_users,
        total_racing_sessions=total_rs,
        total_laps=total_laps,
        total_tokens=int(total_tokens),
        users_by_plan=users_by_plan,
    )


@router.get("/users", response_model=list[UserAdminOut])
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """Lista todos los usuarios con sus estadísticas de uso."""
    users = db.query(User).order_by(User.created_at.desc()).all()

    # Cargar stats en batch para evitar N+1
    rs_counts = dict(
        db.query(RacingSession.user_id, func.count(RacingSession.id))
        .group_by(RacingSession.user_id)
        .all()
    )
    lap_counts = dict(
        db.query(TelemetrySession.user_id, func.count(TelemetrySession.id))
        .group_by(TelemetrySession.user_id)
        .all()
    )
    token_sums = dict(
        db.query(
            Analysis.user_id,
            func.coalesce(func.sum(Analysis.tokens_input + Analysis.tokens_output), 0),
        )
        .group_by(Analysis.user_id)
        .all()
    )

    return [
        UserAdminOut(
            id=u.id,
            email=u.email,
            name=u.name,
            plan=u.plan.value,
            role=u.role.value,
            is_active=u.is_active,
            is_admin=u.is_admin,
            analyses_used=u.analyses_used,
            analyses_limit=u.analyses_limit,
            racing_sessions=rs_counts.get(u.id, 0),
            laps_total=lap_counts.get(u.id, 0),
            tokens_used=int(token_sums.get(u.id, 0)),
            created_at=u.created_at.isoformat(),
        )
        for u in users
    ]


@router.post("/users", response_model=UserAdminOut, status_code=201)
def create_user(
    body: CreateUserIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """Crea un usuario nuevo desde el back office."""
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="El email ya está registrado")

    try:
        plan = Plan(body.plan)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Plan inválido: {body.plan}. Válidos: free, pro, team")

    try:
        role = UserRole(body.role)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Role inválido: {body.role}. Válidos: pilot, technician")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        name=body.name,
        plan=plan,
        role=role,
        is_admin=body.is_admin,
        analyses_reset_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("Admin creó usuario %s (%s, %s)", user.email, user.plan, user.role)
    return UserAdminOut(
        id=user.id,
        email=user.email,
        name=user.name,
        plan=user.plan.value,
        role=user.role.value,
        is_active=user.is_active,
        is_admin=user.is_admin,
        analyses_used=0,
        analyses_limit=user.analyses_limit,
        racing_sessions=0,
        laps_total=0,
        tokens_used=0,
        created_at=user.created_at.isoformat(),
    )


@router.patch("/users/{user_id}", response_model=UserAdminOut)
def update_user(
    user_id: uuid.UUID,
    body: UpdateUserIn,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Edita datos de un usuario: plan, estado, nombre, contraseña."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Evitar que el admin se quite sus propios permisos
    if body.is_admin is False and str(user.id) == str(admin.id):
        raise HTTPException(status_code=400, detail="No puedes quitarte tus propios permisos de admin")

    if body.name is not None:
        user.name = body.name
    if body.plan is not None:
        try:
            user.plan = Plan(body.plan)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Plan inválido: {body.plan}")
    if body.role is not None:
        try:
            user.role = UserRole(body.role)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Role inválido: {body.role}. Válidos: pilot, technician")
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_admin is not None:
        user.is_admin = body.is_admin
    if body.password is not None:
        user.hashed_password = hash_password(body.password)

    db.commit()
    db.refresh(user)

    rs_count = db.query(func.count(RacingSession.id)).filter_by(user_id=user.id).scalar() or 0
    lap_count = db.query(func.count(TelemetrySession.id)).filter_by(user_id=user.id).scalar() or 0
    tokens = db.query(
        func.coalesce(func.sum(Analysis.tokens_input + Analysis.tokens_output), 0)
    ).filter(Analysis.user_id == user.id).scalar() or 0

    return UserAdminOut(
        id=user.id,
        email=user.email,
        name=user.name,
        plan=user.plan.value,
        role=user.role.value,
        is_active=user.is_active,
        is_admin=user.is_admin,
        analyses_used=user.analyses_used,
        analyses_limit=user.analyses_limit,
        racing_sessions=rs_count,
        laps_total=lap_count,
        tokens_used=int(tokens),
        created_at=user.created_at.isoformat(),
    )


@router.get("/users/{user_id}/sessions", response_model=list[SessionAdminOut])
def get_user_sessions(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """Lista todas las sesiones de un piloto."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    rows = (
        db.query(
            RacingSession,
            func.count(TelemetrySession.id).label("lap_count"),
            func.min(TelemetrySession.lap_time).label("best_lap"),
        )
        .outerjoin(TelemetrySession, TelemetrySession.racing_session_id == RacingSession.id)
        .filter(RacingSession.user_id == user_id)
        .group_by(RacingSession.id)
        .order_by(RacingSession.created_at.desc())
        .all()
    )

    return [
        SessionAdminOut(
            id=rs.id,
            name=rs.name,
            track=rs.track,
            car=rs.car,
            simulator=rs.simulator.value if rs.simulator else None,
            session_type=rs.session_type.value if rs.session_type else None,
            session_date=rs.session_date,
            lap_count=lap_count or 0,
            best_lap_fmt=fmt_lap_time(best_lap) if best_lap else "—",
            created_at=rs.created_at.isoformat(),
        )
        for rs, lap_count, best_lap in rows
    ]
