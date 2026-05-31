# ============================================
# FFCES - التقارير (Reports API)
# ============================================
"""
واجهة برمجة تطبيقات التقارير المالية
API endpoints for financial reports generation
"""
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models import User, Custody, Expense, Settlement, Payment, Entitlement, WorkRecord, Project
from app.schemas import ReportRequest, ReportResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/reports", tags=["التقارير"])


@router.post("/generate")
async def generate_report(
    report_request: ReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """توليد تقرير - Generate a financial report"""
    report_type = report_request.report_type
    start_date = report_request.start_date
    end_date = report_request.end_date
    project_id = report_request.project_id
    user_id = report_request.user_id

    data = {}
    summary = {}

    if report_type == "custody_summary":
        data, summary = await _custody_summary_report(db, project_id, start_date, end_date)

    elif report_type == "expense_report":
        data, summary = await _expense_report(db, project_id, start_date, end_date)

    elif report_type == "settlement_report":
        data, summary = await _settlement_report(db, project_id, start_date, end_date)

    elif report_type == "entitlement_report":
        data, summary = await _entitlement_report(db, project_id, user_id, start_date, end_date)

    elif report_type == "project_report":
        if not project_id:
            raise HTTPException(status_code=400, detail="يجب تحديد المشروع لهذا النوع من التقارير")
        data, summary = await _project_report(db, project_id, start_date, end_date)

    else:
        raise HTTPException(status_code=400, detail="نوع التقرير غير معروف")

    await AuditService.log_action(
        db=db,
        user_id=current_user.id,
        action="generate_report",
        entity_type="report",
        entity_id=uuid.uuid4(),  # Report ID
        new_values={"report_type": report_type},
    )

    response = ReportResponse(
        report_type=report_type,
        generated_at=datetime.now(timezone.utc),
        data=data,
        summary=summary,
    )

    if report_request.format == "pdf":
        return await _generate_pdf(response)
    elif report_request.format == "excel":
        return await _generate_excel(response)
    else:
        return response


@router.get("/dashboard-stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """إحصائيات لوحة القيادة - Dashboard statistics"""
    # Total custodies
    total_custodies = (await db.execute(select(func.count(Custody.id)))).scalar() or 0
    active_custodies = (await db.execute(
        select(func.count(Custody.id)).where(Custody.status == "active")
    )).scalar() or 0

    # Total custody amounts
    total_amount = (await db.execute(select(func.coalesce(func.sum(Custody.amount), 0)))).scalar() or Decimal("0")

    # Pending expenses
    pending_expenses = (await db.execute(
        select(func.count(Expense.id)).where(Expense.status == "pending")
    )).scalar() or 0

    # Pending settlements
    pending_settlements = (await db.execute(
        select(func.count(Settlement.id)).where(Settlement.status == "pending")
    )).scalar() or 0

    # This month payments
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_payments = (await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            and_(
                Payment.payment_date >= month_start,
                Payment.status == "completed",
            )
        )
    )).scalar() or Decimal("0")

    return {
        "total_custodies": total_custodies,
        "active_custodies": active_custodies,
        "total_custody_amount": str(total_amount),
        "pending_expenses": pending_expenses,
        "pending_settlements": pending_settlements,
        "month_payments": str(month_payments),
    }


# ===== Report Generation Helpers =====

async def _custody_summary_report(
    db: AsyncSession,
    project_id: Optional[uuid.UUID],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> tuple:
    """تقرير ملخص العهد"""
    conditions = []
    if project_id:
        conditions.append(Custody.project_id == project_id)
    if start_date:
        conditions.append(Custody.issued_date >= start_date)
    if end_date:
        conditions.append(Custody.issued_date <= end_date)

    where = and_(*conditions) if conditions else True

    total = (await db.execute(select(func.count()).select_from(Custody).where(where))).scalar() or 0
    total_amount = (await db.execute(
        select(func.coalesce(func.sum(Custody.amount), 0)).where(where)
    )).scalar() or Decimal("0")
    settled_amount = (await db.execute(
        select(func.coalesce(func.sum(Custody.settled_amount), 0)).where(where)
    )).scalar() or Decimal("0")

    query = select(Custody).where(where).order_by(Custody.issued_date.desc()).limit(100)
    custodies = (await db.execute(query)).scalars().all()

    data = {
        "custodies": [
            {
                "id": str(c.id),
                "purpose": c.purpose,
                "amount": str(c.amount),
                "remaining": str(c.remaining_amount),
                "status": c.status,
            }
            for c in custodies
        ]
    }
    summary = {
        "total_custodies": total,
        "total_amount": str(total_amount),
        "settled_amount": str(settled_amount),
        "active_amount": str(total_amount - settled_amount),
    }
    return data, summary


async def _expense_report(
    db: AsyncSession,
    project_id: Optional[uuid.UUID],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> tuple:
    """تقرير المصروفات"""
    conditions = []
    if start_date:
        conditions.append(Expense.expense_date >= start_date)
    if end_date:
        conditions.append(Expense.expense_date <= end_date)

    where = and_(*conditions) if conditions else True

    # Group by category
    category_query = (
        select(Expense.category, func.count().label("count"), func.sum(Expense.amount).label("total"))
        .where(where)
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
    )
    categories = (await db.execute(category_query)).all()

    total = sum(c.total or 0 for c in categories)

    data = {
        "by_category": [
            {"category": c.category, "count": c.count, "total": str(c.total or 0)}
            for c in categories
        ]
    }
    summary = {
        "total_expenses": str(total),
        "categories_count": len(categories),
    }
    return data, summary


async def _settlement_report(
    db: AsyncSession,
    project_id: Optional[uuid.UUID],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> tuple:
    """تقرير التسويات"""
    conditions = []
    if start_date:
        conditions.append(Settlement.settlement_date >= start_date)
    if end_date:
        conditions.append(Settlement.settlement_date <= end_date)

    where = and_(*conditions) if conditions else True

    total = (await db.execute(select(func.count()).select_from(Settlement).where(where))).scalar() or 0
    total_amount = (await db.execute(
        select(func.coalesce(func.sum(Settlement.amount), 0)).where(where)
    )).scalar() or Decimal("0")
    total_refund = (await db.execute(
        select(func.coalesce(func.sum(Settlement.refund_amount), 0)).where(where)
    )).scalar() or Decimal("0")

    data = {"settlements_count": total}
    summary = {
        "total_amount": str(total_amount),
        "total_refund": str(total_refund),
    }
    return data, summary


async def _entitlement_report(
    db: AsyncSession,
    project_id: Optional[uuid.UUID],
    user_id: Optional[uuid.UUID],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> tuple:
    """تقرير الاستحقاقات"""
    conditions = []
    if user_id:
        conditions.append(Entitlement.user_id == user_id)
    if project_id:
        conditions.append(Entitlement.project_id == project_id)

    where = and_(*conditions) if conditions else True

    total = (await db.execute(select(func.count()).select_from(Entitlement).where(where))).scalar() or 0
    total_amount = (await db.execute(
        select(func.coalesce(func.sum(Entitlement.amount), 0)).where(where)
    )).scalar() or Decimal("0")
    paid_amount = (await db.execute(
        select(func.coalesce(func.sum(Entitlement.amount), 0)).where(
            and_(where, Entitlement.status == "paid")
        )
    )).scalar() or Decimal("0")

    data = {"total_entitlements": total}
    summary = {
        "total_amount": str(total_amount),
        "paid_amount": str(paid_amount),
        "unpaid_amount": str(total_amount - paid_amount),
    }
    return data, summary


async def _project_report(
    db: AsyncSession,
    project_id: uuid.UUID,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> tuple:
    """تقرير المشروع الشامل"""
    project_query = select(Project).where(Project.id == project_id)
    project = (await db.execute(project_query)).scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")

    # Custody stats
    custody_count = (await db.execute(
        select(func.count()).where(Custody.project_id == project_id)
    )).scalar() or 0
    custody_amount = (await db.execute(
        select(func.coalesce(func.sum(Custody.amount), 0)).where(Custody.project_id == project_id)
    )).scalar() or Decimal("0")

    # Expense stats
    expense_count = (await db.execute(
        select(func.count()).where(
            Expense.custody_id.in_(select(Custody.id).where(Custody.project_id == project_id))
        )
    )).scalar() or 0
    expense_amount = (await db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.custody_id.in_(select(Custody.id).where(Custody.project_id == project_id))
        )
    )).scalar() or Decimal("0")

    # Work records stats
    work_count = (await db.execute(
        select(func.count()).where(WorkRecord.project_id == project_id)
    )).scalar() or 0
    work_hours = (await db.execute(
        select(func.coalesce(func.sum(WorkRecord.hours_worked), 0)).where(WorkRecord.project_id == project_id)
    )).scalar() or 0

    data = {
        "project": {
            "name": project.name,
            "code": project.code,
            "status": project.status,
        }
    }
    summary = {
        "total_budget": str(project.total_budget),
        "spent_amount": str(project.spent_amount),
        "remaining_budget": str(project.total_budget - project.spent_amount),
        "custody_count": custody_count,
        "custody_amount": str(custody_amount),
        "expense_count": expense_count,
        "expense_amount": str(expense_amount),
        "work_records_count": work_count,
        "total_work_hours": work_hours,
    }
    return data, summary


# ===== Export Helpers (Stubs - would use reportlab/openpyxl) =====

async def _generate_pdf(report: ReportResponse):
    """Generate PDF report (stub)"""
    # In production: use reportlab to generate PDF
    return {
        "report_type": report.report_type,
        "format": "pdf",
        "generated_at": report.generated_at.isoformat(),
        "message": "PDF generation requires reportlab integration (not yet implemented)",
        "data": report.data,
        "summary": report.summary,
    }


async def _generate_excel(report: ReportResponse):
    """Generate Excel report (stub)"""
    # In production: use openpyxl to generate Excel
    return {
        "report_type": report.report_type,
        "format": "excel",
        "generated_at": report.generated_at.isoformat(),
        "message": "Excel generation requires openpyxl integration (not yet implemented)",
        "data": report.data,
        "summary": report.summary,
    }
