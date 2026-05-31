# ============================================
# FFCES - لوحة القيادة (Dashboard API)
# ============================================
"""
واجهة برمجة تطبيقات لوحة القيادة
API endpoints for the main dashboard
"""
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models import (
    User, Custody, Expense, Settlement, Payment, Entitlement,
    WorkRecord, Project, ApprovalWorkflow,
)

router = APIRouter(prefix="/dashboard", tags=["لوحة القيادة"])


@router.get("")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    البيانات الرئيسية للوحة القيادة
    Main dashboard data for the current user
    """
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # ----- Custody Stats -----
    total_custodies = (await db.execute(
        select(func.count(Custody.id))
    )).scalar() or 0

    active_custodies = (await db.execute(
        select(func.count(Custody.id)).where(Custody.status == "active")
    )).scalar() or 0

    total_custody_amount = (await db.execute(
        select(func.coalesce(func.sum(Custody.amount), 0))
    )).scalar() or Decimal("0")

    # Overdue custodies
    overdue_custodies = (await db.execute(
        select(func.count(Custody.id)).where(
            and_(
                Custody.status.in_(["active", "partially_settled"]),
                Custody.due_date.isnot(None),
                Custody.due_date < now,
            )
        )
    )).scalar() or 0

    # ----- Expense Stats -----
    pending_expenses = (await db.execute(
        select(func.count(Expense.id)).where(Expense.status == "pending")
    )).scalar() or 0

    # ----- Settlement Stats -----
    pending_settlements = (await db.execute(
        select(func.count(Settlement.id)).where(Settlement.status == "pending")
    )).scalar() or 0

    # ----- Approvals (FIX: dynamic count) -----
    pending_approvals = 0
    try:
        pending_query = select(func.count(ApprovalWorkflow.id)).where(
            and_(
                ApprovalWorkflow.approver_id == current_user.id,
                ApprovalWorkflow.status == "pending",
            )
        )
        pending_approvals = (await db.execute(pending_query)).scalar() or 0
    except Exception:
        pending_approvals = 0

    # ----- Payment Stats (this month) -----
    month_payments = (await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            and_(
                Payment.payment_date >= month_start,
                Payment.status == "completed",
            )
        )
    )).scalar() or Decimal("0")

    # ----- Recent Activities -----
    # Recent custodies
    recent_custodies_query = (
        select(Custody)
        .order_by(Custody.created_at.desc())
        .limit(5)
    )
    recent_custodies_result = await db.execute(recent_custodies_query)
    recent_custodies = recent_custodies_result.scalars().all()

    # Recent expenses
    recent_expenses_query = (
        select(Expense)
        .order_by(Expense.created_at.desc())
        .limit(5)
    )
    recent_expenses_result = await db.execute(recent_expenses_query)
    recent_expenses = recent_expenses_result.scalars().all()

    # ----- Chart Data: Monthly Expenses -----
    monthly_expenses = []
    for i in range(6):
        month_date = now - timedelta(days=30 * (5 - i))
        m_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year + 1, month=1)
        else:
            m_end = m_start.replace(month=m_start.month + 1)

        month_total = (await db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                and_(
                    Expense.expense_date >= m_start,
                    Expense.expense_date < m_end,
                    Expense.status.in_(["approved", "verified"]),
                )
            )
        )).scalar() or Decimal("0")

        monthly_expenses.append({
            "month": m_start.strftime("%Y-%m"),
            "total": float(month_total),
        })

    return {
        "stats": {
            "total_custodies": total_custodies,
            "active_custodies": active_custodies,
            "total_custody_amount": str(total_custody_amount),
            "pending_expenses": pending_expenses,
            "pending_settlements": pending_settlements,
            "pending_approvals": pending_approvals,
            "total_payments_this_month": str(month_payments),
            "overdue_custodies": overdue_custodies,
        },
        "recent_custodies": [
            {
                "id": str(c.id),
                "purpose": c.purpose,
                "amount": str(c.amount),
                "status": c.status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in recent_custodies
        ],
        "recent_expenses": [
            {
                "id": str(e.id),
                "category": e.category,
                "amount": str(e.amount),
                "status": e.status,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in recent_expenses
        ],
        "monthly_expenses_chart": monthly_expenses,
        "generated_at": now.isoformat(),
    }


@router.get("/user-summary")
async def get_user_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ملخص المستخدم - User summary for dashboard"""
    from app.services.balance_service import BalanceService

    custody_summary = await BalanceService.get_user_custody_summary(db, current_user.id)

    # User's recent work records
    recent_work_query = (
        select(WorkRecord)
        .where(WorkRecord.user_id == current_user.id)
        .order_by(WorkRecord.date.desc())
        .limit(5)
    )
    recent_work_result = await db.execute(recent_work_query)
    recent_work = recent_work_result.scalars().all()

    # User's pending entitlements
    pending_entitlements = (await db.execute(
        select(func.count()).select_from(Entitlement).where(
            and_(
                Entitlement.user_id == current_user.id,
                Entitlement.status == "calculated",
            )
        )
    )).scalar() or 0

    return {
        "user": {
            "id": str(current_user.id),
            "full_name": current_user.full_name,
            "role": current_user.role,
        },
        "custody_summary": custody_summary,
        "pending_entitlements": pending_entitlements,
        "recent_work_records": [
            {
                "id": str(w.id),
                "date": w.date.isoformat() if w.date else None,
                "hours_worked": w.hours_worked,
                "status": w.status,
            }
            for w in recent_work
        ],
    }


@router.get("/approvals-pending")
async def get_pending_approvals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """الموافقات المعلقة - Pending approvals for the current user"""
    query = (
        select(ApprovalWorkflow)
        .where(
            and_(
                ApprovalWorkflow.approver_id == current_user.id,
                ApprovalWorkflow.status == "pending",
            )
        )
        .order_by(ApprovalWorkflow.created_at.asc())
        .limit(20)
    )
    result = await db.execute(query)
    workflows = result.scalars().all()

    return {
        "pending_count": len(workflows),
        "approvals": [
            {
                "id": str(w.id),
                "entity_type": w.entity_type,
                "entity_id": str(w.entity_id),
                "approval_level": w.approval_level,
                "threshold_amount": str(w.threshold_amount) if w.threshold_amount else None,
                "created_at": w.created_at.isoformat() if w.created_at else None,
            }
            for w in workflows
        ],
    }
