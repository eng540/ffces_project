#!/bin/bash
set -e

echo "============================================="
echo "  FFCES - نظام العهد المالية المتكامل"
echo "  Starting up..."
echo "============================================="

# Install missing email-validator for Pydantic
echo "[0] Installing email-validator..."
pip install email-validator

# ── 1. Clean DATABASE_URL ──
if [ -n "$DATABASE_URL" ]; then
    echo "[0] Cleaning DATABASE_URL..."
    CLEAN_URL=$(python3 /app/clean_url.py)
    if [ -n "$CLEAN_URL" ]; then
        export DATABASE_URL="$CLEAN_URL"
        echo "  DATABASE_URL cleaned successfully"
    else
        echo "  WARNING: Failed to clean DATABASE_URL, using original"
    fi
fi

# ── 2. Fix Alembic migration for asyncpg (split multiple statements) ──
echo "[1/4] Fixing migration for asyncpg compatibility..."
python3 << 'EOF'
import re
file_path = "/app/alembic/versions/001_initial_schema.py"
try:
    with open(file_path, 'r') as f:
        content = f.read()
    pattern = r'op\.execute\(("""|\'\'\')(.*?)\1\)'
    def replacer(match):
        sql_block = match.group(2)
        statements = [s.strip() for s in sql_block.split(';') if s.strip()]
        if len(statements) <= 1:
            return match.group(0)
        new_calls = '\n'.join(f'    op.execute(\"\"\"{stmt}\"\"\")' for stmt in statements)
        return new_calls
    new_content = re.sub(pattern, replacer, content, flags=re.DOTALL)
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print("  Migration fixed: split multiple statements")
    else:
        print("  Migration already compatible or no changes needed")
except Exception as e:
    print(f"  WARNING: Could not fix migration: {e}")
EOF

# ── 3. Wait for PostgreSQL ──
if [ -n "$DATABASE_URL" ]; then
    echo "[2/4] Waiting for PostgreSQL..."
    DB_CONN=$(python3 -c "
import os, re
url = os.environ.get('DATABASE_URL', '')
m = re.search(r'@([^:]+):(\d+)/', url)
print(f'{m.group(1)}:{m.group(2)}' if m else 'localhost:5432')
")
    HOST="${DB_CONN%%:*}"
    PORT="${DB_CONN##*:}"

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

# ── 4. Check Redis ──
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

# ── 5. Run Alembic migrations ──
echo "[4/4] Running Alembic migrations..."
cd /app
if alembic upgrade head; then
    echo "  Migrations completed successfully."
else
    echo "  WARNING: Migration failed - but continuing to start server."
    echo "  Tables may already exist from a previous run."
fi

echo "============================================="
echo "  Starting FFCES server on port 8000..."
echo "  DATABASE_URL ready"
echo "============================================="
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1