#!/usr/bin/env python3
"""
day_report_generator.py — PDF de todas las vueltas del día usando el mismo formato y colores
que telemetry_pdf_generator_v3.py.
Uso: python3 day_report_generator.py "Piloto" "ID" "P|Q|R" [--sim ac|r3e] [--car bmw] [--date YYYY-MM-DD]
"""

import sys, os, json, argparse, re
from pathlib import Path
from datetime import datetime, date, timedelta

# ─── IMPORTAR GENERADOR PRINCIPAL (colores, parse, generate_pdf) ────────────
sys.path.insert(0, '/root/.openclaw/agents/telemetry/workspace')
from telemetry_pdf_generator_v3 import (
    parse_r3e_csv, fmt_time, generate_pdf
)

DIRS = {'ac': Path('/mnt/carrera/ac'), 'r3e': Path('/mnt/carrera/r3e')}
KNOWN_SIMS = ['R3E', 'ACC', 'AC', 'RF2', 'IRACING', 'ASSETTOCORSA', 'RACEROOM']

_SKIP_WORDS = {'bm', 'rt', 'layout', 'f1', 'gt3', 'gt4', 'gtc', 'gte', 'lmp',
               'the', 'de', 'la', 'el', 'en', 'and', 'gp', 'circuit', 'raceway',
               'international', 'speedway', 'ring', '2023', '2024', '2025', '2026'}


def _short_name(raw, fallback='Unknown', max_len=12):
    """Extrae la palabra más representativa de un nombre de auto o pista."""
    parts = re.split(r'[\s_\-]+', raw.strip())
    words = [p for p in parts
             if p and not p.isdigit() and p.lower() not in _SKIP_WORDS and len(p) > 1]
    if not words:
        return fallback.replace(' ', '')[:max_len]
    return max(words, key=len)[:max_len]


# ─── BÚSQUEDA DE CSVs DEL DÍA ───────────────────────────────────────────────

