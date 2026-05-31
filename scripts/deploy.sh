#!/bin/bash
set -euo pipefail

# ============================================
# FFCES Production Deployment Script
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "========================================"
echo "  FFCES Production Deployment"
echo "========================================"
echo ""

# --- Check prerequisites ---
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker is not installed."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || command -v docker compose >/dev/null 2>&1 || { echo "ERROR: docker-compose is not installed."; exit 1; }

# Use the right compose command
if command -v docker compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# --- Check .env ---
if [ ! -f .env ]; then
    echo "[SETUP] Creating .env from .env.example..."
    cp .env.example .env
    echo "[WARN] .env created from template. Please update with production values!"
    echo ""
fi

# --- Validate .env has no default secrets ---
if grep -q "generate-a-secure-random-key-here" .env; then
    echo "[WARN] SECRET_KEY is still set to the default placeholder."
    echo "[WARN] Generate one with: openssl rand -hex 32"
    echo ""
fi

if grep -q "ffces_pass_change_me" .env; then
    echo "[WARN] DB_PASSWORD is still set to the default value."
    echo ""
fi

# --- Pull latest base images ---
echo "[DEPLOY] Pulling latest base images..."
$COMPOSE_CMD pull 2>/dev/null || true
echo ""

# --- Build images ---
echo "[DEPLOY] Building Docker images..."
$COMPOSE_CMD build --parallel
echo ""

# --- Start services ---
echo "[DEPLOY] Starting services..."
$COMPOSE_CMD up -d --remove-orphans
echo ""

# --- Wait for healthy services ---
echo "[DEPLOY] Waiting for services to become healthy..."
timeout=180
elapsed=0
while [ $elapsed -lt $timeout ]; do
    unhealthy=$($COMPOSE_CMD ps --format json 2>/dev/null | grep -c '"Health":"unhealthy"' || true)
    starting=$($COMPOSE_CMD ps --format json 2>/dev/null | grep -c '"Health":"starting"' || true)
    if [ "$unhealthy" -eq 0 ] && [ "$starting" -eq 0 ]; then
        break
    fi
    sleep 5
    elapsed=$((elapsed + 5))
    printf "\r  Waiting... (%ds/%ds)" "$elapsed" "$timeout"
done
echo ""

# --- Service status ---
echo ""
echo "[DEPLOY] Service Status:"
echo "========================================"
$COMPOSE_CMD ps
echo ""

echo "========================================"
echo "  Deployment Complete"
echo "========================================"
echo ""
echo "  Application URL : http://localhost"
echo "  API Endpoint    : http://localhost/api/v1"
echo "  API Docs (int.) : http://localhost/api/docs"
echo ""
echo "  Default admin credentials:"
echo "    Email    : admin@ffces.com"
echo "    Password : Admin@123"
echo ""
echo "  IMPORTANT: Change all default passwords in production!"
echo "========================================"
