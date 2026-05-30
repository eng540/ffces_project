# ============================================================
# Dashboard API Routes
# ============================================================

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from datetime import datetime, date, timedelta
from uuid import UUID

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models import Custody, Expense, Payment, Party, Project, Entitlement
from app.schemas import DashboardSummary, DashboardAlert

router = APIRouter()

@router.get("/summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    org_id = current_user.organization_id
    today = date.today()

    # Total custodies
    custodies_query = select(func.count(Custody.id)).where(Custody.holder.has(organization_id=org_id))
    total_custodies = (await db.execute(custodies_query)).scalar() or 0

    # Open custodies
    open_query = select(func.count(Custody.id)).where(and_(Custody.holder.has(organization_id=org_id), Custody.status == "open"))
    open_custodies = (await db.execute(open_query)).scalar() or 0

    # Overdue custodies
    overdue_query = select(func.count(Custody.id)).where(and_(Custody.holder.has(organization_id=org_id), Custody.status == "overdue"))
    overdue_custodies = (await db.execute(overdue_query)).scalar() or 0

    # Today's expenses
    expenses_query = select(func.sum(Expense.amount)).where(and_(Expense.created_by.has(organization_id=org_id), func.date(Expense.created_at) == today, Expense.status == "approved"))
    total_expenses_today = (await db.execute(expenses_query)).scalar() or 0

    # Today's payments
    payments_query = select(func.sum(Payment.amount)).where(and_(Payment.paid_by.has(organization_id=org_id), func.date(Payment.paid_at) == today))
    total_payments_today = (await db.execute(payments_query)).scalar() or 0

    # Pending approvals (simplified)
    pending_approvals = 0

    # Total parties
    parties_query = select(func.count(Party.id)).where(Party.organization_id == org_id)
    total_parties = (await db.execute(parties_query)).scalar() or 0

    # Active projects
    projects_query = select(func.count(Project.id)).where(and_(Project.organization_id == org_id, Project.status == "active"))
    active_projects = (await db.execute(projects_query)).scalar() or 0

    return {
        "total_custodies": total_custodies,
        "open_custodies": open_custodies,
        "overdue_custodies": overdue_custodies,
        "total_expenses_today": float(total_expenses_today) if total_expenses_today else 0,
        "total_payments_today": float(total_payments_today) if total_payments_today else 0,
        "pending_approvals": pending_approvals,
        "total_parties": total_parties,
        "active_projects": active_projects
    }

@router.get("/alerts")
async def get_dashboard_alerts(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    org_id = current_user.organization_id
    alerts = []

    # Overdue custodies
    overdue_query = select(Custody).where(and_(Custody.holder.has(organization_id=org_id), Custody.status == "overdue")).limit(5)
    result = await db.execute(overdue_query)
    for custody in result.scalars().all():
        alerts.append({
            "type": "overdue_custody",
            "severity": "high",
            "message": f"عهدة {custody.custody_number} متأخرة",
            "entity_type": "custody",
            "entity_id": custody.id,
            "created_at": datetime.now()
        })

    # Low balance parties
    # This would need a more complex query in production

    return alerts
