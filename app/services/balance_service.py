# ============================================================
# Balance Service - Real-time Balance Calculations
# ============================================================

from decimal import Decimal
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models import Custody, Expense, Settlement, Party, Entitlement, Payment
import logging

logger = logging.getLogger(__name__)

class BalanceService:
    """
    خدمة حساب الأرصدة
    جميع الأرصدة تحسب في الوقت الفعلي من المصدر
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_custody_balance(self, custody_id: UUID) -> dict:
        """حساب رصيد العهدة"""
        # المبلغ الأصلي
        custody_query = select(Custody).where(Custody.id == custody_id)
        result = await self.db.execute(custody_query)
        custody = result.scalar_one_or_none()

        if not custody:
            raise ValueError(f"Custody {custody_id} not found")

        # المصروفات المعتمدة
        expenses_query = select(func.sum(Expense.amount)).where(
            and_(
                Expense.custody_id == custody_id,
                Expense.status == "approved"
            )
        )
        expenses_result = await self.db.execute(expenses_query)
        total_expenses = expenses_result.scalar() or Decimal("0")

        # التسويات المكتملة
        settlements_query = select(func.sum(Settlement.amount)).where(
            and_(
                Settlement.custody_id == custody_id,
                Settlement.status == "completed"
            )
        )
        settlements_result = await self.db.execute(settlements_query)
        total_settlements = settlements_result.scalar() or Decimal("0")

        remaining = custody.amount - total_expenses - total_settlements

        # تحديد الحالة
        status = "open"
        if remaining <= 0:
            status = "closed_ready"
        elif custody.due_date and custody.due_date < date.today():
            status = "overdue"
        elif remaining < 0:
            status = "over_spent"

        return {
            "custody_id": str(custody_id),
            "custody_number": custody.custody_number,
            "original_amount": float(custody.amount),
            "total_expenses": float(total_expenses),
            "total_settlements": float(total_settlements),
            "remaining_balance": float(remaining),
            "status": status,
            "currency": custody.currency
        }

    async def get_party_balance(self, party_id: UUID, project_id: UUID = None) -> dict:
        """حساب رصيد الشخص (العامل/المورد)"""
        # الاستحقاقات
        entitlements_query = select(func.sum(Entitlement.amount)).where(
            and_(
                Entitlement.party_id == party_id,
                Entitlement.status.in_(["calculated", "pending_payment", "partially_paid"])
            )
        )
        if project_id:
            entitlements_query = entitlements_query.where(Entitlement.project_id == project_id)

        entitlements_result = await self.db.execute(entitlements_query)
        total_entitlements = entitlements_result.scalar() or Decimal("0")

        # الدفعات
        payments_query = select(
            func.sum(Payment.amount).filter(Payment.payment_type.notin_(["advance", "deduction"])),
            func.sum(Payment.amount).filter(Payment.payment_type == "advance"),
            func.sum(Payment.amount).filter(Payment.payment_type == "deduction")
        ).where(Payment.party_id == party_id)

        if project_id:
            payments_query = payments_query.where(Payment.project_id == project_id)

        payments_result = await self.db.execute(payments_query)
        row = payments_result.one()
        total_payments = row[0] or Decimal("0")
        total_advances = row[1] or Decimal("0")
        total_deductions = row[2] or Decimal("0")

        net_balance = total_entitlements - total_payments - total_deductions + total_advances

        return {
            "party_id": str(party_id),
            "total_entitlements": float(total_entitlements),
            "total_payments": float(total_payments),
            "total_advances": float(total_advances),
            "total_deductions": float(total_deductions),
            "net_balance": float(net_balance),
            "currency": "USD",
            "status": "positive" if net_balance > 0 else "zero" if net_balance == 0 else "negative"
        }

    async def get_project_summary(self, project_id: UUID) -> dict:
        """ملخص المشروع المالي"""
        # إجمالي المصروفات
        expenses_query = select(func.sum(Expense.amount)).where(
            and_(Expense.project_id == project_id, Expense.status == "approved")
        )
        expenses_result = await self.db.execute(expenses_query)
        total_expenses = expenses_result.scalar() or Decimal("0")

        # إجمالي الاستحقاقات
        entitlements_query = select(func.sum(Entitlement.amount)).where(
            Entitlement.project_id == project_id
        )
        entitlements_result = await self.db.execute(entitlements_query)
        total_entitlements = entitlements_result.scalar() or Decimal("0")

        # إجمالي الدفعات
        payments_query = select(func.sum(Payment.amount)).where(
            Payment.project_id == project_id
        )
        payments_result = await self.db.execute(payments_query)
        total_payments = payments_result.scalar() or Decimal("0")

        # ميزانية المشروع
        project_query = select(Project).where(Project.id == project_id)
        project_result = await self.db.execute(project_query)
        project = project_result.scalar_one_or_none()
        budget = project.budget_limit if project else Decimal("0")

        total_spent = total_expenses + total_entitlements + total_payments
        remaining_budget = budget - total_spent if budget else None

        return {
            "project_id": str(project_id),
            "total_expenses": float(total_expenses),
            "total_entitlements": float(total_entitlements),
            "total_payments": float(total_payments),
            "total_spent": float(total_spent),
            "budget_limit": float(budget) if budget else None,
            "remaining_budget": float(remaining_budget) if remaining_budget is not None else None,
            "budget_usage_percentage": float((total_spent / budget) * 100) if budget and budget > 0 else None
        }

from datetime import date
from app.models import Project
