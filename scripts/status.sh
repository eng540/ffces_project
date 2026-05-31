#!/bin/bash
set -euo pipefail

# ============================================
# FFCES Service Status Script
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
echo "  FFCES Service Status"
echo "========================================"
echo ""

# --- Service status ---
echo "Services:"
echo "-------------------------------------------"
$COMPOSE_CMD ps
echo ""

# --- Health check ---
echo "Health Check:"
echo "-------------------------------------------"

# Backend
if curl -sf http://localhost/health > /dev/null 2>&1; then
    echo "  Backend API   : HEALTHY  (http://localhost/health)"
else
    echo "  Backend API   : UNHEALTHY or not reachable"
fi

# Frontend
if curl -sf http://localhost:3000 > /dev/null 2>&1; then
    echo "  Frontend      : HEALTHY  (http://localhost:3000)"
else
    echo "  Frontend      : UNHEALTHY or not reachable"
fi

# Database
if $COMPOSE_CMD exec -T db pg_isready -U ffces_user -d ffces_db > /dev/null 2>&1; then
    DB_SIZE=$($COMPOSE_CMD exec -T db psql -U ffces_user -d ffces_db -t -c "SELECT pg_size_pretty(pg_database_size('ffces_db'));" 2>/dev/null | tr -d ' ' || echo "unknown")
    echo "  PostgreSQL    : HEALTHY  (size: $DB_SIZE)"
else
    echo "  PostgreSQL    : UNHEALTHY or not reachable"
fi

# Redis
if $COMPOSE_CMD exec -T redis redis-cli ping > /dev/null 2>&1; then
    REDIS_MEMORY=$($COMPOSE_CMD exec -T redis redis-cli info memory 2>/dev/null | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r' || echo "unknown")
    echo "  Redis         : HEALTHY  (memory: $REDIS_MEMORY)"
else
    echo "  Redis         : UNHEALTHY or not reachable"
fi

echo ""

# --- Resource usage ---
echo "Resource Usage:"
echo "-------------------------------------------"
if docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>/dev/null | grep -i ffces; then
    :
else
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>/dev/null | head -1
    echo "  (no FFCES containers found)"
fi

echo ""

# --- Volume usage ---
echo "Volume Usage:"
echo "-------------------------------------------"
docker volume ls --filter "label=com.docker.compose.project" --format "table {{.Name}}" 2>/dev/null | head -10

echo ""
echo "========================================"
