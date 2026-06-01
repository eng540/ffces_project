# ============================================
# FFCES - المصروفات (Expenses API)
# ============================================
"""
واجهة برمجة تطبيقات إدارة المصروفات
API endpoints for managing expenses against custodies
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models import User, Expense, Custody
from app.schemas import ExpenseCreate, ExpenseUpdate, PaginatedResponse
from app.services.balance_service import BalanceService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/expenses", tags=["المصروفات"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense_data: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """تسجيل مصروف جديد على عهدة - Record new expense against custody"""
    # Verify custody exists and is active
    custody_query = select(Custody).where(Custody.id == expense_data.custody_id)
    custody_result = await db.execute(custody_query)
    custody = custody_result.scalar_one_or_none()

    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")

    if custody.status not in ["active", "partially_settled"]:
        raise HTTPException(status_code=400, detail="العهدة غير مفعلة للتسجيل")

    # Check remaining balance
    balance_info = await BalanceService.calculate_custody_balance(db, custody.id)
    if expense_data.amount > balance_info["remaining"]:
        raise HTTPException(
            status_code=400,
            detail=f"المبلغ يتجاوز الرصيد المتبقي ({balance_info['remaining']})",
        )

    # Create expense
    expense = Expense(
        **expense_data.model_dump(),
        created_by=current_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(expense)
    await db.flush()
    await db.refresh(expense)

    # Update custody balance status
    try:
        await BalanceService.update_custody_status(db, custody.id)
    except Exception:
        pass

    # Audit log
    await AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="create",
        entity_type="expense",
        entity_id=expense.id,
        new_values={
            "custody_id": str(expense.custody_id),
            "amount": str(expense.amount),
            "category": expense.category,
        },
    )

    return {
        "id": str(expense.id),
        "custody_id": str(expense.custody_id),
        "amount": str(expense.amount),
        "category": expense.category,
        "status": expense.status,
        "message": "تم تسجيل المصروف بنجاح",
    }


@router.get("", response_model=PaginatedResponse)
async def list_expenses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    custody_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """قائمة المصروفات - List expenses with filtering"""
    conditions = []
    if custody_id:
        conditions.append(Expense.custody_id == custody_id)
    if status_filter:
        conditions.append(Expense.status == status_filter)
    if category:
        conditions.append(Expense.category == category)

    where_clause = and_(*conditions) if conditions else True

    count_query = select(func.count()).select_from(Expense).where(where_clause)
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    data_query = (
        select(Expense)
        .options(selectinload(Expense.custody), selectinload(Expense.created_by_user))
        .where(where_clause)
        .order_by(Expense.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(data_query)
    expenses = result.scalars().all()

    items = [
        {
            "id": str(e.id),
            "custody_id": str(e.custody_id),
            "amount": str(e.amount),
            "currency": e.currency,
            "category": e.category,
            "description": e.description,
            "expense_date": e.expense_date.isoformat() if e.expense_date else None,
            "receipt_number": e.receipt_number,
            "vendor": e.vendor,
            "status": e.status,
            "created_by": str(e.created_by) if e.created_by else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in expenses
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{expense_id}")
async def get_expense(
    expense_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """تفاصيل المصروف - Expense details"""
    query = (
        select(Expense)
        .options(selectinload(Expense.custody), selectinload(Expense.created_by_user), selectinload(Expense.approver))
        .where(Expense.id == expense_id)
    )
    result = await db.execute(query)
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(status_code=404, detail="المصروف غير موجود")

    return {
        "id": str(expense.id),
        "custody_id": str(expense.custody_id),
        "amount": str(expense.amount),
        "currency": expense.currency,
        "category": expense.category,
        "description": expense.description,
        "expense_date": expense.expense_date.isoformat() if expense.expense_date else None,
        "receipt_number": expense.receipt_number,
        "vendor": expense.vendor,
        "status": expense.status,
        "approved_by": str(expense.approved_by) if expense.approved_by else None,
        "approved_at": expense.approved_at.isoformat() if expense.approved_at else None,
        "rejection_reason": expense.rejection_reason,
        "verified_at": expense.verified_at.isoformat() if expense.verified_at else None,
        "created_at": expense.created_at.isoformat() if expense.created_at else None,
    }


@router.put("/{expense_id}")
async def update_expense(
    expense_id: uuid.UUID,
    expense_data: ExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """تحديث بيانات المصروف - Update expense"""
    query = select(Expense).where(Expense.id == expense_id)
    result = await db.execute(query)
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(status_code=404, detail="المصروف غير موجود")

    if expense.status not in ["pending"]:
        raise HTTPException(status_code=400, detail="لا يمكن تعديل مصروف تمت معالجته")

    update_data = expense_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(expense, key, value)

    expense.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "id": str(expense.id),
        "message": "تم تحديث المصروف بنجاح",
    }


@router.post("/{expense_id}/approve")
async def approve_expense(
    expense_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "accountant", "manager"])),
):
    """اعتماد مصروف - Approve expense"""
    query = select(Expense).where(Expense.id == expense_id)
    result = await db.execute(query)
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(status_code=404, detail="المصروف غير موجود")

    if expense.status != "pending":
        raise HTTPException(status_code=400, detail="لا يمكن اعتماد مصروف تمت معالجته")

    expense.status = "approved"
    expense.approved_by = current_user.id
    expense.approved_at = datetime.now(timezone.utc)
    await db.flush()

    # Update custody balance
    try:
        await BalanceService.update_custody_status(db, expense.custody_id)
    except Exception:
        pass

    await AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="approve",
        entity_type="expense",
        entity_id=expense.id,
    )

    return {
        "id": str(expense.id),
        "status": "approved",
        "message": "تم اعتماد المصروف بنجاح",
    }


@router.post("/{expense_id}/reject")
async def reject_expense(
    expense_id: uuid.UUID,
    reason: str = Query(..., min_length=3),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "accountant", "manager"])),
):
    """رفض مصروف - Reject expense"""
    query = select(Expense).where(Expense.id == expense_id)
    result = await db.execute(query)
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(status_code=404, detail="المصروف غير موجود")

    if expense.status != "pending":
        raise HTTPException(status_code=400, detail="لا يمكن رفض مصروف تمت معالجته")

    expense.status = "rejected"
    expense.approved_by = current_user.id
    expense.approved_at = datetime.now(timezone.utc)
    expense.rejection_reason = reason
    await db.flush()

    await AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="reject",
        entity_type="expense",
        entity_id=expense.id,
    )

    return {
        "id": str(expense.id),
        "status": "rejected",
        "message": "تم رفض المصروف",
    }
