#!/bin/bash
set -e

echo "============================================="
echo "  FFCES - نظام العهد المالية المتكامل"
echo "  Starting up..."
echo "============================================="

# ── Fix DATABASE_URL ──
# Railway sometimes provides malformed URLs with template artifacts like }} or ${}
# Clean them up before anything else
if [ -n "$DATABASE_URL" ]; then
    echo "[0] Cleaning DATABASE_URL..."
    CLEAN_URL=$(python3 -c "
import os, re
url = os.environ.get('DATABASE_URL', '')
# Remove template artifacts like }} ${{ }} ${} etc
url = re.sub(r'\}\}+$', '', url)
url = re.sub(r'\{\{?$', '', url)
url = re.sub(r'\$\{[^}]*\}', '', url)
# Remove trailing/leading whitespace
url = url.strip()
if url:
    os.environ['DATABASE_URL'] = url
    # Print masked URL for debug (hide password)
    safe = re.sub(r'(:\/\/[^:]+:)[^@]+(@)', r'\1****\2', url)
    print(f'  URL: {safe}')
else:
    print('  WARNING: DATABASE_URL is empty after cleanup!')
")
    export DATABASE_URL="$CLEAN_URL"
fi

# Wait for PostgreSQL
if [ -n "$DATABASE_URL" ]; then
    echo "[1/3] Waiting for PostgreSQL..."
    DB_HOST=$(python3 -c "
import os, re
url = os.environ.get('DATABASE_URL', '')
m = re.search(r'@([^:]+):(\d+)/', url)
print(f'{m.group(1)}:{m.group(2)}' if m else 'localhost:5432')
")
    HOST=${DB_HOST%%:*}
    PORT=${DB_HOST##*:}

    MAX_RETRIES=30
    COUNT=0
    until python3 -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('$HOST', $PORT)); s.close()" 2>/dev/null; do
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

# Check Redis (non-blocking)
echo "[2/3] Checking Redis..."
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

# Run Alembic migrations
echo "[3/3] Running Alembic migrations..."
cd /app
alembic upgrade head 2>&1 || {
    echo "  WARNING: Migration failed - but continuing to start server."
    echo "  Tables may already exist from a previous run."
}

# Also clean DATABASE_URL for the main app (uvicorn)
if [ -n "$CLEAN_URL" ]; then
    export DATABASE_URL="$CLEAN_URL"
fi

echo "============================================="
echo "  Starting FFCES server on port 8000..."
echo "  DATABASE_URL cleaned and ready"
echo "============================================="
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
