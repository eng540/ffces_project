# ============================================
# FFCES - الاستحقاقات (Entitlements API)
# ============================================
"""
واجهة برمجة تطبيقات إدارة الاستحقاقات المالية
API endpoints for managing financial entitlements
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
from app.models import User, Entitlement, EntitlementRule, WorkRecord
from app.schemas import EntitlementCreate, EntitlementUpdate, PaginatedResponse
from app.services.entitlement_engine import EntitlementEngine
from app.services.audit_service import AuditService

router = APIRouter(prefix="/entitlements", tags=["الاستحقاقات"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_entitlement(
    entitlement_data: EntitlementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """إنشاء استحقاق يدوياً - Create entitlement manually"""
    # Verify rule exists
    rule_query = select(EntitlementRule).where(EntitlementRule.id == entitlement_data.rule_id)
    rule_result = await db.execute(rule_query)
    if not rule_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="قاعدة الاستحقاق غير موجودة")

    entitlement = Entitlement(
        **entitlement_data.model_dump(),
        created_at=datetime.now(timezone.utc),
    )
    db.add(entitlement)
    await db.flush()
    await db.refresh(entitlement)

    return {
        "id": str(entitlement.id),
        "user_id": str(entitlement.user_id),
        "rule_id": str(entitlement.rule_id),
        "amount": str(entitlement.amount),
        "status": entitlement.status,
        "message": "تم إنشاء الاستحقاق بنجاح",
    }


@router.post("/calculate", status_code=status.HTTP_201_CREATED)
async def calculate_entitlements(
    work_record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """حساب الاستحقاقات تلقائياً لسجل عمل - Auto-calculate entitlements for work record"""
    # Verify work record exists
    wr_query = select(WorkRecord).where(WorkRecord.id == work_record_id)
    wr_result = await db.execute(wr_query)
    work_record = wr_result.scalar_one_or_none()

    if not work_record:
        raise HTTPException(status_code=404, detail="سجل العمل غير موجود")

    try:
        entitlements = await EntitlementEngine.calculate_entitlements(
            db=db,
            work_record_id=work_record_id,
            calculated_by=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not entitlements:
        return {
            "message": "لا توجد استحقاقات قابلة للتطبيق لهذا السجل",
            "entitlements": [],
        }

    return {
        "work_record_id": str(work_record_id),
        "entitlements_count": len(entitlements),
        "entitlements": [
            {
                "id": str(e.id),
                "amount": str(e.amount),
                "status": e.status,
            }
            for e in entitlements
        ],
        "message": "تم حساب الاستحقاقات بنجاح",
    }


@router.get("", response_model=PaginatedResponse)
async def list_entitlements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    user_id: Optional[uuid.UUID] = Query(None),
    project_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """قائمة الاستحقاقات - List entitlements"""
    conditions = []
    if user_id:
        conditions.append(Entitlement.user_id == user_id)
    if project_id:
        conditions.append(Entitlement.project_id == project_id)
    if status_filter:
        conditions.append(Entitlement.status == status_filter)

    where_clause = and_(*conditions) if conditions else True

    count_query = select(func.count()).select_from(Entitlement).where(where_clause)
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    data_query = (
        select(Entitlement)
        .where(where_clause)
        .order_by(Entitlement.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(data_query)
    entitlements = result.scalars().all()

    items = [
        {
            "id": str(e.id),
            "user_id": str(e.user_id),
            "project_id": str(e.project_id),
            "rule_id": str(e.rule_id),
            "amount": str(e.amount),
            "currency": e.currency,
            "status": e.status,
            "period_start": e.period_start.isoformat() if e.period_start else None,
            "period_end": e.period_end.isoformat() if e.period_end else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entitlements
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{entitlement_id}")
async def get_entitlement(
    entitlement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """تفاصيل الاستحقاق - Entitlement details"""
    query = select(Entitlement).where(Entitlement.id == entitlement_id)
    result = await db.execute(query)
    entitlement = result.scalar_one_or_none()

    if not entitlement:
        raise HTTPException(status_code=404, detail="الاستحقاق غير موجود")

    return {
        "id": str(entitlement.id),
        "user_id": str(entitlement.user_id),
        "project_id": str(entitlement.project_id),
        "rule_id": str(entitlement.rule_id),
        "work_record_id": str(entitlement.work_record_id) if entitlement.work_record_id else None,
        "amount": str(entitlement.amount),
        "currency": entitlement.currency,
        "status": entitlement.status,
        "period_start": entitlement.period_start.isoformat() if entitlement.period_start else None,
        "period_end": entitlement.period_end.isoformat() if entitlement.period_end else None,
        "calculation_basis": entitlement.calculation_basis,
        "approved_by": str(entitlement.approved_by) if entitlement.approved_by else None,
        "approved_at": entitlement.approved_at.isoformat() if entitlement.approved_at else None,
        "paid_at": entitlement.paid_at.isoformat() if entitlement.paid_at else None,
        "notes": entitlement.notes,
        "created_at": entitlement.created_at.isoformat() if entitlement.created_at else None,
    }


@router.put("/{entitlement_id}")
async def update_entitlement(
    entitlement_id: uuid.UUID,
    entitlement_data: EntitlementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "accountant"])),
):
    """تحديث بيانات الاستحقاق - Update entitlement"""
    query = select(Entitlement).where(Entitlement.id == entitlement_id)
    result = await db.execute(query)
    entitlement = result.scalar_one_or_none()

    if not entitlement:
        raise HTTPException(status_code=404, detail="الاستحقاق غير موجود")

    if entitlement.status not in ["calculated"]:
        raise HTTPException(status_code=400, detail="لا يمكن تعديل استحقاق تمت معالجته")

    update_data = entitlement_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(entitlement, key, value)

    entitlement.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "id": str(entitlement.id),
        "message": "تم تحديث الاستحقاق بنجاح",
    }


@router.post("/{entitlement_id}/approve")
async def approve_entitlement(
    entitlement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "accountant", "manager"])),
):
    """اعتماد استحقاق - Approve entitlement"""
    try:
        entitlement = await EntitlementEngine.approve_entitlement(
            db=db,
            entitlement_id=entitlement_id,
            approved_by=current_user.id,
            approve=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    await AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="approve",
        entity_type="entitlement",
        entity_id=entitlement.id,
    )

    return {
        "id": str(entitlement.id),
        "status": "approved",
        "message": "تم اعتماد الاستحقاق بنجاح",
    }


@router.post("/{entitlement_id}/reject")
async def reject_entitlement(
    entitlement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "accountant", "manager"])),
):
    """رفض استحقاق - Reject entitlement"""
    try:
        entitlement = await EntitlementEngine.approve_entitlement(
            db=db,
            entitlement_id=entitlement_id,
            approved_by=current_user.id,
            approve=False,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "id": str(entitlement.id),
        "status": "rejected",
        "message": "تم رفض الاستحقاق",
    }


# =============================================
# Entitlement Rules Management
# =============================================
@router.get("/rules", response_model=PaginatedResponse, tags=["قواعد الاستحقاق"])
async def list_entitlement_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    entitlement_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """قائمة قواعد الاستحقاق - List entitlement rules"""
    conditions = []
    if entitlement_type:
        conditions.append(EntitlementRule.entitlement_type == entitlement_type)

    where_clause = and_(*conditions) if conditions else True

    count_query = select(func.count()).select_from(EntitlementRule).where(where_clause)
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    data_query = (
        select(EntitlementRule)
        .where(where_clause)
        .order_by(EntitlementRule.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(data_query)
    rules = result.scalars().all()

    items = [
        {
            "id": str(r.id),
            "name": r.name,
            "name_en": r.name_en,
            "entitlement_type": r.entitlement_type,
            "amount": str(r.amount),
            "unit": r.unit,
            "max_amount": str(r.max_amount) if r.max_amount else None,
            "is_active": r.is_active,
            "effective_date": r.effective_date.isoformat() if r.effective_date else None,
            "expiry_date": r.expiry_date.isoformat() if r.expiry_date else None,
        }
        for r in rules
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }
