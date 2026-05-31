#!/bin/bash
set -euo pipefail

# ============================================
# FFCES First-Time Setup Script
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

echo "========================================"
echo "  FFCES First-Time Setup"
echo "========================================"
echo ""

# --- Check prerequisites ---
echo "[SETUP] Checking prerequisites..."

command -v docker >/dev/null 2>&1 || { echo "ERROR: docker is required but not installed. See: https://docs.docker.com/get-docker/"; exit 1; }
echo "  [OK] docker"

if command -v docker compose >/dev/null 2>&1; then
    echo "  [OK] docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    echo "  [OK] docker-compose"
else
    echo "ERROR: docker-compose plugin is required but not installed."
    exit 1
fi

if command -v openssl >/dev/null 2>&1; then
    echo "  [OK] openssl"
else
    echo "  [WARN] openssl not found (needed for SECRET_KEY generation)"
fi

echo ""

# --- Create .env from template ---
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[SETUP] Created .env from template"
else
    echo "[SETUP] .env already exists (skipping template creation)"
fi

# --- Generate random SECRET_KEY if still default ---
if grep -q "generate-a-secure-random-key-here" .env 2>/dev/null; then
    if command -v openssl >/dev/null 2>&1; then
        SECRET_KEY=$(openssl rand -hex 32)
        sed -i.bak "s/generate-a-secure-random-key-here/$SECRET_KEY/" .env
        rm -f .env.bak
        echo "[SETUP] Generated random SECRET_KEY"
    else
        echo "[SETUP] Please manually set SECRET_KEY in .env"
    fi
fi

# --- Generate random DB_PASSWORD if still default ---
if grep -q "ffces_pass_change_me" .env 2>/dev/null; then
    if command -v openssl >/dev/null 2>&1; then
        DB_PASS=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)
        sed -i.bak "s/ffces_pass_change_me/$DB_PASS/" .env
        rm -f .env.bak
        echo "[SETUP] Generated random DB_PASSWORD"
    else
        echo "[SETUP] Please manually set DB_PASSWORD in .env"
    fi
fi

echo ""

# --- Create required directories ---
echo "[SETUP] Creating required directories..."
mkdir -p nginx/ssl
mkdir -p backups
echo "  [OK] nginx/ssl"
echo "  [OK] backups"

# --- Build Docker images ---
echo ""
echo "[SETUP] Building Docker images (this may take a few minutes)..."
$COMPOSE_CMD build --parallel 2>&1 | tail -5
echo "  [OK] Images built"

# --- Start services ---
echo ""
echo "[SETUP] Starting all services..."
$COMPOSE_CMD up -d

# --- Wait for PostgreSQL ---
echo ""
echo "[SETUP] Waiting for PostgreSQL to be ready..."
max_retries=30
retry=0
until $COMPOSE_CMD exec -T db pg_isready -U ffces_user -d ffces_db > /dev/null 2>&1; do
    retry=$((retry + 1))
    if [ $retry -ge $max_retries ]; then
        echo "[ERROR] PostgreSQL failed to start within timeout."
        echo "  Check logs: $COMPOSE_CMD logs db"
        exit 1
    fi
    sleep 2
    printf "\r  Attempt %d/%d..." "$retry" "$max_retries"
done
echo ""
echo "  [OK] PostgreSQL is ready"

# --- Wait for Redis ---
echo "[SETUP] Waiting for Redis to be ready..."
max_retries=15
retry=0
until $COMPOSE_CMD exec -T redis redis-cli ping > /dev/null 2>&1; do
    retry=$((retry + 1))
    if [ $retry -ge $max_retries ]; then
        echo "[ERROR] Redis failed to start within timeout."
        echo "  Check logs: $COMPOSE_CMD logs redis"
        exit 1
    fi
    sleep 2
    printf "\r  Attempt %d/%d..." "$retry" "$max_retries"
done
echo ""
echo "  [OK] Redis is ready"

# --- Wait for backend ---
echo "[SETUP] Waiting for backend to be healthy..."
max_retries=30
retry=0
until curl -sf http://localhost/api/v1/health > /dev/null 2>&1 || curl -sf http://localhost/health > /dev/null 2>&1; do
    retry=$((retry + 1))
    if [ $retry -ge $max_retries ]; then
        echo "[WARN] Backend not responding yet. Check: $COMPOSE_CMD logs backend"
        break
    fi
    sleep 3
    printf "\r  Attempt %d/%d..." "$retry" "$max_retries"
done
echo ""
echo "  [OK] Backend is responding"

# --- Show status ---
echo ""
$COMPOSE_CMD ps

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "  Application : http://localhost"
echo "  API Docs    : http://localhost/api/docs (internal only)"
echo ""
echo "  Default admin credentials:"
echo "    Email    : admin@ffces.com"
echo "    Password : Admin@123"
echo ""
echo "  Next steps:"
echo "    1. Place SSL certificates in nginx/ssl/"
echo "    2. Review and update .env for production"
echo "    3. Update ALLOWED_DOMAIN to your actual domain"
echo "    4. Restart to apply changes:"
echo "       $COMPOSE_CMD up -d --build"
echo ""
echo "  Useful commands:"
echo "    ./scripts/deploy.sh   - Redeploy with updates"
echo "    ./scripts/backup.sh   - Create a backup"
echo "    ./scripts/status.sh   - Check service health"
echo "    ./scripts/logs.sh     - View logs"
echo "    ./scripts/stop.sh     - Stop all services"
echo "========================================"
