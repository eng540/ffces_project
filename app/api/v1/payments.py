# ============================================================
# Payments API Routes
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models import Payment, Party, Project, Custody, Entitlement
from app.schemas import PaymentCreate, PaymentResponse, PaginatedResponse
from app.services.balance_service import BalanceService
from app.services.ledger_service import LedgerService
from app.services.audit_service import AuditService

router = APIRouter()

@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role(["accountant", "financial_manager", "super_admin"]))
):
    party_query = select(Party).where(Party.id == data.party_id)
    result = await db.execute(party_query)
    party = result.scalar_one_or_none()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    # If paying from custody, verify balance
    if data.custody_id:
        custody_query = select(Custody).where(Custody.id == data.custody_id)
        result = await db.execute(custody_query)
        custody = result.scalar_one_or_none()
        if not custody or custody.status != "open":
            raise HTTPException(status_code=400, detail="Custody not available")

        balance_service = BalanceService(db)
        balance = await balance_service.get_custody_balance(data.custody_id)
        if float(data.amount) > balance["remaining_balance"]:
            raise HTTPException(status_code=400, detail="Insufficient custody balance")

    # If linked to entitlements, update them
    if data.entitlement_ids:
        for ent_id in data.entitlement_ids:
            ent_query = select(Entitlement).where(Entitlement.id == ent_id)
            result = await db.execute(ent_query)
            entitlement = result.scalar_one_or_none()
            if entitlement:
                entitlement.paid_amount += data.amount
                entitlement.status = "fully_paid" if entitlement.paid_amount >= entitlement.amount else "partially_paid"

    payment = Payment(
        party_id=data.party_id,
        project_id=data.project_id,
        custody_id=data.custody_id,
        amount=data.amount,
        currency=data.currency,
        payment_type=data.payment_type,
        payment_method=data.payment_method,
        reference_number=data.reference_number,
        entitlement_ids=data.entitlement_ids or [],
        notes=data.notes,
        paid_by=current_user.id,
        paid_at=data.paid_at
    )

    db.add(payment)
    await db.flush()
    await db.refresh(payment)

    ledger = LedgerService(db)
    await ledger.create_payment_entry(payment, current_user.id)

    audit = AuditService(db)
    await audit.log_create(
        user_id=current_user.id,
        entity_type="payment",
        entity_id=payment.id,
        data={"amount": float(data.amount), "party_id": str(data.party_id), "type": data.payment_type}
    )

    return payment

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: UUID, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    query = select(Payment).where(Payment.id == payment_id)
    result = await db.execute(query)
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment

@router.get("", response_model=PaginatedResponse)
async def list_payments(
    party_id: Optional[UUID] = Query(None),
    project_id: Optional[UUID] = Query(None),
    payment_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = select(Payment).order_by(desc(Payment.paid_at))
    if party_id: query = query.where(Payment.party_id == party_id)
    if project_id: query = query.where(Payment.project_id == project_id)
    if payment_type: query = query.where(Payment.payment_type == payment_type)

    count_result = await db.execute(query)
    total = len(count_result.scalars().all())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size}
