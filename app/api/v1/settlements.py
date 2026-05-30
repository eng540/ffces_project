# ============================================================
# Settlements API Routes
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models import Settlement, Custody
from app.schemas import SettlementCreate, SettlementResponse, PaginatedResponse
from app.services.ledger_service import LedgerService
from app.services.audit_service import AuditService

router = APIRouter()

@router.post("", response_model=SettlementResponse, status_code=status.HTTP_201_CREATED)
async def create_settlement(
    data: SettlementCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role(["financial_manager", "accountant", "super_admin"]))
):
    custody_query = select(Custody).where(Custody.id == data.custody_id)
    result = await db.execute(custody_query)
    custody = result.scalar_one_or_none()
    if not custody:
        raise HTTPException(status_code=404, detail="Custody not found")
    if custody.status not in ["open", "partially_settled"]:
        raise HTTPException(status_code=400, detail="Custody cannot be settled")

    settlement = Settlement(
        custody_id=data.custody_id,
        settlement_type=data.settlement_type,
        amount=data.amount,
        currency=data.currency,
        target_custody_id=data.target_custody_id,
        status="completed",
        settled_by=current_user.id,
        settled_at=datetime.now(),
        notes=data.notes
    )

    db.add(settlement)
    await db.flush()
    await db.refresh(settlement)

    ledger = LedgerService(db)
    await ledger.create_settlement_entry(settlement, current_user.id)

    audit = AuditService(db)
    await audit.log_create(
        user_id=current_user.id,
        entity_type="settlement",
        entity_id=settlement.id,
        data={"amount": float(data.amount), "type": data.settlement_type, "custody_id": str(data.custody_id)}
    )

    return settlement

@router.get("/{settlement_id}", response_model=SettlementResponse)
async def get_settlement(settlement_id: UUID, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    query = select(Settlement).where(Settlement.id == settlement_id)
    result = await db.execute(query)
    settlement = result.scalar_one_or_none()
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return settlement

@router.get("", response_model=PaginatedResponse)
async def list_settlements(
    custody_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = select(Settlement).order_by(desc(Settlement.created_at))
    if custody_id: query = query.where(Settlement.custody_id == custody_id)
    if status: query = query.where(Settlement.status == status)

    count_result = await db.execute(query)
    total = len(count_result.scalars().all())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size}
