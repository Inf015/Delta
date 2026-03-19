#!/usr/bin/env python3
"""
list_sessions.py — Lista y filtra sesiones de telemetría disponibles.
Uso: python3 list_sessions.py [--sim ac|r3e] [--car bmw] [--date 2026-03-18] [--limit N]

Salida: tabla formateada para el bot + JSON_SESSIONS al final.
"""

import os, sys, json, argparse
from pathlib import Path
from datetime import datetime, date

DIRS = {
    'ac':  Path('/mnt/carrera/ac'),
    'r3e': Path('/mnt/carrera/r3e'),
}
KNOWN_SIMS = ['R3E', 'ACC', 'AC', 'RF2', 'IRACING', 'ASSETTOCORSA', 'RACEROOM']


def fmt_time(seconds):
    try:
        s = float(seconds)
        if s <= 0: return "—"
        m = int(s // 60)
        return f"{m}:{s - m*60:06.3f}"
    except:
        return "—"


def read_csv_meta(path):
    """Lee solo las primeras líneas del CSV para extraer metadata."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = [f.readline() for _ in range(8)]

        meta = {}
        for i, line in enumerate(lines[:6]):
            parts = [p.strip() for p in line.strip().split(',')]
            if len(parts) >= 4:
                sim = parts[0].upper().replace(' ', '')
                if any(sim.startswith(s) for s in KNOWN_SIMS):
                    meta = {
                        'sim':      parts[0].upper().replace(' ', ''),
                        'date':     parts[2] if len(parts) > 2 else '',
                        'track':    parts[3] if len(parts) > 3 else '—',
                        'car':      parts[4] if len(parts) > 4 else '—',
                        'session':  parts[5] if len(parts) > 5 else '—',
                        'laptime':  parts[6] if len(parts) > 6 else '0',
                        's1':       parts[7] if len(parts) > 7 else '',
                        's2':       parts[8] if len(parts) > 8 else '',
                        's3':       parts[9] if len(parts) > 9 else '',
                    }
                    # Tyre compound (line i+2)
                    try:
                        track_parts = [p.strip() for p in lines[i+2].strip().split(',')]
                        track_hdr   = [p.strip() for p in lines[i+1].strip().split(',')]
                        tyre_idx = next((j for j, h in enumerate(track_hdr) if 'Tyre' in h), None)
                        if tyre_idx is not None and tyre_idx < len(track_parts):
                            meta['tyre'] = track_parts[tyre_idx]
                    except:
                        pass
                    break

        if not meta:
            return None

        # Normalizar car: si es numérico o vacío
        car = meta.get('car', '').strip()
        if not car or car.lstrip('-').isdigit():
            meta['car'] = '—'

        # Normalizar laptime
        try:
            meta['laptime_s'] = float(meta['laptime'])
        except:
            meta['laptime_s'] = 0.0

        # Normalizar fecha (puede ser "2026-03-18 00:56:39")
        meta['date_only'] = meta['date'].split(' ')[0] if meta.get('date') else ''

        # Tamaño del archivo en KB
        meta['size_kb'] = round(path.stat().st_size / 1024, 0)

        # mtime como referencia de orden
        meta['mtime'] = path.stat().st_mtime
        meta['path']  = str(path)
        meta['filename'] = path.name

        return meta
    except Exception as e:
        return None


def load_all_sessions(sim_filter=None):
    """Carga metadata de todos los CSVs disponibles."""
    sessions = []
    dirs_to_scan = {}

    if sim_filter:
        sf = sim_filter.lower()
        if sf in DIRS:
            dirs_to_scan[sf] = DIRS[sf]
    else:
        dirs_to_scan = DIRS

    for sim_key, d in dirs_to_scan.items():
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if f.suffix != '.csv' or f.stat().st_size < 500:
                continue
            meta = read_csv_meta(f)
            if meta:
                meta['dir_sim'] = sim_key  # 'ac' o 'r3e'
                sessions.append(meta)

    # Ordenar por mtime descendente (más reciente primero)
    sessions.sort(key=lambda x: x['mtime'], reverse=True)
    return sessions


def filter_sessions(sessions, car=None, date_filter=None):
    """Aplica filtros de auto y fecha."""
    result = sessions

    if car:
        car_lower = car.lower()
        result = [s for s in result
                  if car_lower in s.get('car', '').lower()
                  or car_lower in s.get('filename', '').lower()]

    if date_filter:
        result = [s for s in result
                  if s.get('date_only', '').startswith(date_filter)
                  or date_filter in s.get('filename', '')]

    return result


def format_table(sessions, limit=20):
    """Formatea la tabla de sesiones para el bot."""
    if not sessions:
        return "No se encontraron sesiones con esos filtros."

    shown = sessions[:limit]
    lines = []
    lines.append(f"{'#':<3} {'Sim':<5} {'Fecha':<12} {'Pista':<28} {'Auto':<22} {'S.Type':<7} {'Mejor':<10} {'Goma'}")
    lines.append("─" * 100)

    for i, s in enumerate(shown, 1):
        track = s.get('track', '—')[:27]
        car   = s.get('car',   '—')[:21]
        sim   = s.get('sim',   s.get('dir_sim', '—').upper())[:4]
        stype = s.get('session', '—')[:6]
        fecha = s.get('date_only', '—')[:11]
        lap   = fmt_time(s.get('laptime_s', 0))
        tyre  = s.get('tyre', '—')[:10]
        lines.append(f"{i:<3} {sim:<5} {fecha:<12} {track:<28} {car:<22} {stype:<7} {lap:<10} {tyre}")

    if len(sessions) > limit:
        lines.append(f"\n... y {len(sessions) - limit} sesión(es) más. Usa --limit N para ver más.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sim',   help='Simulador: ac o r3e')
    parser.add_argument('--car',   help='Filtro por auto (parcial, ej: bmw)')
    parser.add_argument('--date',  help='Filtro por fecha (ej: 2026-03-18)')
    parser.add_argument('--limit', type=int, default=20, help='Máximo de resultados')
    parser.add_argument('--json',  action='store_true', help='Salida JSON')
    parser.add_argument('--nth',   type=int, default=0,
                        help='Retorna la ruta de la Nth sesión (para /reporte)')
    args = parser.parse_args()

    sessions = load_all_sessions(sim_filter=args.sim)
    sessions = filter_sessions(sessions, car=args.car, date_filter=args.date)

    # Si --nth, solo retorna la ruta de esa sesión (para usar en /reporte)
    if args.nth > 0:
        if args.nth <= len(sessions):
            s = sessions[args.nth - 1]
            # Retorna el directorio padre (para pasar al generador de PDF)
            parent = str(Path(s['path']).parent)
            print(f"SESSION_PATH:{parent}")
            print(f"SESSION_META:{json.dumps(s)}")
        else:
            print(f"ERROR: Solo hay {len(sessions)} sesión(es) con esos filtros.")
        return

    if args.json:
        print("JSON_SESSIONS:" + json.dumps(sessions[:args.limit], default=str))
        return

    # Tabla formateada
    total = len(sessions)
    print(f"📂 {total} sesión(es) encontrada(s)\n")
    print(format_table(sessions, limit=args.limit))
    print(f"\nJSON_SESSIONS:" + json.dumps(sessions[:args.limit], default=str))


if __name__ == '__main__':
    main()
