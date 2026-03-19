#!/usr/bin/env python3
"""
Generador de reportes PDF de telemetría - formato oficial v4.0
Análisis completo: gomas, frenos, G-forces, dinámica, setup
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import sys, os, glob, json

# ─── COLORES BASE ──────────────────────────────────────────────────────────
RED    = colors.HexColor('#c0392b')
DARK   = colors.HexColor('#1a1a1a')
GREY   = colors.HexColor('#666666')
BGROW  = colors.HexColor('#f5f5f5')
BGHEAD = colors.HexColor('#c0392b')
BGBLUE = colors.HexColor('#2c3e50')
GREEN  = colors.HexColor('#27ae60')
ORANGE = colors.HexColor('#e67e22')
BLUE   = colors.HexColor('#2980b9')
YELLOW = colors.HexColor('#f39c12')

# ─── COLORES DE CELDA (semáforo + F1) ──────────────────────────────────────
# Temperaturas de goma
C_TYRE_COLD   = colors.HexColor('#AED6F1')  # azul    — muy fría  (<50°C)
C_TYRE_WARM   = colors.HexColor('#D6EAF8')  # azul claro — calentando (50-75°C)
C_TYRE_OK     = colors.HexColor('#D5F5E3')  # verde   — óptima  (75-105°C)
C_TYRE_HOT    = colors.HexColor('#FDEBD0')  # naranja — caliente (105-120°C)
C_TYRE_CRIT   = colors.HexColor('#FADBD8')  # rojo    — crítica  (>120°C)
# Temperaturas de freno
C_BRAKE_COLD  = colors.HexColor('#AED6F1')  # azul    — fría     (<200°C)
C_BRAKE_OK    = colors.HexColor('#D5F5E3')  # verde   — óptima  (200-550°C)
C_BRAKE_HOT   = colors.HexColor('#FDEBD0')  # naranja — caliente (550-720°C)
C_BRAKE_CRIT  = colors.HexColor('#FADBD8')  # rojo    — crítica  (>720°C)
# Presión de goma
C_PRESS_LOW   = colors.HexColor('#AED6F1')  # azul    — baja     (<22 PSI)
C_PRESS_OK    = colors.HexColor('#D5F5E3')  # verde   — óptima  (22-32 PSI)
C_PRESS_HIGH  = colors.HexColor('#FDEBD0')  # naranja — alta     (>32 PSI)
# Slip / desgaste / sectores
C_SLIP_OK     = colors.HexColor('#D5F5E3')  # verde   — bajo     (<3%)
C_SLIP_MED    = colors.HexColor('#FDEBD0')  # naranja — medio    (3-7%)
C_SLIP_HIGH   = colors.HexColor('#FADBD8')  # rojo    — alto     (>7%)
C_SECTOR_BEST = colors.HexColor('#7D3C98')  # morado  — mejor sector (F1)
C_LAP_BEST    = colors.HexColor('#D5F5E3')  # verde   — mejor vuelta
C_LAP_SLOW    = colors.HexColor('#FADBD8')  # rojo suave — peor vuelta
C_DELTA_POS   = colors.HexColor('#FADBD8')  # rojo    — tiempo perdido
C_DELTA_ZERO  = colors.HexColor('#D5F5E3')  # verde   — mejor
C_GFORCE_HIGH = colors.HexColor('#FDEBD0')  # naranja — G alto
C_GFORCE_CRIT = colors.HexColor('#FADBD8')  # rojo    — G muy alto


def tyre_temp_color(val):
    try:
        v = float(val)
        if v < 50:   return C_TYRE_COLD
        if v < 75:   return C_TYRE_WARM
        if v < 105:  return C_TYRE_OK
        if v < 120:  return C_TYRE_HOT
        return C_TYRE_CRIT
    except: return colors.white


def brake_temp_color(val):
    try:
        v = float(val)
        if v < 200:  return C_BRAKE_COLD
        if v < 550:  return C_BRAKE_OK
        if v < 720:  return C_BRAKE_HOT
        return C_BRAKE_CRIT
    except: return colors.white


def press_color(val):
    try:
        v = float(val)
        if v < 22:   return C_PRESS_LOW
        if v <= 32:  return C_PRESS_OK
        return C_PRESS_HIGH
    except: return colors.white


def slip_color(val):
    try:
        v = float(val)
        if v < 3:    return C_SLIP_OK
        if v < 7:    return C_SLIP_MED
        return C_SLIP_HIGH
    except: return colors.white


def wear_color(val):
    try:
        v = float(val)
        if v < 0.5:  return C_SLIP_OK
        if v < 1.5:  return C_SLIP_MED
        return C_SLIP_HIGH
    except: return colors.white


def delta_color(val):
    try:
        v = float(val)
        if v <= 0:   return C_DELTA_ZERO
        if v < 1.0:  return colors.white
        return C_DELTA_POS
    except: return colors.white

KNOWN_SIMS = ['R3E', 'ACC', 'AC', 'RF2', 'IRACING', 'ASSETTOCORSA', 'RACEROOM']

# ─── MAPEO DE COLUMNAS COMPLETO ────────────────────────────────────────────
COL_MAP = {
    # Tiempo y distancia
    'laptime': 'LapTime', 'lapdistance': 'LapDistance',
    'totaldistance': 'TotalDistance', 'sector': 'Sector',
    'sector1time': 'S1Live', 'sector2time': 'S2Live',
    # Dinámica básica
    'speed': 'Speed', 'enginerevs': 'RPM', 'gear': 'Gear', 'steer': 'Steer',
    'throttlepercentage': 'Throttle', 'brakepercentage': 'Brake', 'clutch': 'Clutch',
    # Motor
    'enginetemperature': 'EngineTemp', 'torque': 'Torque',
    'fuelremaining': 'FuelRemaining',
    # G-forces
    'gforcelatitudinal': 'GLat', 'gforcelongitudinal': 'GLon', 'gforcevertical': 'GVert',
    # Coordenadas
    'x': 'X', 'y': 'Y', 'z': 'Z',
    'yaw': 'Yaw', 'roll': 'Roll', 'pitch': 'Pitch',
    # Ride height
    'frontrideheight': 'RideHeightF', 'rearrideheight': 'RideHeightR',
    # Velocidad de ruedas
    'wheelspeedrearleft': 'WheelSpeedRL', 'wheelspeedrearright': 'WheelSpeedRR',
    'wheelspeedfrontleft': 'WheelSpeedFL', 'wheelspeedfrontright': 'WheelSpeedFR',
    # Slip
    'wheelsliprearleft': 'SlipRL', 'wheelsliprearright': 'SlipRR',
    'wheelslipfrontleft': 'SlipFL', 'wheelslipfrontright': 'SlipFR',
    # Temperatura frenos
    'braketemperaturerearleft': 'BrakeTempRL', 'braketemperaturerearright': 'BrakeTempRR',
    'braketemperaturefrontleft': 'BrakeTempFL', 'braketemperaturefrontright': 'BrakeTempFR',
    # Temperatura gomas (superficie)
    'tyretemperaturerearleft': 'TyreTempRL', 'tyretemperaturerearright': 'TyreTempRR',
    'tyretemperaturefrontleft': 'TyreTempFL', 'tyretemperaturefrontright': 'TyreTempFR',
    # Temperatura carcasa
    'tyrecarcasstemperaturerearleft': 'CarcTempRL', 'tyrecarcasstemperaturerearright': 'CarcTempRR',
    'tyrecarcasstemperaturefrontleft': 'CarcTempFL', 'tyrecarcasstemperaturefrontright': 'CarcTempFR',
    # Temperatura 3 zonas (inner/middle/outer) → para análisis de camber
    'rearleftinside': 'TyreInnerRL', 'rearleftmiddle': 'TyreMiddleRL', 'rearleftoutside': 'TyreOuterRL',
    'rearrightinside': 'TyreInnerRR', 'rearrightmiddle': 'TyreMiddleRR', 'rearrightoutside': 'TyreOuterRR',
    'frontleftinside': 'TyreInnerFL', 'frontleftmiddle': 'TyreMiddleFL', 'frontleftoutside': 'TyreOuterFL',
    'frontrightinside': 'TyreInnerFR', 'frontrightmiddle': 'TyreMiddleFR', 'frontrightoutside': 'TyreOuterFR',
    # Presión gomas (en pista)
    'tyrepressurerearleft': 'TyrePressRL', 'tyrepressurerearright': 'TyrePressRR',
    'tyrepressurefrontleft': 'TyrePressFL', 'tyrepressurefrontright': 'TyrePressFR',
    # Desgaste
    'tyrewearrearleft': 'TyreWearRL', 'tyrewearrearright': 'TyreWearRR',
    'tyrewearfrontleft': 'TyreWearFL', 'tyrewearfrontright': 'TyreWearFR',
    # Suspensión
    'suspensionpositionrearleft': 'SuspPosRL', 'suspensionpositionrearright': 'SuspPosRR',
    'suspensionpositionfrontleft': 'SuspPosFL', 'suspensionpositionfrontright': 'SuspPosFR',
    'suspensionvelocityrearleft': 'SuspVelRL', 'suspensionvelocityrearright': 'SuspVelRR',
    'suspensionvelocityfrontleft': 'SuspVelFL', 'suspensionvelocityfrontright': 'SuspVelFR',
    # Carga en ruedas
    'loadrearleft': 'LoadRL', 'loadrearright': 'LoadRR',
    'loadfrontleft': 'LoadFL', 'loadfrontright': 'LoadFR',
}

# Columnas numéricas a convertir
NUMERIC_COLS = [
    'LapTime', 'LapDistance', 'Speed', 'RPM', 'Throttle', 'Brake', 'Gear', 'Steer',
    'EngineTemp', 'Torque', 'FuelRemaining', 'GLat', 'GLon', 'GVert',
    'WheelSpeedRL', 'WheelSpeedRR', 'WheelSpeedFL', 'WheelSpeedFR',
    'SlipRL', 'SlipRR', 'SlipFL', 'SlipFR',
    'BrakeTempRL', 'BrakeTempRR', 'BrakeTempFL', 'BrakeTempFR',
    'TyreTempRL', 'TyreTempRR', 'TyreTempFL', 'TyreTempFR',
    'CarcTempRL', 'CarcTempRR', 'CarcTempFL', 'CarcTempFR',
    'TyreInnerRL', 'TyreMiddleRL', 'TyreOuterRL',
    'TyreInnerRR', 'TyreMiddleRR', 'TyreOuterRR',
    'TyreInnerFL', 'TyreMiddleFL', 'TyreOuterFL',
    'TyreInnerFR', 'TyreMiddleFR', 'TyreOuterFR',
    'TyrePressRL', 'TyrePressRR', 'TyrePressFL', 'TyrePressFR',
    'TyreWearRL', 'TyreWearRR', 'TyreWearFL', 'TyreWearFR',
    'SuspPosRL', 'SuspPosRR', 'SuspPosFL', 'SuspPosFR',
    'SuspVelRL', 'SuspVelRR', 'SuspVelFL', 'SuspVelFR',
    'LoadRL', 'LoadRR', 'LoadFL', 'LoadFR',
    'RideHeightF', 'RideHeightR',
]


def fmt_time(seconds):
    try:
        s = float(seconds)
        if s <= 0: return "—"
        m = int(s // 60)
        rem = s - m * 60
        return f"{m}:{rem:06.3f}"
    except:
        return str(seconds)


def fmt_delta(seconds):
    try:
        s = float(seconds)
        return "0.000" if s == 0 else (f"+{s:.3f}" if s > 0 else f"{s:.3f}")
    except:
        return str(seconds)


def safe(val, fmt=".1f", fallback="—"):
    try:
        v = float(val)
        if np.isnan(v): return fallback
        return format(v, fmt)
    except:
        return fallback


def col_series(df, col):
    """Retorna serie numérica limpia o None si no existe."""
    if col not in df.columns:
        return None
    s = pd.to_numeric(df[col], errors='coerce').dropna()
    return s if not s.empty else None


def parse_r3e_csv(csv_path):
    """Parsea CSV y retorna dict con meta, setup, s1/s2/s3, lap_time, df."""
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    meta = {}
    setup = {}
    s1 = s2 = s3 = None
    data_start = 7

    # Línea 1-2: game/track/car meta
    for i, line in enumerate(lines[:10]):
        parts = [p.strip() for p in line.strip().split(',')]
        if len(parts) >= 4:
            sim = parts[0].upper().replace(' ', '')
            if any(sim.startswith(s) for s in KNOWN_SIMS):
                meta = {
                    'game':    parts[0],
                    'version': parts[1] if len(parts) > 1 else '',
                    'date':    parts[2] if len(parts) > 2 else '',
                    'track':   parts[3] if len(parts) > 3 else 'Unknown',
                    'car':     parts[4] if len(parts) > 4 else 'Unknown',
                    'event':   parts[5] if len(parts) > 5 else 'Unknown',
                    'laptime': parts[6] if len(parts) > 6 else '0',
                }
                try:
                    s1 = float(parts[7]) if len(parts) > 7 and parts[7] else None
                    s2 = float(parts[8]) if len(parts) > 8 and parts[8] else None
                    s3 = float(parts[9]) if len(parts) > 9 and parts[9] else None
                except:
                    pass
                # Parse track metadata (2 lines after meta)
                try:
                    track_hdr = [p.strip().split('[')[0].strip() for p in lines[i+1].strip().split(',')]
                    track_val = [p.strip() for p in lines[i+2].strip().split(',')]
                    for k, v in zip(track_hdr, track_val):
                        meta[k] = v
                except:
                    pass
                # Parse setup (2 lines after track meta)
                try:
                    setup_hdr = [p.strip() for p in lines[i+3].strip().split(',')]
                    setup_val = [p.strip() for p in lines[i+4].strip().split(',')]
                    for k, v in zip(setup_hdr, setup_val):
                        try:
                            setup[k] = float(v) if v else 0.0
                        except:
                            setup[k] = v
                except:
                    pass
                break

    # Buscar encabezado de telemetría
    for i, line in enumerate(lines):
        stripped = line.strip()
        if 'LapDistance' in stripped and 'LapTime' in stripped and ',' in stripped:
            data_start = i
            break

    # Cargar telemetría
    try:
        df = pd.read_csv(csv_path, skiprows=data_start, low_memory=False)
        df.columns = df.columns.str.strip()

        # Mapear columnas usando COL_MAP global
        col_rename = {}
        for col in df.columns:
            base = col.split('[')[0].strip().lower().replace(' ', '').replace('_', '')
            if base in COL_MAP:
                col_rename[col] = COL_MAP[base]
        df = df.rename(columns=col_rename)

        # Convertir a numérico
        for col in NUMERIC_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
    except Exception as e:
        df = pd.DataFrame()

    # Normalizar campo car
    if meta:
        car_val = meta.get('car', '').strip()
        if not car_val or car_val.lstrip('-').isdigit():
            meta['car'] = 'Dato no disponible en telemetría'

    lap_time = float(meta.get('laptime', 0)) if meta else 0

    return {
        'meta': meta, 'setup': setup,
        'lap_time': lap_time,
        's1': s1, 's2': s2, 's3': s3,
        'df': df, 'path': str(csv_path)
    }


def parse_r3e_timestamp(folder_name):
    try:
        return datetime.strptime(folder_name, '%Y%m%d %H:%M:%S')
    except:
        return None


def find_session_csvs(csv_input, gap_minutes=5):
    p = Path(csv_input)
    if p.is_file():
        for levels in range(1, 5):
            ancestor = p
            for _ in range(levels):
                ancestor = ancestor.parent
            ts = parse_r3e_timestamp(ancestor.name)
            if ts is not None:
                return _group_by_session(ancestor.parent, ts, gap_minutes)
        return [p]
    elif p.is_dir():
        ts = parse_r3e_timestamp(p.name)
        if ts is not None:
            return _group_by_session(p.parent, ts, gap_minutes)
        subdirs = [d for d in p.iterdir() if d.is_dir() and parse_r3e_timestamp(d.name)]
        if subdirs:
            subdirs.sort(key=lambda d: parse_r3e_timestamp(d.name))
            latest_ts = parse_r3e_timestamp(subdirs[-1].name)
            return _group_by_session(p, latest_ts, gap_minutes)
        flat_csvs = [f for f in p.iterdir() if f.is_file() and f.suffix == '.csv' and f.stat().st_size > 1000]
        if flat_csvs:
            flat_csvs.sort(key=lambda f: f.stat().st_mtime)
            ref_mtime = flat_csvs[-1].stat().st_mtime
            return _group_flat_by_session(flat_csvs, ref_mtime, gap_minutes)
        return sorted(p.rglob('*.csv'))
    else:
        csvs = sorted(glob.glob(str(csv_input)))
        return [Path(c) for c in csvs]


def _group_by_session(root_dir, ref_ts, gap_minutes):
    gap = gap_minutes * 60
    all_ts_dirs = []
    for d in Path(root_dir).iterdir():
        if d.is_dir():
            ts = parse_r3e_timestamp(d.name)
            if ts is not None:
                all_ts_dirs.append((ts, d))
    all_ts_dirs.sort(key=lambda x: x[0])
    ref_idx = next((i for i, (ts, _) in enumerate(all_ts_dirs) if ts == ref_ts), None)
    if ref_idx is None:
        return sorted(Path(root_dir).rglob('*.csv'))
    session_dirs = [all_ts_dirs[ref_idx][1]]
    for i in range(ref_idx - 1, -1, -1):
        if (all_ts_dirs[i+1][0] - all_ts_dirs[i][0]).total_seconds() <= gap:
            session_dirs.append(all_ts_dirs[i][1])
        else:
            break
    for i in range(ref_idx + 1, len(all_ts_dirs)):
        if (all_ts_dirs[i][0] - all_ts_dirs[i-1][0]).total_seconds() <= gap:
            session_dirs.append(all_ts_dirs[i][1])
        else:
            break
    csvs = []
    for d in session_dirs:
        csvs.extend(d.rglob('*.csv'))
    return sorted(csvs)


def _group_flat_by_session(csv_files, ref_mtime, gap_minutes):
    gap = gap_minutes * 60
    files_with_mtime = [(f, f.stat().st_mtime) for f in csv_files if f.stat().st_size > 1000]
    files_with_mtime.sort(key=lambda x: x[1])
    ref_idx = min(range(len(files_with_mtime)),
                  key=lambda i: abs(files_with_mtime[i][1] - ref_mtime))
    session = [files_with_mtime[ref_idx][0]]
    for i in range(ref_idx - 1, -1, -1):
        if files_with_mtime[i+1][1] - files_with_mtime[i][1] <= gap:
            session.append(files_with_mtime[i][0])
        else:
            break
    for i in range(ref_idx + 1, len(files_with_mtime)):
        if files_with_mtime[i][1] - files_with_mtime[i-1][1] <= gap:
            session.append(files_with_mtime[i][0])
        else:
            break
    return sorted(session)


def _corner_stats(df, cols):
    """Calcula avg/max para una lista de columnas. Retorna dict col→{avg,max}."""
    result = {}
    for col in cols:
        s = col_series(df, col)
        if s is not None and len(s) > 10:
            # Filter out warmup zeros (first 5% of lap)
            s_filtered = s[s > 0]
            if not s_filtered.empty:
                result[col] = {'avg': float(s_filtered.mean()), 'max': float(s_filtered.max())}
    return result


def _camber_diagnosis(inner_avg, outer_avg):
    """Diagnóstico de camber por diferencia inner/outer."""
    if inner_avg is None or outer_avg is None:
        return None
    diff = inner_avg - outer_avg
    if diff > 20:
        return f"⚠ Exceso camber negativo ({diff:.0f}°C inner-outer)"
    elif diff < -15:
        return f"⚠ Camber insuficiente ({abs(diff):.0f}°C outer-inner)"
    else:
        return "✓ Distribución aceptable"


def analyze_telemetry(laps_data):
    """Análisis completo de toda la telemetría disponible."""
    insights = {
        'braking': [], 'early_lift_zones': [],
        'max_speed': 0, 'avg_throttle': 0,
        'tyres': {}, 'brakes': {}, 'gforces': {},
        'suspension': {}, 'fuel': {}, 'engine': {},
        'wheel_slip': {}, 'tyre_zones': {},
    }

    best_lap = min(laps_data, key=lambda x: x['lap_time']) if laps_data else None
    if not best_lap or best_lap['df'].empty:
        return insights

    df = best_lap['df']

    # ── Velocidad ──────────────────────────────────────────────────────────
    spd = col_series(df, 'Speed')
    if spd is not None:
        insights['max_speed'] = round(float(spd.max()), 1)
        insights['avg_speed'] = round(float(spd.mean()), 1)

    # ── Throttle/Brake ─────────────────────────────────────────────────────
    thr = col_series(df, 'Throttle')
    if thr is not None:
        insights['avg_throttle'] = round(float(thr.mean()), 1)
        insights['full_throttle_pct'] = round(float((thr > 95).mean() * 100), 1)
        dist = df['LapDistance'].values if 'LapDistance' in df.columns else np.arange(len(df))
        t_vals = thr.reindex(df.index).fillna(0).values
        for i in range(20, len(t_vals) - 20):
            if t_vals[i] < 20 and t_vals[i-10] < 30 and t_vals[i+15] > 70:
                d = dist[i] if i < len(dist) else i
                insights['early_lift_zones'].append(round(float(d), 0))
                if len(insights['early_lift_zones']) >= 3:
                    break

    brk = col_series(df, 'Brake')
    if brk is not None:
        spd_arr = col_series(df, 'Speed')
        dist = df['LapDistance'].values if 'LapDistance' in df.columns else np.arange(len(df))
        brake_arr = brk.reindex(df.index).fillna(0).values
        in_brake = False
        for i in range(5, len(brake_arr) - 5):
            if brake_arr[i] > 85 and not in_brake:
                in_brake = True
                d = float(dist[i]) if i < len(dist) else i
                spd_val = float(spd_arr.iloc[i]) if spd_arr is not None and i < len(spd_arr) else 0
                insights['braking'].append({'dist': round(d, 0), 'speed': round(spd_val, 1),
                                            'intensity': round(float(brake_arr[i]), 1)})
                if len(insights['braking']) >= 5:
                    break
            elif brake_arr[i] < 10:
                in_brake = False

    # ── G-Forces ───────────────────────────────────────────────────────────
    glat = col_series(df, 'GLat')
    glon = col_series(df, 'GLon')
    gvert = col_series(df, 'GVert')
    if glat is not None:
        insights['gforces']['lat_max_left']  = round(float(glat.max()), 2)
        insights['gforces']['lat_max_right'] = round(float(abs(glat.min())), 2)
        insights['gforces']['lat_avg']       = round(float(glat.abs().mean()), 2)
    if glon is not None:
        insights['gforces']['lon_max_brake'] = round(float(abs(glon.min())), 2)
        insights['gforces']['lon_max_acc']   = round(float(glon.max()), 2)
    if gvert is not None:
        insights['gforces']['vert_max']      = round(float(gvert.abs().max()), 2)
        insights['gforces']['vert_avg']      = round(float(gvert.abs().mean()), 2)

    # ── Gomas: Temperatura superficial ────────────────────────────────────
    for corner, col in [('FL', 'TyreTempFL'), ('FR', 'TyreTempFR'),
                         ('RL', 'TyreTempRL'), ('RR', 'TyreTempRR')]:
        s = col_series(df, col)
        if s is not None:
            hot = s[s > 40]
            if not hot.empty:
                insights['tyres'][corner] = {
                    'avg': round(float(hot.mean()), 1),
                    'max': round(float(hot.max()), 1),
                    'min': round(float(hot.min()), 1),
                }

    # ── Gomas: Temperatura 3 zonas (camber analysis) ───────────────────────
    for corner, cols in [
        ('FL', ('TyreInnerFL', 'TyreMiddleFL', 'TyreOuterFL')),
        ('FR', ('TyreInnerFR', 'TyreMiddleFR', 'TyreOuterFR')),
        ('RL', ('TyreInnerRL', 'TyreMiddleRL', 'TyreOuterRL')),
        ('RR', ('TyreInnerRR', 'TyreMiddleRR', 'TyreOuterRR')),
    ]:
        inner_s = col_series(df, cols[0])
        mid_s   = col_series(df, cols[1])
        outer_s = col_series(df, cols[2])
        zone_data = {}
        inner_avg = outer_avg = None
        if inner_s is not None:
            hot = inner_s[inner_s > 40]
            if not hot.empty:
                inner_avg = float(hot.mean())
                zone_data['inner'] = round(inner_avg, 1)
        if mid_s is not None:
            hot = mid_s[mid_s > 40]
            if not hot.empty:
                zone_data['mid'] = round(float(hot.mean()), 1)
        if outer_s is not None:
            hot = outer_s[outer_s > 40]
            if not hot.empty:
                outer_avg = float(hot.mean())
                zone_data['outer'] = round(outer_avg, 1)
        if zone_data:
            zone_data['diagnosis'] = _camber_diagnosis(inner_avg, outer_avg)
            insights['tyre_zones'][corner] = zone_data

    # ── Gomas: Presión en pista ────────────────────────────────────────────
    for corner, col in [('FL', 'TyrePressFL'), ('FR', 'TyrePressFR'),
                         ('RL', 'TyrePressRL'), ('RR', 'TyrePressRR')]:
        s = col_series(df, col)
        if s is not None:
            hot = s[s > 1]
            if not hot.empty:
                td = insights['tyres'].setdefault(corner, {})
                td['press_avg'] = round(float(hot.mean()), 1)
                td['press_max'] = round(float(hot.max()), 1)
                td['press_min'] = round(float(hot.min()), 1)

    # ── Gomas: Desgaste ────────────────────────────────────────────────────
    for corner, col in [('FL', 'TyreWearFL'), ('FR', 'TyreWearFR'),
                         ('RL', 'TyreWearRL'), ('RR', 'TyreWearRR')]:
        s = col_series(df, col)
        if s is not None and len(s) > 10:
            td = insights['tyres'].setdefault(corner, {})
            td['wear_end'] = round(float(s.iloc[-1]), 2)
            td['wear_start'] = round(float(s.iloc[0]), 2)
            td['wear_delta'] = round(float(s.iloc[-1] - s.iloc[0]), 2)

    # ── Gomas: Wheel slip ──────────────────────────────────────────────────
    for corner, col in [('FL', 'SlipFL'), ('FR', 'SlipFR'),
                         ('RL', 'SlipRL'), ('RR', 'SlipRR')]:
        s = col_series(df, col)
        if s is not None:
            td = insights['tyres'].setdefault(corner, {})
            abs_slip = s.abs()
            td['slip_avg'] = round(float(abs_slip.mean()), 2)
            td['slip_max'] = round(float(abs_slip.max()), 2)

    # ── Frenos: Temperatura ────────────────────────────────────────────────
    for corner, col in [('FL', 'BrakeTempFL'), ('FR', 'BrakeTempFR'),
                         ('RL', 'BrakeTempRL'), ('RR', 'BrakeTempRR')]:
        s = col_series(df, col)
        if s is not None:
            hot = s[s > 50]
            if not hot.empty:
                insights['brakes'][corner] = {
                    'avg': round(float(hot.mean()), 0),
                    'max': round(float(hot.max()), 0),
                }

    # ── Suspensión ─────────────────────────────────────────────────────────
    for corner, col in [('FL', 'SuspPosFL'), ('FR', 'SuspPosFR'),
                         ('RL', 'SuspPosRL'), ('RR', 'SuspPosRR')]:
        s = col_series(df, col)
        if s is not None and len(s) > 10:
            insights['suspension'][corner] = {
                'avg': round(float(s.mean()) * 1000, 1),   # mm
                'max': round(float(s.max()) * 1000, 1),
                'min': round(float(s.min()) * 1000, 1),
                'range': round((float(s.max()) - float(s.min())) * 1000, 1),
            }

    # ── Motor y combustible ────────────────────────────────────────────────
    rpm_s = col_series(df, 'RPM')
    if rpm_s is not None:
        insights['engine']['rpm_max'] = round(float(rpm_s.max()), 0)
        insights['engine']['rpm_avg'] = round(float(rpm_s.mean()), 0)
    torque_s = col_series(df, 'Torque')
    if torque_s is not None:
        tq = torque_s[torque_s > 0]
        if not tq.empty:
            insights['engine']['torque_max'] = round(float(tq.max()), 0)
            insights['engine']['torque_avg'] = round(float(tq.mean()), 0)
    etemp_s = col_series(df, 'EngineTemp')
    if etemp_s is not None:
        insights['engine']['temp_max'] = round(float(etemp_s.max()), 0)
        insights['engine']['temp_avg'] = round(float(etemp_s.mean()), 0)

    fuel_s = col_series(df, 'FuelRemaining')
    if fuel_s is not None and len(fuel_s) > 10:
        insights['fuel']['start'] = round(float(fuel_s.iloc[0]), 2)
        insights['fuel']['end']   = round(float(fuel_s.iloc[-1]), 2)
        insights['fuel']['used']  = round(float(fuel_s.iloc[0] - fuel_s.iloc[-1]), 2)

    return insights


def consistency_score(times):
    if len(times) < 2:
        return 100.0, 0.0
    std = float(np.std(times))
    score = max(0, 100 - (std / 3.0 * 100))
    return round(score, 1), round(std, 3)


def lap_state(idx, lap_time, best_time, prev_time):
    if abs(lap_time - best_time) < 0.001:
        return "✓ MEJOR VUELTA"
    if idx == 0:
        return "✗ CALENTAMIENTO"
    if prev_time is not None and lap_time < prev_time:
        return "▲ MEJORANDO"
    return "✓ VÁLIDA"


def _hdr_style(bg=None):
    bg = bg or BGHEAD
    return [
        ('BACKGROUND', (0, 0), (-1, 0), bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BGROW]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]


def _cell_color(val, thresholds, colors_list):
    """Retorna color de celda según umbrales."""
    try:
        v = float(val)
        for thr, col in zip(thresholds, colors_list):
            if v >= thr:
                return col
    except:
        pass
    return colors.white


def generate_pdf(laps_data, pilot_name, pilot_id, session_type, session_num, output_path):
    if not laps_data:
        print("Error: no hay datos de vueltas")
        return None

    valid_laps = [l for l in laps_data if l['lap_time'] > 0]
    valid_laps.sort(key=lambda x: x['lap_time'])
    best_lap = valid_laps[0]
    best_time = best_lap['lap_time']
    chrono_laps = sorted(laps_data, key=lambda x: x.get('meta', {}).get('date', ''))

    all_times = [l['lap_time'] for l in valid_laps]
    worst_time = max(all_times)
    avg_time = np.mean(all_times)
    score, std = consistency_score(all_times)
    meta = best_lap['meta']
    setup = best_lap.get('setup', {})
    ins = analyze_telemetry(valid_laps)

    doc = SimpleDocTemplate(str(output_path), pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)

    styles = getSampleStyleSheet()
    s_title  = ParagraphStyle('T',  parent=styles['Normal'], fontSize=26, textColor=RED,
                              alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=4)
    s_best_l = ParagraphStyle('BL', parent=styles['Normal'], fontSize=12, textColor=DARK,
                              alignment=TA_CENTER, fontName='Helvetica-Bold', spaceBefore=16)
    s_best_t = ParagraphStyle('BT', parent=styles['Normal'], fontSize=36, textColor=GREEN,
                              alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=24)
    s_sec    = ParagraphStyle('S',  parent=styles['Normal'], fontSize=12, textColor=DARK,
                              fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6)
    s_body   = ParagraphStyle('B',  parent=styles['Normal'], fontSize=9, textColor=DARK,
                              leading=13, spaceAfter=3)
    s_bold   = ParagraphStyle('Bo', parent=styles['Normal'], fontSize=9, textColor=DARK,
                              fontName='Helvetica-Bold', spaceAfter=2)
    s_score  = ParagraphStyle('Sc', parent=styles['Normal'], fontSize=15,
                              textColor=GREEN if score >= 70 else ORANGE,
                              fontName='Helvetica-Bold', spaceAfter=4)

    content = []

    # ═══ PORTADA ═══════════════════════════════════════════════════════════
    content.append(Paragraph("REPORTE DE TELEMETRÍA", s_title))
    content.append(HRFlowable(width="100%", thickness=2, color=RED))
    content.append(Spacer(1, 0.3*cm))

    pt = Table([
        ['Piloto:', pilot_name],
        ['Simulador:', meta.get('game', 'Unknown')],
        ['Pista:', meta.get('track', 'Unknown')],
        ['Auto:', meta.get('car', 'Unknown')],
        ['Evento:', meta.get('event', 'Unknown')],
        ['Sesión:', f"{session_type} — S{session_num}"],
        ['Fecha:', meta.get('date', '')],
        ['Vueltas:', str(len(chrono_laps))],
        ['Compuesto:', meta.get('Tyre', meta.get('tyre', '—'))],
    ], colWidths=[3.5*cm, 11*cm])
    pt.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, BGROW]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    content.append(pt)
    content.append(Paragraph("MEJOR TIEMPO", s_best_l))
    content.append(Paragraph(fmt_time(best_time), s_best_t))
    content.append(PageBreak())

    # ═══ 1. RESUMEN DE SESIÓN ══════════════════════════════════════════════
    content.append(Paragraph("1. RESUMEN DE SESIÓN", s_sec))
    content.append(HRFlowable(width="100%", thickness=1, color=RED))
    content.append(Spacer(1, 0.2*cm))

    s1_str = fmt_time(best_lap['s1']) if best_lap.get('s1') else "No disponible"
    s2_str = fmt_time(best_lap['s2']) if best_lap.get('s2') else "No disponible"
    s3_str = fmt_time(best_lap['s3']) if best_lap.get('s3') else "No disponible"

    rt_data = [
        ['Métrica', 'Valor'],
        ['Total de vueltas', str(len(chrono_laps))],
        ['Mejor vuelta', fmt_time(best_time)],
        ['Peor vuelta', fmt_time(worst_time)],
        ['Promedio', fmt_time(avg_time)],
        ['Sector 1 (mejor vuelta)', s1_str],
        ['Sector 2 (mejor vuelta)', s2_str],
        ['Sector 3 (mejor vuelta)', s3_str],
        ['Velocidad máxima', f"{ins['max_speed']} km/h" if ins.get('max_speed') else "—"],
        ['Throttle promedio', f"{ins['avg_throttle']}%" if ins.get('avg_throttle') else "—"],
        ['A fondo (>95%)', f"{ins.get('full_throttle_pct', '—')}% del tiempo"],
    ]

    # Agregar sector teórico si hay datos
    if all(lap.get('s1') for lap in chrono_laps) and len(chrono_laps) > 1:
        bS1 = min(l['s1'] for l in chrono_laps if l.get('s1'))
        bS2 = min(l['s2'] for l in chrono_laps if l.get('s2'))
        bS3 = min(l['s3'] for l in chrono_laps if l.get('s3'))
        teorico = bS1 + bS2 + bS3
        diff = best_time - teorico
        rt_data.append(['Tiempo teórico óptimo', f"{fmt_time(teorico)} (−{diff:.3f}s potencial)"])

    if ins.get('fuel'):
        rt_data.append(['Combustible usado', f"{ins['fuel'].get('used', '—')} l/vuelta aprox."])
    if ins.get('engine'):
        e = ins['engine']
        if e.get('rpm_max'):
            rt_data.append(['RPM máximo', f"{e['rpm_max']:.0f} rpm"])
        if e.get('torque_max'):
            rt_data.append(['Torque máximo', f"{e['torque_max']:.0f} Nm"])

    rt = Table(rt_data, colWidths=[8*cm, 6.5*cm])
    rt.setStyle(TableStyle(_hdr_style()))
    content.append(rt)
    content.append(Spacer(1, 0.4*cm))

    # ═══ 2. TIEMPOS POR VUELTA ════════════════════════════════════════════
    content.append(Paragraph("2. TIEMPOS POR VUELTA", s_sec))
    content.append(HRFlowable(width="100%", thickness=1, color=RED))
    content.append(Spacer(1, 0.2*cm))

    # Mejores sectores de la sesión (estilo F1 — morado)
    best_s1 = min((l['s1'] for l in chrono_laps if l.get('s1')), default=None)
    best_s2 = min((l['s2'] for l in chrono_laps if l.get('s2')), default=None)
    best_s3 = min((l['s3'] for l in chrono_laps if l.get('s3')), default=None)
    worst_lap_t = max(all_times)

    lap_rows = [['Vuelta', 'Tiempo', 'S1', 'S2', 'S3', 'Delta', 'Estado']]
    lt_style = _hdr_style(BGBLUE)

    prev_time = None
    for i, lap in enumerate(chrono_laps):
        t = lap['lap_time']
        delta = t - best_time
        state = lap_state(i, t, best_time, prev_time)
        s1d = fmt_time(lap['s1']) if lap.get('s1') else "—"
        s2d = fmt_time(lap['s2']) if lap.get('s2') else "—"
        s3d = fmt_time(lap['s3']) if lap.get('s3') else "—"
        lap_rows.append([str(i+1), fmt_time(t), s1d, s2d, s3d, fmt_delta(delta), state])
        row = i + 1

        # Mejor vuelta: verde
        if abs(t - best_time) < 0.001:
            lt_style.append(('BACKGROUND', (0, row), (1, row), C_LAP_BEST))
            lt_style.append(('BACKGROUND', (5, row), (6, row), C_LAP_BEST))
            lt_style.append(('FONTNAME',   (0, row), (-1, row), 'Helvetica-Bold'))
        # Peor vuelta: rojo suave (solo si hay >2 vueltas)
        elif len(all_times) > 2 and abs(t - worst_lap_t) < 0.001:
            lt_style.append(('BACKGROUND', (0, row), (1, row), C_LAP_SLOW))

        # Delta: colorear columna 5
        lt_style.append(('BACKGROUND', (5, row), (5, row), delta_color(delta)))

        # Mejor sector S1 → morado F1
        if lap.get('s1') and best_s1 and abs(lap['s1'] - best_s1) < 0.001:
            lt_style.append(('BACKGROUND', (2, row), (2, row), C_SECTOR_BEST))
            lt_style.append(('TEXTCOLOR',  (2, row), (2, row), colors.white))
            lt_style.append(('FONTNAME',   (2, row), (2, row), 'Helvetica-Bold'))
        # Mejor sector S2 → morado F1
        if lap.get('s2') and best_s2 and abs(lap['s2'] - best_s2) < 0.001:
            lt_style.append(('BACKGROUND', (3, row), (3, row), C_SECTOR_BEST))
            lt_style.append(('TEXTCOLOR',  (3, row), (3, row), colors.white))
            lt_style.append(('FONTNAME',   (3, row), (3, row), 'Helvetica-Bold'))
        # Mejor sector S3 → morado F1
        if lap.get('s3') and best_s3 and abs(lap['s3'] - best_s3) < 0.001:
            lt_style.append(('BACKGROUND', (4, row), (4, row), C_SECTOR_BEST))
            lt_style.append(('TEXTCOLOR',  (4, row), (4, row), colors.white))
            lt_style.append(('FONTNAME',   (4, row), (4, row), 'Helvetica-Bold'))

        prev_time = t

    lt = Table(lap_rows, colWidths=[1.5*cm, 2.6*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.4*cm, 3.1*cm])
    lt.setStyle(TableStyle(lt_style))
    content.append(lt)

    # Leyenda
    legend_data = [['■ Mejor vuelta', '■ Mejor sector (F1)', '■ Delta positivo', '■ Peor vuelta']]
    leg = Table(legend_data, colWidths=[3.8*cm, 3.8*cm, 3.8*cm, 3.8*cm])
    leg.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), C_LAP_BEST),
        ('BACKGROUND', (1,0), (1,0), C_SECTOR_BEST),
        ('TEXTCOLOR',  (1,0), (1,0), colors.white),
        ('BACKGROUND', (2,0), (2,0), C_DELTA_POS),
        ('BACKGROUND', (3,0), (3,0), C_LAP_SLOW),
        ('FONTSIZE',   (0,0), (-1,-1), 7),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    content.append(Spacer(1, 0.1*cm))
    content.append(leg)
    content.append(Spacer(1, 0.4*cm))

    # ═══ 3. CONSISTENCY SCORE ════════════════════════════════════════════
    content.append(Paragraph("3. CONSISTENCY SCORE", s_sec))
    content.append(HRFlowable(width="100%", thickness=1, color=RED))
    content.append(Spacer(1, 0.2*cm))

    score_label = ("Muy consistente" if score >= 90 else
                   "Consistencia aceptable" if score >= 70 else
                   "Inconsistente" if score >= 50 else "Muy inconsistente")
    content.append(Paragraph(f"{score} / 100 — {score_label}", s_score))
    content.append(Paragraph(f"Desviación estándar: {std:.3f}s entre vueltas", s_body))

    if len(chrono_laps) < 2:
        interp = "Una sola vuelta — score no representativo. Se necesitan ≥2 vueltas."
    elif score >= 70:
        interp = "Buena repetibilidad. El margen restante está en la línea sector a sector."
    else:
        best_idx = chrono_laps.index(best_lap) + 1
        interp = f"Variabilidad alta ({std:.3f}s). Enfocarse en repetir la línea de vuelta {best_idx}."
    content.append(Paragraph(f"<b>Interpretación:</b> {interp}", s_body))
    content.append(PageBreak())

    # ═══ 4. ANÁLISIS DE GOMAS ════════════════════════════════════════════
    content.append(Paragraph("4. ANÁLISIS DE GOMAS", s_sec))
    content.append(HRFlowable(width="100%", thickness=1, color=RED))
    content.append(Spacer(1, 0.2*cm))

    tyres = ins.get('tyres', {})
    zones = ins.get('tyre_zones', {})
    tyre_corners = ['FL', 'FR', 'RL', 'RR']
    tyre_labels  = ['Delantera Izq', 'Delantera Der', 'Trasera Izq', 'Trasera Der']

    if tyres:
        # Tabla de gomas: una fila por métrica, una columna por esquina → coloreado celda a celda
        tw_rows = [['Métrica', 'FL', 'FR', 'RL', 'RR']]
        tw_style = _hdr_style(BGBLUE)

        # Filas de temperatura avg y max
        for metric_key, label_txt in [('avg', 'Temp promedio (°C)'), ('max', 'Temp máx (°C)'),
                                       ('min', 'Temp mín (°C)')]:
            vals = [tyres.get(c, {}).get(metric_key) for c in tyre_corners]
            if any(v is not None for v in vals):
                row_idx = len(tw_rows)
                tw_rows.append([label_txt] + [safe(v, '.0f') for v in vals])
                for ci, v in enumerate(vals, 1):
                    if v is not None:
                        tw_style.append(('BACKGROUND', (ci, row_idx), (ci, row_idx), tyre_temp_color(v)))

        # Presión avg
        vals_p = [tyres.get(c, {}).get('press_avg') for c in tyre_corners]
        if any(v is not None for v in vals_p):
            row_idx = len(tw_rows)
            tw_rows.append(['Presión promedio (PSI)'] + [safe(v, '.1f') for v in vals_p])
            for ci, v in enumerate(vals_p, 1):
                if v is not None:
                    tw_style.append(('BACKGROUND', (ci, row_idx), (ci, row_idx), press_color(v)))

        # Presión max
        vals_pm = [tyres.get(c, {}).get('press_max') for c in tyre_corners]
        if any(v is not None for v in vals_pm):
            row_idx = len(tw_rows)
            tw_rows.append(['Presión máx (PSI)'] + [safe(v, '.1f') for v in vals_pm])
            for ci, v in enumerate(vals_pm, 1):
                if v is not None:
                    tw_style.append(('BACKGROUND', (ci, row_idx), (ci, row_idx), press_color(v)))

        # Desgaste Δ%
        vals_w = [tyres.get(c, {}).get('wear_delta') for c in tyre_corners]
        if any(v is not None for v in vals_w):
            row_idx = len(tw_rows)
            tw_rows.append(['Desgaste Δ (%)'] + [safe(v, '.2f') for v in vals_w])
            for ci, v in enumerate(vals_w, 1):
                if v is not None:
                    tw_style.append(('BACKGROUND', (ci, row_idx), (ci, row_idx), wear_color(abs(v))))

        # Slip máximo
        vals_s = [tyres.get(c, {}).get('slip_max') for c in tyre_corners]
        if any(v is not None for v in vals_s):
            row_idx = len(tw_rows)
            tw_rows.append(['Slip máximo (%)'] + [safe(v, '.1f') for v in vals_s])
            for ci, v in enumerate(vals_s, 1):
                if v is not None:
                    tw_style.append(('BACKGROUND', (ci, row_idx), (ci, row_idx), slip_color(v)))

        tw = Table(tw_rows, colWidths=[4.0*cm, 3.2*cm, 3.2*cm, 3.2*cm, 3.2*cm])
        tw.setStyle(TableStyle(tw_style))
        content.append(tw)

        # Leyenda temperatura
        tleg_data = [['■ Muy fría (<50°C)', '■ Calentando (50-75°C)', '■ Óptima (75-105°C)',
                      '■ Caliente (105-120°C)', '■ Crítica (>120°C)']]
        tleg = Table(tleg_data, colWidths=[3.2*cm, 3.6*cm, 3.2*cm, 3.5*cm, 3.0*cm])
        tleg.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), C_TYRE_COLD),
            ('BACKGROUND', (1,0), (1,0), C_TYRE_WARM),
            ('BACKGROUND', (2,0), (2,0), C_TYRE_OK),
            ('BACKGROUND', (3,0), (3,0), C_TYRE_HOT),
            ('BACKGROUND', (4,0), (4,0), C_TYRE_CRIT),
            ('FONTSIZE',   (0,0), (-1,-1), 6),
            ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        content.append(Spacer(1, 0.1*cm))
        content.append(tleg)
        content.append(Spacer(1, 0.3*cm))
    else:
        content.append(Paragraph("Datos de temperatura de gomas no disponibles en este CSV.", s_body))

    # Tabla 3 zonas (camber analysis) — coloreado relativo inner vs outer
    if zones:
        content.append(Paragraph("Distribución de temperatura por zona (diagnóstico de camber):", s_bold))
        zone_hdr = ['Goma', 'Inner (°C)', 'Middle (°C)', 'Outer (°C)', 'Diagnóstico']
        zone_data = [zone_hdr]
        zone_style = _hdr_style(BGBLUE)
        for ri, (corner, label) in enumerate(zip(tyre_corners, tyre_labels), 1):
            z = zones.get(corner, {})
            if z:
                inner = z.get('inner')
                mid   = z.get('mid')
                outer = z.get('outer')
                zone_data.append([
                    label,
                    safe(inner, '.0f'),
                    safe(mid,   '.0f'),
                    safe(outer, '.0f'),
                    z.get('diagnosis', '—'),
                ])
                # Color cada zona según temperatura de goma
                for ci, v in [(1, inner), (2, mid), (3, outer)]:
                    if v is not None:
                        zone_style.append(('BACKGROUND', (ci, ri), (ci, ri), tyre_temp_color(v)))
                # Si hay desequilibrio pronunciado, marcar diagnóstico
                if inner and outer:
                    if abs(inner - outer) > 15:
                        zone_style.append(('BACKGROUND', (4, ri), (4, ri), C_TYRE_HOT))
        if len(zone_data) > 1:
            zt = Table(zone_data, colWidths=[3.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 5.2*cm])
            zt.setStyle(TableStyle(zone_style))
            content.append(zt)
        content.append(Spacer(1, 0.3*cm))

    # Interpretación de gomas
    tyre_notes = []
    for corner, label in zip(tyre_corners, tyre_labels):
        z = zones.get(corner, {})
        avg_t = tyres.get(corner, {}).get('avg')
        diag = z.get('diagnosis', '') if z else ''
        if avg_t and avg_t > 115:
            tyre_notes.append(f"• {label}: sobrecalentamiento ({avg_t:.0f}°C) — riesgo de ampollas. Reducir presión de freno o ajustar camber.")
        elif avg_t and avg_t < 55:
            tyre_notes.append(f"• {label}: temperatura baja ({avg_t:.0f}°C) — goma sin calentar. Aumentar agresividad en warmup.")
        if diag and '⚠' in diag:
            tyre_notes.append(f"• {label}: {diag}")
        slip_m = tyres.get(corner, {}).get('slip_max')
        if slip_m and slip_m > 8:
            tyre_notes.append(f"• {label}: slip elevado (max {slip_m:.1f}%) — pérdida de agarre importante detectada.")

    if tyre_notes:
        content.append(Paragraph("<b>Hallazgos:</b>", s_bold))
        for note in tyre_notes:
            content.append(Paragraph(note, s_body))
    elif tyres:
        content.append(Paragraph("Gomas operando dentro de rangos normales.", s_body))
    content.append(PageBreak())

    # ═══ 5. ANÁLISIS DE FRENOS ═══════════════════════════════════════════
    content.append(Paragraph("5. ANÁLISIS DE FRENOS", s_sec))
    content.append(HRFlowable(width="100%", thickness=1, color=RED))
    content.append(Spacer(1, 0.2*cm))

    brakes = ins.get('brakes', {})
    if brakes:
        bt_rows  = [['Métrica', 'FL', 'FR', 'RL', 'RR']]
        bt_style = _hdr_style(BGBLUE)

        for metric_key, label_txt in [('avg', 'Temp promedio (°C)'), ('max', 'Temp máxima (°C)')]:
            vals = [brakes.get(c, {}).get(metric_key) for c in tyre_corners]
            if any(v is not None for v in vals):
                row_idx = len(bt_rows)
                bt_rows.append([label_txt] + [safe(v, '.0f') for v in vals])
                for ci, v in enumerate(vals, 1):
                    if v is not None:
                        bt_style.append(('BACKGROUND', (ci, row_idx), (ci, row_idx), brake_temp_color(v)))

        bt = Table(bt_rows, colWidths=[4.0*cm, 3.2*cm, 3.2*cm, 3.2*cm, 3.2*cm])
        bt.setStyle(TableStyle(bt_style))
        content.append(bt)

        # Leyenda frenos
        bleg_data = [['■ Fría (<200°C)', '■ Óptima (200-550°C)', '■ Caliente (550-720°C)', '■ Crítica (>720°C)']]
        bleg = Table(bleg_data, colWidths=[3.8*cm, 4.2*cm, 4.2*cm, 4.0*cm])
        bleg.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), C_BRAKE_COLD),
            ('BACKGROUND', (1,0), (1,0), C_BRAKE_OK),
            ('BACKGROUND', (2,0), (2,0), C_BRAKE_HOT),
            ('BACKGROUND', (3,0), (3,0), C_BRAKE_CRIT),
            ('FONTSIZE',   (0,0), (-1,-1), 6),
            ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        content.append(Spacer(1, 0.1*cm))
        content.append(bleg)
        content.append(Spacer(1, 0.3*cm))

        # Análisis de balance de frenos
        brake_notes = []
        fl_avg = brakes.get('FL', {}).get('avg')
        fr_avg = brakes.get('FR', {}).get('avg')
        rl_avg = brakes.get('RL', {}).get('avg')
        rr_avg = brakes.get('RR', {}).get('avg')

        if fl_avg and rl_avg:
            front_avg = (fl_avg + (fr_avg or fl_avg)) / 2
            rear_avg  = (rl_avg + (rr_avg or rl_avg)) / 2
            if front_avg > rear_avg * 1.4:
                brake_notes.append(f"• Frenos delanteros mucho más calientes que traseros ({front_avg:.0f}°C vs {rear_avg:.0f}°C) — considera mover brake bias hacia atrás.")
            elif rear_avg > front_avg * 1.3:
                brake_notes.append(f"• Frenos traseros más calientes ({rear_avg:.0f}°C vs {front_avg:.0f}°C) — considera mover brake bias hacia adelante.")
            else:
                brake_notes.append(f"• Balance delantero/trasero aceptable ({front_avg:.0f}°C F / {rear_avg:.0f}°C R).")

        if fl_avg and fr_avg and abs(fl_avg - fr_avg) > 80:
            brake_notes.append(f"• Asimetría lateral delantera ({fl_avg:.0f}°C FL vs {fr_avg:.0f}°C FR) — revisar pastillas o conducto de frío.")

        for corner, label in zip(tyre_corners, tyre_labels):
            mx = brakes.get(corner, {}).get('max')
            if mx and mx > 800:
                brake_notes.append(f"• {label}: temperatura máxima crítica ({mx:.0f}°C) — riesgo de fade y ebullición del líquido.")

        for note in brake_notes:
            content.append(Paragraph(note, s_body))
    else:
        content.append(Paragraph("Datos de temperatura de frenos no disponibles en este CSV.", s_body))

    content.append(Spacer(1, 0.4*cm))

    # ═══ 6. G-FORCES Y DINÁMICA ═══════════════════════════════════════════
    content.append(Paragraph("6. G-FORCES Y DINÁMICA DEL VEHÍCULO", s_sec))
    content.append(HRFlowable(width="100%", thickness=1, color=RED))
    content.append(Spacer(1, 0.2*cm))

    gf = ins.get('gforces', {})
    susp = ins.get('suspension', {})

    def gforce_color(val, med=2.0, high=3.5):
        try:
            v = float(val)
            if v >= high: return C_BRAKE_CRIT   # rojo — muy alto
            if v >= med:  return C_GFORCE_HIGH   # naranja — alto
            return C_SLIP_OK                      # verde — normal
        except: return colors.white

    if gf:
        gf_rows_data = [
            ('G lateral máx izquierda',  gf.get('lat_max_left'),  2.0, 3.5,
             'Carga alta en curvas izq.' if gf.get('lat_max_left', 0) > 3 else 'Normal'),
            ('G lateral máx derecha',    gf.get('lat_max_right'), 2.0, 3.5,
             'Carga alta en curvas der.' if gf.get('lat_max_right', 0) > 3 else 'Normal'),
            ('G longitudinal (frenada)', gf.get('lon_max_brake'), 2.5, 4.0,
             'Frenada muy intensa' if gf.get('lon_max_brake', 0) > 4 else
             'Frenada intensa' if gf.get('lon_max_brake', 0) > 2.5 else 'Frenada moderada'),
            ('G longitudinal (aceleración)', gf.get('lon_max_acc'), 0.6, 1.2,
             'Buena tracción' if gf.get('lon_max_acc', 0) > 0.8 else 'Tracción moderada'),
        ]
        gf_data = [['Métrica', 'Valor', 'Interpretación']]
        gf_style = _hdr_style()
        for ri, (label, val, med, high, interp) in enumerate(gf_rows_data, 1):
            gf_data.append([label, f"{val:.2f} G" if val else "—", interp])
            if val is not None:
                gf_style.append(('BACKGROUND', (1, ri), (1, ri), gforce_color(val, med, high)))

        gft = Table(gf_data, colWidths=[5.5*cm, 2.5*cm, 6.5*cm])
        gft.setStyle(TableStyle(gf_style))
        content.append(gft)
        content.append(Spacer(1, 0.3*cm))

    if susp:
        content.append(Paragraph("Datos de suspensión (mejor vuelta):", s_bold))
        susp_data = [['Esquina', 'Recorrido prom (mm)', 'Rango total (mm)', 'Min (mm)', 'Max (mm)']]
        for corner, label in zip(tyre_corners, tyre_labels):
            s_data = susp.get(corner, {})
            if s_data:
                susp_data.append([
                    label,
                    safe(s_data.get('avg'), '.1f'),
                    safe(s_data.get('range'), '.1f'),
                    safe(s_data.get('min'), '.1f'),
                    safe(s_data.get('max'), '.1f'),
                ])
        if len(susp_data) > 1:
            st = Table(susp_data, colWidths=[3.5*cm, 3.5*cm, 3.5*cm, 2.5*cm, 2.5*cm])
            st.setStyle(TableStyle(_hdr_style(BGBLUE)))
            content.append(st)
            content.append(Spacer(1, 0.2*cm))

        susp_notes = []
        for corner, label in zip(tyre_corners, tyre_labels):
            s_data = susp.get(corner, {})
            if s_data:
                if s_data.get('min', 0) < -5:
                    susp_notes.append(f"• {label}: suspensión toca fondo ({s_data['min']:.1f}mm) — aumentar ride height o endurecer resorte.")
                if s_data.get('range', 0) < 3:
                    susp_notes.append(f"• {label}: muy poco recorrido ({s_data['range']:.1f}mm) — suspensión demasiado dura o sin contacto.")
        for note in susp_notes:
            content.append(Paragraph(note, s_body))

    if not gf and not susp:
        content.append(Paragraph("Datos de G-forces y suspensión no disponibles.", s_body))

    content.append(PageBreak())

    # ═══ 7. SETUP UTILIZADO ══════════════════════════════════════════════
    content.append(Paragraph("7. SETUP UTILIZADO EN ESTA SESIÓN", s_sec))
    content.append(HRFlowable(width="100%", thickness=1, color=RED))
    content.append(Spacer(1, 0.2*cm))

    # Setup del CSV (línea metadata)
    setup_fields = [
        ('FWing', 'Alerón delantero'),
        ('RWing', 'Alerón trasero'),
        ('FrontCamber', 'Camber delantero (°)'),
        ('RearCamber', 'Camber trasero (°)'),
        ('FrontToe', 'Toe delantero (°)'),
        ('RearToe', 'Toe trasero (°)'),
        ('FrontSusp', 'Suspensión delantera'),
        ('RearSusp', 'Suspensión trasera'),
        ('FrontAntiRoll', 'Anti-roll delantero'),
        ('RearAntiRoll', 'Anti-roll trasero'),
        ('FrontSuspH', 'Ride height delantero'),
        ('RearSuspH', 'Ride height trasero'),
        ('BrakePressure', 'Presión de freno'),
        ('BrakeBias', 'Brake bias (%)'),
        ('FLTyrePressure', 'Presión goma FL (setup)'),
        ('FRTyrePressure', 'Presión goma FR (setup)'),
        ('RLTyrePressure', 'Presión goma RL (setup)'),
        ('RRTyrePressure', 'Presión goma RR (setup)'),
        ('FuelLoad', 'Combustible inicial (l)'),
        ('OnThrottle', 'Diff on-throttle (%)'),
        ('OffThrottle', 'Diff off-throttle (%)'),
    ]

    setup_available = [(label, setup.get(key)) for key, label in setup_fields
                       if setup.get(key) is not None and setup.get(key, 0) != 0]

    if setup_available:
        setup_table_data = [['Parámetro', 'Valor']] + [
            [label, f"{val:.3f}" if isinstance(val, float) else str(val)]
            for label, val in setup_available
        ]
        sett = Table(setup_table_data, colWidths=[8*cm, 6.5*cm])
        sett.setStyle(TableStyle(_hdr_style()))
        content.append(sett)
    else:
        content.append(Paragraph(
            "Setup no capturado en este CSV (valores en cero). "
            "El simulador no reportó parámetros de configuración para esta sesión.",
            s_body))
        # Aun así mostrar presiones y ride heights medidas en pista si existen
        if ins.get('tyres'):
            content.append(Spacer(1, 0.2*cm))
            content.append(Paragraph("Presiones medidas durante la vuelta (en pista):", s_bold))
            press_data = [['Goma', 'Promedio (PSI)', 'Mínimo', 'Máximo']]
            for corner, label in zip(tyre_corners, tyre_labels):
                td = ins['tyres'].get(corner, {})
                if td.get('press_avg'):
                    press_data.append([label, safe(td['press_avg']), safe(td['press_min']), safe(td['press_max'])])
            if len(press_data) > 1:
                pt2 = Table(press_data, colWidths=[4*cm, 3.5*cm, 3*cm, 3*cm])
                pt2.setStyle(TableStyle(_hdr_style(BGBLUE)))
                content.append(pt2)

    content.append(Spacer(1, 0.4*cm))

    # ═══ 8. ANÁLISIS TÉCNICO DETALLADO ══════════════════════════════════
    content.append(Paragraph("8. ANÁLISIS TÉCNICO DETALLADO", s_sec))
    content.append(HRFlowable(width="100%", thickness=1, color=RED))
    content.append(Spacer(1, 0.2*cm))

    # Fortalezas
    content.append(Paragraph("Fortalezas identificadas:", s_bold))
    fortalezas = []
    if ins.get('max_speed', 0) > 0:
        fortalezas.append(f"Velocidad máxima: {ins['max_speed']} km/h — buen aprovechamiento de rectas")
    if ins.get('avg_throttle', 0) > 60:
        fortalezas.append(f"Throttle promedio: {ins['avg_throttle']}% — buena aplicación de acelerador")
    if ins.get('full_throttle_pct', 0) > 40:
        fortalezas.append(f"A fondo completo el {ins['full_throttle_pct']}% del tiempo — buena gestión de rectas")
    if len(ins.get('braking', [])) >= 3:
        fortalezas.append(f"Frenadas fuertes detectadas en {len(ins['braking'])} zonas — buena confianza en los frenos")
    if score >= 70 and len(chrono_laps) > 1:
        fortalezas.append("Consistencia aceptable entre vueltas")
    if gf.get('lat_max_left', 0) > 2 or gf.get('lat_max_right', 0) > 2:
        fortalezas.append(f"G lateral alto (hasta {max(gf.get('lat_max_left',0), gf.get('lat_max_right',0))}G) — buen uso de los neumáticos")
    if not fortalezas:
        fortalezas.append("Vuelta válida completada correctamente")
    for f in fortalezas:
        content.append(Paragraph(f"• {f}", s_body))
    content.append(Spacer(1, 0.1*cm))

    # Áreas de mejora
    content.append(Paragraph("Áreas de mejora:", s_bold))
    mejoras = []
    if ins['braking']:
        b = ins['braking'][0]
        mejoras.append(f"Zona de frenada a {b['dist']}m: {b['intensity']}% de frenada a {b['speed']} km/h — revisar punto de entrada")
    if ins['early_lift_zones']:
        mejoras.append(f"Levantamiento temprano de acelerador en {len(ins['early_lift_zones'])} zonas — posible sobreviraje o trazada conservadora")
    if std > 0.5 and len(chrono_laps) > 1:
        mejoras.append(f"Variabilidad de {std:.3f}s — algún sector cambia entre vueltas")
    if best_lap.get('s1') and best_lap.get('s2') and best_lap.get('s3'):
        ss = [best_lap['s1'], best_lap['s2'], best_lap['s3']]
        slow_s = ss.index(max(ss)) + 1
        mejoras.append(f"Sector {slow_s} es el más lento ({fmt_time(max(ss))}) — mayor potencial de mejora")
    # Notas de gomas
    for corner, label in zip(tyre_corners, tyre_labels):
        avg_t = ins['tyres'].get(corner, {}).get('avg')
        if avg_t and avg_t > 115:
            mejoras.append(f"Goma {corner} sobrecalentada ({avg_t:.0f}°C) — ajustar camber o presión de setup")
    for corner, label in zip(tyre_corners, tyre_labels):
        slip_m = ins['tyres'].get(corner, {}).get('slip_max')
        if slip_m and slip_m > 8:
            mejoras.append(f"Slip excesivo en {corner} ({slip_m:.1f}%) — revisar diferencial o suavizar inputs")
    if not mejoras:
        mejoras.append("Optimizar punto de frenada en curvas medias")
        mejoras.append("Aplicar throttle más temprano desde el vértice")
    for m in mejoras:
        content.append(Paragraph(f"• {m}", s_body))
    content.append(Spacer(1, 0.1*cm))

    # Recomendaciones de setup (basadas en datos)
    content.append(Paragraph("Recomendaciones de setup:", s_bold))
    setup_recs = []
    brakes = ins.get('brakes', {})
    fl_avg = brakes.get('FL', {}).get('avg')
    rl_avg = brakes.get('RL', {}).get('avg')
    if fl_avg and rl_avg:
        front_avg = (fl_avg + (brakes.get('FR', {}).get('avg') or fl_avg)) / 2
        rear_avg  = (rl_avg + (brakes.get('RR', {}).get('avg') or rl_avg)) / 2
        if front_avg > rear_avg * 1.4:
            setup_recs.append("Mover brake bias hacia atrás — frenos delanteros sobrecargados")
        elif rear_avg > front_avg * 1.3:
            setup_recs.append("Mover brake bias hacia adelante — frenos traseros sobrecargados")

    rear_slip = max(ins['tyres'].get('RL', {}).get('slip_max', 0),
                    ins['tyres'].get('RR', {}).get('slip_max', 0))
    front_slip = max(ins['tyres'].get('FL', {}).get('slip_max', 0),
                     ins['tyres'].get('FR', {}).get('slip_max', 0))
    if rear_slip > front_slip * 1.5 and rear_slip > 5:
        setup_recs.append("Sobreviraje detectado por slip trasero elevado — endurecer barra anti-roll trasera o aumentar alerón trasero")
    elif front_slip > rear_slip * 1.5 and front_slip > 5:
        setup_recs.append("Subviraje detectado por slip delantero elevado — ablandar barra anti-roll delantera o reducir presión gomas delanteras")

    for corner, label in zip(tyre_corners, tyre_labels):
        z = ins['tyre_zones'].get(corner, {})
        diag = z.get('diagnosis', '')
        if diag and 'Exceso camber' in diag:
            setup_recs.append(f"Reducir camber negativo {corner} — goma trabajando más en zona interior")
        elif diag and 'insuficiente' in diag:
            setup_recs.append(f"Aumentar camber negativo {corner} — goma trabajando más en zona exterior")

    if not setup_recs:
        setup_recs.append("Verificar presiones de llantas calientes vs. temperaturas registradas")
        setup_recs.append("Evaluar rigidez de barras estabilizadoras según comportamiento en curvas rápidas")
    for rec in setup_recs:
        content.append(Paragraph(f"• {rec}", s_body))
    content.append(PageBreak())

    # ═══ 9. TOP 5 OPORTUNIDADES ══════════════════════════════════════════
    content.append(Paragraph("9. TOP 5 OPORTUNIDADES DE MEJORA", s_sec))
    content.append(HRFlowable(width="100%", thickness=1, color=RED))
    content.append(Spacer(1, 0.2*cm))

    opportunities = []
    if ins['braking']:
        b = ins['braking'][0]
        opportunities.append((
            f"Zona de frenada a {b['dist']}m", "−0.10s",
            f"Frenada al {b['intensity']:.0f}% a {b['speed']} km/h. Ajustar punto de entrada.",
            "Vuelta más rápida."))
    if ins['early_lift_zones']:
        opportunities.append((
            "Aplicación del acelerador", "−0.08s",
            f"Throttle tardío en {len(ins['early_lift_zones'])} zonas. Iniciar antes desde el vértice.",
            "Consistente entre vueltas."))
    if std > 0 and len(chrono_laps) > 1:
        opportunities.append((
            "Consistencia de línea", f"−{min(std, 0.15):.2f}s en promedio",
            f"Repetir línea de vuelta {chrono_laps.index(best_lap)+1}. Variabilidad: {std:.3f}s.",
            "Todas las vueltas."))
    if all(lap.get('s1') for lap in chrono_laps) and len(chrono_laps) > 1:
        bS1 = min(l['s1'] for l in chrono_laps if l.get('s1'))
        bS2 = min(l['s2'] for l in chrono_laps if l.get('s2'))
        bS3 = min(l['s3'] for l in chrono_laps if l.get('s3'))
        teorico = bS1 + bS2 + bS3
        diff = best_time - teorico
        if diff > 0.01:
            opportunities.append((
                "Tiempo teórico óptimo", f"−{diff:.3f}s",
                f"Combinar S1={fmt_time(bS1)}, S2={fmt_time(bS2)}, S3={fmt_time(bS3)} en la misma vuelta.",
                "Requiere consistencia de los 3 sectores."))

    # Oportunidades de gomas/frenos
    for corner, label in zip(tyre_corners, tyre_labels):
        avg_t = ins['tyres'].get(corner, {}).get('avg')
        if avg_t and avg_t > 115 and len(opportunities) < 5:
            opportunities.append((
                f"Temperatura goma {corner}", "−0.05s",
                f"Goma {corner} a {avg_t:.0f}°C — fuera del rango óptimo. Ajustar camber o presión.",
                "Toda la sesión."))
            break

    fallbacks = [
        ("Warmup de llantas", "−0.05s",
         "2 vueltas lentas para temperatura óptima antes del ataque.",
         "Vuelta 1."),
        ("Cambios de marcha", "−0.03s",
         "Revisar puntos de cambio en rectas — minimizar caída de RPM.",
         "Recta principal."),
        ("Línea en curvas lentas", "−0.07s",
         "Retrasar frenada 5-10m en horquillas para ganar velocidad de entrada.",
         "Curvas de baja velocidad."),
        ("Aceleración salida curva", "−0.06s",
         "Throttle progresivo desde vértice para maximizar tracción.",
         "Curvas de media y baja velocidad."),
        ("Sector más lento", "−0.08s",
         "Dedicar atención al sector con mayor delta vs. teórico.",
         "Sector de mayor potencial."),
    ]
    for fb in fallbacks:
        if len(opportunities) >= 5:
            break
        if not any(fb[0].split()[0] in o[0] for o in opportunities):
            opportunities.append(fb)

    for i, (title, gain, action, when) in enumerate(opportunities[:5], 1):
        content.append(Paragraph(f"<b>{i}. {title} ({gain})</b>", s_bold))
        content.append(Paragraph(action, s_body))
        content.append(Paragraph(f"Ocurre en: {when}", s_body))
        content.append(Spacer(1, 0.1*cm))
    content.append(Spacer(1, 0.2*cm))

    # ═══ 10. PLAN DE ACCIÓN ══════════════════════════════════════════════
    content.append(Paragraph("10. PLAN DE ACCIÓN PARA LA PRÓXIMA SESIÓN", s_sec))
    content.append(HRFlowable(width="100%", thickness=1, color=RED))
    content.append(Spacer(1, 0.2*cm))

    content.append(Paragraph("■ 3 Focos principales:", s_bold))
    content.append(Spacer(1, 0.1*cm))

    target_s = min(std / 2, 0.10)
    best_idx = chrono_laps.index(best_lap) + 1
    focos = [
        ("Optimizar frenada en zona de mayor carga",
         f"5 vueltas de ataque, replicar línea de vuelta {best_idx}",
         "Reducir delay de frenada, ganar ~0.10s"),
        ("Repetibilidad entre vueltas",
         "Grabar línea óptima + 8 vueltas de práctica enfocada",
         f"Variabilidad: ±{target_s:.2f}s objetivo (vs ±{std:.3f}s actual)"
         if len(chrono_laps) > 1 else "Establecer línea de referencia"),
        ("Warmup estructurado + temperatura de gomas",
         "2 vueltas suave → verificar temp gomas → 3 vueltas de ataque",
         "Eliminar penalidad de temperatura en vuelta 1"),
    ]

    for i, (focus, exercise, goal) in enumerate(focos, 1):
        content.append(Paragraph(f"<b>Enfoque {i}: {focus}</b>", s_bold))
        content.append(Paragraph(f"Ejercicio: {exercise}", s_body))
        content.append(Paragraph(f"Objetivo: {goal}", s_body))
        content.append(Spacer(1, 0.15*cm))

    target_time = best_time - 1.2
    target_score = min(100, score + 10) if len(chrono_laps) > 1 else 90
    content.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    content.append(Spacer(1, 0.1*cm))
    content.append(Paragraph(
        f"■ Meta de tiempo: <font color='#27ae60'>{fmt_time(target_time)}</font> (~1.2s mejor)", s_body))
    content.append(Paragraph(
        f"■ Meta Consistency Score: <font color='#27ae60'>{target_score:.0f}+</font>", s_body))
    content.append(Paragraph("■ Timeline estimado: 2-3 sesiones de práctica", s_body))
    content.append(PageBreak())

    # ═══ 11. DIAGNÓSTICO DEL INGENIERO DE PISTA ══════════════════════════
    content.append(Paragraph("11. DIAGNÓSTICO DEL INGENIERO DE PISTA", s_sec))
    content.append(HRFlowable(width="100%", thickness=2, color=RED))
    content.append(Spacer(1, 0.3*cm))

    s_coach_intro = ParagraphStyle('CI', parent=styles['Normal'], fontSize=9, textColor=GREY,
                                   fontName='Helvetica-Oblique', leading=13, spaceAfter=10)
    s_coach_head  = ParagraphStyle('CH', parent=styles['Normal'], fontSize=10, textColor=DARK,
                                   fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=4)
    s_coach_body  = ParagraphStyle('CB', parent=styles['Normal'], fontSize=9, textColor=DARK,
                                   leading=14, spaceAfter=4, leftIndent=10)

    content.append(Paragraph(
        f"Análisis cualitativo de la sesión — {meta.get('track','')}, {session_type} S{session_num}",
        s_coach_intro))

    # ── ✅ LO QUE ESTÁ BIEN ──────────────────────────────────────────────
    content.append(Paragraph("✅  LO QUE ESTÁ BIEN", s_coach_head))

    bien = []
    # Gomas en rango
    tyre_ok = all(
        50 <= ins['tyres'].get(c, {}).get('avg', 0) <= 115
        for c in ['FL', 'FR', 'RL', 'RR'] if ins['tyres'].get(c, {}).get('avg')
    )
    if tyre_ok and ins['tyres']:
        avgs = [ins['tyres'][c]['avg'] for c in ['FL','FR','RL','RR'] if ins['tyres'].get(c,{}).get('avg')]
        bien.append(f"Gomas en temperatura óptima — {min(avgs):.0f}–{max(avgs):.0f}°C. No hay sobrecalentamiento ni goma fría.")

    # Presiones
    presses = [ins['tyres'].get(c, {}).get('press_avg') for c in ['FL','FR','RL','RR']
               if ins['tyres'].get(c, {}).get('press_avg')]
    if presses and 20 <= min(presses) and max(presses) <= 35:
        bien.append(f"Presiones equilibradas en pista — {min(presses):.1f}–{max(presses):.1f} PSI.")

    # Slip bajo
    slips = [ins['tyres'].get(c, {}).get('slip_max', 0) for c in ['FL','FR','RL','RR']]
    if slips and max(slips) < 5:
        bien.append(f"Slip mínimo en todas las esquinas (máx {max(slips):.1f}%) — buen agarre durante toda la vuelta.")

    # G lateral
    lat = max(ins['gforces'].get('lat_max_left', 0), ins['gforces'].get('lat_max_right', 0))
    if lat > 2.0:
        bien.append(f"G lateral hasta {lat:.2f}G — el coche está cargado en curva sin perder tracción.")

    # Frenada fuerte
    lon_brk = ins['gforces'].get('lon_max_brake', 0)
    if lon_brk > 2.5:
        bien.append(f"Frenada intensa ({lon_brk:.2f}G) — buena confianza en los frenos.")

    # Throttle agresivo
    ft_pct = ins.get('full_throttle_pct', 0)
    if ft_pct > 40:
        bien.append(f"{ft_pct:.1f}% del tiempo a throttle completo — buen aprovechamiento de las rectas.")

    # Velocidad max
    if ins.get('max_speed', 0) > 0:
        bien.append(f"Velocidad máxima: {ins['max_speed']} km/h.")

    if not bien:
        bien.append("Vuelta válida completada sin incidentes.")

    for b in bien:
        content.append(Paragraph(f"• {b}", s_coach_body))

    # ── 🔥 PROBLEMAS DETECTADOS ──────────────────────────────────────────
    content.append(Paragraph("🔥  PROBLEMAS DETECTADOS", s_coach_head))

    problemas = []
    # Frenos calientes
    brakes = ins.get('brakes', {})
    brake_issues = []
    for corner, label in zip(['FL','FR','RL','RR'], ['Delantera Izq','Delantera Der','Trasera Izq','Trasera Der']):
        mx = brakes.get(corner, {}).get('max', 0)
        if mx > 700:
            brake_issues.append(f"{label}: {mx:.0f}°C — zona crítica")
        elif mx > 550:
            brake_issues.append(f"{label}: {mx:.0f}°C — límite superior")
    if brake_issues:
        problemas.append("Temperatura de frenos elevada: " + " | ".join(brake_issues) + ".")

    fl_avg_b = brakes.get('FL', {}).get('avg', 0)
    fr_avg_b = brakes.get('FR', {}).get('avg', 0)
    rl_avg_b = brakes.get('RL', {}).get('avg', 0)
    rr_avg_b = brakes.get('RR', {}).get('avg', 0)
    if fl_avg_b and rl_avg_b:
        f_avg = (fl_avg_b + fr_avg_b) / 2 if fr_avg_b else fl_avg_b
        r_avg = (rl_avg_b + rr_avg_b) / 2 if rr_avg_b else rl_avg_b
        if f_avg > r_avg * 1.35:
            problemas.append(
                f"Balance de frenos: eje delantero carga {f_avg:.0f}°C vs trasero {r_avg:.0f}°C — "
                f"los delanteros están haciendo demasiado trabajo.")
    if fl_avg_b and fr_avg_b and abs(fl_avg_b - fr_avg_b) > 70:
        side = "derecha" if fr_avg_b > fl_avg_b else "izquierda"
        problemas.append(
            f"Asimetría lateral en frenos delanteros — lado {side} más caliente "
            f"({max(fl_avg_b, fr_avg_b):.0f}°C vs {min(fl_avg_b, fr_avg_b):.0f}°C).")

    # Gomas fuera de rango
    for corner, label in zip(['FL','FR','RL','RR'], ['FL','FR','RL','RR']):
        avg_t = ins['tyres'].get(corner, {}).get('avg', 0)
        if avg_t > 115:
            problemas.append(f"Goma {label} sobrecalentada ({avg_t:.0f}°C) — riesgo de ampollas y pérdida de agarre.")
        elif avg_t and avg_t < 55:
            problemas.append(f"Goma {label} fría ({avg_t:.0f}°C) — nunca llegó a temperatura óptima.")

    # Slip elevado
    for corner, label in zip(['FL','FR','RL','RR'], ['FL','FR','RL','RR']):
        slip_m = ins['tyres'].get(corner, {}).get('slip_max', 0)
        if slip_m > 8:
            problemas.append(f"Slip excesivo en {label} ({slip_m:.1f}%) — pérdida de agarre importante.")

    # Camber issues
    for corner, label in zip(['FL','FR','RL','RR'], ['FL','FR','RL','RR']):
        z = ins.get('tyre_zones', {}).get(corner, {})
        diag = z.get('diagnosis', '')
        if diag and '⚠' in diag:
            problemas.append(f"Goma {label}: {diag.replace('⚠ ','')}.")

    # Suspensión toca fondo
    for corner, label in zip(['FL','FR','RL','RR'], ['FL','FR','RL','RR']):
        s_min = ins.get('suspension', {}).get(corner, {}).get('min', 0)
        if s_min < -5:
            problemas.append(f"Suspensión {label} toca fondo ({s_min:.1f}mm) — revisar ride height o dureza.")

    if ins.get('early_lift_zones'):
        problemas.append(
            f"Levantamiento temprano del acelerador en {len(ins['early_lift_zones'])} zonas — "
            f"posible sobreviraje o trazada conservadora en salida de curva.")

    if not problemas:
        problemas.append("No se detectaron problemas críticos. Sesión limpia.")

    for p in problemas:
        content.append(Paragraph(f"• {p}", s_coach_body))

    # ── ⚡ ESTILO DE PILOTAJE ─────────────────────────────────────────────
    content.append(Paragraph("⚡  ESTILO DE PILOTAJE", s_coach_head))

    pilotaje = []
    if ins.get('avg_throttle'):
        nivel = "agresivo" if ins['avg_throttle'] > 60 else "conservador"
        pilotaje.append(f"Throttle promedio {ins['avg_throttle']}% — estilo {nivel}.")
    if ins.get('full_throttle_pct') is not None:
        pilotaje.append(f"{ins['full_throttle_pct']:.1f}% del tiempo a fondo completo (>95%).")
    if lon_brk:
        pilotaje.append(f"Frenada máxima: {lon_brk:.2f}G longitudinal.")
    lon_acc = ins['gforces'].get('lon_max_acc', 0)
    if lon_acc:
        pilotaje.append(f"Aceleración máxima: {lon_acc:.2f}G — "
                        + ("buen aprovechamiento." if lon_acc > 0.8 else "margen para mejorar tracción."))
    if lat:
        pilotaje.append(f"G lateral máximo: {lat:.2f}G — "
                        + ("buen uso del potencial aerodinámico." if lat > 2.5 else "curvas cargadas con margen."))
    if ins.get('engine', {}).get('rpm_max'):
        pilotaje.append(f"RPM máximo alcanzado: {ins['engine']['rpm_max']:.0f} rpm.")

    for p in pilotaje:
        content.append(Paragraph(f"• {p}", s_coach_body))

    # ── 💡 RECOMENDACIONES DE SETUP ──────────────────────────────────────
    content.append(Paragraph("💡  RECOMENDACIONES DE SETUP PARA PRÓXIMA SESIÓN", s_coach_head))

    setup_recs = []
    # Brake bias
    if fl_avg_b and rl_avg_b:
        f_avg = (fl_avg_b + (fr_avg_b or fl_avg_b)) / 2
        r_avg = (rl_avg_b + (rr_avg_b or rl_avg_b)) / 2
        if f_avg > r_avg * 1.35:
            diff_pct = round((f_avg - r_avg) / f_avg * 100)
            setup_recs.append(
                f"Brake bias: mover bias hacia atrás (eje trasero tiene capacidad disponible — "
                f"delantero está {diff_pct:.0f}% más caliente). Prueba 1-2% menos en delantero.")
    # Alerón trasero
    if brakes and any(brakes.get(c, {}).get('max', 0) > 600 for c in ['FL','FR']):
        setup_recs.append(
            "Aumentar alerón trasero ligeramente: más carga aerodinámica reduce la velocidad de entrada "
            "a frenada, aliviando el trabajo de los frenos delanteros.")
    # Suspensión trasera
    rear_range = max(
        ins.get('suspension', {}).get('RL', {}).get('range', 0),
        ins.get('suspension', {}).get('RR', {}).get('range', 0))
    front_range = max(
        ins.get('suspension', {}).get('FL', {}).get('range', 0),
        ins.get('suspension', {}).get('FR', {}).get('range', 0))
    if front_range > 0 and rear_range > 0 and rear_range < front_range * 0.6:
        setup_recs.append(
            "Suspensión trasera más blanda: el recorrido trasero es bajo vs delantero — "
            "ablandar mejora distribución de carga en frenada y reduce temperatura delantera.")
    # Camber por diagnóstico de zonas
    for corner, label in zip(['FL','FR','RL','RR'], ['delantera izq','delantera der','trasera izq','trasera der']):
        z = ins.get('tyre_zones', {}).get(corner, {})
        inner = z.get('inner', 0)
        outer = z.get('outer', 0)
        if inner and outer:
            if inner - outer > 20:
                setup_recs.append(
                    f"Camber goma {label}: reducir camber negativo — zona interior {inner-outer:.0f}°C "
                    f"más caliente que exterior, la goma no trabaja pareja.")
            elif outer - inner > 15:
                setup_recs.append(
                    f"Camber goma {label}: aumentar camber negativo — zona exterior {outer-inner:.0f}°C "
                    f"más caliente, la goma trabaja solo en el borde exterior.")
    # Línea de frenada
    if ins['braking']:
        b = ins['braking'][0]
        setup_recs.append(
            f"Línea de frenada: en zona {b['dist']}m el freno llega al {b['intensity']:.0f}% a {b['speed']} km/h — "
            f"frenada progresiva más temprana distribuiría mejor la temperatura.")

    if not setup_recs:
        setup_recs.append("Setup equilibrado para esta sesión. Priorizar consistencia de línea sobre cambios de setup.")

    for i, rec in enumerate(setup_recs, 1):
        content.append(Paragraph(f"{i}. {rec}", s_coach_body))

    # ── 📈 META ──────────────────────────────────────────────────────────
    content.append(Paragraph("📈  META PARA LA PRÓXIMA SESIÓN", s_coach_head))
    target_brake = 550  # °C objetivo para frenos delanteros
    current_max_brake = max((brakes.get(c, {}).get('max', 0) for c in ['FL','FR']), default=0)
    if current_max_brake > 0:
        content.append(Paragraph(
            f"• Reducir temperatura máxima de frenos delanteros de {current_max_brake:.0f}°C a ~{target_brake}°C "
            f"sin perder rendimiento en frenada — lograrlo con ajuste de bias y línea más progresiva.",
            s_coach_body))
    content.append(Paragraph(
        f"• Tiempo objetivo: {fmt_time(best_time - 0.8)} (−0.8s) en la próxima sesión con setup ajustado.",
        s_coach_body))
    content.append(Paragraph(
        f"• Consistency Score objetivo: {min(100, score + 12):.0f}+/100 "
        f"(actual: {score}/100).",
        s_coach_body))

    # ── Footer ───────────────────────────────────────────────────────────
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(GREY)
        txt = (f"Reporte generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
               f"{meta.get('game','')} — {meta.get('track','')} | Piloto: {pilot_name} | v4.0")
        canvas.drawCentredString(A4[0]/2, 0.5*cm, txt)
        canvas.restoreState()

    try:
        doc.build(content, onFirstPage=footer, onLaterPages=footer)
        result = {
            "pdf": str(output_path),
            "pilot": pilot_name,
            "pilot_id": pilot_id,
            "track": meta.get("track", ""),
            "car": meta.get("car", ""),
            "simulator": meta.get("game", ""),
            "best_time": fmt_time(best_time),
            "consistency_score": score,
            "laps": len(chrono_laps),
            "session_type": session_type,
            "session_num": session_num,
        }
        print(f"✅ PDF generado: {output_path}")
        print("JSON_STATS:" + json.dumps(result))
        return str(output_path)
    except Exception as e:
        print(f"✗ Error generando PDF: {e}")
        import traceback; traceback.print_exc()
        return None


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python3 telemetry_pdf_generator_v4.py <directorio_o_csv> [piloto] [id] [P|Q|R] [num_sesion] [output]")
        sys.exit(1)

    csv_input  = sys.argv[1]
    pilot_name = sys.argv[2] if len(sys.argv) > 2 else "Piloto"
    pilot_id   = sys.argv[3] if len(sys.argv) > 3 else "001"
    sess_type  = sys.argv[4] if len(sys.argv) > 4 else "Q"
    sess_num   = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    output     = sys.argv[6] if len(sys.argv) > 6 else None

    csv_files = find_session_csvs(csv_input)
    if not csv_files:
        print(f"Error: no se encontraron CSVs en {csv_input}")
        sys.exit(1)

    print(f"📂 {len(csv_files)} vuelta(s) encontrada(s)")
    laps_data = []
    for f in csv_files:
        lap = parse_r3e_csv(f)
        if lap['lap_time'] > 0:
            laps_data.append(lap)
#            print(f"  • {Path(f).name}: {fmt_time(lap['lap_time'])} "
#                  f"(S1:{fmt_time(lap['s1']) if lap['s1'] else '—'} "
#                  f"S2:{fmt_time(lap['s2']) if lap['s2'] else '—'} "
#                  f"S3:{fmt_time(lap['s3']) if lap['s3'] else '—'})")

    if not laps_data:
        print("Error: no se pudieron leer tiempos válidos")
        sys.exit(1)

    if not output:
        best = min(laps_data, key=lambda x: x['lap_time'])
        m = best['meta']
        date_str = datetime.now().strftime('%Y-%m-%d')
        track = m.get('track', 'Unknown').replace(' ', '').replace('/', '')
        car   = m.get('car',   'Unknown').replace(' ', '').replace('/', '')
        pilot_clean = pilot_name.replace(' ', '')
        sim   = m.get('game',  'Unknown').replace(' ', '')
        if car == 'Datonodisp' or len(car) > 25:
            car = 'Unknown'
        fname = f"{date_str}_{pilot_id}_{pilot_clean}_{car}_{track}_{sess_type}_S{sess_num}.pdf"
        parent = Path(csv_files[0]).parent
        candidate = parent.parent.parent
        if candidate.exists() and str(candidate) not in ('/', '/mnt', '/mnt/carrera'):
            output = candidate / fname
        else:
            output = Path('/tmp') / fname

    generate_pdf(laps_data, pilot_name, pilot_id, sess_type, sess_num, Path(output))
