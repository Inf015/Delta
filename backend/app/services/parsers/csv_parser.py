"""
Parser de CSVs de telemetría — Assetto Corsa (AC).

Formato (8 líneas de header):
  Línea 1: player,v8,[jugador],0,[timestamp]
  Línea 2: Game,version,date,track,car,event,laptime [s],S1 [s],S2 [s],S3 [s],S4+ [s]
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

import pandas as pd
from pydantic import BaseModel, field_validator


# ─── Modelos Pydantic ────────────────────────────────────────────────────────

class LapSetup(BaseModel):
    # Aerodinámica
    front_wing: float = 0.0
    rear_wing: float = 0.0
    # Diferencial
    on_throttle: float = 0.0
    off_throttle: float = 0.0
    # Geometría
    front_camber: float = 0.0
    rear_camber: float = 0.0
    front_toe: float = 0.0
    rear_toe: float = 0.0
    # Suspensión
    front_susp: float = 0.0
    rear_susp: float = 0.0
    front_arb: float = 0.0
    rear_arb: float = 0.0
    front_susp_h: float = 0.0   # ride height delantera (FrontSuspH)
    rear_susp_h: float = 0.0    # ride height trasera (RearSuspH)
    # Frenos
    brake_pressure: float = 0.0
    brake_bias: float = 0.0
    # Presiones de neumáticos
    fl_tyre_pressure: float = 0.0
    fr_tyre_pressure: float = 0.0
    rl_tyre_pressure: float = 0.0
    rr_tyre_pressure: float = 0.0
    # Peso / combustible
    ballast: float = 0.0
    fuel_load: float = 0.0

    @property
    def has_data(self) -> bool:
        return any([
            self.front_wing, self.rear_wing,
            self.brake_bias, self.brake_pressure,
            self.fl_tyre_pressure, self.fr_tyre_pressure,
            self.front_camber, self.rear_camber,
            self.fuel_load,
        ])


class LapMeta(BaseModel):
    simulator: str        # siempre "AC"
    player: str
    date: str
    track: str
    car: str
    event: str            # Practice | Qualify | Race
    lap_number: int

    lap_time: float       # segundos
    s1: float
    s2: float
    s3: float

    track_length: float   # metros
    track_temp: float
    ambient_temp: float
    tyre_compound: str

    valid: bool
    pit_lap: bool

    setup: LapSetup
    file_path: str

    @property
    def lap_time_fmt(self) -> str:
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


# ─── Mapeo de columnas → snake_case interno ───────────────────────────────────

_COL_ALIASES: dict[str, str] = {
    # Posición y tiempo
    "lapdistance [m]":      "lap_distance",
    "totaldistance [m]":    "total_distance",
    "laptime [s]":          "lap_time",
    "sector1time [s]":      "s1_live",
    "sector2time [s]":      "s2_live",
    "sector3time [s]":      "s3_live",
    "sector [int]":         "sector",
    # Movimiento
    "speed [km/h]":         "speed",
    "x [m]":                "x",
    "y [m]":                "y",
    "z [m]":                "z",
    "gforcelatitudinal [g]": "g_lat",
    "gforcelongitudinal [g]": "g_lon",
    "gforcevertical [g]":   "g_vert",
    "yaw [rad]":            "yaw",
    "roll [rad]":           "roll",
    "pitch [rad]":          "pitch",
    "localangularvelocityx [rad/s]": "ang_vel_x",
    "localangularvelocityy [rad/s]": "ang_vel_y",
    "localangularvelocityz [rad/s]": "ang_vel_z",
    # Velocidades globales (typo "Wold" es de AC)
    "woldspeedx [km/h]":    "world_speed_x",
    "woldspeedy [km/h]":    "world_speed_y",
    "woldspeedz [km/h]":    "world_speed_z",
    # Controles del piloto
    "throttlepercentage [%]": "throttle",
    "brakepercentage [%]":  "brake",
    "steer [%]":            "steer",       # normalizado -1.0..1.0
    "clutch [%]":           "clutch",
    "gear [int]":           "gear",
    "handbrake [%]":        "handbrake",
    # Motor
    "enginerevs [rpm]":     "rpm",
    "enginetemperature [c]": "engine_temp",
    "torque [nm]":          "torque",
    "fuelremaining [l]":    "fuel",
    # DRS / flags de pista
    "drs [0/1]":            "drs",
    "canusedrs [0/1]":      "can_use_drs",
    "raceposition [int]":   "race_position",
    "currentflag [int]":    "flag",
    "currentlapinvalid [int]": "lap_invalid",
    "inpits [int]":         "in_pits",
    # ERS / KERS (fórmulas y híbridos)
    "kerslevel [j]":        "kers_level",
    "mgukharsted [j]":      "mguk_harvested",   # alias con typo de AC
    "mgukharested [j]":     "mguk_harvested",
    "mgukharved [j]":       "mguk_harvested",
    "mgukharvested [j]":    "mguk_harvested",
    "mguhharvested [j]":    "mguh_harvested",
    "ersspent [j]":         "ers_spent",
    "ersmode [int]":        "ers_mode",
    "fuelmixmode [int]":    "fuel_mix",
    "icepower [w]":         "ice_power",
    "mgukpower [w]":        "mguk_power",
    # Neumáticos — temperatura superficial
    "tyretemperaturerearleft [c]":   "tyre_temp_rl",
    "tyretemperaturerearright [c]":  "tyre_temp_rr",
    "tyretemperaturefrontleft [c]":  "tyre_temp_fl",
    "tyretemperaturefrontright [c]": "tyre_temp_fr",
    # Neumáticos — temperatura carcasa
    "tyrecarcasstemperaturerearleft [c]":   "tyre_carcass_rl",
    "tyrecarcasstemperaturerearright [c]":  "tyre_carcass_rr",
    "tyrecarcasstemperaturefrontleft [c]":  "tyre_carcass_fl",
    "tyrecarcasstemperaturefrontright [c]": "tyre_carcass_fr",
    # Neumáticos — temperatura zonas (inner/mid/outer)
    "rearleftinside [c]":   "tyre_inner_rl",
    "rearleftmiddle [c]":   "tyre_mid_rl",
    "rearleftoutside [c]":  "tyre_outer_rl",
    "rearrightinside [c]":  "tyre_inner_rr",
    "rearrightmiddle [c]":  "tyre_mid_rr",
    "rearrightoutside [c]": "tyre_outer_rr",
    "frontleftinside [c]":  "tyre_inner_fl",
    "frontleftmiddle [c]":  "tyre_mid_fl",
    "frontleftoutside [c]": "tyre_outer_fl",
    "frontrightinside [c]": "tyre_inner_fr",
    "frontrightmiddle [c]": "tyre_mid_fr",
    "frontrightoutside [c]":"tyre_outer_fr",
    # Neumáticos — presión
    "tyrepressurerearleft [psi]":   "tyre_press_rl",
    "tyrepressurerearright [psi]":  "tyre_press_rr",
    "tyrepressurefrontleft [psi]":  "tyre_press_fl",
    "tyrepressurefrontright [psi]": "tyre_press_fr",
    # Neumáticos — desgaste
    "tyrewearrearleft [%]":   "tyre_wear_rl",
    "tyrewearrearright [%]":  "tyre_wear_rr",
    "tyrewearfrontleft [%]":  "tyre_wear_fl",
    "tyrewearfrontright [%]": "tyre_wear_fr",
    # Frenos
    "braketemperaturerearleft [c]":   "brake_temp_rl",
    "braketemperaturerearright [c]":  "brake_temp_rr",
    "braketemperaturefrontleft [c]":  "brake_temp_fl",
    "braketemperaturefrontright [c]": "brake_temp_fr",
    # Ruedas — velocidad y slip
    "wheelspeedrearleft [km/h]":   "wheel_speed_rl",
    "wheelspeedrearright [km/h]":  "wheel_speed_rr",
    "wheelspeedfrontleft [km/h]":  "wheel_speed_fl",
    "wheelspeedfrontright [km/h]": "wheel_speed_fr",
    "wheelsliprearleft [%]":   "slip_rl",
    "wheelsliprearright [%]":  "slip_rr",
    "wheelslipfrontleft [%]":  "slip_fl",
    "wheelslipfrontright [%]": "slip_fr",
    # Suspensión — posición, velocidad, aceleración
    "suspensionpositionrearleft [m]":   "susp_pos_rl",
    "suspensionpositionrearright [m]":  "susp_pos_rr",
    "suspensionpositionfrontleft [m]":  "susp_pos_fl",
    "suspensionpositionfrontright [m]": "susp_pos_fr",
    "frontrideheight [m]":  "ride_height_f",
    "rearrideheight [m]":   "ride_height_r",
    "suspensionvelocityrearleft [m/s]":   "susp_vel_rl",
    "suspensionvelocityrearright [m/s]":  "susp_vel_rr",
    "suspensionvelocityfrontleft [m/s]":  "susp_vel_fl",
    "suspensionvelocityfrontright [m/s]": "susp_vel_fr",
    "suspensionaccelerationrearleft [m/s^2]":   "susp_accel_rl",
    "suspensionaccelerationrearright [m/s^2]":  "susp_accel_rr",
    "suspensionaccelerationfrontleft [m/s^2]":  "susp_accel_fl",
    "suspensionaccelerationfrontright [m/s^2]": "susp_accel_fr",
    # Cargas de rueda
    "loadrearleft [n]":   "load_rl",
    "loadrearright [n]":  "load_rr",
    "loadfrontleft [n]":  "load_fl",
    "loadfrontright [n]": "load_fr",
}

_KNOWN_SIMS = {"R3E", "ACC", "AC", "RF2", "IRACING", "ASSETTOCORSA", "RACEROOM"}


def _normalize_col(name: str) -> str:
    key = name.lower().strip()
    return _COL_ALIASES.get(key, re.sub(r"[^a-z0-9_]", "_", key))


# ─── Parser principal ─────────────────────────────────────────────────────────

def parse_csv(path: str | Path) -> Optional[ParsedLap]:
    path = Path(path)
    if not path.exists() or path.stat().st_size < 500:
        return None

    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            lines = [f.readline() for _ in range(8)]
    except OSError:
        return None

    # ── Línea 1: player ──────────────────────────────────────────────────────
    player_parts = [p.strip() for p in lines[0].split(",")]
    player = player_parts[2] if len(player_parts) > 2 else "Unknown"

    # ── Líneas 2-3: meta ─────────────────────────────────────────────────────
    meta_hdr = [p.strip() for p in lines[1].split(",")]
    meta_val = [p.strip() for p in lines[2].split(",")]

    sim_raw = meta_val[0].upper().replace(" ", "") if meta_val else ""
    if not any(sim_raw.startswith(s) for s in _KNOWN_SIMS):
        return None

    def _get(hdr: list, val: list, key: str, default: str = "") -> str:
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

    # S3 fallback: si el sim no lo reporta directamente, calcularlo
    if s3 == 0.0 and lap_time > 0 and s1 > 0 and s2 > 0:
        s3 = round(lap_time - s1 - s2, 3)

    # ── Líneas 4-5: track ────────────────────────────────────────────────────
    track_hdr = [p.strip() for p in lines[3].split(",")]
    track_val = [p.strip() for p in lines[4].split(",")]

    lap_num    = int(_float(_get(track_hdr, track_val, "Lap [int]", "1"))) or 1
    track_len  = _float(_get(track_hdr, track_val, "Tracklen"))
    tyre       = _get(track_hdr, track_val, "Tyre")
    valid_str  = _get(track_hdr, track_val, "Valid", "true").lower()
    pit_str    = _get(track_hdr, track_val, "Pitlap", "false").lower()
    track_temp = _float(_get(track_hdr, track_val, "TrackTemp"))
    ambient    = _float(_get(track_hdr, track_val, "AmbientTemp"))

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
        front_susp_h    = _float(_get(setup_hdr, setup_val, "FrontSuspH")),
        rear_susp_h     = _float(_get(setup_hdr, setup_val, "RearSuspH")),
        brake_pressure  = _float(_get(setup_hdr, setup_val, "BrakePressure")),
        brake_bias      = _float(_get(setup_hdr, setup_val, "BrakeBias")),
        fl_tyre_pressure= _float(_get(setup_hdr, setup_val, "FLTyrePressure")),
        fr_tyre_pressure= _float(_get(setup_hdr, setup_val, "FRTyrePressure")),
        rl_tyre_pressure= _float(_get(setup_hdr, setup_val, "RLTyrePressure")),
        rr_tyre_pressure= _float(_get(setup_hdr, setup_val, "RRTyrePressure")),
        ballast         = _float(_get(setup_hdr, setup_val, "Ballast")),
        fuel_load       = _float(_get(setup_hdr, setup_val, "FuelLoad")),
    )

    # ── Línea 8+: telemetría ──────────────────────────────────────────────────
    try:
        df = pd.read_csv(path, skiprows=7, header=0, encoding="utf-8-sig", on_bad_lines="skip")
    except Exception:
        return None

    if df.empty:
        return None

    df.columns = [_normalize_col(c) for c in df.columns]

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Usar CurrentLapInvalid de telemetría como fuente de verdad si está disponible
    if "lap_invalid" in df.columns and df["lap_invalid"].max() == 1:
        valid = False

    # Filtrar puntos de pits
    if "in_pits" in df.columns:
        df = df[df["in_pits"].fillna(0) == 0]

    if df.empty:
        return None

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
    m = lap.meta
    return m.valid and not m.pit_lap and m.lap_time > min_time
