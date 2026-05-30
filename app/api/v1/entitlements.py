# ============================================================
# Entitlements API Routes
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import List, Optional
from uuid import UUID
from datetime import date

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models import Entitlement, Party, Project, EntitlementRule
from app.schemas import EntitlementCreate, EntitlementResponse, EntitlementCalculationRequest, PaginatedResponse
from app.services.entitlement_engine import EntitlementEngine
from app.services.balance_service import BalanceService

router = APIRouter()

@router.post("/calculate")
async def calculate_entitlements(
    data: EntitlementCalculationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["accountant", "financial_manager", "field_supervisor", "super_admin"]))
):
    engine = EntitlementEngine(db)
    entitlements = await engine.calculate_entitlements(
        party_id=data.party_id,
        project_id=data.project_id,
        period_start=data.period_start,
        period_end=data.period_end,
        created_by=current_user.id
    )

    return {
        "message": f"Calculated {len(entitlements)} entitlements",
        "entitlements": entitlements,
        "total_amount": sum(e.amount for e in entitlements)
    }

@router.get("/{entitlement_id}", response_model=EntitlementResponse)
async def get_entitlement(entitlement_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Entitlement).where(Entitlement.id == entitlement_id)
    result = await db.execute(query)
    entitlement = result.scalar_one_or_none()
    if not entitlement: raise HTTPException(status_code=404, detail="Entitlement not found")
    return entitlement

@router.get("", response_model=PaginatedResponse)
async def list_entitlements(party_id: Optional[UUID] = Query(None), project_id: Optional[UUID] = Query(None), status: Optional[str] = Query(None), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Entitlement).order_by(desc(Entitlement.created_at))
    if party_id: query = query.where(Entitlement.party_id == party_id)
    if project_id: query = query.where(Entitlement.project_id == project_id)
    if status: query = query.where(Entitlement.status == status)

    count_result = await db.execute(query)
    total = len(count_result.scalars().all())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size}
