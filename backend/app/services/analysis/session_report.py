"""
Calcula las secciones 1-7 del reporte de sesión a partir de las vueltas y sus pre-análisis.
Retorna un dict JSON-serializable que el endpoint combina con el análisis de Claude (secciones 8-11).
"""

from __future__ import annotations

import statistics
from typing import Any

from app.utils.formatters import fmt_lap_time as _fmt


def _lap_status(lap: dict, best_time: float, prev_time: float | None, lap_index: int) -> str:
    t = lap["lap_time"]
    if abs(t - best_time) < 0.001:
        return "MEJOR VUELTA"
    if lap_index == 0:
        return "CALENTAMIENTO"
    if prev_time and t < prev_time:
        return "MEJORANDO"
    return "VÁLIDA"


def _avg(values: list[float]) -> float | None:
    vals = [v for v in values if v and v > 0]
    return sum(vals) / len(vals) if vals else None


def _best_f1_sectors(laps: list[dict]) -> dict:
    """El mejor sector individual entre todas las vueltas (tiempo teórico óptimo F1-style)."""
    s1_vals = [l["s1"] for l in laps if l.get("s1") and l["s1"] > 0]
    s2_vals = [l["s2"] for l in laps if l.get("s2") and l["s2"] > 0]
    s3_vals = [l["s3"] for l in laps if l.get("s3") and l["s3"] > 0]
    return {
        "s1": min(s1_vals) if s1_vals else 0,
        "s2": min(s2_vals) if s2_vals else 0,
        "s3": min(s3_vals) if s3_vals else 0,
        "valid": bool(s1_vals and s2_vals and s3_vals),
    }


