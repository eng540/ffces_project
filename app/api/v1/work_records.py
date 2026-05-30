# ============================================================
# Work Records API Routes
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models import WorkRecord, Party, Project
from app.schemas import WorkRecordCreate, WorkRecordResponse, WorkRecordVerification, PaginatedResponse
from app.services.audit_service import AuditService

router = APIRouter()

@router.post("", response_model=WorkRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_work_record(
    data: WorkRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role(["field_supervisor", "accountant", "super_admin"]))
):
    party_query = select(Party).where(Party.id == data.party_id)
    result = await db.execute(party_query)
    party = result.scalar_one_or_none()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    work_record = WorkRecord(
        party_id=data.party_id,
        project_id=data.project_id,
        record_date=data.record_date,
        quantity=data.quantity,
        unit=data.unit,
        description=data.description,
        location=data.location,
        created_by=current_user.id,
        status="pending"
    )

    db.add(work_record)
    await db.flush()
    await db.refresh(work_record)

    audit = AuditService(db)
    await audit.log_create(
        user_id=current_user.id,
        entity_type="work_record",
        entity_id=work_record.id,
        data={"quantity": float(data.quantity), "unit": data.unit, "party_id": str(data.party_id)}
    )

    return work_record

@router.post("/bulk")
async def create_bulk_work_records(
    data: List[WorkRecordCreate],
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role(["field_supervisor", "accountant", "super_admin"]))
):
    records = []
    for item in data:
        record = WorkRecord(
            party_id=item.party_id,
            project_id=item.project_id,
            record_date=item.record_date,
            quantity=item.quantity,
            unit=item.unit,
            description=item.description,
            created_by=current_user.id,
            status="pending"
        )
        db.add(record)
        records.append(record)

    await db.flush()

    audit = AuditService(db)
    await audit.log_create(
        user_id=current_user.id,
        entity_type="work_record_bulk",
        entity_id=records[0].id if records else None,
        data={"count": len(records)}
    )

    return {"message": f"Created {len(records)} work records", "records": records}

@router.patch("/{record_id}/verify")
async def verify_work_record(
    record_id: UUID,
    data: WorkRecordVerification,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role(["field_supervisor", "accountant", "super_admin"]))
):
    query = select(WorkRecord).where(WorkRecord.id == record_id)
    result = await db.execute(query)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Work record not found")

    record.status = data.status
    record.verified_by = current_user.id
    record.verified_at = datetime.now()
    record.verification_method = data.verification_method
    if data.status == "rejected":
        record.rejection_reason = data.rejection_reason

    await db.flush()

    return {"message": f"Work record {data.status}", "record_id": str(record_id)}

@router.get("", response_model=PaginatedResponse)
async def list_work_records(
    party_id: Optional[UUID] = Query(None),
    project_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    query = select(WorkRecord).order_by(desc(WorkRecord.record_date))
    if party_id: query = query.where(WorkRecord.party_id == party_id)
    if project_id: query = query.where(WorkRecord.project_id == project_id)
    if status: query = query.where(WorkRecord.status == status)

    count_result = await db.execute(query)
    total = len(count_result.scalars().all())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size}
