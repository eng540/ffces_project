#!/bin/bash
set -euo pipefail

# ============================================
# FFCES Database & Storage Backup Script
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

BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "========================================"
echo "  FFCES Backup"
echo "========================================"
echo ""

# --- Check services are running ---
if ! $COMPOSE_CMD ps db | grep -q "Up\|running\|healthy"; then
    echo "[ERROR] Database service is not running. Start services first."
    exit 1
fi

# --- Backup PostgreSQL ---
echo "[BACKUP] Backing up PostgreSQL database..."
$COMPOSE_CMD exec -T db pg_dump -U ffces_user -F c -b -v ffces_db > "$BACKUP_DIR/database.dump" 2>/dev/null
echo "  -> $BACKUP_DIR/database.dump"

# Also create a plain SQL backup for portability
$COMPOSE_CMD exec -T db pg_dump -U ffces_user --clean --if-exists ffces_db > "$BACKUP_DIR/database.sql" 2>/dev/null
gzip "$BACKUP_DIR/database.sql"
echo "  -> $BACKUP_DIR/database.sql.gz"

# --- Backup environment config ---
echo "[BACKUP] Backing up environment configuration..."
if [ -f .env ]; then
    cp .env "$BACKUP_DIR/env.backup"
    echo "  -> $BACKUP_DIR/env.backup"
fi

# --- Backup MinIO metadata ---
echo "[BACKUP] Backing up MinIO storage info..."
if $COMPOSE_CMD ps minio | grep -q "Up\|running\|healthy"; then
    $COMPOSE_CMD exec -T minio mc admin info local > "$BACKUP_DIR/minio_info.txt" 2>&1 || true
    # List buckets
    $COMPOSE_CMD exec -T minio mc ls local/ > "$BACKUP_DIR/minio_buckets.txt" 2>&1 || true
    echo "  -> $BACKUP_DIR/minio_info.txt"
fi

# --- Generate checksums ---
echo "[BACKUP] Generating checksums..."
cd "$BACKUP_DIR"
sha256sum * > checksums.sha256
cd "$PROJECT_DIR"

# --- Record backup info ---
cat > "$BACKUP_DIR/backup_info.txt" << EOF
FFCES Backup
============
Date: $(date -Iseconds)
Hostname: $(hostname)
Docker Compose: $($COMPOSE_CMD version --short 2>/dev/null || echo "unknown")
Database size: $(docker exec ffces-db du -sh /var/lib/postgresql/data 2>/dev/null | cut -f1 || echo "unknown")
Files:
$(ls -lh "$BACKUP_DIR")
EOF

echo ""
echo "========================================"
echo "  Backup Complete"
echo "========================================"
echo ""
echo "  Location: $BACKUP_DIR"
echo "  Files:"
ls -lh "$BACKUP_DIR"
echo ""
echo "  To restore:"
echo "    ./scripts/restore.sh $BACKUP_DIR"
echo "========================================"
