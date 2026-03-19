"""
Pre-análisis de telemetría — cálculos sin IA.

Genera un dict estructurado que se guarda en Analysis.pre_analysis y que
Claude usará como contexto para su análisis.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.parsers.csv_parser import ParsedLap


def _series(df: pd.DataFrame, col: str) -> pd.Series | None:
    if col not in df.columns:
        return None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return s if not s.empty else None


def _safe(val, fmt: str = ".1f") -> str | None:
    try:
        v = float(val)
        if np.isnan(v):
            return None
        return format(v, fmt)
    except Exception:
        return None


def compute(lap: ParsedLap) -> dict:
    """
    Calcula métricas clave a partir del DataFrame de telemetría.
    Retorna un dict JSON-serializable listo para guardar en BD.
    """
    m = lap.meta
    df = lap.telemetry

    result: dict = {
        "track":      m.track,
        "car":        m.car,
        "simulator":  m.simulator,
        "lap_time":   m.lap_time,
        "lap_time_fmt": m.lap_time_fmt,
        "s1": m.s1, "s2": m.s2, "s3": m.s3,
        "tyre_compound": m.tyre_compound,
        "track_temp":    m.track_temp,
        "ambient_temp":  m.ambient_temp,
        "track_length":  m.track_length,
    }

    # ── Velocidad ─────────────────────────────────────────────────────────────
    spd = _series(df, "speed")
    if spd is not None:
        result["speed"] = {
            "max":  round(float(spd.max()), 1),
            "avg":  round(float(spd.mean()), 1),
            "min":  round(float(spd.min()), 1),
        }

    # ── Throttle / Brake ──────────────────────────────────────────────────────
    thr = _series(df, "throttle")
    brk = _series(df, "brake")
    if thr is not None:
        result["throttle"] = {
            "avg":         round(float(thr.mean()), 1),
            "full_pct":    round(float((thr > 95).mean() * 100), 1),
            "coasting_pct": round(float((thr < 5).mean() * 100), 1),
        }
    if brk is not None:
        result["brake"] = {
            "avg":       round(float(brk.mean()), 1),
            "max":       round(float(brk.max()), 1),
            "hard_pct":  round(float((brk > 80).mean() * 100), 1),
        }

    # ── G-Forces ──────────────────────────────────────────────────────────────
    g_lat  = _series(df, "g_lat")
    g_lon  = _series(df, "g_lon")
    g_vert = _series(df, "g_vert")
    gf: dict = {}
    if g_lat is not None:
        gf["lat_max_left"]  = round(float(g_lat.max()), 2)
        gf["lat_max_right"] = round(float(abs(g_lat.min())), 2)
        gf["lat_avg"]       = round(float(g_lat.abs().mean()), 2)
    if g_lon is not None:
        gf["lon_max_brake"] = round(float(abs(g_lon.min())), 2)
        gf["lon_max_acc"]   = round(float(g_lon.max()), 2)
    if g_vert is not None:
        gf["vert_max"]      = round(float(g_vert.abs().max()), 2)
    if gf:
        result["g_forces"] = gf

    # ── Temperatura de gomas ──────────────────────────────────────────────────
    tyre_temp: dict = {}
    for corner in ("fl", "fr", "rl", "rr"):
        s = _series(df, f"tyre_temp_{corner}")
        if s is not None:
            hot = s[s > 40]
            if not hot.empty:
                tyre_temp[corner.upper()] = {
                    "avg": round(float(hot.mean()), 1),
                    "max": round(float(hot.max()), 1),
                    "min": round(float(hot.min()), 1),
                }
    if tyre_temp:
        result["tyre_temp"] = tyre_temp

    # ── Temperatura de zonas (camber) ─────────────────────────────────────────
    tyre_zones: dict = {}
    for corner in ("fl", "fr", "rl", "rr"):
        inner_s = _series(df, f"tyre_inner_{corner}")
        mid_s   = _series(df, f"tyre_mid_{corner}")
        outer_s = _series(df, f"tyre_outer_{corner}")
        zone: dict = {}
        inner_avg = outer_avg = None
        if inner_s is not None:
            hot = inner_s[inner_s > 40]
            if not hot.empty:
                inner_avg = float(hot.mean())
                zone["inner"] = round(inner_avg, 1)
        if mid_s is not None:
            hot = mid_s[mid_s > 40]
            if not hot.empty:
                zone["mid"] = round(float(hot.mean()), 1)
        if outer_s is not None:
            hot = outer_s[outer_s > 40]
            if not hot.empty:
                outer_avg = float(hot.mean())
                zone["outer"] = round(outer_avg, 1)
        if zone:
            # diagnóstico de camber
            if inner_avg is not None and outer_avg is not None:
                diff = inner_avg - outer_avg
                if diff > 20:
                    zone["camber_diag"] = f"excess_negative ({diff:.0f}°C inner-outer)"
                elif diff < -15:
                    zone["camber_diag"] = f"insufficient ({abs(diff):.0f}°C outer-inner)"
                else:
                    zone["camber_diag"] = "ok"
            tyre_zones[corner.upper()] = zone
    if tyre_zones:
        result["tyre_zones"] = tyre_zones

    # ── Presión de gomas ──────────────────────────────────────────────────────
    tyre_press: dict = {}
    for corner in ("fl", "fr", "rl", "rr"):
        s = _series(df, f"tyre_press_{corner}")
        if s is not None:
            hot = s[s > 1]
            if not hot.empty:
                tyre_press[corner.upper()] = {
                    "avg": round(float(hot.mean()), 1),
                    "max": round(float(hot.max()), 1),
                    "min": round(float(hot.min()), 1),
                }
    if tyre_press:
        result["tyre_press"] = tyre_press

    # ── Temperatura de frenos ─────────────────────────────────────────────────
    brake_temp: dict = {}
    for corner in ("fl", "fr", "rl", "rr"):
        s = _series(df, f"brake_temp_{corner}")
        if s is not None:
            hot = s[s > 50]
            if not hot.empty:
                brake_temp[corner.upper()] = {
                    "avg": round(float(hot.mean()), 0),
                    "max": round(float(hot.max()), 0),
                }
    if brake_temp:
        result["brake_temp"] = brake_temp
        # balance delantero/trasero
        fl = brake_temp.get("FL", {}).get("avg", 0)
        fr = brake_temp.get("FR", {}).get("avg", 0)
        rl = brake_temp.get("RL", {}).get("avg", 0)
        rr = brake_temp.get("RR", {}).get("avg", 0)
        if fl and rl:
            f_avg = (fl + fr) / 2 if fr else fl
            r_avg = (rl + rr) / 2 if rr else rl
            result["brake_balance"] = {
                "front_avg": round(f_avg, 0),
                "rear_avg":  round(r_avg, 0),
                "bias":      "front_heavy" if f_avg > r_avg * 1.35 else
                             "rear_heavy"  if r_avg > f_avg * 1.30 else "balanced",
            }

    # ── Slip ──────────────────────────────────────────────────────────────────
    slip: dict = {}
    for corner in ("fl", "fr", "rl", "rr"):
        s = _series(df, f"slip_{corner}")
        if s is not None:
            abs_slip = s.abs()
            slip[corner.upper()] = {
                "avg": round(float(abs_slip.mean()), 2),
                "max": round(float(abs_slip.max()), 2),
            }
    if slip:
        result["slip"] = slip
        # detección de sobre/subviraje
        rear_slip  = max(slip.get("RL", {}).get("max", 0), slip.get("RR", {}).get("max", 0))
        front_slip = max(slip.get("FL", {}).get("max", 0), slip.get("FR", {}).get("max", 0))
        if rear_slip > front_slip * 1.5 and rear_slip > 5:
            result["handling"] = "oversteer"
        elif front_slip > rear_slip * 1.5 and front_slip > 5:
            result["handling"] = "understeer"
        else:
            result["handling"] = "neutral"

    # ── Suspensión ────────────────────────────────────────────────────────────
    susp: dict = {}
    for corner in ("fl", "fr", "rl", "rr"):
        s = _series(df, f"susp_pos_{corner}")
        if s is not None and len(s) > 10:
            susp[corner.upper()] = {
                "avg":   round(float(s.mean()) * 1000, 1),
                "range": round((float(s.max()) - float(s.min())) * 1000, 1),
                "min":   round(float(s.min()) * 1000, 1),
                "max":   round(float(s.max()) * 1000, 1),
            }
    if susp:
        result["suspension"] = susp

    # ── Motor y combustible ────────────────────────────────────────────────────
    rpm_s = _series(df, "rpm")
    if rpm_s is not None:
        result["engine"] = {
            "rpm_max": round(float(rpm_s.max()), 0),
            "rpm_avg": round(float(rpm_s.mean()), 0),
        }
    fuel_s = _series(df, "fuel")
    if fuel_s is not None and len(fuel_s) > 10:
        result["fuel"] = {
            "start": round(float(fuel_s.iloc[0]), 2),
            "end":   round(float(fuel_s.iloc[-1]), 2),
            "used":  round(float(fuel_s.iloc[0] - fuel_s.iloc[-1]), 2),
        }

    # ── Sector más débil ──────────────────────────────────────────────────────
    if m.s1 and m.s2 and m.s3 and m.s1 > 0 and m.s2 > 0 and m.s3 > 0:
        sectors = {"S1": m.s1, "S2": m.s2, "S3": m.s3}
        # sector débil = el que representa más % del total respecto a pista larga
        # (simple: el más lento en términos absolutos)
        result["weak_sector"] = max(sectors, key=lambda k: sectors[k])

    # ── Zonas de frenada detectadas (top 5) ────────────────────────────────────
    brk_s = _series(df, "brake")
    spd_s = _series(df, "speed")
    dist_col = "lap_distance" if "lap_distance" in df.columns else None

    if brk_s is not None and dist_col:
        dist_arr  = df[dist_col].values
        brake_arr = brk_s.reindex(df.index).fillna(0).values
        spd_arr   = spd_s.reindex(df.index).fillna(0).values if spd_s is not None else None
        braking_zones = []
        in_brake = False
        for i in range(5, len(brake_arr) - 5):
            if brake_arr[i] > 85 and not in_brake:
                in_brake = True
                d    = float(dist_arr[i]) if i < len(dist_arr) else i
                spd  = float(spd_arr[i])  if spd_arr is not None and i < len(spd_arr) else 0
                braking_zones.append({
                    "dist_m":    round(d, 0),
                    "speed_kmh": round(spd, 1),
                    "intensity": round(float(brake_arr[i]), 1),
                })
                if len(braking_zones) >= 5:
                    break
            elif brake_arr[i] < 10:
                in_brake = False
        if braking_zones:
            result["braking_zones"] = braking_zones

    return result
