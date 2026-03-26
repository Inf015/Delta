"""
Parser de CSVs de telemetría — AC y R3E.

Formato (8 líneas de header, idéntico en ambos simuladores):
  Línea 1: player,v8,[jugador],0,[timestamp]
  Línea 2: Game,version,date,track,car,event,laptime [s],S1,S2,S3,S4+
  Línea 3: valores meta
  Línea 4: track header
  Línea 5: track values (TrackID, Tracklen, Tyre, Valid, Pitlap, ...)
  Línea 6: setup header
  Línea 7: setup values
  Línea 8: telemetry header
  Línea 9+: datos de telemetría
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, field_validator


# ─── Modelos Pydantic ────────────────────────────────────────────────────────

class LapSetup(BaseModel):
    front_wing: float = 0.0
    rear_wing: float = 0.0
    on_throttle: float = 0.0
    off_throttle: float = 0.0
    front_camber: float = 0.0
    rear_camber: float = 0.0
    front_toe: float = 0.0
    rear_toe: float = 0.0
    front_susp: float = 0.0
    rear_susp: float = 0.0
    front_arb: float = 0.0
    rear_arb: float = 0.0
    brake_pressure: float = 0.0
    brake_bias: float = 0.0
    fl_tyre_pressure: float = 0.0
    fr_tyre_pressure: float = 0.0
    rl_tyre_pressure: float = 0.0
    rr_tyre_pressure: float = 0.0

    @property
    def has_data(self) -> bool:
        """True si el sim exportó datos de setup (no todos son 0.0)."""
        return any([
            self.front_wing, self.rear_wing, self.brake_bias,
            self.fl_tyre_pressure, self.fr_tyre_pressure,
        ])


class LapMeta(BaseModel):
    # Identificación
    simulator: str           # "AC" | "R3E"
    player: str
    date: str
    track: str
    car: str
    event: str               # Practice | Qualify | Race
    lap_number: int

    # Tiempos
    lap_time: float          # segundos
    s1: float
    s2: float
    s3: float

    # Pista
    track_length: float      # metros
    track_temp: float
    ambient_temp: float
    tyre_compound: str

    # Flags
    valid: bool
    pit_lap: bool

    # Setup (puede ser vacío)
    setup: LapSetup

    # Path del archivo origen
    file_path: str

    @property
    def lap_time_fmt(self) -> str:
        """Retorna el tiempo en formato m:ss.mmm."""
        if self.lap_time <= 0:
            return "—"
        m = int(self.lap_time // 60)
        s = self.lap_time - m * 60
        return f"{m}:{s:06.3f}"

    @field_validator("simulator")
    @classmethod
    def normalize_simulator(cls, v: str) -> str:
        v = v.upper().replace(" ", "")
        if v.startswith("AC") or "ASSETTO" in v:
            return "AC"
        if v.startswith("R3E") or "RACEROOM" in v:
            return "R3E"
        return v


class ParsedLap(BaseModel):
    meta: LapMeta
    telemetry: pd.DataFrame

    model_config = {"arbitrary_types_allowed": True}


# ─── Mapeo de columnas (normaliza nombres a snake_case interno) ───────────────

_COL_ALIASES: dict[str, str] = {
    "lapdistance [m]": "lap_distance",
    "totaldistance [m]": "total_distance",
    "laptime [s]": "lap_time",
    "sector1time [s]": "s1_live",
    "sector2time [s]": "s2_live",
    "sector3time [s]": "s3_live",
    "sector [int]": "sector",
    "speed [km/h]": "speed",
    "enginerevs [rpm]": "rpm",
    "throttlepercentage [%]": "throttle",
    "brakepercentage [%]": "brake",
    "steer [%]": "steer",
    "clutch [%]": "clutch",
    "gear [int]": "gear",
    "x [m]": "x",
    "y [m]": "y",
    "z [m]": "z",
    "gforcelatitudinal [g]": "g_lat",
    "gforcelongitudinal [g]": "g_lon",
    "gforcevertical [g]": "g_vert",
    "fuelremaining [l]": "fuel",
    "enginetemperature [c]": "engine_temp",
    "torque [nm]": "torque",
    "inpits [int]": "in_pits",
    # Gomas — temperatura
    "tyretemperaturerearleft [c]": "tyre_temp_rl",
    "tyretemperaturerearright [c]": "tyre_temp_rr",
    "tyretemperaturefrontleft [c]": "tyre_temp_fl",
    "tyretemperaturefrontright [c]": "tyre_temp_fr",
    # Gomas — carcasa
    "tyrecarcasstemperaturerearleft [c]": "tyre_carcass_rl",
    "tyrecarcasstemperaturerearright [c]": "tyre_carcass_rr",
    "tyrecarcasstemperaturefrontleft [c]": "tyre_carcass_fl",
    "tyrecarcasstemperaturefrontright [c]": "tyre_carcass_fr",
    # Gomas — presión
    "tyrepressurerearleft [psi]": "tyre_press_rl",
    "tyrepressurerearright [psi]": "tyre_press_rr",
    "tyrepressurefrontleft [psi]": "tyre_press_fl",
    "tyrepressurefrontright [psi]": "tyre_press_fr",
    # Gomas — desgaste
    "tyrewearrearleft [%]": "tyre_wear_rl",
    "tyrewearrearright [%]": "tyre_wear_rr",
    "tyrewearfrontleft [%]": "tyre_wear_fl",
    "tyrewearfrontright [%]": "tyre_wear_fr",
    # Gomas — zona interna/media/externa
    "rearleftinside [c]": "tyre_inner_rl",
    "rearleftmiddle [c]": "tyre_mid_rl",
    "rearleftoutside [c]": "tyre_outer_rl",
    "rearrightinside [c]": "tyre_inner_rr",
    "rearrightmiddle [c]": "tyre_mid_rr",
    "rearrightoutside [c]": "tyre_outer_rr",
    "frontleftinside [c]": "tyre_inner_fl",
    "frontleftmiddle [c]": "tyre_mid_fl",
    "frontleftoutside [c]": "tyre_outer_fl",
    "frontrightinside [c]": "tyre_inner_fr",
    "frontrightmiddle [c]": "tyre_mid_fr",
    "frontrightoutside [c]": "tyre_outer_fr",
    # Frenos
    "braketemperaturerearleft [c]": "brake_temp_rl",
    "braketemperaturerearright [c]": "brake_temp_rr",
    "braketemperaturefrontleft [c]": "brake_temp_fl",
    "braketemperaturefrontright [c]": "brake_temp_fr",
    # Slip
    "wheelsliprearleft [%]": "slip_rl",
    "wheelsliprearright [%]": "slip_rr",
    "wheelslipfrontleft [%]": "slip_fl",
    "wheelslipfrontright [%]": "slip_fr",
    # Velocidad de rueda
    "wheelspeedrearleft [km/h]": "wheel_speed_rl",
    "wheelspeedrearright [km/h]": "wheel_speed_rr",
    "wheelspeedfrontleft [km/h]": "wheel_speed_fl",
    "wheelspeedfrontright [km/h]": "wheel_speed_fr",
    # Suspensión
    "suspensionpositionrearleft [m]": "susp_pos_rl",
    "suspensionpositionrearright [m]": "susp_pos_rr",
    "suspensionpositionfrontleft [m]": "susp_pos_fl",
    "suspensionpositionfrontright [m]": "susp_pos_fr",
    "frontrideheight [m]": "ride_height_f",
    "rearrideheight [m]": "ride_height_r",
    # Carga
    "loadrearleft [n]": "load_rl",
    "loadrearright [n]": "load_rr",
    "loadfrontleft [n]": "load_fl",
    "loadfrontright [n]": "load_fr",
    # Orientación
    "yaw [rad]": "yaw",
    "roll [rad]": "roll",
    "pitch [rad]": "pitch",
}

_KNOWN_SIMS = {"R3E", "ACC", "AC", "RF2", "IRACING", "ASSETTOCORSA", "RACEROOM"}


def _normalize_col(name: str) -> str:
    return _COL_ALIASES.get(name.lower().strip(), re.sub(r"[^a-z0-9_]", "_", name.lower().strip()))


# ─── Parser principal ─────────────────────────────────────────────────────────

def parse_csv(path: str | Path) -> Optional[ParsedLap]:
    """
    Lee un CSV de telemetría y retorna un ParsedLap con meta + DataFrame.
    Retorna None si el archivo es inválido o no reconocido.
    """
    path = Path(path)
    if not path.exists() or path.stat().st_size < 500:
        return None

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = [f.readline() for _ in range(8)]
    except OSError:
        return None

    # ── Línea 1: player ──────────────────────────────────────────────────────
    player_parts = [p.strip() for p in lines[0].split(",")]
    player = player_parts[2] if len(player_parts) > 2 else "Unknown"

    # ── Líneas 2-3: meta ─────────────────────────────────────────────────────
    meta_hdr = [p.strip() for p in lines[1].split(",")]
    meta_val = [p.strip() for p in lines[2].split(",")]

    # Detectar si línea 2 es el header correcto
    sim_raw = meta_val[0].upper().replace(" ", "") if meta_val else ""
    if not any(sim_raw.startswith(s) for s in _KNOWN_SIMS):
        return None

    def _get(hdr, val, key, default=""):
        try:
            idx = next(i for i, h in enumerate(hdr) if key.lower() in h.lower())
            return val[idx].strip() if idx < len(val) else default
        except StopIteration:
            return default

    def _float(s: str, default: float = 0.0) -> float:
        try:
            return float(s)
        except (ValueError, TypeError):
            return default

    lap_time = _float(_get(meta_hdr, meta_val, "laptime"))
    s1       = _float(_get(meta_hdr, meta_val, "S1"))
    s2       = _float(_get(meta_hdr, meta_val, "S2"))
    s3       = _float(_get(meta_hdr, meta_val, "S3"))
    track    = _get(meta_hdr, meta_val, "track")
    car      = _get(meta_hdr, meta_val, "car")
    event    = _get(meta_hdr, meta_val, "event")
    date     = _get(meta_hdr, meta_val, "date")
    lap_num  = int(_float(_get(meta_hdr, meta_val, "lap", "1"))) or 1

    # ── Líneas 4-5: track ────────────────────────────────────────────────────
    track_hdr = [p.strip() for p in lines[3].split(",")]
    track_val = [p.strip() for p in lines[4].split(",")]

    track_len   = _float(_get(track_hdr, track_val, "Tracklen"))
    tyre        = _get(track_hdr, track_val, "Tyre")
    valid_str   = _get(track_hdr, track_val, "Valid", "true").lower()
    pit_str     = _get(track_hdr, track_val, "Pitlap", "false").lower()
    track_temp  = _float(_get(track_hdr, track_val, "TrackTemp"))
    ambient     = _float(_get(track_hdr, track_val, "AmbientTemp"))

    valid   = valid_str == "true"
    pit_lap = pit_str == "true"

    # ── Líneas 6-7: setup ────────────────────────────────────────────────────
    setup_hdr = [p.strip() for p in lines[5].split(",")]
    setup_val = [p.strip() for p in lines[6].split(",")]

    setup = LapSetup(
        front_wing      = _float(_get(setup_hdr, setup_val, "FWing")),
        rear_wing       = _float(_get(setup_hdr, setup_val, "RWing")),
        on_throttle     = _float(_get(setup_hdr, setup_val, "OnThrottle")),
        off_throttle    = _float(_get(setup_hdr, setup_val, "OffThrottle")),
        front_camber    = _float(_get(setup_hdr, setup_val, "FrontCamber")),
        rear_camber     = _float(_get(setup_hdr, setup_val, "RearCamber")),
        front_toe       = _float(_get(setup_hdr, setup_val, "FrontToe")),
        rear_toe        = _float(_get(setup_hdr, setup_val, "RearToe")),
        front_susp      = _float(_get(setup_hdr, setup_val, "FrontSusp")),
        rear_susp       = _float(_get(setup_hdr, setup_val, "RearSusp")),
        front_arb       = _float(_get(setup_hdr, setup_val, "FrontAntiRoll")),
        rear_arb        = _float(_get(setup_hdr, setup_val, "RearAntiRoll")),
        brake_pressure  = _float(_get(setup_hdr, setup_val, "BrakePressure")),
        brake_bias      = _float(_get(setup_hdr, setup_val, "BrakeBias")),
        fl_tyre_pressure= _float(_get(setup_hdr, setup_val, "FLTyrePressure")),
        fr_tyre_pressure= _float(_get(setup_hdr, setup_val, "FRTyrePressure")),
        rl_tyre_pressure= _float(_get(setup_hdr, setup_val, "RLTyrePressure")),
        rr_tyre_pressure= _float(_get(setup_hdr, setup_val, "RRTyrePressure")),
    )

    # ── Línea 8+: telemetría ──────────────────────────────────────────────────
    try:
        # skiprows=7 salta líneas 1-7, dejando línea 8 (telemetry header) como header=0
        df = pd.read_csv(path, skiprows=7, header=0, encoding="utf-8", on_bad_lines="skip")
    except Exception:
        return None

    if df.empty:
        return None

    # Normalizar nombres de columnas
    df.columns = [_normalize_col(c) for c in df.columns]

    # Convertir a numérico donde sea posible
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Filtrar puntos dentro de pits si hay columna
    if "in_pits" in df.columns:
        df = df[df["in_pits"] == 0]

    meta = LapMeta(
        simulator    = sim_raw,
        player       = player,
        date         = date,
        track        = track,
        car          = car,
        event        = event,
        lap_number   = lap_num,
        lap_time     = lap_time,
        s1           = s1,
        s2           = s2,
        s3           = s3,
        track_length = track_len,
        track_temp   = track_temp,
        ambient_temp = ambient,
        tyre_compound= tyre,
        valid        = valid,
        pit_lap      = pit_lap,
        setup        = setup,
        file_path    = str(path),
    )

    return ParsedLap(meta=meta, telemetry=df)


def is_valid_lap(lap: ParsedLap, min_time: float = 30.0) -> bool:
    """
    True si la vuelta es usable para análisis.
    Descarta: inválidas, pit laps, tiempo <= 0, tiempo absurdamente bajo.
    """
    m = lap.meta
    return (
        m.valid
        and not m.pit_lap
        and m.lap_time > min_time
    )