def compute(laps: list[dict], setup_data: dict | None = None, track_info: dict | None = None) -> dict:
    """
    laps: lista de dicts con:
      lap_number, lap_time, s1, s2, s3, valid, pre_analysis (dict | None)
    Ordenados por lap_number.

    Retorna dict con secciones 1-7.
    """
    if not laps:
        return {}

    valid_laps = [l for l in laps if l.get("valid", True) and l["lap_time"] > 30]
    if not valid_laps:
        valid_laps = laps

    # ── Sección 1: Resumen ────────────────────────────────────────────────────
    lap_times = [l["lap_time"] for l in valid_laps]
    best_time = min(lap_times)
    worst_time = max(lap_times)
    avg_time = statistics.mean(lap_times)

    best_lap = next(l for l in valid_laps if l["lap_time"] == best_time)
    best_pre = best_lap.get("pre_analysis") or {}

    f1_sectors = _best_f1_sectors(laps)
    if f1_sectors["valid"]:
        theoretical_best = f1_sectors["s1"] + f1_sectors["s2"] + f1_sectors["s3"]
        potential_gain = max(0.0, round(best_time - theoretical_best, 3))
    else:
        theoretical_best = 0
        potential_gain = 0

    summary: dict[str, Any] = {
        "total_laps": len(laps),
        "valid_laps": len(valid_laps),
        "best_lap": best_time,
        "best_lap_fmt": _fmt(best_time),
        "worst_lap": worst_time,
        "worst_lap_fmt": _fmt(worst_time),
        "avg_lap": avg_time,
        "avg_lap_fmt": _fmt(avg_time),
        "best_s1": best_lap.get("s1", 0),
        "best_s1_fmt": _fmt(best_lap.get("s1", 0)),
        "best_s2": best_lap.get("s2", 0),
        "best_s2_fmt": _fmt(best_lap.get("s2", 0)),
        "best_s3": best_lap.get("s3", 0),
        "best_s3_fmt": _fmt(best_lap.get("s3", 0)),
        "theoretical_best": theoretical_best,
        "theoretical_best_fmt": _fmt(theoretical_best),
        "potential_gain": round(potential_gain, 3),
        "f1_best_s1": f1_sectors["s1"],
        "f1_best_s2": f1_sectors["s2"],
        "f1_best_s3": f1_sectors["s3"],
    }

    # métricas del mejor pre_analysis
    speed = best_pre.get("speed", {})
    throttle = best_pre.get("throttle", {})
    engine = best_pre.get("engine", {})
    fuel = best_pre.get("fuel", {})

    if speed:
        summary["max_speed_kmh"] = speed.get("max")
    if throttle:
        summary["throttle_avg_pct"] = throttle.get("avg")
        summary["throttle_full_pct"] = throttle.get("full_pct")
    if engine:
        summary["rpm_max"] = engine.get("rpm_max")
    if fuel:
        summary["fuel_used_per_lap"] = fuel.get("used")

    brake_data = best_pre.get("brake", {})
    if brake_data:
        summary["brake_hard_pct"] = brake_data.get("hard_pct")
    if best_pre.get("handling"):
        summary["handling"] = best_pre.get("handling")
    if best_pre.get("weak_sector"):
        summary["weak_sector"] = best_pre.get("weak_sector")

    # ── Sección 2: Tiempos por vuelta ─────────────────────────────────────────
    lap_table = []
    prev_time = None
    for i, lap in enumerate(laps):
        t = lap["lap_time"]
        delta = t - best_time
        status = _lap_status(lap, best_time, prev_time, i)

        # Resaltar mejor sector F1 (cada sector que es el mejor entre todas las vueltas)
        pre = lap.get("pre_analysis") or {}
        lap_table.append({
            "lap_number": lap["lap_number"],
            "lap_time": t,
            "lap_time_fmt": _fmt(t),
            "s1": lap.get("s1", 0),
            "s1_fmt": _fmt(lap.get("s1", 0)),
            "s2": lap.get("s2", 0),
            "s2_fmt": _fmt(lap.get("s2", 0)),
            "s3": lap.get("s3", 0),
            "s3_fmt": _fmt(lap.get("s3", 0)),
            "delta": round(delta, 3),
            "delta_fmt": f"+{delta:.3f}" if delta > 0 else "0.000",
            "status": status,
            "valid": lap.get("valid", True),
            "is_best": abs(delta) < 0.001,
            "is_best_s1": f1_sectors["s1"] > 0 and abs(lap.get("s1", 0) - f1_sectors["s1"]) < 0.001,
            "is_best_s2": f1_sectors["s2"] > 0 and abs(lap.get("s2", 0) - f1_sectors["s2"]) < 0.001,
            "is_best_s3": f1_sectors["s3"] > 0 and abs(lap.get("s3", 0) - f1_sectors["s3"]) < 0.001,
            "incidents": pre.get("incidents", []),
        })
        prev_time = t

    # ── Sección 3: Consistency Score ──────────────────────────────────────────
    consistency: dict[str, Any] = {
        "score": 0,
        "label": "Vuelta única" if len(valid_laps) == 1 else "Sin datos",
        "std_dev": 0,
        "interpretation": "Solo hay 1 vuelta válida — sube más vueltas para calcular la consistencia." if len(valid_laps) == 1 else None,
    }
    if len(valid_laps) >= 2:
        # Excluir outliers (>2x best_time)
        clean = [t for t in lap_times if t < best_time * 2]
        if len(clean) >= 2:
            std = statistics.stdev(clean)
            # Score: 100 a 0 basado en desviación. <0.3s = 100, >20s = 0
            score = max(0, 100 - int(std * 5))
            label = (
                "Excelente" if score >= 80 else
                "Buena"     if score >= 60 else
                "Regular"   if score >= 40 else
                "Baja"      if score >= 20 else
                "Muy inconsistente"
            )
            consistency = {
                "score": score,
                "label": label,
                "std_dev": round(std, 3),
                "interpretation": f"Variabilidad de {std:.3f}s entre vueltas limpias. "
                                   f"{'Enfocarse en repetir la línea de vuelta ' + str(best_lap['lap_number']) + '.' if score < 40 else 'Buen ritmo consistente.'}",
            }

    # ── Sección 4: Análisis de gomas ──────────────────────────────────────────
    tyre_temp   = best_pre.get("tyre_temp", {})
    tyre_press  = best_pre.get("tyre_press", {})
    tyre_zones  = best_pre.get("tyre_zones", {})
    slip_data   = best_pre.get("slip", {})

    tyre_analysis: dict[str, Any] = {}
    if tyre_temp:
        tyre_analysis["temp"] = tyre_temp
    if tyre_press:
        tyre_analysis["press"] = tyre_press
    if tyre_zones:
        # build camber table
        camber_table = []
        labels = {"FL": "Delantera Izq", "FR": "Delantera Der", "RL": "Trasera Izq", "RR": "Trasera Der"}
        for corner, label in labels.items():
            zone = tyre_zones.get(corner, {})
            if zone:
                diag_raw = zone.get("camber_diag", "ok")
                diag = "✓ Distribución aceptable" if diag_raw == "ok" else f"⚠ {diag_raw}"
                camber_table.append({
                    "corner": label,
                    "inner": zone.get("inner"),
                    "mid": zone.get("mid"),
                    "outer": zone.get("outer"),
                    "diagnosis": diag,
                })
        tyre_analysis["camber_table"] = camber_table
    if slip_data:
        tyre_analysis["slip"] = slip_data

    tyre_wear_data = best_pre.get("tyre_wear", {})
    if tyre_wear_data:
        wear_table = []
        labels_w = {"FL": "Del. Izq", "FR": "Del. Der", "RL": "Tras. Izq", "RR": "Tras. Der"}
        for corner, label in labels_w.items():
            w = tyre_wear_data.get(corner, {})
            if w:
                wear_table.append({
                    "corner": label,
                    "avg_pct": w.get("avg"),
                    "max_pct": w.get("max"),
                    "end_pct": w.get("end"),
                })
        if wear_table:
            tyre_analysis["wear"] = wear_table
        if "diagnosis" in tyre_wear_data:
            tyre_analysis["wear_diagnosis"] = tyre_wear_data["diagnosis"]

    tyre_carcass_data = best_pre.get("tyre_carcass", {})
    if tyre_carcass_data:
        tyre_analysis["carcass"] = {k: v for k, v in tyre_carcass_data.items() if k != "overheating_risk"}
        if "overheating_risk" in tyre_carcass_data:
            tyre_analysis["overheating_risk"] = tyre_carcass_data["overheating_risk"]

    # ── Sección 5: Análisis de frenos ─────────────────────────────────────────
    brake_temp    = best_pre.get("brake_temp", {})
    brake_balance = best_pre.get("brake_balance", {})

    brake_analysis: dict[str, Any] = {}
    if brake_temp:
        brake_analysis["temp"] = brake_temp
    if brake_balance:
        brake_analysis["balance"] = brake_balance
        if brake_balance.get("bias") == "front_heavy":
            brake_analysis["warning"] = (
                f"Frenos delanteros mucho más calientes que traseros "
                f"({brake_balance.get('front_avg', 0):.0f}°C vs {brake_balance.get('rear_avg', 0):.0f}°C) "
                f"— considera mover brake bias hacia atrás."
            )

    braking_zones = best_pre.get("braking_zones", [])
    if braking_zones:
        brake_analysis["zones"] = braking_zones

    # ── Sección 6: G-Forces y dinámica ────────────────────────────────────────
    g_forces   = best_pre.get("g_forces", {})
    suspension = best_pre.get("suspension", {})

    dynamics: dict[str, Any] = {}
    if g_forces:
        dynamics["g_forces"] = [
            {"metric": "G lateral máx izquierda", "value": f"{g_forces.get('lat_max_left', 0):.2f} G",  "interpretation": "Carga alta en curvas izq."},
            {"metric": "G lateral máx derecha",   "value": f"{g_forces.get('lat_max_right', 0):.2f} G", "interpretation": "Carga alta en curvas der."},
            {"metric": "G longitudinal (frenada)", "value": f"{g_forces.get('lon_max_brake', 0):.2f} G","interpretation": "Frenada intensa" if g_forces.get("lon_max_brake", 0) > 2 else "Frenada moderada"},
            {"metric": "G longitudinal (aceleración)", "value": f"{g_forces.get('lon_max_acc', 0):.2f} G", "interpretation": "Buena tracción" if g_forces.get("lon_max_acc", 0) > 0.7 else "Tracción moderada"},
        ]
    if suspension:
        susp_table = []
        labels_s = {"FL": "Delantera Izq", "FR": "Delantera Der", "RL": "Trasera Izq", "RR": "Trasera Der"}
        for corner, label in labels_s.items():
            s = suspension.get(corner, {})
            if s:
                susp_table.append({
                    "corner": label,
                    "avg_mm": s.get("avg"),
                    "range_mm": s.get("range"),
                    "min_mm": s.get("min"),
                    "max_mm": s.get("max"),
                })
        dynamics["suspension"] = susp_table

    ride_h = best_pre.get("ride_height", {})
    if ride_h:
        dynamics["ride_height"] = {
            "front_mm": ride_h.get("front", {}).get("avg_mm"),
            "rear_mm":  ride_h.get("rear", {}).get("avg_mm"),
            "rake_mm":  ride_h.get("rake_mm"),
            "diagnosis": ride_h.get("rake_diagnosis"),
        }

    loads_data = best_pre.get("tyre_loads", {})
    if loads_data:
        dynamics["tyre_loads"] = loads_data

    susp_vel_data = best_pre.get("susp_velocity", {})
    if susp_vel_data:
        dynamics["damper_analysis"] = {
            "diagnosis": susp_vel_data.get("damper_diagnosis"),
            "corners": {c: susp_vel_data[c] for c in ("FL", "FR", "RL", "RR") if c in susp_vel_data},
        }

    yaw_data = best_pre.get("yaw_rate", {})
    if yaw_data:
        dynamics["yaw_rate"] = yaw_data

    lsd_data = best_pre.get("lsd_analysis", {})
    if lsd_data:
        dynamics["lsd_analysis"] = lsd_data

    steering_data = best_pre.get("steering", {})
    if steering_data:
        dynamics["steering"] = steering_data

    # ── Sección 7: Setup ──────────────────────────────────────────────────────
    setup_section: dict[str, Any] = {}

    if setup_data:
        # Setup subido manualmente por el piloto (.ini)
        setup_section["has_setup_data"] = True
        setup_section["source"] = "ini"
        setup_section["raw"] = setup_data

        # Presiones de neumáticos del .ini
        ini_pressure = (setup_data.get("tyres") or {}).get("pressure_psi", {})
        if ini_pressure:
            labels_p = {"LF": "Delantera Izq", "RF": "Delantera Der", "LR": "Trasera Izq", "RR": "Trasera Der"}
            setup_section["tyre_pressures"] = [
                {"corner": labels_p.get(c, c), "target": v}
                for c, v in ini_pressure.items()
            ]
    else:
        # Intentar con datos del CSV
        tyre_press_data = best_pre.get("tyre_press", {})
        if tyre_press_data:
            press_table = []
            labels_p = {"FL": "Delantera Izq", "FR": "Delantera Der", "RL": "Trasera Izq", "RR": "Trasera Der"}
            for corner, label in labels_p.items():
                p = tyre_press_data.get(corner, {})
                if p:
                    press_table.append({
                        "corner": label,
                        "avg": p.get("avg"),
                        "min": p.get("min"),
                        "max": p.get("max"),
                    })
            if press_table:
                setup_section["tyre_pressures"] = press_table

        setup_section["has_setup_data"] = False
        setup_section["note"] = "No se subió archivo de setup. Sube el .ini de AC para ver el setup completo."

    result: dict[str, Any] = {
        "section_1_summary":     summary,
        "section_2_lap_table":   lap_table,
        "section_3_consistency": consistency,
        "section_4_tyres":       tyre_analysis,
        "section_5_brakes":      brake_analysis,
        "section_6_dynamics":    dynamics,
        "section_7_setup":       setup_section,
        # secciones 8-11 las añade el endpoint después de llamar Claude
    }

    if track_info:
        result["section_0_track"] = track_info

    return result
