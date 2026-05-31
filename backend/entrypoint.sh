#!/bin/bash
set -e

echo "============================================="
echo "  FFCES - نظام العهد المالية المتكامل"
echo "  Starting up..."
echo "============================================="

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
alembic upgrade head
if [ $? -eq 0 ]; then
    echo "  Migrations completed successfully."
else
    echo "  ERROR: Migration failed!"
    echo "  Check DATABASE_URL and database connection."
    exit 1
fi

echo "============================================="
echo "  Starting FFCES server on port 8000..."
echo "============================================="
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
