# ============================================
# FFCES - سجلات العمل (Work Records API)
# ============================================
"""
واجهة برمجة تطبيقات إدارة سجلات العمل الميداني
API endpoints for managing field work records
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models import User, WorkRecord, Project
from app.schemas import WorkRecordCreate, WorkRecordUpdate, PaginatedResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/work-records", tags=["سجلات العمل"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_work_record(
    work_record_data: WorkRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """تسجيل سجل عمل جديد - Create a new work record"""
    # Verify project exists
    project_query = select(Project).where(Project.id == work_record_data.project_id)
    project_result = await db.execute(project_query)
    if not project_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="المشروع غير موجود")

    work_record = WorkRecord(
        **work_record_data.model_dump(),
        created_at=datetime.now(timezone.utc),
    )
    db.add(work_record)
    await db.flush()
    await db.refresh(work_record)

    await AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="create",
        entity_type="work_record",
        entity_id=work_record.id,
        new_values={
            "project_id": str(work_record.project_id),
            "date": work_record.date.isoformat() if work_record.date else None,
            "hours_worked": work_record.hours_worked,
        },
    )

    return {
        "id": str(work_record.id),
        "user_id": str(work_record.user_id),
        "project_id": str(work_record.project_id),
        "date": work_record.date.isoformat() if work_record.date else None,
        "hours_worked": work_record.hours_worked,
        "status": work_record.status,
        "message": "تم تسجيل سجل العمل بنجاح",
    }


@router.get("", response_model=PaginatedResponse)
async def list_work_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[uuid.UUID] = Query(None),
    project_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """قائمة سجلات العمل - List work records with filtering"""
    conditions = []
    if user_id:
        conditions.append(WorkRecord.user_id == user_id)
    if project_id:
        conditions.append(WorkRecord.project_id == project_id)
    if status_filter:
        conditions.append(WorkRecord.status == status_filter)
    if date_from:
        conditions.append(WorkRecord.date >= date_from)
    if date_to:
        conditions.append(WorkRecord.date <= date_to)

    where_clause = and_(*conditions) if conditions else True

    count_query = select(func.count()).select_from(WorkRecord).where(where_clause)
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    data_query = (
        select(WorkRecord)
        .where(where_clause)
        .order_by(WorkRecord.date.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(data_query)
    records = result.scalars().all()

    items = [
        {
            "id": str(r.id),
            "user_id": str(r.user_id),
            "project_id": str(r.project_id),
            "date": r.date.isoformat() if r.date else None,
            "start_time": r.start_time.isoformat() if r.start_time else None,
            "end_time": r.end_time.isoformat() if r.end_time else None,
            "hours_worked": r.hours_worked,
            "location": r.location,
            "description": r.description,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{record_id}")
async def get_work_record(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """تفاصيل سجل العمل - Work record details"""
    query = select(WorkRecord).where(WorkRecord.id == record_id)
    result = await db.execute(query)
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="سجل العمل غير موجود")

    return {
        "id": str(record.id),
        "user_id": str(record.user_id),
        "project_id": str(record.project_id),
        "date": record.date.isoformat() if record.date else None,
        "start_time": record.start_time.isoformat() if record.start_time else None,
        "end_time": record.end_time.isoformat() if record.end_time else None,
        "hours_worked": record.hours_worked,
        "location": record.location,
        "description": record.description,
        "status": record.status,
        "approved_by": str(record.approved_by) if record.approved_by else None,
        "approved_at": record.approved_at.isoformat() if record.approved_at else None,
        "notes": record.notes,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


@router.put("/{record_id}")
async def update_work_record(
    record_id: uuid.UUID,
    record_data: WorkRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """تحديث سجل عمل - Update work record"""
    query = select(WorkRecord).where(WorkRecord.id == record_id)
    result = await db.execute(query)
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="سجل العمل غير موجود")

    if record.status not in ["draft"]:
        raise HTTPException(status_code=400, detail="لا يمكن تعديل سجل عمل تم إرساله")

    update_data = record_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(record, key, value)

    record.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "id": str(record.id),
        "message": "تم تحديث سجل العمل بنجاح",
    }


@router.post("/{record_id}/submit")
async def submit_work_record(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """إرسال سجل عمل للموافقة - Submit work record for approval"""
    query = select(WorkRecord).where(WorkRecord.id == record_id)
    result = await db.execute(query)
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="سجل العمل غير موجود")

    if record.status not in ["draft"]:
        raise HTTPException(status_code=400, detail="لا يمكن إرسال سجل عمل تم معالجته")

    record.status = "submitted"
    await db.flush()

    return {
        "id": str(record.id),
        "status": "submitted",
        "message": "تم إرسال سجل العمل للموافقة",
    }


@router.post("/{record_id}/approve")
async def approve_work_record(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager"])),
):
    """اعتماد سجل عمل - Approve work record"""
    query = select(WorkRecord).where(WorkRecord.id == record_id)
    result = await db.execute(query)
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="سجل العمل غير موجود")

    if record.status != "submitted":
        raise HTTPException(status_code=400, detail="لا يمكن اعتماد سجل عمل غير مُرسل")

    record.status = "approved"
    record.approved_by = current_user.id
    record.approved_at = datetime.now(timezone.utc)
    await db.flush()

    await AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="approve",
        entity_type="work_record",
        entity_id=record.id,
    )

    return {
        "id": str(record.id),
        "status": "approved",
        "message": "تم اعتماد سجل العمل بنجاح",
    }


@router.post("/{record_id}/reject")
async def reject_work_record(
    record_id: uuid.UUID,
    reason: str = Query(..., min_length=3),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager"])),
):
    """رفض سجل عمل - Reject work record"""
    query = select(WorkRecord).where(WorkRecord.id == record_id)
    result = await db.execute(query)
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="سجل العمل غير موجود")

    if record.status != "submitted":
        raise HTTPException(status_code=400, detail="لا يمكن رفض سجل عمل غير مُرسل")

    record.status = "rejected"
    record.approved_by = current_user.id
    record.approved_at = datetime.now(timezone.utc)
    record.notes = f"سبب الرفض: {reason}"
    await db.flush()

    return {
        "id": str(record.id),
        "status": "rejected",
        "message": "تم رفض سجل العمل",
    }
