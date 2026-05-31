# ============================================
# FFCES - الجهات والمشاريع (Parties & Projects API)
# ============================================
"""
واجهة برمجة تطبيقات إدارة الجهات والمشاريع
API endpoints for managing parties and projects
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models import User, Party, Project, Custody, Settlement, Payment
from app.schemas import (
    PartyCreate, PartyUpdate, PartyResponse,
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectSummary,
    PaginatedResponse,
)

router = APIRouter(prefix="/parties", tags=["الجهات والمشاريع"])


# =============================================
# Parties CRUD
# =============================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_party(
    party_data: PartyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "accountant", "manager"])),
):
    """إنشاء جهة جديدة - Create a new party"""
    # Check code uniqueness
    query = select(Party).where(
        and_(Party.code == party_data.code, Party.organization_id == party_data.organization_id)
    )
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="رمز الجهة مسجل مسبقاً")

    party = Party(**party_data.model_dump())
    db.add(party)
    await db.flush()
    await db.refresh(party)

    return {
        "id": str(party.id),
        "name": party.name,
        "code": party.code,
        "type": party.type,
        "message": "تم إنشاء الجهة بنجاح",
    }


@router.get("", response_model=PaginatedResponse)
async def list_parties(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    party_type: Optional[str] = Query(None, alias="type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """قائمة الجهات - List parties with pagination"""
    conditions = []
    if search:
        conditions.append(Party.name.ilike(f"%{search}%"))
    if party_type:
        conditions.append(Party.type == party_type)

    where_clause = and_(*conditions) if conditions else True

    count_query = select(func.count()).select_from(Party).where(where_clause)
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    data_query = (
        select(Party)
        .where(where_clause)
        .order_by(Party.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(data_query)
    parties = result.scalars().all()

    items = [
        {
            "id": str(p.id),
            "name": p.name,
            "code": p.code,
            "type": p.type,
            "national_id": p.national_id,
            "phone": p.phone,
            "email": p.email,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in parties
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{party_id}")
async def get_party(
    party_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """بيانات جهة مع الرصيد - Get party details with balance"""
    query = select(Party).where(Party.id == party_id)
    result = await db.execute(query)
    party = result.scalar_one_or_none()

    if not party:
        raise HTTPException(status_code=404, detail="الجهة غير موجودة")

    # Calculate total payments balance (received - paid)
    received_query = select(func.coalesce(func.sum(Payment.amount), 0)).where(
        and_(Payment.payee_id == party_id, Payment.status == "completed")
    )
    total_received = (await db.execute(received_query)).scalar() or Decimal("0")

    paid_query = select(func.coalesce(func.sum(Payment.amount), 0)).where(
        and_(Payment.payer_id == party_id, Payment.status == "completed")
    )
    total_paid = (await db.execute(paid_query)).scalar() or Decimal("0")

    return {
        "id": str(party.id),
        "name": party.name,
        "name_en": party.name_en,
        "type": party.type,
        "code": party.code,
        "national_id": party.national_id,
        "phone": party.phone,
        "email": party.email,
        "address": party.address,
        "bank_name": party.bank_name,
        "bank_account": party.bank_account,
        "iban": party.iban,
        "is_active": party.is_active,
        "total_balance": str(total_received - total_paid),
        "created_at": party.created_at.isoformat() if party.created_at else None,
    }


@router.put("/{party_id}")
async def update_party(
    party_id: uuid.UUID,
    party_data: PartyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "accountant", "manager"])),
):
    """تحديث بيانات جهة - Update party details"""
    query = select(Party).where(Party.id == party_id)
    result = await db.execute(query)
    party = result.scalar_one_or_none()

    if not party:
        raise HTTPException(status_code=404, detail="الجهة غير موجودة")

    update_data = party_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(party, key, value)

    party.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(party)

    return {
        "id": str(party.id),
        "name": party.name,
        "message": "تم تحديث بيانات الجهة بنجاح",
    }


# =============================================
# Projects CRUD (nested under parties prefix but separate)
# =============================================

@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager"])),
):
    """إنشاء مشروع جديد - Create a new project"""
    # Check code uniqueness
    query = select(Project).where(Project.code == project_data.code)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="رمز المشروع مسجل مسبقاً")

    project = Project(**project_data.model_dump())
    db.add(project)
    await db.flush()
    await db.refresh(project)

    return {
        "id": str(project.id),
        "name": project.name,
        "code": project.code,
        "message": "تم إنشاء المشروع بنجاح",
    }


@router.get("/projects", response_model=PaginatedResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """قائمة المشاريع - List projects with pagination"""
    conditions = []
    if search:
        conditions.append(Project.name.ilike(f"%{search}%"))
    if status:
        conditions.append(Project.status == status)

    where_clause = and_(*conditions) if conditions else True

    count_query = select(func.count()).select_from(Project).where(where_clause)
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    data_query = (
        select(Project)
        .where(where_clause)
        .order_by(Project.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(data_query)
    projects = result.scalars().all()

    items = [
        {
            "id": str(p.id),
            "name": p.name,
            "code": p.code,
            "status": p.status,
            "total_budget": str(p.total_budget),
            "spent_amount": str(p.spent_amount),
            "start_date": p.start_date.isoformat() if p.start_date else None,
            "end_date": p.end_date.isoformat() if p.end_date else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in projects
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/projects/{project_id}")
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """بيانات مشروع مع ملخص - Get project details with summary"""
    query = select(Project).where(Project.id == project_id)
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")

    # Calculate summary stats
    custody_count_query = select(func.count()).where(Custody.project_id == project_id)
    custody_count = (await db.execute(custody_count_query)).scalar() or 0

    custody_amount_query = select(func.coalesce(func.sum(Custody.amount), 0)).where(Custody.project_id == project_id)
    total_custody = (await db.execute(custody_amount_query)).scalar() or Decimal("0")

    settlement_count_query = select(func.count()).where(
        and_(Settlement.custody_id.in_(select(Custody.id).where(Custody.project_id == project_id)))
    )
    settlement_count = (await db.execute(settlement_count_query)).scalar() or 0

    remaining_budget = project.total_budget - project.spent_amount

    return {
        "id": str(project.id),
        "name": project.name,
        "name_en": project.name_en,
        "code": project.code,
        "description": project.description,
        "status": project.status,
        "total_budget": str(project.total_budget),
        "spent_amount": str(project.spent_amount),
        "remaining_budget": str(remaining_budget),
        "location": project.location,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "end_date": project.end_date.isoformat() if project.end_date else None,
        "manager_id": str(project.manager_id) if project.manager_id else None,
        "summary": {
            "custody_count": custody_count,
            "total_custody_amount": str(total_custody),
            "settlement_count": settlement_count,
        },
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


@router.put("/projects/{project_id}")
async def update_project(
    project_id: uuid.UUID,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager"])),
):
    """تحديث بيانات مشروع - Update project details"""
    query = select(Project).where(Project.id == project_id)
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")

    update_data = project_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    project.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(project)

    return {
        "id": str(project.id),
        "name": project.name,
        "message": "تم تحديث بيانات المشروع بنجاح",
    }
