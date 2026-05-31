# ============================================
# FFCES - خدمة أرصدة العهد (Balance Service)
# ============================================
"""
خدمة مراقبة وإدارة أرصدة العهد
Monitors and manages custody balances and status
"""
import uuid
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Tuple, Dict
from uuid import UUID

from sqlalchemy import select, and_, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Custody, Settlement, Project, User


class BalanceService:
    """
    خدمة الأرصدة - Balance Monitoring Service
    Tracks custody balances, detects overdue custodies, and updates statuses
    """

    @staticmethod
    async def calculate_custody_balance(
        db: AsyncSession,
        custody_id: UUID,
    ) -> Dict:
        """
        حساب رصيد العهدة الحالي (المصروفات المقبولة + التسويات المكتملة)
        Calculate current custody balance
        """
        query = select(Custody).where(Custody.id == custody_id)
        result = await db.execute(query)
        custody = result.scalar_one_or_none()

        if not custody:
            raise ValueError("العهدة غير موجودة / Custody not found")

        # Calculate total approved expenses
        from app.models import Expense
        expense_query = select(func.coalesce(func.sum(Expense.amount), 0)).where(
            and_(
                Expense.custody_id == custody_id,
                Expense.status.in_(["approved", "verified"]),
            )
        )
        total_expenses = (await db.execute(expense_query)).scalar() or Decimal("0")

        # Calculate total completed settlements
        settlement_query = select(func.coalesce(func.sum(Settlement.amount), 0)).where(
            and_(
                Settlement.custody_id == custody_id,
                Settlement.status == "completed",
            )
        )
        total_settlements = (await db.execute(settlement_query)).scalar() or Decimal("0")

        remaining = custody.amount - total_expenses

        return {
            "custody_id": custody_id,
            "original_amount": custody.amount,
            "total_expenses": total_expenses,
            "total_settlements": total_settlements,
            "remaining": remaining,
            "utilization_rate": (total_expenses / custody.amount * 100) if custody.amount > 0 else 0,
        }

    @staticmethod
    async def update_custody_status(
        db: AsyncSession,
        custody_id: UUID,
    ) -> str:
        """
        تحديث حالة العهدة تلقائياً بناءً على الرصيد
        Auto-update custody status based on balance
        """
        balance_info = await BalanceService.calculate_custody_balance(db, custody_id)
        remaining = balance_info["remaining"]

        query = select(Custody).where(Custody.id == custody_id)
        result = await db.execute(query)
        custody = result.scalar_one_or_none()

        if not custody:
            raise ValueError("العهدة غير موجودة")

        # CRITICAL FIX: Check negative BEFORE zero/less-equal
        if remaining < 0:
            new_status = "overdue"
        elif remaining <= 0:
            new_status = "settled"
        elif remaining < custody.amount:
            new_status = "partially_settled"
        else:
            # Check if past due date
            if custody.due_date and datetime.now(timezone.utc) > custody.due_date:
                new_status = "overdue"
            else:
                new_status = "active"

        if custody.status != new_status:
            custody.status = new_status
            custody.remaining_amount = max(remaining, Decimal("0"))
            custody.settled_amount = balance_info["total_settlements"]
            await db.flush()

        return new_status

    @staticmethod
    async def get_overdue_custodies(
        db: AsyncSession,
        org_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Custody], int]:
        """
        جلب العهد المتأخرة / المتجاوزة
        Fetch overdue custodies
        """
        today = datetime.now(timezone.utc)

        conditions = [
            Custody.status.in_(["active", "partially_settled", "overdue"]),
            Custody.due_date.isnot(None),
            Custody.due_date < today,
        ]

        if org_id:
            # Need to join through project to get org_id
            from app.models import Project
            conditions.append(
                Custody.project_id.in_(
                    select(Project.id).where(Project.organization_id == org_id)
                )
            )

        count_query = select(func.count()).select_from(Custody).where(and_(*conditions))
        total = (await db.execute(count_query)).scalar() or 0

        data_query = (
            select(Custody)
            .where(and_(*conditions))
            .order_by(Custody.due_date.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(data_query)
        custodies = result.scalars().all()

        return list(custodies), total

    @staticmethod
    async def get_user_custody_summary(
        db: AsyncSession,
        user_id: UUID,
    ) -> Dict:
        """
        ملخص عهد المستخدم
        User's custody summary
        """
        # Total custodies
        total_query = select(func.count()).where(Custody.holder_id == user_id)
        total_custodies = (await db.execute(total_query)).scalar() or 0

        # Active custodies
        active_query = select(func.count()).where(
            and_(
                Custody.holder_id == user_id,
                Custody.status == "active",
            )
        )
        active_custodies = (await db.execute(active_query)).scalar() or 0

        # Total amount
        amount_query = select(func.coalesce(func.sum(Custody.amount), 0)).where(
            Custody.holder_id == user_id
        )
        total_amount = (await db.execute(amount_query)).scalar() or Decimal("0")

        # Total remaining (unsettled)
        remaining_query = select(
            func.coalesce(func.sum(
                Custody.amount - func.coalesce(
                    select(func.sum(Settlement.amount)).where(
                        and_(
                            Settlement.custody_id == Custody.id,
                            Settlement.status == "completed",
                        )
                    ).correlate(Custody).scalar_subquery(),
                    Decimal("0")
                )
            ), 0)
        ).where(
            and_(
                Custody.holder_id == user_id,
                Custody.status.in_(["active", "partially_settled"]),
            )
        )
        total_remaining = (await db.execute(remaining_query)).scalar() or Decimal("0")

        return {
            "user_id": user_id,
            "total_custodies": total_custodies,
            "active_custodies": active_custodies,
            "total_amount": total_amount,
            "total_remaining": total_remaining,
        }

    @staticmethod
    async def get_project_balance_summary(
        db: AsyncSession,
        project_id: UUID,
    ) -> Dict:
        """
        ملخص أرصدة المشروع
        Project balance summary
        """
        # Project custody totals
        custody_amount_query = select(func.coalesce(func.sum(Custody.amount), 0)).where(
            Custody.project_id == project_id
        )
        total_custody_amount = (await db.execute(custody_amount_query)).scalar() or Decimal("0")

        custody_settled_query = select(func.coalesce(func.sum(Custody.settled_amount), 0)).where(
            Custody.project_id == project_id
        )
        total_settled = (await db.execute(custody_settled_query)).scalar() or Decimal("0")

        custody_remaining_query = select(func.coalesce(func.sum(Custody.remaining_amount), 0)).where(
            Custody.project_id == project_id
        )
        total_remaining = (await db.execute(custody_remaining_query)).scalar() or Decimal("0")

        # Active custodies count
        active_count_query = select(func.count()).where(
            and_(
                Custody.project_id == project_id,
                Custody.status == "active",
            )
        )
        active_count = (await db.execute(active_count_query)).scalar() or 0

        return {
            "project_id": project_id,
            "total_custody_amount": total_custody_amount,
            "total_settled": total_settled,
            "total_remaining": total_remaining,
            "active_custodies": active_count,
        }

    @staticmethod
    async def bulk_update_statuses(
        db: AsyncSession,
        custody_ids: Optional[List[UUID]] = None,
        org_id: Optional[UUID] = None,
    ) -> int:
        """
        تحديث حالات مجموعة من العهد
        Bulk update custody statuses
        """
        conditions = []
        if custody_ids:
            conditions.append(Custody.id.in_(custody_ids))
        if org_id:
            from app.models import Project
            conditions.append(
                Custody.project_id.in_(
                    select(Project.id).where(Project.organization_id == org_id)
                )
            )

        if not conditions:
            return 0

        query = select(Custody).where(and_(*conditions))
        result = await db.execute(query)
        custodies = result.scalars().all()

        updated = 0
        for custody in custodies:
            await BalanceService.update_custody_status(db, custody.id)
            updated += 1

        return updated
