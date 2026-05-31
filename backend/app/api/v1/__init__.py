# ============================================
# FFCES - واجهة برمجة التطبيقات - الإصدار 1
# ============================================
from app.api.v1.custodies import router as custodies_router
from app.api.v1.expenses import router as expenses_router
from app.api.v1.work_records import router as work_records_router
from app.api.v1.entitlements import router as entitlements_router
from app.api.v1.payments import router as payments_router
from app.api.v1.settlements import router as settlements_router
from app.api.v1.reports import router as reports_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.parties import router as parties_router

__all__ = [
    "custodies_router",
    "expenses_router",
    "work_records_router",
    "entitlements_router",
    "payments_router",
    "settlements_router",
    "reports_router",
    "dashboard_router",
    "parties_router",
]
