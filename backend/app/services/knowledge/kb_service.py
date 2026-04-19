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

    # ── Sector débil (por frecuencia acumulada) ──────────────────────────────
    # Contamos cuántas sesiones fue débil cada sector.
    # weak_sector = el más frecuente históricamente, no el último.
    existing_cp = dict(profile.corner_profiles or {})
    sector_counts: dict[str, int] = existing_cp.get("sector_counts", {"S1": 0, "S2": 0, "S3": 0})
    weak = pre_analysis.get("weak_sector")
    if weak and weak in ("S1", "S2", "S3"):
        sector_counts[weak] = sector_counts.get(weak, 0) + 1
    existing_cp["sector_counts"] = sector_counts
    # El sector débil es el más frecuente (al menos 1 aparición)
    if any(sector_counts.values()):
        profile.weak_sector = max(sector_counts, key=lambda k: sector_counts[k])

    # ── Historial de tiempos (para regresión lineal) ──────────────────────────
    lap_times_history: list[float] = existing_cp.get("lap_times", [])
    lap_times_history.append(lap_time)
    if len(lap_times_history) > 20:
        lap_times_history = lap_times_history[-20:]
    existing_cp["lap_times"] = lap_times_history

    # ── Tendencia: regresión lineal sobre últimas N sesiones ──────────────────
    # slope negativo = tiempos bajando = piloto mejorando → trend positivo
    n = len(lap_times_history)
    if n >= 3:
        x_mean = (n - 1) / 2.0
        y_mean = sum(lap_times_history) / n
        num = sum((i - x_mean) * (lap_times_history[i] - y_mean) for i in range(n))
        den = sum((i - x_mean) ** 2 for i in range(n))
        slope = num / den if den != 0 else 0.0
        # positivo = mejorando (slope negativo → trend positivo)
        profile.trend = round(-slope, 3)
    elif prev_count >= 1 and profile.avg_lap > 0:
        # fallback hasta tener 3 sesiones: delta simple
        prev_avg = (profile.avg_lap * profile.sessions_count - lap_time) / prev_count
        profile.trend = round(prev_avg - lap_time, 3)

    # ── Corner profiles acumulados ────────────────────────────────────────────
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
        history: list = existing_cp.get("history", [])
        history.append(new_corners)
        if len(history) > 10:
            history = history[-10:]
        existing_cp["history"] = history
        existing_cp["latest"] = new_corners

    profile.corner_profiles = existing_cp

    # ── Setup más común ───────────────────────────────────────────────────────
    if pre_analysis.get("tyre_press"):
        profile.common_setup = {"tyre_press": pre_analysis["tyre_press"]}

    # ── Estilo de conducción (sin tokens) ─────────────────────────────────────
    ds = dict(profile.driving_style or {})

    # Manejo dominante
    handling = pre_analysis.get("handling")
    if handling:
        hc = ds.get("handling_counts", {"understeer": 0, "oversteer": 0, "neutral": 0})
        hc[handling] = hc.get(handling, 0) + 1
        ds["handling_counts"] = hc

    # Historial understeer score — en pre_analysis está en steering.understeer_score
    us = (pre_analysis.get("steering") or {}).get("understeer_score")
    if us is not None:
        uh = ds.get("understeer_history", [])
        uh.append(round(float(us), 2))
        ds["understeer_history"] = uh[-15:]

    # Historial throttle promedio — en pre_analysis está en throttle.avg
    thr = (pre_analysis.get("throttle") or {}).get("avg")
    if thr is not None:
        th = ds.get("throttle_history", [])
        th.append(round(float(thr), 1))
        ds["throttle_history"] = th[-15:]

    # Historial G frenada máxima — en pre_analysis está en g_forces.lon_max_brake
    bg = (pre_analysis.get("g_forces") or {}).get("lon_max_brake")
    if bg is not None:
        bh = ds.get("brake_g_history", [])
        bh.append(round(abs(float(bg)), 3))
        ds["brake_g_history"] = bh[-15:]

    # Historial slip trasero promedio — slip.RL.avg y slip.RR.avg
    slip = pre_analysis.get("slip")
    if isinstance(slip, dict):
        rl_avg = (slip.get("RL") or {}).get("avg") or 0
        rr_avg = (slip.get("RR") or {}).get("avg") or 0
        rear_slip = (rl_avg + rr_avg) / 2
        if rear_slip > 0:
            sh = ds.get("slip_rear_history", [])
            sh.append(round(rear_slip, 3))
            ds["slip_rear_history"] = sh[-15:]

    profile.driving_style = ds

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

    areas_this_session: set[str] = set()
    recurring: dict = dict(profile.recurring_issues or {})
    for issue in issues:
        area = (issue.get("area") or "").strip().lower()
        if not area:
            continue
        areas_this_session.add(area)
        entry = recurring.get(area, {"count": 0, "confirmed": False, "sessions_since_seen": 0, "last_lap_time": 0.0})
        entry["count"] += 1
        entry["sessions_since_seen"] = 0
        entry["last_lap_time"] = current_lap_time
        if entry["count"] >= 3:
            entry["confirmed"] = True
        recurring[area] = entry

    # Decaer issues no vistos esta sesión — si llevan 5 sesiones sin aparecer, dejar de confirmarlos
    for area, entry in recurring.items():
        if area not in areas_this_session:
            entry["sessions_since_seen"] = entry.get("sessions_since_seen", 0) + 1
            if entry.get("confirmed") and entry["sessions_since_seen"] >= 5:
                entry["confirmed"] = False

    profile.recurring_issues = recurring
    db.flush()
