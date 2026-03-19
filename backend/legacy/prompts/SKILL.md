# Skill: Racing Telemetry Analyst

## Trigger
Activa cuando el usuario mencione: telemetría, vuelta, lap, tiempos, reporte, CSV, simulador, sesión.

## Scripts (ver MEMORY.md para uso completo)
- Sesión individual: telemetry_pdf_generator_v3.py
- Todas las vueltas: day_report_generator.py (ya sube a Drive)

## Formato de tiempos — OBLIGATORIO
Siempre m:ss.mmm (ej: 1:32.450). NUNCA segundos crudos (92.450s).
Usa el campo best_time del JSON_STATS — no lo calcules ni lo extraigas del nombre de archivo.

## Tipo de sesión
Si no está en el CSV: "¿Tipo de sesión? (P / Q / R)"

## PDF — 11 secciones
1. Portada
2. Resumen de sesión
3. Tiempos por vuelta (colores F1: mejor sector=morado, mejor vuelta=verde, peor=rojo)
4. Consistency Score
5. Análisis de gomas (temp/presión/desgaste/slip con semáforo de colores)
6. Análisis de frenos (temp por esquina con semáforo)
7. G-Forces y dinámica (G lateral/longitudinal + suspensión)
8. Setup utilizado
9. Análisis técnico detallado
10. Top 5 oportunidades de mejora
11. Diagnóstico del ingeniero de pista (✅ bien / ❌ problemas / ⚡ estilo / 💡 setup / 📈 meta)

## Detección de simulador
- "ac", "assetto" → AC → /mnt/carrera/ac
- "r3e", "raceroom" → R3E → /mnt/carrera/r3e
Nunca mezcles datos de un simulador con otro.
