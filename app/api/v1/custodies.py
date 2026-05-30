# ============================================================
# Custody API Routes
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models import Custody, User, Project
from app.schemas import CustodyCreate, CustodyResponse, CustodyBalanceResponse, PaginatedResponse
from app.services.balance_service import BalanceService
from app.services.audit_service import AuditService
from app.services.ledger_service import LedgerService

router = APIRouter()

@router.post("", response_model=CustodyResponse, status_code=status.HTTP_201_CREATED)
async def create_custody(
    data: CustodyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["financial_manager", "accountant", "super_admin"]))
):
    holder_query = select(User).where(and_(User.id == data.holder_id, User.is_active == True))
    result = await db.execute(holder_query)
    holder = result.scalar_one_or_none()
    if not holder:
        raise HTTPException(status_code=404, detail="Holder not found")

    custody = Custody(
        holder_id=data.holder_id,
        issued_by=current_user.id,
        project_id=data.project_id,
        amount=data.amount,
        currency=data.currency,
        purpose=data.purpose,
        due_date=data.due_date,
        notes=data.notes,
        status="open"
    )

    db.add(custody)
    await db.flush()
    await db.refresh(custody)

    ledger = LedgerService(db)
    await ledger.create_custody_issued_entry(custody, current_user.id)

    audit = AuditService(db)
    await audit.log_create(
        user_id=current_user.id,
        entity_type="custody",
        entity_id=custody.id,
        data={"custody_number": custody.custody_number, "amount": float(data.amount)}
    )

    return custody

@router.get("/{custody_id}", response_model=CustodyResponse)
async def get_custody(custody_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Custody).where(Custody.id == custody_id)
    result = await db.execute(query)
    custody = result.scalar_one_or_none()
    if not custody:
        raise HTTPException(status_code=404, detail="Custody not found")

    balance_service = BalanceService(db)
    balance = await balance_service.get_custody_balance(custody_id)

    response_data = {**custody.__dict__, "total_expenses": balance["total_expenses"], "total_settlements": balance["total_settlements"], "remaining_balance": balance["remaining_balance"]}
    return response_data

@router.get("/{custody_id}/balance", response_model=CustodyBalanceResponse)
async def get_custody_balance(custody_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    balance_service = BalanceService(db)
    try:
        return await balance_service.get_custody_balance(custody_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", response_model=PaginatedResponse)
async def list_custodies(status: Optional[str] = Query(None), holder_id: Optional[UUID] = Query(None), project_id: Optional[UUID] = Query(None), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Custody).order_by(desc(Custody.created_at))
    if status: query = query.where(Custody.status == status)
    if holder_id: query = query.where(Custody.holder_id == holder_id)
    if project_id: query = query.where(Custody.project_id == project_id)

    count_result = await db.execute(query)
    total = len(count_result.scalars().all())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size}

@router.post("/{custody_id}/settle")
async def settle_custody(custody_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role(["financial_manager", "accountant", "super_admin"]))):
    query = select(Custody).where(Custody.id == custody_id)
    result = await db.execute(query)
    custody = result.scalar_one_or_none()
    if not custody: raise HTTPException(status_code=404, detail="Custody not found")
    if custody.status in ["closed", "cancelled"]: raise HTTPException(status_code=400, detail="Custody already closed")

    balance_service = BalanceService(db)
    balance = await balance_service.get_custody_balance(custody_id)
    remaining = Decimal(str(balance["remaining_balance"]))

    if remaining < 0: raise HTTPException(status_code=400, detail=f"Cannot settle: over-spent by {abs(remaining)}")

    from app.models import Settlement
    settlement = Settlement(custody_id=custody_id, settlement_type="cash_return" if remaining > 0 else "expense_acknowledgment", amount=remaining if remaining > 0 else Decimal("0"), status="completed", settled_by=current_user.id, settled_at=datetime.now())
    db.add(settlement)

    custody.status = "closed"
    custody.closed_at = datetime.now()
    custody.closed_by = current_user.id

    ledger = LedgerService(db)
    await ledger.create_settlement_entry(settlement, current_user.id)
    await db.flush()

    return {"message": "Custody settled successfully", "custody_id": str(custody_id), "returned_amount": float(remaining) if remaining > 0 else 0, "status": "closed"}
