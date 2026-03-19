# HEARTBEAT.md - Periodic Checks

## Verificación automática de nuevas sesiones

### TRIGGER
Al inicio de cada conversación, o cuando el usuario escribe:
- "hay algo nuevo?"
- "nuevas sesiones?"
- "qué hay?"
- "/status"

### ACCIÓN
1. Ejecuta sync:
   ```bash
   python3 /usr/local/bin/sync_csvs_from_drive.py
   ```
2. Lista CSVs más recientes:
   ```bash
   ls -t /mnt/carrera/ac/*.csv 2>/dev/null | head -3
   ls -t /mnt/carrera/r3e/*.csv 2>/dev/null | head -3
   ```
3. Responde:

Si hay archivos nuevos:
```
📥 [N] sesión(es) nueva(s) detectada(s):
- AC: [nombre_archivo] ([fecha])
- R3E: [nombre_archivo] ([fecha])
¿Genero el reporte?
```

Si no hay nada nuevo:
```
No hay sesiones nuevas desde la última sincronización.
```

### FRECUENCIA
- Sincronización automática: cada 5 min via cron (`/usr/local/bin/sync_csvs_from_drive.py`)
- Reporte al usuario: solo cuando el usuario lo pida explícitamente
