# ============================================
# FFCES - المدفوعات (Payments API)
# ============================================
"""
واجهة برمجة تطبيقات إدارة المدفوعات
API endpoints for managing payments
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
from app.models import User, Payment, Party
from app.schemas import PaymentCreate, PaymentUpdate, PaginatedResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/payments", tags=["المدفوعات"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "accountant"])),
):
    """إنشاء دفعة جديدة - Create a new payment"""
    # Validate payee exists
    if payment_data.payee_id:
        payee_query = select(Party).where(Party.id == payment_data.payee_id)
        payee_result = await db.execute(payee_query)
        if not payee_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="الجهة المستفيدة غير موجودة")

    payment = Payment(
        **payment_data.model_dump(),
        created_by=current_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    await db.flush()
    await db.refresh(payment)

    await AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="create",
        entity_type="payment",
        entity_id=payment.id,
        new_values={
            "amount": str(payment.amount),
            "payment_method": payment.payment_method,
            "payee_id": str(payment.payee_id) if payment.payee_id else None,
        },
    )

    return {
        "id": str(payment.id),
        "amount": str(payment.amount),
        "payment_method": payment.payment_method,
        "status": payment.status,
        "message": "تم إنشاء الدفعة بنجاح",
    }


@router.get("", response_model=PaginatedResponse)
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    payment_method: Optional[str] = Query(None),
    payee_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """قائمة المدفوعات - List payments"""
    conditions = []
    if status_filter:
        conditions.append(Payment.status == status_filter)
    if payment_method:
        conditions.append(Payment.payment_method == payment_method)
    if payee_id:
        conditions.append(Payment.payee_id == payee_id)

    where_clause = and_(*conditions) if conditions else True

    count_query = select(func.count()).select_from(Payment).where(where_clause)
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    data_query = (
        select(Payment)
        .where(where_clause)
        .order_by(Payment.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(data_query)
    payments = result.scalars().all()

    items = [
        {
            "id": str(p.id),
            "amount": str(p.amount),
            "currency": p.currency,
            "payment_method": p.payment_method,
            "payment_date": p.payment_date.isoformat() if p.payment_date else None,
            "reference_number": p.reference_number,
            "description": p.description,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in payments
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{payment_id}")
async def get_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """تفاصيل الدفعة - Payment details"""
    query = select(Payment).where(Payment.id == payment_id)
    result = await db.execute(query)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="الدفعة غير موجودة")

    return {
        "id": str(payment.id),
        "amount": str(payment.amount),
        "currency": payment.currency,
        "payment_method": payment.payment_method,
        "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
        "reference_number": payment.reference_number,
        "description": payment.description,
        "status": payment.status,
        "bank_name": payment.bank_name,
        "bank_account": payment.bank_account,
        "created_by": str(payment.created_by) if payment.created_by else None,
        "approved_by": str(payment.approved_by) if payment.approved_by else None,
        "approved_at": payment.approved_at.isoformat() if payment.approved_at else None,
        "completed_at": payment.completed_at.isoformat() if payment.completed_at else None,
        "organization_id": str(payment.organization_id),
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
    }


@router.put("/{payment_id}")
async def update_payment(
    payment_id: uuid.UUID,
    payment_data: PaymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "accountant"])),
):
    """تحديث بيانات الدفعة - Update payment"""
    query = select(Payment).where(Payment.id == payment_id)
    result = await db.execute(query)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="الدفعة غير موجودة")

    if payment.status not in ["pending", "processing"]:
        raise HTTPException(status_code=400, detail="لا يمكن تعديل دفعة تمت معالجتها")

    update_data = payment_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(payment, key, value)

    payment.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "id": str(payment.id),
        "message": "تم تحديث الدفعة بنجاح",
    }


@router.post("/{payment_id}/approve")
async def approve_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager"])),
):
    """اعتماد دفعة - Approve payment"""
    query = select(Payment).where(Payment.id == payment_id)
    result = await db.execute(query)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="الدفعة غير موجودة")

    if payment.status != "pending":
        raise HTTPException(status_code=400, detail="لا يمكن اعتماد دفعة تمت معالجتها")

    payment.status = "processing"
    payment.approved_by = current_user.id
    payment.approved_at = datetime.now(timezone.utc)
    await db.flush()

    await AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="approve",
        entity_type="payment",
        entity_id=payment.id,
    )

    return {
        "id": str(payment.id),
        "status": "processing",
        "message": "تم اعتماد الدفعة",
    }


@router.post("/{payment_id}/complete")
async def complete_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "accountant"])),
):
    """إتمام دفعة - Complete payment"""
    query = select(Payment).where(Payment.id == payment_id)
    result = await db.execute(query)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="الدفعة غير موجودة")

    if payment.status != "processing":
        raise HTTPException(status_code=400, detail="لا يمكن إتمام دفعة ليست قيد المعالجة")

    payment.status = "completed"
    payment.completed_at = datetime.now(timezone.utc)
    await db.flush()

    await AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="complete",
        entity_type="payment",
        entity_id=payment.id,
    )

    return {
        "id": str(payment.id),
        "status": "completed",
        "message": "تم إتمام الدفعة بنجاح",
    }