def read_csv_meta_quick(path):
    """Lee solo las primeras líneas para extraer metadata básica."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = [f.readline() for _ in range(8)]
        for line in lines[:6]:
            parts = [p.strip() for p in line.strip().split(',')]
            if len(parts) >= 4:
                sim = parts[0].upper().replace(' ', '')
                if any(sim.startswith(s) for s in KNOWN_SIMS):
                    date_str = parts[2].split(' ')[0] if len(parts) > 2 else ''
                    car      = parts[4] if len(parts) > 4 else ''
                    return {'date': date_str, 'car': car, 'sim': sim}
        return None
    except Exception:
        return None


def find_day_csvs(sim_filter, car_filter, date_str=None):
    """Encuentra todos los CSVs que coincidan con los filtros.
    date_str filtra por mtime del archivo (zona horaria del servidor).
    date_str=None = sin filtro de fecha.
    """
    dirs_to_scan = {sim_filter: DIRS[sim_filter]} if sim_filter and sim_filter in DIRS else DIRS
    results = []

    # Calcular rango de mtime si hay filtro de fecha
    mtime_start = mtime_end = None
    if date_str:
        try:
            d0 = datetime.strptime(date_str, '%Y-%m-%d')
            mtime_start = d0.timestamp()
            mtime_end   = (d0 + timedelta(days=1)).timestamp()
        except ValueError:
            pass

    for sim_key, d in dirs_to_scan.items():
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if f.suffix != '.csv' or f.stat().st_size < 500:
                continue
            if mtime_start is not None:
                mt = f.stat().st_mtime
                if not (mtime_start <= mt < mtime_end):
                    continue
            meta = read_csv_meta_quick(f)
            if not meta:
                continue
            if car_filter:
                car_low = car_filter.lower()
                if car_low not in meta['car'].lower() and car_low not in f.name.lower():
                    continue
            results.append(f)
    results.sort(key=lambda p: p.stat().st_mtime)
    return results


# ─── GOOGLE DRIVE UPLOAD ────────────────────────────────────────────────────

def upload_to_drive(pdf_path, pilot_name, pilot_id):
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        TOKEN_PATH  = '/root/.config/gdrive/oauth_token.json'
        ROOT_FOLDER = '1x-2bByARqKM1ZYdXW1Sn0zTkcyTToq4W'

        with open(TOKEN_PATH) as f:
            data = json.load(f)
        creds = Credentials(
            token=data['token'], refresh_token=data['refresh_token'],
            token_uri=data['token_uri'], client_id=data['client_id'],
            client_secret=data['client_secret'], scopes=data['scopes']
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            data['token'] = creds.token
            with open(TOKEN_PATH, 'w') as f:
                json.dump(data, f)

        service = build('drive', 'v3', credentials=creds)

        folders = service.files().list(
            q=f"'{ROOT_FOLDER}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields='files(id,name)'
        ).execute().get('files', [])
        pilot_folder = next((f for f in folders if pilot_id in f['name']), None)
        if not pilot_folder:
            pilot_safe  = pilot_name.replace(' ', '')
            pilot_folder = service.files().create(
                body={'name': f'{pilot_id}_{pilot_safe}',
                      'mimeType': 'application/vnd.google-apps.folder',
                      'parents': [ROOT_FOLDER]},
                fields='id,name'
            ).execute()

        folder_id = pilot_folder['id']
        uploaded  = service.files().create(
            body={'name': Path(pdf_path).name, 'parents': [folder_id]},
            media_body=MediaFileUpload(str(pdf_path), mimetype='application/pdf'),
            fields='id,webViewLink'
        ).execute()

        return uploaded.get('webViewLink', ''), f'https://drive.google.com/drive/folders/{folder_id}'
    except Exception as e:
        return None, f'ERROR_DRIVE: {e}'


# ─── MAIN ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pilot',      help='Nombre del piloto')
    parser.add_argument('pilot_id',   help='ID del piloto')
    parser.add_argument('sess_type',  help='P / Q / R')
    parser.add_argument('--sim',      help='ac o r3e')
    parser.add_argument('--car',      help='Filtro por auto')
    parser.add_argument('--date',     default=None, help='YYYY-MM-DD. Omitir = todas las fechas')
    parser.add_argument('--output',   help='Ruta del PDF de salida')
    args = parser.parse_args()

    if args.date and args.date.lower() == 'hoy':
        args.date = date.today().strftime('%Y-%m-%d')
    elif args.date and args.date.lower() == 'ayer':
        args.date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')

    print(f"🔍 Buscando sesiones: sim={args.sim or 'todos'} | "
          f"auto={args.car or 'todos'} | fecha={args.date or 'todas'}")

    csv_paths = find_day_csvs(args.sim, args.car, args.date)
    if not csv_paths:
        print(f"No se encontraron CSVs con esos filtros.")
        sys.exit(1)

    print(f"📂 {len(csv_paths)} vuelta(s) encontrada(s)")

    laps_data = []
    for p in csv_paths:
        lap = parse_r3e_csv(p)
        if lap['lap_time'] > 0:
            laps_data.append(lap)
#            print(f"  • {p.name}: {fmt_time(lap['lap_time'])}")

    if not laps_data:
        print("Error: no hay vueltas válidas")
        sys.exit(1)

    # Nombre del archivo con formato ALL
    if not args.output:
        best  = min(laps_data, key=lambda x: x['lap_time'])
        m     = best['meta']
        pilot_c     = args.pilot.replace(' ', '')
        car_short   = _short_name(m.get('car', '') or (args.car or ''), fallback=args.car or 'Unknown')
        track_short = _short_name(m.get('track', ''), fallback='Track')
        date_label = args.date or date.today().strftime('%Y-%m-%d')
        fname  = f"{date_label}_{args.pilot_id}_{pilot_c}_ALL_{car_short}_{track_short}_{args.sess_type}_S1.pdf"
        output = Path('/tmp') / fname
    else:
        output = Path(args.output)

    # Generar PDF con el mismo formato y colores del generador principal
    pdf_path = generate_pdf(laps_data, args.pilot, args.pilot_id,
                            args.sess_type, 1, output)

    if pdf_path:
        pdf_link, folder_link = upload_to_drive(pdf_path, args.pilot, args.pilot_id)
        if pdf_link and not str(pdf_link).startswith('ERROR'):
            print(f"DRIVE_PDF_LINK:{pdf_link}")
            print(f"DRIVE_FOLDER_LINK:{folder_link}")
        else:
            print(f"DRIVE_ERROR:{folder_link}")


if __name__ == '__main__':
    main()
