# TOOLS.md - Infrastructure Notes

## Servidor

- **Host:** franky
- **IP Tailscale:** 100.80.115.53
- **OS:** DietPi (ARM)
- **Usuario SSH:** root
- **SSH key:** ~/.ssh/franky

## Rutas clave

- **CSVs AC:**     `/mnt/carrera/ac/` (archivos planos, sincronizados desde Drive)
- **CSVs R3E:**    `/mnt/carrera/r3e/` (archivos planos, sincronizados desde Drive)
- **Workspace:**   `/root/.openclaw/agents/telemetry/workspace/`
- **Script PDF:**  `/root/.openclaw/agents/telemetry/workspace/telemetry_pdf_generator_v3.py`
- **Sync script:** `/usr/local/bin/sync_csvs_from_drive.py`
- **OAuth token:** `/root/.config/gdrive/oauth_token.json`

## Google Drive — Folder IDs

- **Raíz telemetría:** `1x-2bByARqKM1ZYdXW1Sn0zTkcyTToq4W`
- **Piloto Oliver:**   `1eiVHgbu1vYX-ogobTs2zQ_CPwhcZgs1m` (1100292_OliverInfante)
- **CSVs AC Drive:**   `15HFvwfhwCzCtayhM8JlKraiQevLejJK1`
- **CSVs R3E Drive:**  `1hZGu3ZtHETDi_8AWt4kckoDeXt22ypcb`
- **Cuenta Drive:**    oliver132123@gmail.com

## Telegram

- **Bot token:** en `/root/.openclaw/agents/telemetry/workspace/` o env TELEGRAM_BOT_TOKEN
- **Chat del piloto:** configurado en el bot principal

## Python packages disponibles

- reportlab (PDF generation)
- google-auth, google-api-python-client (Drive API)
- anthropic (LLM)
