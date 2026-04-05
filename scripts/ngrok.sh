#!/usr/bin/env bash
# ─── SimTelemetry Pro — ngrok tunnel helper ────────────────────────────────────
# Levanta el stack completo con nginx y abre un túnel ngrok en el puerto 80.
#
# Requisitos:
#   - Docker Desktop corriendo
#   - ngrok instalado y autenticado: https://dashboard.ngrok.com/get-started/setup
#   - Archivo .env con ANTHROPIC_API_KEY etc. completado
#
# Uso:
#   ./scripts/ngrok.sh            # Inicia todo
#   ./scripts/ngrok.sh stop       # Detiene el stack

set -euo pipefail

COMPOSE_CMD="docker compose -f docker-compose.yml -f docker-compose.ngrok.yml"

stop() {
  echo "→ Deteniendo stack..."
  $COMPOSE_CMD down
  echo "✓ Stack detenido."
  exit 0
}

[[ "${1:-}" == "stop" ]] && stop

# ── 1. Verificar dependencias ──────────────────────────────────────────────────
command -v docker >/dev/null 2>&1 || { echo "✗ docker no encontrado"; exit 1; }
command -v ngrok  >/dev/null 2>&1 || { echo "✗ ngrok no encontrado — instalar: https://ngrok.com/download"; exit 1; }

# ── 2. Levantar el stack ───────────────────────────────────────────────────────
echo "→ Iniciando stack (esto puede tardar la primera vez)..."
$COMPOSE_CMD up -d --build

echo "→ Esperando que nginx esté listo..."
for i in $(seq 1 20); do
  if curl -sf http://localhost/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

# ── 3. Abrir túnel ngrok ───────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Abriendo túnel ngrok en el puerto 80..."
echo "  → La URL pública aparecerá a continuación."
echo "  → No es necesario cambiar ningún env var: el backend acepta"
echo "    automáticamente cualquier origen *.ngrok-free.app."
echo "  → Para detener: Ctrl+C  y luego  ./scripts/ngrok.sh stop"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ngrok http 80
