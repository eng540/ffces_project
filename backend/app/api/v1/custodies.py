# ============================================
# FFCES - العهد (Custodies API)
# ============================================
"""
واجهة برمجة تطبيقات إدارة العهد المالية
API endpoints for managing financial custodies
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
from app.models import User, Custody, Expense, Settlement
from app.schemas import CustodyCreate, CustodyUpdate, CustodyResponse, PaginatedResponse
from app.services.balance_service import BalanceService
from app.services.ledger_service import LedgerService
from app.services.audit_service import AuditService
from app.services.approval_service import ApprovalService

router = APIRouter(prefix="/custodies", tags=["العهد"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_custody(
    custody_data: CustodyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "accountant", "manager"])),
):
    """إصدار عهدة جديدة - Issue a new custody"""
    # Validate holder and custodian exist
    holder_query = select(User).where(User.id == custody_data.holder_id)
    holder_result = await db.execute(holder_query)
    holder = holder_result.scalar_one_or_none()
    if not holder:
        raise HTTPException(status_code=404, detail="حامل العهدة غير موجود")

    custodian_query = select(User).where(User.id == custody_data.custodian_id)
    custodian_result = await db.execute(custodian_query)
    if not custodian_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="المستلم غير موجود")

    # Create custody
    custody = Custody(**custody_data.model_dump())
    custody.remaining_amount = custody.amount
    custody.settled_amount = Decimal("0")
    db.add(custody)
    await db.flush()
    await db.refresh(custody)

    # Create ledger entry
    org_id = holder.organization_id
    try:
        await LedgerService.create_custody_entry(db, custody, current_user.id, org_id)
    except Exception:
        pass  # Ledger entry is non-critical; custody is created regardless

    # Initiate approval workflow if amount exceeds threshold
    try:
        await ApprovalService.initiate_workflow(
            db, "custody", custody.id, custody.amount, current_user.id, org_id
        )
    except Exception:
        pass

    # Audit log
    await AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="create",
        entity_type="custody",
        entity_id=custody.id,
        new_values={
            "amount": str(custody.amount),
            "holder_id": str(custody.holder_id),
            "purpose": custody.purpose,
        },
    )

    return {
        "id": str(custody.id),
        "amount": str(custody.amount),
        "remaining_amount": str(custody.remaining_amount),
        "status": custody.status,
        "purpose": custody.purpose,
        "message": "تم إصدار العهدة بنجاح",
    }


@router.get("", response_model=PaginatedResponse)
async def list_custodies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    holder_id: Optional[uuid.UUID] = Query(None),
    project_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """قائمة العهد - List custodies with filtering and pagination"""
    conditions = []
    if search:
        conditions.append(Custody.purpose.ilike(f"%{search}%"))
    if status_filter:
        conditions.append(Custody.status == status_filter)
    if holder_id:
        conditions.append(Custody.holder_id == holder_id)
    if project_id:
        conditions.append(Custody.project_id == project_id)

    where_clause = and_(*conditions) if conditions else True

    count_query = select(func.count()).select_from(Custody).where(where_clause)
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    data_query = (
        select(Custody)
        .options(selectinload(Custody.holder), selectinload(Custody.custodian), selectinload(Custody.project))
        .where(where_clause)
        .order_by(Custody.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(data_query)
    custodies = result.scalars().all()

    items = [
        {
            "id": str(c.id),
            "purpose": c.purpose,
            "amount": str(c.amount),
            "remaining_amount": str(c.remaining_amount),
            "settled_amount": str(c.settled_amount),
            "status": c.status,
            "custody_type": c.custody_type,
            "holder_name": c.holder.full_name if c.holder else None,
            "custodian_name": c.custodian.full_name if c.custodian else None,
            "project_name": c.project.name if c.project else None,
            "issued_date": c.issued_date.isoformat() if c.issued_date else None,
            "due_date": c.due_date.isoformat() if c.due_date else None,
        }
        for c in custodies
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{custody_id}")
async def get_custody(
    custody_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """تفاصيل العهدة مع الرصيد - Custody details with balance"""
    query = (
        select(Custody)
        .options(selectinload(Custody.holder), selectinload(Custody.custodian), selectinload(Custody.project))
        .where(Custody.id == custody_id)
    )
    result = await db.execute(query)
    custody = result.scalar_one_or_none()

    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")

    # Get balance info
    try:
        balance_info = await BalanceService.calculate_custody_balance(db, custody.id)
    except Exception:
        balance_info = {
            "total_expenses": Decimal("0"),
            "total_settlements": Decimal("0"),
            "remaining": custody.remaining_amount,
            "utilization_rate": 0,
        }

    # Get related expenses
    expenses_query = select(Expense).where(Expense.custody_id == custody_id).order_by(Expense.created_at.desc())
    expenses_result = await db.execute(expenses_query)
    expenses = expenses_result.scalars().all()

    # Get related settlements
    settlements_query = select(Settlement).where(Settlement.custody_id == custody_id).order_by(Settlement.created_at.desc())
    settlements_result = await db.execute(settlements_query)
    settlements = settlements_result.scalars().all()

    return {
        "id": str(custody.id),
        "purpose": custody.purpose,
        "amount": str(custody.amount),
        "remaining_amount": str(custody.remaining_amount),
        "settled_amount": str(custody.settled_amount),
        "status": custody.status,
        "custody_type": custody.custody_type,
        "currency": custody.currency,
        "holder": {
            "id": str(custody.holder.id),
            "name": custody.holder.full_name,
        } if custody.holder else None,
        "custodian": {
            "id": str(custody.custodian.id),
            "name": custody.custodian.full_name,
        } if custody.custodian else None,
        "project": {
            "id": str(custody.project.id),
            "name": custody.project.name,
        } if custody.project else None,
        "issued_date": custody.issued_date.isoformat() if custody.issued_date else None,
        "due_date": custody.due_date.isoformat() if custody.due_date else None,
        "balance": {
            "total_expenses": str(balance_info["total_expenses"]),
            "total_settlements": str(balance_info["total_settlements"]),
            "remaining": str(balance_info["remaining"]),
            "utilization_rate": balance_info["utilization_rate"],
        },
        "expenses": [
            {
                "id": str(e.id),
                "amount": str(e.amount),
                "category": e.category,
                "description": e.description,
                "status": e.status,
                "expense_date": e.expense_date.isoformat() if e.expense_date else None,
            }
            for e in expenses
        ],
        "settlements": [
            {
                "id": str(s.id),
                "amount": str(s.amount),
                "status": s.status,
                "settlement_date": s.settlement_date.isoformat() if s.settlement_date else None,
            }
            for s in settlements
        ],
    }


@router.put("/{custody_id}")
async def update_custody(
    custody_id: uuid.UUID,
    custody_data: CustodyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "accountant", "manager"])),
):
    """تحديث بيانات العهدة - Update custody"""
    query = select(Custody).where(Custody.id == custody_id)
    result = await db.execute(query)
    custody = result.scalar_one_or_none()

    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")

    update_data = custody_data.model_dump(exclude_unset=True)
    old_values = {k: str(getattr(custody, k)) for k in update_data if getattr(custody, k, None) is not None}

    for key, value in update_data.items():
        setattr(custody, key, value)

    custody.updated_at = datetime.now(timezone.utc)
    await db.flush()

    await AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="update",
        entity_type="custody",
        entity_id=custody.id,
        old_values=old_values,
        new_values={k: str(v) for k, v in update_data.items()},
    )

    return {
        "id": str(custody.id),
        "message": "تم تحديث العهدة بنجاح",
    }


@router.post("/{custody_id}/refresh-balance")
async def refresh_custody_balance(
    custody_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """تحديث حالة ورصيد العهدة - Refresh custody status and balance"""
    new_status = await BalanceService.update_custody_status(db, custody_id)

    return {
        "custody_id": str(custody_id),
        "new_status": new_status,
        "message": "تم تحديث حالة العهدة بنجاح",
    }
