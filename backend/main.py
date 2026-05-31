# ============================================
# FFCES - نقطة الدخول الرئيسية (Main Application Entry Point)
# ============================================
"""
Field Financial Custody & Entitlements System
نظام العهد المالية والاستحقاقات الميدانية

Production-ready FastAPI backend with:
- Async PostgreSQL (asyncpg + SQLAlchemy 2.0)
- JWT Authentication (python-jose + passlib)
- Redis caching
- Celery background tasks
- Multi-level approval workflows
- Full Arabic RTL support
"""
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import Base, engine, get_db

# ===== Import Auth Router (from app.core) =====
from app.core.auth import router as auth_router

# ===== Import API V1 Routers (from app.api.v1) =====
from app.api.v1 import (
    custodies_router,
    expenses_router,
    work_records_router,
    entitlements_router,
    payments_router,
    settlements_router,
    reports_router,
    dashboard_router,
    parties_router,
)


# ===== Application Lifespan =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    دورة حياة التطبيق
    Application startup and shutdown events
    """
    # Startup
    print("🚀 FFCES Starting up...")
    print(f"   Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'configured'}")
    print(f"   Debug: {settings.DEBUG}")
    print(f"   CORS origins: {settings.cors_origins_list}")

    # Try connecting to Redis
    try:
        from app.core.redis_client import redis_client
        await redis_client.connect()
        print("   Redis: connected")
    except Exception as e:
        print(f"   Redis: not available ({e.__class__.__name__})")

    yield

    # Shutdown
    print("👋 FFCES Shutting down...")
    try:
        from app.core.redis_client import redis_client
        await redis_client.disconnect()
        print("   Redis: disconnected")
    except Exception:
        pass


# ===== Create FastAPI Application =====
app = FastAPI(
    title="FFCES - نظام العهد المالية والاستحقاقات",
    title_en="Field Financial Custody & Entitlements System",
    description="""
    ## نظام العهد المالية والاستحقاقات الميدانية
    Field Financial Custody & Entitlements System (FFCES)

    ### الميزات الرئيسية:
    - 🏦 إدارة العهد المالية (Financial Custodies)
    - 💰 تسجيل المصروفات (Expense Tracking)
    - 📊 لوحة قيادة تفاعلية (Interactive Dashboard)
    - ✅ سير موافقات متعدد المستويات (Multi-level Approvals)
    - 📝 تسوية العهد (Custody Settlements)
    - 💵 إدارة المدفوعات (Payment Management)
    - 🏗️ إدارة المشاريع (Project Management)
    - 👷 سجلات العمل الميداني (Field Work Records)
    - 📋 تقارير مالية شاملة (Financial Reports)
    - 🔒 مصادقة JWT آمنة (Secure JWT Authentication)
    - 📜 سجل تدقيق كامل (Full Audit Trail)
    - 📐 شجرة حسابات محاسبية (Chart of Accounts)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


# ===== CORS Middleware =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Register Routers =====
app.include_router(auth_router, prefix="/api/v1")
app.include_router(custodies_router, prefix="/api/v1")
app.include_router(expenses_router, prefix="/api/v1")
app.include_router(work_records_router, prefix="/api/v1")
app.include_router(entitlements_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(settlements_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(parties_router, prefix="/api/v1")


# ===== Health Check =====
@app.get("/api/v1/health", tags=["الصحة"])
async def health_check():
    """
    فحص حالة النظام
    System health check endpoint
    """
    return {
        "status": "healthy",
        "service": "FFCES Backend",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": "configured",
            "redis": "configured",
            "celery": "configured",
        },
    }


# ===== Global Exception Handler =====
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    معالج الأخطاء العام
    Global exception handler for unhandled errors
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": "خطأ في الخادم / Internal Server Error",
            "detail": str(exc) if settings.DEBUG else "حدث خطأ غير متوقع",
            "path": str(request.url),
        },
    )


# ── Serve Frontend Static Files ──
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(os.path.join(STATIC_DIR, "index.html")):
    # Mount _next static assets
    next_dir = os.path.join(STATIC_DIR, "_next")
    if os.path.isdir(next_dir):
        app.mount("/_next", StaticFiles(directory=next_dir), name="next_static")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(STATIC_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
