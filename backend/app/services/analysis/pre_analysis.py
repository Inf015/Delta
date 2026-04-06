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
            hot = s[s > 10]  # >10°C para excluir placeholders (0-4°C) sin filtrar días fríos
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
            hot = inner_s[inner_s > 10]
            if not hot.empty:
                inner_avg = float(hot.mean())
                zone["inner"] = round(inner_avg, 1)
        if mid_s is not None:
            hot = mid_s[mid_s > 10]
            if not hot.empty:
                zone["mid"] = round(float(hot.mean()), 1)
        if outer_s is not None:
            hot = outer_s[outer_s > 10]
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
            hot = s[s > 0]
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
            hot = s[s > 20]  # 20°C mínimo para excluir valores placeholder (4°C fijo del MX5)
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
        if fl > 0 and rl > 0:
            f_avg = (fl + fr) / 2 if fr > 0 else fl
            r_avg = (rl + rr) / 2 if rr > 0 else rl
            result["brake_balance"] = {
                "front_avg": round(f_avg, 0),
                "rear_avg":  round(r_avg, 0),
                "bias":      "front_heavy" if f_avg > r_avg * 1.30 else
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
        import pandas as _pd
        f_start = fuel_s.iloc[0]
        f_end   = fuel_s.iloc[-1]
        if _pd.notna(f_start) and _pd.notna(f_end) and f_start >= f_end:
            result["fuel"] = {
                "start": round(float(f_start), 2),
                "end":   round(float(f_end), 2),
                "used":  round(float(f_start - f_end), 2),
            }

    # ── Dirección (análisis de subviraje por correlación steer vs G lat) ───────
    steer_s = _series(df, "steer")
    if steer_s is not None and g_lat is not None:
        steer_vals = steer_s.reindex(df.index).fillna(0)
        g_vals = g_lat.reindex(df.index).fillna(0)
        # Subviraje: mucho steer con poca G lateral (piloto gira más de lo que el coche responde)
        # Usamos solo zonas con steer > 20% y speed > 60 km/h
        mask = (steer_vals.abs() > 20)
        if "speed" in df.columns:
            speed_s2 = pd.to_numeric(df["speed"], errors="coerce").fillna(0)
            mask = mask & (speed_s2 > 60)
        if mask.sum() > 20:
            steer_filtered = steer_vals[mask]
            g_filtered = g_vals[mask]
            # Ratio g/steer: bajo ratio = subviraje
            ratio = g_filtered.abs() / (steer_filtered.abs() + 0.001)
            understeer_score = round(float(1.0 / (ratio.mean() + 0.01)), 2)  # alto = más subviraje
            result["steering"] = {
                "avg_abs": round(float(steer_vals.abs().mean()), 1),
                "max_abs": round(float(steer_vals.abs().max()), 1),
                "understeer_score": understeer_score,
                "understeer_level": "high" if understeer_score > 0.3 else "medium" if understeer_score > 0.15 else "low",
            }

    # ── Desgaste de gomas ─────────────────────────────────────────────────────
    tyre_wear: dict = {}
    for corner in ("fl", "fr", "rl", "rr"):
        s = _series(df, f"tyre_wear_{corner}")
        if s is not None and len(s) > 10:
            valid = s[(s >= 0) & (s <= 100)]
            if not valid.empty:
                tyre_wear[corner.upper()] = {
                    "avg": round(float(valid.mean()), 2),
                    "max": round(float(valid.max()), 2),
                    "end": round(float(valid.iloc[-1]), 2),
                }
    if tyre_wear:
        result["tyre_wear"] = tyre_wear
        # Diagnóstico de desgaste diferencial
        ends = {c: d["end"] for c, d in tyre_wear.items() if "end" in d}
        if len(ends) == 4:
            front_avg = (ends.get("FL", 0) + ends.get("FR", 0)) / 2
            rear_avg  = (ends.get("RL", 0) + ends.get("RR", 0)) / 2
            left_avg  = (ends.get("FL", 0) + ends.get("RL", 0)) / 2
            right_avg = (ends.get("FR", 0) + ends.get("RR", 0)) / 2
            diag: list[str] = []
            if abs(front_avg - rear_avg) > 0.5:
                diag.append("rear_heavy" if rear_avg > front_avg else "front_heavy")
            if abs(left_avg - right_avg) > 0.5:
                diag.append("left_heavy" if left_avg > right_avg else "right_heavy")
            if diag:
                result["tyre_wear"]["diagnosis"] = diag

    # ── Ride Height (altura de carrocería) ────────────────────────────────────
    ride_h: dict = {}
    for side, col in (("front", "ride_height_f"), ("rear", "ride_height_r")):
        s = _series(df, col)
        if s is not None and len(s) > 10:
            # Convertir m → mm
            mm = s * 1000
            valid = mm[mm > 0]
            if not valid.empty:
                ride_h[side] = {
                    "avg_mm": round(float(valid.mean()), 1),
                    "min_mm": round(float(valid.min()), 1),
                    "max_mm": round(float(valid.max()), 1),
                    "range_mm": round(float(valid.max() - valid.min()), 1),
                }
    if len(ride_h) == 2:
        result["ride_height"] = ride_h
        # Rake = rear - front (positivo = nose down = más agarre delantero)
        rake = ride_h["rear"]["avg_mm"] - ride_h["front"]["avg_mm"]
        result["ride_height"]["rake_mm"] = round(rake, 1)
        result["ride_height"]["rake_diagnosis"] = (
            "aggressive_front_aero" if rake < -5 else
            "neutral" if abs(rake) <= 5 else
            "rear_stability"
        )

    # ── Cargas en rueda (aero/mecánica) ───────────────────────────────────────
    loads: dict = {}
    for corner in ("fl", "fr", "rl", "rr"):
        s = _series(df, f"load_{corner}")
        if s is not None and len(s) > 10:
            valid = s[s > 0]
            if not valid.empty:
                loads[corner.upper()] = {
                    "avg_N": round(float(valid.mean()), 0),
                    "max_N": round(float(valid.max()), 0),
                    "min_N": round(float(valid.min()), 0),
                }
    if loads:
        result["tyre_loads"] = loads
        if len(loads) == 4:
            front_load = (loads.get("FL", {}).get("avg_N", 0) + loads.get("FR", {}).get("avg_N", 0)) / 2
            rear_load  = (loads.get("RL", {}).get("avg_N", 0) + loads.get("RR", {}).get("avg_N", 0)) / 2
            if front_load > 0 and rear_load > 0:
                total = front_load + rear_load
                result["tyre_loads"]["front_pct"] = round(front_load / total * 100, 1)
                result["tyre_loads"]["rear_pct"]  = round(rear_load  / total * 100, 1)
                result["tyre_loads"]["balance_diag"] = (
                    "front_heavy" if result["tyre_loads"]["front_pct"] > 55 else
                    "rear_heavy"  if result["tyre_loads"]["rear_pct"]  > 55 else
                    "balanced"
                )

    # ── Velocidad de suspensión (análisis de amortiguadores) ─────────────────
    susp_vel: dict = {}
    for corner in ("fl", "fr", "rl", "rr"):
        s = _series(df, f"susp_vel_{corner}")
        if s is not None and len(s) > 10:
            abs_vel = s.abs()
            susp_vel[corner.upper()] = {
                "avg_ms":  round(float(abs_vel.mean()), 3),
                "max_ms":  round(float(abs_vel.max()), 3),
                "p95_ms":  round(float(abs_vel.quantile(0.95)), 3),
            }
    if susp_vel:
        result["susp_velocity"] = susp_vel
        # Diagnóstico de amortiguación
        all_p95 = [v["p95_ms"] for v in susp_vel.values()]
        avg_p95 = sum(all_p95) / len(all_p95)
        result["susp_velocity"]["damper_diagnosis"] = (
            "overdamped"   if avg_p95 < 0.05 else
            "well_damped"  if avg_p95 < 0.15 else
            "underdamped"  if avg_p95 < 0.30 else
            "very_soft"
        )

    # ── Temperatura de carcasa de goma ────────────────────────────────────────
    tyre_carcass: dict = {}
    for corner in ("fl", "fr", "rl", "rr"):
        s = _series(df, f"tyre_carcass_{corner}")
        if s is not None:
            hot = s[s > 10]
            if not hot.empty:
                tyre_carcass[corner.upper()] = {
                    "avg": round(float(hot.mean()), 1),
                    "max": round(float(hot.max()), 1),
                }
    if tyre_carcass:
        result["tyre_carcass"] = tyre_carcass
        # Comparar carcasa vs superficie para detectar overheating interno
        overheated = []
        for c in ("FL", "FR", "RL", "RR"):
            surf = result.get("tyre_temp", {}).get(c, {}).get("avg", 0)
            carc = tyre_carcass.get(c, {}).get("avg", 0)
            if surf > 0 and carc > 0 and carc > surf * 0.95:
                overheated.append(c)
        if overheated:
            result["tyre_carcass"]["overheating_risk"] = overheated

    # ── Yaw rate (rotación del vehículo — detecta inestabilidad) ─────────────
    yaw_s = _series(df, "ang_vel_z")  # Z = yaw en coordenadas del vehículo
    if yaw_s is not None and len(yaw_s) > 10:
        yaw_abs = yaw_s.abs()
        result["yaw_rate"] = {
            "avg_rads":  round(float(yaw_abs.mean()), 3),
            "max_rads":  round(float(yaw_abs.max()), 3),
            "p95_rads":  round(float(yaw_abs.quantile(0.95)), 3),
        }

    # ── Diferencial de velocidad de ruedas (LSD / tracción) ──────────────────
    ws_rl = _series(df, "wheel_speed_rl")
    ws_rr = _series(df, "wheel_speed_rr")
    ws_fl = _series(df, "wheel_speed_fl")
    ws_fr = _series(df, "wheel_speed_fr")
    if ws_rl is not None and ws_rr is not None:
        # Alinear índices
        common = ws_rl.index.intersection(ws_rr.index)
        if len(common) > 20:
            rear_diff = (ws_rl.loc[common] - ws_rr.loc[common]).abs()
            # Solo en zonas de aceleración (throttle > 50%)
            lsd_diag = {}
            if thr is not None:
                thr_aligned = thr.reindex(common).fillna(0)
                accel_mask = thr_aligned > 50
                if accel_mask.sum() > 10:
                    accel_diff = rear_diff[accel_mask]
                    lsd_diag["accel_diff_avg"] = round(float(accel_diff.mean()), 2)
                    lsd_diag["accel_diff_max"] = round(float(accel_diff.max()), 2)
                    lsd_diag["lsd_diagnosis"] = (
                        "open_diff"      if lsd_diag["accel_diff_avg"] > 15 else
                        "light_locking"  if lsd_diag["accel_diff_avg"] > 5  else
                        "well_locked"
                    )
            result["lsd_analysis"] = lsd_diag

    # ── Sector más débil ──────────────────────────────────────────────────────
    if m.s1 and m.s2 and m.s3 and m.s1 > 0 and m.s2 > 0 and m.s3 > 0:
        # Validar que los sectores sumen aproximadamente el tiempo de vuelta
        sector_sum = m.s1 + m.s2 + m.s3
        if m.lap_time > 0 and abs(sector_sum - m.lap_time) < 1.0:
            sectors = {"S1": m.s1, "S2": m.s2, "S3": m.s3}
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

    # ── Detección de incidentes ────────────────────────────────────────────────
    incidents = _detect_incidents(df, spd_s, g_lat, g_lon, g_vert, dist_col)
    if incidents:
        result["incidents"] = incidents

    return result


def _detect_incidents(
    df: pd.DataFrame,
    spd_s: pd.Series | None,
    g_lat: pd.Series | None,
    g_lon: pd.Series | None,
    g_vert: pd.Series | None,
    dist_col: str | None,
) -> list[dict]:
    """
    Detecta incidentes de pilotaje: salidas de pista, accidentes, trompos,
    impactos y kerbs severos.
    """
    n = len(df)
    if n < 20:
        return []

    incidents: list[dict] = []

    def get_dist(i: int) -> float | None:
        if dist_col and i < n:
            try:
                return round(float(df[dist_col].iloc[i]), 0)
            except Exception:
                pass
        return None

    # 1. Caída brusca de velocidad sin frenada → salida o accidente
    if spd_s is not None:
        spd_arr = spd_s.reindex(df.index).fillna(0).values
        brk_arr: np.ndarray | None = None
        if "brake" in df.columns:
            brk_arr = pd.to_numeric(df["brake"], errors="coerce").fillna(0).values

        window = min(25, n // 4)  # ~0.5 s a 50 Hz
        in_event = False
        for i in range(window, n - 5):
            drop = float(spd_arr[i - window]) - float(spd_arr[i])
            if drop > 40 and not in_event:
                avg_brake = float(brk_arr[i - window:i].mean()) if brk_arr is not None else 100.0
                if avg_brake < 25:
                    in_event = True
                    v_before = float(spd_arr[i - window])
                    v_now = float(spd_arr[i])
                    incidents.append({
                        "type": "off_track_or_crash",
                        "dist_m": get_dist(i),
                        "detail": f"Caída de velocidad {v_before:.0f}→{v_now:.0f} km/h sin frenada (freno {avg_brake:.0f}%)",
                        "severity": "high" if drop > 80 else "medium",
                    })
            elif float(spd_arr[i]) > float(spd_arr[max(0, i - window)]) - 10:
                in_event = False

    # 2. Pico de G lateral >4 G → trompo o accidente
    if g_lat is not None:
        g_lat_arr = g_lat.reindex(df.index).fillna(0).values
        in_event = False
        for i in range(n):
            val = abs(float(g_lat_arr[i]))
            if val > 4.0 and not in_event:
                in_event = True
                incidents.append({
                    "type": "spin_or_crash",
                    "dist_m": get_dist(i),
                    "detail": f"Fuerza lateral {val:.1f} G — posible trompo o impacto",
                    "severity": "high",
                })
            elif val < 2.0:
                in_event = False

    # 3. Pico de G longitudinal >4.5 G → impacto frontal
    if g_lon is not None:
        g_lon_arr = g_lon.reindex(df.index).fillna(0).values
        in_event = False
        for i in range(n):
            val = abs(float(g_lon_arr[i]))
            if val > 4.5 and not in_event:
                in_event = True
                incidents.append({
                    "type": "impact",
                    "dist_m": get_dist(i),
                    "detail": f"Impacto longitudinal {val:.1f} G",
                    "severity": "high",
                })
            elif val < 2.0:
                in_event = False

    # 4. Slip simultáneo en las 4 ruedas >15 % → superficie fuera de pista
    slip_cols = [f"slip_{c}" for c in ("fl", "fr", "rl", "rr")]
    if all(c in df.columns for c in slip_cols):
        slip_arrays = [
            pd.to_numeric(df[c], errors="coerce").fillna(0).abs().values
            for c in slip_cols
        ]
        in_event = False
        for i in range(n):
            vals = [float(s[i]) for s in slip_arrays]
            if all(v > 15 for v in vals) and not in_event:
                in_event = True
                incidents.append({
                    "type": "all_wheel_slip",
                    "dist_m": get_dist(i),
                    "detail": f"Slip 4 ruedas {min(vals):.0f}–{max(vals):.0f}% — posible suelo fuera de pista",
                    "severity": "medium",
                })
            elif not all(v > 8 for v in vals):
                in_event = False

    # 5. Pico de G vertical >3 G → kerb severo o salto
    if g_vert is not None:
        g_vert_arr = g_vert.reindex(df.index).fillna(0).values
        in_event = False
        for i in range(n):
            val = abs(float(g_vert_arr[i]))
            if val > 3.0 and not in_event:
                in_event = True
                incidents.append({
                    "type": "kerb_or_jump",
                    "dist_m": get_dist(i),
                    "detail": f"Impacto vertical {val:.1f} G — kerb severo o salto",
                    "severity": "low" if val < 4.0 else "medium",
                })
            elif val < 1.5:
                in_event = False

    # Deduplicar: mantener solo uno cada 50 m
    incidents.sort(key=lambda x: x.get("dist_m") or 0)
    deduped: list[dict] = []
    last_dist: float = -999.0
    for inc in incidents:
        dist = inc.get("dist_m")
        if dist is None:
            deduped.append(inc)
            continue
        d = float(dist)
        if d - last_dist > 50:
            deduped.append(inc)
            last_dist = d

    return deduped[:10]
