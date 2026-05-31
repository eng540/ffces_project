#!/bin/bash
set -euo pipefail

# ============================================
# FFCES Database & Storage Restore Script
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

# --- Check argument ---
if [ -z "${1:-}" ]; then
    echo "Usage: $0 <backup_directory>"
    echo ""
    echo "Example:"
    echo "  $0 ./backups/20240101_120000"
    echo "  $0 ./backups/20240101_120000/database.dump"
    echo ""
    echo "Available backups:"
    ls -d ./backups/*/ 2>/dev/null || echo "  (none found)"
    exit 1
fi

BACKUP_PATH="$1"

# Support passing either the backup directory or the dump file directly
if [ -f "$BACKUP_PATH" ]; then
    BACKUP_DIR="$(dirname "$BACKUP_PATH")"
else
    BACKUP_DIR="$BACKUP_PATH"
fi

if [ ! -d "$BACKUP_DIR" ]; then
    echo "ERROR: Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "========================================"
echo "  FFCES Restore"
echo "========================================"
echo ""
echo "  Source: $BACKUP_DIR"
echo ""

# --- Show backup info ---
if [ -f "$BACKUP_DIR/backup_info.txt" ]; then
    echo "  Backup Info:"
    echo "  -------------------------------------------"
    cat "$BACKUP_DIR/backup_info.txt"
    echo "  -------------------------------------------"
    echo ""
fi

# --- Confirmation ---
echo "[WARN] This will OVERWRITE current data!"
echo "[WARN] Make sure you have a current backup before proceeding."
echo ""
read -rp "Type 'yes' to confirm restore: " confirm
if [ "$confirm" != "yes" ]; then
    echo "Restore aborted."
    exit 0
fi

echo ""

# --- Verify checksums if available ---
if [ -f "$BACKUP_DIR/checksums.sha256" ]; then
    echo "[RESTORE] Verifying backup integrity..."
    cd "$BACKUP_DIR"
    if sha256sum --check checksums.sha256 2>/dev/null; then
        echo "  -> Checksums verified."
    else
        echo "[WARN] Some checksums failed. Proceed with caution."
        read -rp "Continue anyway? (yes/no): " continue_anyway
        if [ "$continue_anyway" != "yes" ]; then
            echo "Restore aborted."
            exit 1
        fi
    fi
    cd "$PROJECT_DIR"
fi

# --- Check services are running ---
echo "[RESTORE] Verifying services..."
if ! $COMPOSE_CMD ps db | grep -q "Up\|running\|healthy"; then
    echo "[ERROR] Database service is not running. Start services first:"
    echo "  $COMPOSE_CMD up -d db"
    exit 1
fi

# --- Restore PostgreSQL (prefer custom dump) ---
if [ -f "$BACKUP_DIR/database.dump" ]; then
    echo "[RESTORE] Restoring database from custom dump..."
    # Drop and recreate
    $COMPOSE_CMD exec -T db dropdb -U ffces_user --if-exists ffces_db 2>/dev/null || true
    $COMPOSE_CMD exec -T db createdb -U ffces_user ffces_db
    cat "$BACKUP_DIR/database.dump" | $COMPOSE_CMD exec -T db pg_restore -U ffces_user -d ffces_db --clean --if-exists -v
    echo "  -> Database restored from custom dump."
elif [ -f "$BACKUP_DIR/database.sql.gz" ]; then
    echo "[RESTORE] Restoring database from SQL dump..."
    # Drop and recreate
    $COMPOSE_CMD exec -T db dropdb -U ffces_user --if-exists ffces_db 2>/dev/null || true
    $COMPOSE_CMD exec -T db createdb -U ffces_user ffces_db
    gunzip -c "$BACKUP_DIR/database.sql.gz" | $COMPOSE_CMD exec -T db psql -U ffces_user ffces_db -v ON_ERROR_STOP=1
    echo "  -> Database restored from SQL dump."
else
    echo "[WARN] No database backup file found in $BACKUP_DIR"
fi

# --- Restore environment (optional) ---
if [ -f "$BACKUP_DIR/env.backup" ]; then
    echo ""
    read -rp "Restore .env from backup? (yes/no): " restore_env
    if [ "$restore_env" = "yes" ]; then
        cp "$BACKUP_DIR/env.backup" .env
        echo "  -> .env restored."
        echo "  -> Run '$COMPOSE_CMD up -d' to apply new environment."
    fi
fi

echo ""
echo "========================================"
echo "  Restore Complete"
echo "========================================"
echo ""
echo "  Consider restarting services:"
echo "    $COMPOSE_CMD restart"
echo "========================================"
