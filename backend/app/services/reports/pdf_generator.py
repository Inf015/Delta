"""
Wrapper del generador de PDFs legacy adaptado para Docker.

Convierte nuestro ParsedLap → formato dict que espera el generador original
y llama generate_pdf() del código legacy sin modificarlo.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pandas as pd

from app.core.config import settings
from app.services.parsers.csv_parser import ParsedLap

# ── Añadir legacy al path para importar generate_pdf directamente ─────────────
_LEGACY = Path(__file__).parent.parent.parent.parent / "legacy" / "scripts"
if str(_LEGACY) not in sys.path:
    sys.path.insert(0, str(_LEGACY))

from telemetry_pdf_generator_v3 import (  # noqa: E402
    generate_pdf as _legacy_generate_pdf,
    analyze_telemetry,
)

# ── Mapeo: nuestro snake_case → nombres PascalCase del legacy ─────────────────
_OUR_TO_LEGACY: dict[str, str] = {
    "lap_distance":    "LapDistance",
    "total_distance":  "TotalDistance",
    "lap_time":        "LapTime",
    "s1_live":         "S1Live",
    "s2_live":         "S2Live",
    "sector":          "Sector",
    "speed":           "Speed",
    "rpm":             "RPM",
    "throttle":        "Throttle",
    "brake":           "Brake",
    "steer":           "Steer",
    "clutch":          "Clutch",
    "gear":            "Gear",
    "x":               "X",
    "y":               "Y",
    "z":               "Z",
    "g_lat":           "GLat",
    "g_lon":           "GLon",
    "g_vert":          "GVert",
    "fuel":            "FuelRemaining",
    "engine_temp":     "EngineTemp",
    "torque":          "Torque",
    "in_pits":         "InPits",
    # Gomas — temperatura superficie
    "tyre_temp_fl":    "TyreTempFL",
    "tyre_temp_fr":    "TyreTempFR",
    "tyre_temp_rl":    "TyreTempRL",
    "tyre_temp_rr":    "TyreTempRR",
    # Gomas — carcasa
    "tyre_carcass_fl": "CarcTempFL",
    "tyre_carcass_fr": "CarcTempFR",
    "tyre_carcass_rl": "CarcTempRL",
    "tyre_carcass_rr": "CarcTempRR",
    # Gomas — zonas (camber)
    "tyre_inner_fl":   "TyreInnerFL",
    "tyre_mid_fl":     "TyreMiddleFL",
    "tyre_outer_fl":   "TyreOuterFL",
    "tyre_inner_fr":   "TyreInnerFR",
    "tyre_mid_fr":     "TyreMiddleFR",
    "tyre_outer_fr":   "TyreOuterFR",
    "tyre_inner_rl":   "TyreInnerRL",
    "tyre_mid_rl":     "TyreMiddleRL",
    "tyre_outer_rl":   "TyreOuterRL",
    "tyre_inner_rr":   "TyreInnerRR",
    "tyre_mid_rr":     "TyreMiddleRR",
    "tyre_outer_rr":   "TyreOuterRR",
    # Presión
    "tyre_press_fl":   "TyrePressFL",
    "tyre_press_fr":   "TyrePressFR",
    "tyre_press_rl":   "TyrePressRL",
    "tyre_press_rr":   "TyrePressRR",
    # Desgaste
    "tyre_wear_fl":    "TyreWearFL",
    "tyre_wear_fr":    "TyreWearFR",
    "tyre_wear_rl":    "TyreWearRL",
    "tyre_wear_rr":    "TyreWearRR",
    # Frenos
    "brake_temp_fl":   "BrakeTempFL",
    "brake_temp_fr":   "BrakeTempFR",
    "brake_temp_rl":   "BrakeTempRL",
    "brake_temp_rr":   "BrakeTempRR",
    # Slip
    "slip_fl":         "SlipFL",
    "slip_fr":         "SlipFR",
    "slip_rl":         "SlipRL",
    "slip_rr":         "SlipRR",
    # Velocidad de rueda
    "wheel_speed_fl":  "WheelSpeedFL",
    "wheel_speed_fr":  "WheelSpeedFR",
    "wheel_speed_rl":  "WheelSpeedRL",
    "wheel_speed_rr":  "WheelSpeedRR",
    # Suspensión
    "susp_pos_fl":     "SuspPosFL",
    "susp_pos_fr":     "SuspPosFR",
    "susp_pos_rl":     "SuspPosRL",
    "susp_pos_rr":     "SuspPosRR",
    # Carga
    "load_fl":         "LoadFL",
    "load_fr":         "LoadFR",
    "load_rl":         "LoadRL",
    "load_rr":         "LoadRR",
    # Ride height
    "ride_height_f":   "RideHeightF",
    "ride_height_r":   "RideHeightR",
    # Orientación
    "yaw":             "Yaw",
    "roll":            "Roll",
    "pitch":           "Pitch",
}


def _to_legacy_df(df: pd.DataFrame) -> pd.DataFrame:
    """Renombra columnas snake_case → PascalCase que espera el legacy."""
    return df.rename(columns=_OUR_TO_LEGACY)


def _parsed_lap_to_legacy_dict(lap: ParsedLap) -> dict:
    """Convierte ParsedLap al dict que consume generate_pdf del legacy."""
    m = lap.meta
    s = m.setup

    meta_dict = {
        "game":     m.simulator,
        "version":  "",
        "date":     m.date,
        "track":    m.track,
        "car":      m.car,
        "event":    m.event,
        "laptime":  str(m.lap_time),
        # campos de track que usa el legacy para portada
        "Tyre":     m.tyre_compound,
        "TrackTemp": str(m.track_temp),
        "AmbientTemp": str(m.ambient_temp),
    }

    setup_dict = {
        "FWing":          s.front_wing,
        "RWing":          s.rear_wing,
        "OnThrottle":     s.on_throttle,
        "OffThrottle":    s.off_throttle,
        "FrontCamber":    s.front_camber,
        "RearCamber":     s.rear_camber,
        "FrontToe":       s.front_toe,
        "RearToe":        s.rear_toe,
        "FrontSusp":      s.front_susp,
        "RearSusp":       s.rear_susp,
        "FrontAntiRoll":  s.front_arb,
        "RearAntiRoll":   s.rear_arb,
        "BrakePressure":  s.brake_pressure,
        "BrakeBias":      s.brake_bias,
        "FLTyrePressure": s.fl_tyre_pressure,
        "FRTyrePressure": s.fr_tyre_pressure,
        "RLTyrePressure": s.rl_tyre_pressure,
        "RRTyrePressure": s.rr_tyre_pressure,
    }

    return {
        "meta":     meta_dict,
        "setup":    setup_dict,
        "lap_time": m.lap_time,
        "s1":       m.s1 or None,
        "s2":       m.s2 or None,
        "s3":       m.s3 or None,
        "df":       _to_legacy_df(lap.telemetry),
        "path":     m.file_path,
    }


def generate_pdf(parsed_lap: ParsedLap, pilot_name: str = "Piloto") -> str:
    """
    Genera el PDF de 11 secciones a partir de un ParsedLap.

    Retorna la ruta absoluta del PDF generado.
    """
    lap_dict = _parsed_lap_to_legacy_dict(parsed_lap)

    out_dir = Path(settings.pdf_data_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_track = parsed_lap.meta.track.replace(" ", "_").replace("/", "-")[:40]
    safe_car = parsed_lap.meta.car.replace(" ", "_").replace("/", "-")[:30]
    filename = f"{uuid.uuid4()}_{safe_track}_{safe_car}.pdf"
    output_path = out_dir / filename

    result = _legacy_generate_pdf(
        laps_data=[lap_dict],
        pilot_name=pilot_name,
        pilot_id=0,
        session_type=parsed_lap.meta.event,
        session_num=parsed_lap.meta.lap_number,
        output_path=output_path,
    )

    if result is None:
        raise RuntimeError("El generador legacy no pudo crear el PDF")

    return result


def generate_session_pdf(
    csv_paths: list[str],
    pilot_name: str,
    track: str,
    car: str,
    session_type: str,
    session_id: str,
) -> str:
    """
    Genera el PDF de sesión completa (11 secciones) a partir de múltiples CSVs.
    Cada CSV = una vuelta. El legacy genera el reporte con todas las vueltas.

    Retorna la ruta absoluta del PDF generado.
    """
    from app.services.parsers.csv_parser import parse_csv

    laps_data = []
    for csv_path in csv_paths:
        parsed = parse_csv(csv_path)
        if parsed is not None:
            laps_data.append(_parsed_lap_to_legacy_dict(parsed))

    if not laps_data:
        raise RuntimeError("No se pudo parsear ningún CSV de la sesión")

    out_dir = Path(settings.pdf_data_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_track = track.replace(" ", "_").replace("/", "-")[:40]
    safe_car = car.replace(" ", "_").replace("/", "-")[:30]
    filename = f"session_{session_id}_{safe_track}_{safe_car}.pdf"
    output_path = out_dir / filename

    result = _legacy_generate_pdf(
        laps_data=laps_data,
        pilot_name=pilot_name,
        pilot_id=0,
        session_type=session_type,
        session_num=1,
        output_path=output_path,
    )

    if result is None:
        raise RuntimeError("El generador legacy no pudo crear el PDF de sesión")

    return result
