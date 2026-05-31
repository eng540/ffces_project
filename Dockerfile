# ============================================================
# FFCES - Single Web Container (Frontend + Backend)
# PostgreSQL and Redis are external services
# Alembic runs automatically on startup
# ============================================================

# ── Stage 1: Build Frontend (Next.js static export) ──
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
# Override next.config for static export
RUN npx next build

# ── Stage 2: Final Python container ──
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/app/ ./app/
COPY backend/main.py .
COPY backend/alembic.ini .
COPY backend/alembic/ ./alembic/
COPY backend/entrypoint.sh .
COPY backend/clean_url.py .
COPY backend/ensure_admin.py .
RUN chmod +x entrypoint.sh

# Copy frontend static files from build stage
COPY --from=frontend-builder /frontend/out ./static/

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]
