#!/bin/bash
set -euo pipefail

# ============================================
# FFCES Logs Viewer Script
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

SERVICE="${1:-}"
LINES="${2:-100}"

if [ -n "$SERVICE" ]; then
    echo "[LOGS] Showing last $LINES lines for '$SERVICE' (follow mode)..."
    echo "  Press Ctrl+C to exit"
    echo ""
    $COMPOSE_CMD logs --tail="$LINES" -f "$SERVICE"
else
    echo "[LOGS] Showing last $LINES lines for all services (follow mode)..."
    echo "  Press Ctrl+C to exit"
    echo ""
    $COMPOSE_CMD logs --tail="$LINES" -f
fi
