# MEMORY.md — Long-Term Memory

## Piloto activo
- Nombre: Oliver Infante | ID: 1100292
- Drive folder: 1eiVHgbu1vYX-ogobTs2zQ_CPwhcZgs1m

## Infraestructura
- CSVs AC:  /mnt/carrera/ac/  (archivos planos)
- CSVs R3E: /mnt/carrera/r3e/ (archivos planos)
- Sync automático: cron cada 5 min via sync_csvs_from_drive.py

## Scripts disponibles

### telemetry_pdf_generator_v3.py — Sesión individual
```bash
python3 /root/.openclaw/agents/telemetry/workspace/telemetry_pdf_generator_v3.py \
  /mnt/carrera/[ac|r3e] "Oliver Infante" "1100292" "[P|Q|R]" [N]
```
- N=1: sesión más reciente | N=2: anterior, etc.
- Agrupa vueltas por gap de mtime (5 min estándar)
- Output: JSON_STATS:{pdf, best_time, car, track, laps, consistency_score, session_num, simulator}
- El PDF tiene 11 secciones con colores F1

### day_report_generator.py — Todas las vueltas de un auto
```bash
python3 /usr/local/bin/day_report_generator.py \
  "Oliver Infante" "1100292" "[P|Q|R]" --sim [ac|r3e] --car [auto]
```
- Sin --date: incluye TODAS las vueltas del auto (sin filtro de fecha ni gap)
- Con --date YYYY-MM-DD: filtra por fecha de modificación del archivo
- Sube a Drive automáticamente
- Output: JSON_STATS + DRIVE_PDF_LINK + DRIVE_FOLDER_LINK

### list_sessions.py — Listar/filtrar sesiones disponibles
```bash
python3 /usr/local/bin/list_sessions.py [--sim ac|r3e] [--car X] [--date YYYY-MM-DD] [--limit 20]
python3 /usr/local/bin/list_sessions.py --sim ac --car nissan --nth 1  # retorna SESSION_PATH
```

## Formato de nombre de archivo
- Sesión: YYYY-MM-DD_ID_NombrePiloto_Auto_Pista_Tipo_SN.pdf
- Todas:  YYYY-MM-DD_ID_NombrePiloto_ALL_Auto_Pista_Tipo_S1.pdf

## Drive — Folder IDs
- Raíz telemetría: 1x-2bByARqKM1ZYdXW1Sn0zTkcyTToq4W
- Oliver:          1eiVHgbu1vYX-ogobTs2zQ_CPwhcZgs1m
- CSVs AC:         15HFvwfhwCzCtayhM8JlKraiQevLejJK1
- CSVs R3E:        1hZGu3ZtHETDi_8AWt4kckoDeXt22ypcb
