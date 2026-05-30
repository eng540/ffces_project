# ============================================================
# Expenses API Routes - Full Implementation
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models import Expense, Custody, Project, Party
from app.schemas import ExpenseCreate, ExpenseResponse, ExpenseApproval, PaginatedResponse
from app.services.balance_service import BalanceService
from app.services.approval_service import ApprovalService
from app.services.audit_service import AuditService
from app.services.ledger_service import LedgerService

router = APIRouter()

@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    data: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role(["custodian", "field_supervisor", "accountant", "financial_manager", "super_admin"]))
):
    custody_query = select(Custody).where(Custody.id == data.custody_id)
    result = await db.execute(custody_query)
    custody = result.scalar_one_or_none()
    if not custody or custody.status != "open":
        raise HTTPException(status_code=400, detail="Custody not found or not open")

    balance_service = BalanceService(db)
    balance = await balance_service.get_custody_balance(data.custody_id)
    remaining = balance["remaining_balance"]

    if float(data.amount) > remaining:
        raise HTTPException(status_code=400, detail=f"Expense exceeds remaining balance: {remaining}")

    expense = Expense(
        custody_id=data.custody_id,
        project_id=data.project_id,
        amount=data.amount,
        currency=data.currency,
        category=data.category,
        description=data.description,
        expense_date=data.expense_date,
        beneficiary_type=data.beneficiary_type,
        party_id=data.party_id,
        beneficiary_name=data.beneficiary_name,
        location=data.location,
        created_by=current_user.id,
        status="pending_approval"
    )

    db.add(expense)
    await db.flush()
    await db.refresh(expense)

    approval = ApprovalService(db)
    await approval.create_approval_workflow(
        entity_type="expense",
        entity_id=expense.id,
        amount=data.amount,
        org_id=current_user.organization_id,
        requested_by=current_user.id
    )

    audit = AuditService(db)
    await audit.log_create(
        user_id=current_user.id,
        entity_type="expense",
        entity_id=expense.id,
        data={"amount": float(data.amount), "category": data.category, "custody_id": str(data.custody_id)}
    )

    return expense

@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(expense_id: UUID, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    query = select(Expense).where(Expense.id == expense_id)
    result = await db.execute(query)
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense

@router.patch("/{expense_id}/approve")
async def approve_expense(
    expense_id: UUID,
    data: ExpenseApproval,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role(["accountant", "financial_manager", "super_admin"]))
):
    query = select(Expense).where(Expense.id == expense_id)
    result = await db.execute(query)
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.status != "pending_approval":
        raise HTTPException(status_code=400, detail="Expense not pending approval")

    if data.status == "approved":
        expense.status = "approved"
        expense.approved_by = current_user.id
        expense.approved_at = datetime.now()
        ledger = LedgerService(db)
        await ledger.create_expense_entry(expense, current_user.id)
        message = "Expense approved"
    else:
        expense.status = "rejected"
        expense.rejection_reason = data.rejection_reason
        message = "Expense rejected"

    audit = AuditService(db)
    await audit.log_approve(
        user_id=current_user.id,
        entity_type="expense",
        entity_id=expense.id,
        data={"status": data.status, "reason": data.rejection_reason}
    )
    await db.flush()

    return {"message": message, "expense_id": str(expense_id), "status": expense.status}

@router.get("", response_model=PaginatedResponse)
async def list_expenses(
    custody_id: Optional[UUID] = Query(None),
    project_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = select(Expense).order_by(desc(Expense.created_at))
    if custody_id: query = query.where(Expense.custody_id == custody_id)
    if project_id: query = query.where(Expense.project_id == project_id)
    if status: query = query.where(Expense.status == status)

    count_result = await db.execute(query)
    total = len(count_result.scalars().all())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size}
