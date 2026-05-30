# ============================================================
# FFCES - Field Financial Custody & Entitlements System
# FastAPI Backend - Main Application
# ============================================================

from fastapi import FastAPI, Depends, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
from app.core.config import settings
from app.core.database import engine, Base, get_db
from app.api.v1 import auth, custodies, expenses, parties, work_records, entitlements, payments, settlements, reports, dashboard
from app.services.audit_service import AuditService
from app.core.redis_client import redis_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("FFCES starting up...")
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.create_all)
        pass
    await redis_client.connect()
    logger.info("FFCES startup complete")
    yield
    # Shutdown
    logger.info("FFCES shutting down...")
    await redis_client.disconnect()
    await engine.dispose()

app = FastAPI(
    title="FFCES - Field Financial Custody & Entitlements System",
    description="نظام إدارة العهد والمستحقات والمصروفات الميدانية",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "error_id": str(uuid.uuid4())}
    )

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(custodies.router, prefix="/api/v1/custodies", tags=["Custodies"])
app.include_router(expenses.router, prefix="/api/v1/expenses", tags=["Expenses"])
app.include_router(parties.router, prefix="/api/v1/parties", tags=["Parties"])
app.include_router(work_records.router, prefix="/api/v1/work-records", tags=["Work Records"])
app.include_router(entitlements.router, prefix="/api/v1/entitlements", tags=["Entitlements"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments"])
app.include_router(settlements.router, prefix="/api/v1/settlements", tags=["Settlements"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "FFCES", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
