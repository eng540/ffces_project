#!/bin/bash
set -euo pipefail

# ============================================
# FFCES Stop Script
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Use the right compose command
if command -v docker compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

ACTION="${1:-}"

case "$ACTION" in
    hard)
        echo "[STOP] Stopping FFCES and removing volumes..."
        $COMPOSE_CMD down -v
        echo "[STOP] All services stopped. Data volumes removed."
        ;;
    clean)
        echo "[STOP] Stopping FFCES and removing everything (including images)..."
        $COMPOSE_CMD down -v --rmi local
        echo "[STOP] All services stopped. Data and images removed."
        ;;
    *)
        echo "[STOP] Stopping FFCES services..."
        $COMPOSE_CMD down
        echo "[STOP] All services stopped (volumes preserved)."
        echo ""
        echo "  To remove volumes as well: $0 hard"
        echo "  To remove volumes and images: $0 clean"
        ;;
esac
