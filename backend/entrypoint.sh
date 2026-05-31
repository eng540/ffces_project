#!/bin/bash
set -e

echo "============================================="
echo "  FFCES - نظام العهد المالية المتكامل"
echo "  Starting up..."
echo "============================================="

# ── Install email-validator if missing (Pydantic EmailStr dependency) ──
echo "[0] Checking dependencies..."
pip install email-validator 2>/dev/null || true

# ── Fix DATABASE_URL ──
# Railway sometimes provides malformed URLs with template artifacts like }} or ${}
# Use separate Python script to avoid bash substitution conflicts with regex patterns
if [ -n "$DATABASE_URL" ]; then
    echo "[1] Cleaning DATABASE_URL..."
    CLEAN_URL=$(python3 /app/clean_url.py) && export DATABASE_URL="$CLEAN_URL"
    echo "  DATABASE_URL cleaned successfully"
fi

# ── Wait for PostgreSQL ──
# Use DB_HOST and DB_PORT variables (NOT PORT!) to avoid overwriting Railway's PORT
if [ -n "$DATABASE_URL" ]; then
    echo "[2/4] Waiting for PostgreSQL..."

    # Extract host:port from DATABASE_URL using Python (avoids bash regex issues)
    DB_CONN=$(python3 -c "
import os, re
url = os.environ.get('DATABASE_URL', '')
m = re.search(r'@([^:]+):(\d+)/', url)
print(f'{m.group(1)}:{m.group(2)}' if m else 'localhost:5432')
")
    DB_HOST="${DB_CONN%%:*}"
    DB_PORT="${DB_CONN##*:}"

    MAX_RETRIES=30
    COUNT=0
    until python3 -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('$DB_HOST', $DB_PORT)); s.close()" 2>/dev/null; do
        COUNT=$((COUNT+1))
        if [ $COUNT -ge $MAX_RETRIES ]; then
            echo "  WARNING: PostgreSQL not ready after 60s. Continuing..."
            break
        fi
        echo "  Waiting for PostgreSQL... ($COUNT/$MAX_RETRIES)"
        sleep 2
    done
    echo "  PostgreSQL check complete."
fi

# ── Check Redis (non-blocking) ──
echo "[3/4] Checking Redis..."
python3 -c "
import redis, os
url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
try:
    r = redis.from_url(url, socket_timeout=3)
    r.ping()
    print('  Redis: connected')
except Exception as e:
    print(f'  Redis: not available ({e})')
" 2>/dev/null || echo "  Redis: not available"

# ── Run Alembic migrations ──
echo "[4/4] Running Alembic migrations..."
cd /app
alembic upgrade head 2>&1 || {
    echo "  WARNING: Migration failed - but continuing to start server."
    echo "  Tables may already exist from a previous run."
}
echo "  Migrations completed successfully."

# ── Ensure Admin User exists with correct password ──
# This is needed because the seed migration uses ON CONFLICT DO NOTHING,
# so if the migration was already applied with a wrong hash, re-running won't fix it.
echo "[5/5] Ensuring admin user..."
python3 /app/ensure_admin.py

echo "============================================="
echo "  Starting FFCES server on port ${PORT:-8000}..."
echo "  DATABASE_URL ready"
echo "============================================="
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
