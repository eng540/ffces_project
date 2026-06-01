# ============================================
# FFCES - التسويات (Settlements API)
# ============================================
"""
واجهة برمجة تطبيقات إدارة تسويات العهد
API endpoints for managing custody settlements
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models import User, Settlement, Custody
from app.schemas import SettlementCreate, SettlementUpdate, PaginatedResponse
from app.services.balance_service import BalanceService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/settlements", tags=["التسويات"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_settlement(
    settlement_data: SettlementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """إنشاء تسوية عهدة - Create a custody settlement"""
    # Verify custody exists
    custody_query = select(Custody).where(Custody.id == settlement_data.custody_id)
    custody_result = await db.execute(custody_query)
    custody = custody_result.scalar_one_or_none()

    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")

    if custody.status not in ["active", "partially_settled"]:
        raise HTTPException(status_code=400, detail="العهدة غير مفعلة للتسوية")

    # Calculate refund if any
    balance_info = await BalanceService.calculate_custody_balance(db, custody.id)
    total_expenses = balance_info["total_expenses"]
    refund = max(custody.amount - total_expenses, Decimal("0"))

    settlement = Settlement(
        **settlement_data.model_dump(),
        refund_amount=refund,
        created_at=datetime.now(timezone.utc),
    )
    db.add(settlement)
    await db.flush()
    await db.refresh(settlement)

    await AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="create",
        entity_type="settlement",
        entity_id=settlement.id,
        new_values={
            "custody_id": str(settlement.custody_id),
            "amount": str(settlement.amount),
            "refund_amount": str(settlement.refund_amount),
        },
    )

    return {
        "id": str(settlement.id),
        "custody_id": str(settlement.custody_id),
        "amount": str(settlement.amount),
        "refund_amount": str(settlement.refund_amount),
        "status": settlement.status,
        "message": "تم إنشاء التسوية بنجاح",
    }


@router.get("", response_model=PaginatedResponse)
async def list_settlements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    custody_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    user_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """قائمة التسويات - List settlements"""
    conditions = []
    if custody_id:
        conditions.append(Settlement.custody_id == custody_id)
    if status_filter:
        conditions.append(Settlement.status == status_filter)
    if user_id:
        conditions.append(Settlement.user_id == user_id)

    where_clause = and_(*conditions) if conditions else True

    count_query = select(func.count()).select_from(Settlement).where(where_clause)
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    data_query = (
        select(Settlement)
        .where(where_clause)
        .order_by(Settlement.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(data_query)
    settlements = result.scalars().all()

    items = [
        {
            "id": str(s.id),
            "custody_id": str(s.custody_id),
            "user_id": str(s.user_id),
            "amount": str(s.amount),
            "refund_amount": str(s.refund_amount),
            "status": s.status,
            "settlement_date": s.settlement_date.isoformat() if s.settlement_date else None,
            "description": s.description,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in settlements
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{settlement_id}")
async def get_settlement(
    settlement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """تفاصيل التسوية - Settlement details"""
    query = select(Settlement).where(Settlement.id == settlement_id)
    result = await db.execute(query)
    settlement = result.scalar_one_or_none()

    if not settlement:
        raise HTTPException(status_code=404, detail="التسوية غير موجودة")

    return {
        "id": str(settlement.id),
        "custody_id": str(settlement.custody_id),
        "user_id": str(settlement.user_id),
        "amount": str(settlement.amount),
        "refund_amount": str(settlement.refund_amount),
        "currency": settlement.currency,
        "status": settlement.status,
        "settlement_date": settlement.settlement_date.isoformat() if settlement.settlement_date else None,
        "description": settlement.description,
        "approved_by": str(settlement.approved_by) if settlement.approved_by else None,
        "approved_at": settlement.approved_at.isoformat() if settlement.approved_at else None,
        "completed_at": settlement.completed_at.isoformat() if settlement.completed_at else None,
        "notes": settlement.notes,
        "created_at": settlement.created_at.isoformat() if settlement.created_at else None,
    }


@router.put("/{settlement_id}")
async def update_settlement(
    settlement_id: uuid.UUID,
    settlement_data: SettlementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """تحديث بيانات التسوية - Update settlement"""
    query = select(Settlement).where(Settlement.id == settlement_id)
    result = await db.execute(query)
    settlement = result.scalar_one_or_none()

    if not settlement:
        raise HTTPException(status_code=404, detail="التسوية غير موجودة")

    if settlement.status not in ["pending"]:
        raise HTTPException(status_code=400, detail="لا يمكن تعديل تسوية تمت معالجتها")

    update_data = settlement_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settlement, key, value)

    settlement.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "id": str(settlement.id),
        "message": "تم تحديث التسوية بنجاح",
    }


@router.post("/{settlement_id}/approve")
async def approve_settlement(
    settlement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "accountant", "manager"])),
):
    """اعتماد تسوية - Approve settlement"""
    query = select(Settlement).where(Settlement.id == settlement_id)
    result = await db.execute(query)
    settlement = result.scalar_one_or_none()

    if not settlement:
        raise HTTPException(status_code=404, detail="التسوية غير موجودة")

    if settlement.status != "pending":
        raise HTTPException(status_code=400, detail="لا يمكن اعتماد تسوية تمت معالجتها")

    settlement.status = "approved"
    settlement.approved_by = current_user.id
    settlement.approved_at = datetime.now(timezone.utc)
    await db.flush()

    # Update custody status
    try:
        await BalanceService.update_custody_status(db, settlement.custody_id)
    except Exception:
        pass

    await AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="approve",
        entity_type="settlement",
        entity_id=settlement.id,
    )

    return {
        "id": str(settlement.id),
        "status": "approved",
        "message": "تم اعتماد التسوية بنجاح",
    }


@router.post("/{settlement_id}/complete")
async def complete_settlement(
    settlement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "accountant"])),
):
    """إتمام تسوية - Complete settlement"""
    query = select(Settlement).where(Settlement.id == settlement_id)
    result = await db.execute(query)
    settlement = result.scalar_one_or_none()

    if not settlement:
        raise HTTPException(status_code=404, detail="التسوية غير موجودة")

    if settlement.status != "approved":
        raise HTTPException(status_code=400, detail="لا يمكن إتمام تسوية غير معتمدة")

    settlement.status = "completed"
    settlement.completed_at = datetime.now(timezone.utc)
    await db.flush()

    # Update custody
    try:
        custody_query = select(Custody).where(Custody.id == settlement.custody_id)
        custody_result = await db.execute(custody_query)
        custody = custody_result.scalar_one_or_none()

        if custody:
            custody.settled_amount += settlement.amount
            custody.remaining_amount = max(custody.amount - custody.settled_amount, Decimal("0"))
            await BalanceService.update_custody_status(db, custody.id)
    except Exception:
        pass

    await AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="complete",
        entity_type="settlement",
        entity_id=settlement.id,
    )

    return {
        "id": str(settlement.id),
        "status": "completed",
        "message": "تم إتمام التسوية بنجاح",
    }
