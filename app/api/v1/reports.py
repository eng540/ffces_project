# ============================================================
# Reports API Routes
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from typing import Optional
from uuid import UUID
from datetime import date

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models import Custody, Expense, Payment, Party, Project, Entitlement, Settlement
from app.services.balance_service import BalanceService

router = APIRouter()

@router.get("/custody-statement")
async def custody_statement(
    custody_id: UUID,
    format: str = Query("json"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    balance_service = BalanceService(db)
    balance = await balance_service.get_custody_balance(custody_id)

    custody_query = select(Custody).where(Custody.id == custody_id)
    result = await db.execute(custody_query)
    custody = result.scalar_one_or_none()

    expenses_query = select(Expense).where(Expense.custody_id == custody_id).order_by(desc(Expense.expense_date))
    result = await db.execute(expenses_query)
    expenses = result.scalars().all()

    settlements_query = select(Settlement).where(Settlement.custody_id == custody_id).order_by(desc(Settlement.created_at))
    result = await db.execute(settlements_query)
    settlements = result.scalars().all()

    return {
        "custody": custody,
        "balance": balance,
        "expenses": expenses,
        "settlements": settlements,
        "format": format
    }

@router.get("/party-ledger")
async def party_ledger(
    party_id: UUID,
    project_id: Optional[UUID] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    format: str = Query("json"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    balance_service = BalanceService(db)
    balance = await balance_service.get_party_balance(party_id, project_id)

    party_query = select(Party).where(Party.id == party_id)
    result = await db.execute(party_query)
    party = result.scalar_one_or_none()

    entitlements_query = select(Entitlement).where(Entitlement.party_id == party_id).order_by(desc(Entitlement.period_end))
    if project_id: entitlements_query = entitlements_query.where(Entitlement.project_id == project_id)
    result = await db.execute(entitlements_query)
    entitlements = result.scalars().all()

    payments_query = select(Payment).where(Payment.party_id == party_id).order_by(desc(Payment.paid_at))
    if project_id: payments_query = payments_query.where(Payment.project_id == project_id)
    result = await db.execute(payments_query)
    payments = result.scalars().all()

    return {
        "party": party,
        "balance": balance,
        "entitlements": entitlements,
        "payments": payments,
        "format": format
    }

@router.get("/project-summary")
async def project_summary(
    project_id: UUID,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    format: str = Query("json"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    balance_service = BalanceService(db)
    summary = await balance_service.get_project_summary(project_id)

    project_query = select(Project).where(Project.id == project_id)
    result = await db.execute(project_query)
    project = result.scalar_one_or_none()

    # Expenses by category
    expenses_query = select(Expense.category, func.sum(Expense.amount)).where(
        and_(Expense.project_id == project_id, Expense.status == "approved")
    ).group_by(Expense.category)
    result = await db.execute(expenses_query)
    expenses_by_category = [{"category": cat, "amount": float(amt)} for cat, amt in result.all()]

    return {
        "project": project,
        "summary": summary,
        "expenses_by_category": expenses_by_category,
        "format": format
    }

@router.get("/open-custodies")
async def open_custodies_report(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role(["financial_manager", "accountant", "super_admin"]))
):
    query = select(Custody).where(Custody.status.in_(["open", "overdue", "partially_settled"])).order_by(desc(Custody.issued_at))
    result = await db.execute(query)
    custodies = result.scalars().all()

    balance_service = BalanceService(db)
    report = []
    for custody in custodies:
        balance = await balance_service.get_custody_balance(custody.id)
        report.append({
            "custody": custody,
            "balance": balance
        })

    return {"total": len(report), "custodies": report}
