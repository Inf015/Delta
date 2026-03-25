"""
Knowledge Base service — actualiza KnowledgeProfile sin consumir tokens AI.

El perfil acumula estadísticas de todas las sesiones del piloto
en la misma combinación pista+auto+simulador.
"""

from __future__ import annotations

import uuid

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeProfile, Recommendation
from app.models.session import TelemetrySession


def get_or_create_profile(
    db: Session,
    user_id: uuid.UUID,
    session: TelemetrySession,
) -> KnowledgeProfile:
    """Retorna el perfil existente o crea uno nuevo."""
    profile = (
        db.query(KnowledgeProfile)
        .filter_by(
            user_id=user_id,
            track=session.track,
            car=session.car,
            simulator=session.simulator.value,
        )
        .first()
    )
    if profile is None:
        profile = KnowledgeProfile(
            user_id=user_id,
            track=session.track,
            car=session.car,
            simulator=session.simulator.value,
            sessions_count=0,
            best_lap=0.0,
            avg_lap=0.0,
            trend=0.0,
        )
        db.add(profile)
        db.flush()
    return profile


def update_profile(
    db: Session,
    profile: KnowledgeProfile,
    session: TelemetrySession,
    pre_analysis: dict,
) -> KnowledgeProfile:
    """
    Actualiza el perfil con los datos de la nueva sesión.
    Recalcula best_lap, avg_lap, weak_sector, trend y corner_profiles.
    Sin tokens — solo matemáticas.
    """
    lap_time = session.lap_time

    # ── Contador y tiempos ────────────────────────────────────────────────────
    prev_count = profile.sessions_count
    profile.sessions_count = prev_count + 1

    # best_lap: mínimo histórico
    if profile.best_lap <= 0 or lap_time < profile.best_lap:
        profile.best_lap = lap_time

    # avg_lap: media móvil incremental
    if prev_count == 0:
        profile.avg_lap = lap_time
    else:
        profile.avg_lap = (profile.avg_lap * prev_count + lap_time) / profile.sessions_count

    # ── Sector débil ──────────────────────────────────────────────────────────
    weak = pre_analysis.get("weak_sector")
    if weak:
        profile.weak_sector = weak

    # ── Tendencia (segundos ganados cada 5 sesiones) ──────────────────────────
    # Solo calculable con ≥2 sesiones; usando simple δ respecto al avg anterior
    if prev_count >= 1 and profile.avg_lap > 0:
        # tendencia positiva = mejorando (avg bajando)
        prev_avg = (profile.avg_lap * profile.sessions_count - lap_time) / prev_count
        profile.trend = round(prev_avg - lap_time, 3)

    # ── Corner profiles acumulados ────────────────────────────────────────────
    # Guarda g-forces, velocidad máx y temp de frenos del pre-análisis
    new_corners: dict = {}
    if pre_analysis.get("g_forces"):
        new_corners["g_forces"] = pre_analysis["g_forces"]
    if pre_analysis.get("speed"):
        new_corners["speed"] = pre_analysis["speed"]
    if pre_analysis.get("brake_temp"):
        new_corners["brake_temp"] = pre_analysis["brake_temp"]
    if pre_analysis.get("handling"):
        new_corners["handling"] = pre_analysis["handling"]

    if new_corners:
        existing = profile.corner_profiles or {}
        # Guardar historial por sesión (máx últimas 10)
        history: list = existing.get("history", [])
        history.append(new_corners)
        if len(history) > 10:
            history = history[-10:]
        existing["history"] = history
        existing["latest"] = new_corners
        profile.corner_profiles = existing

    # ── Setup más común ───────────────────────────────────────────────────────
    if pre_analysis.get("tyre_press"):
        profile.common_setup = {"tyre_press": pre_analysis["tyre_press"]}

    db.flush()
    return profile


def update_after_ai(
    db: Session,
    profile: KnowledgeProfile,
    ai_result: dict,
    current_lap_time: float,
) -> None:
    """
    Llamar DESPUÉS de Claude. Hace dos cosas:
    1. Marca las recomendaciones anteriores como testeadas y calcula su delta.
    2. Actualiza recurring_issues con los problemas que Claude detectó ahora.
    """
    # ── 1. Cerrar ciclo de recomendaciones anteriores ─────────────────────────
    prev_recs = (
        db.query(Recommendation)
        .filter_by(profile_id=profile.id, tested=False)
        .order_by(desc(Recommendation.created_at))
        .limit(5)
        .all()
    )
    if prev_recs and profile.avg_lap > 0:
        # delta positivo = mejoraste (lap_time bajó respecto al avg del perfil)
        delta = round(profile.avg_lap - current_lap_time, 3)
        for rec in prev_recs:
            rec.tested = True
            rec.delta_improvement = delta
        db.flush()

    # ── 2. Rastrear problemas recurrentes ─────────────────────────────────────
    issues = ai_result.get("issues", [])
    if not issues:
        return

    recurring: dict = dict(profile.recurring_issues or {})
    for issue in issues:
        area = (issue.get("area") or "").strip().lower()
        if not area:
            continue
        entry = recurring.get(area, {"count": 0, "confirmed": False, "last_lap_time": 0.0})
        entry["count"] += 1
        entry["last_lap_time"] = current_lap_time
        if entry["count"] >= 3:
            entry["confirmed"] = True
        recurring[area] = entry

    profile.recurring_issues = recurring
    db.flush()
