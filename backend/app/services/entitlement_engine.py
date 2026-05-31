# ============================================
# FFCES - محرك الاستحقاقات (Entitlement Engine)
# ============================================
"""
محرك حساب الاستحقاقات المالية
Calculates financial entitlements based on rules, work records, and conditions
"""
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    EntitlementRule, Entitlement, WorkRecord, User, Project, Custody,
)


class EntitlementEngine:
    """
    محرك حساب الاستحقاقات - Entitlement Calculation Engine
    Matches rules against work records and calculates amounts
    """

    @staticmethod
    async def calculate_entitlements(
        db: AsyncSession,
        work_record_id: UUID,
        calculated_by: UUID,
    ) -> List[Entitlement]:
        """
        حساب الاستحقاقات لسجل عمل محدد
        Calculate entitlements for a given work record
        """
        # Fetch work record with user and project info
        query = select(WorkRecord).where(WorkRecord.id == work_record_id)
        result = await db.execute(query)
        work_record = result.scalar_one_or_none()

        if not work_record:
            raise ValueError("سجل العمل غير موجود / Work record not found")

        # Fetch applicable rules for this user's role and project
        user_query = select(User).where(User.id == work_record.user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()

        if not user:
            raise ValueError("المستخدم غير موجود / User not found")

        rules_query = select(EntitlementRule).where(
            and_(
                EntitlementRule.is_active == True,
                EntitlementRule.effective_date <= datetime.now(timezone.utc),
                # Either no expiry or expiry in future
                (
                    EntitlementRule.expiry_date.is_(None)
                    | (EntitlementRule.expiry_date > datetime.now(timezone.utc))
                ),
            )
        )
        rules_result = await db.execute(rules_query)
        all_rules = rules_result.scalars().all()

        entitlements = []
        for rule in all_rules:
            # Check if rule applies to this user's role or project
            if rule.role and rule.role != user.role:
                continue
            if rule.project_id and rule.project_id != work_record.project_id:
                continue

            # Calculate amount based on unit
            amount = EntitlementEngine._calculate_amount(
                rule=rule,
                work_record=work_record,
                user=user,
            )

            if amount <= 0:
                continue

            # Cap at max_amount if defined
            if rule.max_amount and amount > rule.max_amount:
                amount = rule.max_amount

            # Create entitlement
            entitlement = Entitlement(
                user_id=user.id,
                project_id=work_record.project_id,
                rule_id=rule.id,
                work_record_id=work_record.id,
                amount=amount,
                currency=rule.currency,
                status="calculated",
                period_start=work_record.date,
                period_end=work_record.date,
                calculation_basis=json.dumps({
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "unit": rule.unit,
                    "rate": str(rule.amount),
                    "work_hours": work_record.hours_worked,
                    "formula": "hours * rate" if rule.unit == "hourly" else "fixed",
                }),
            )
            db.add(entitlement)
            entitlements.append(entitlement)

        if entitlements:
            await db.flush()

        return entitlements

    @staticmethod
    def _calculate_amount(
        rule: EntitlementRule,
        work_record: WorkRecord,
        user: User,
    ) -> Decimal:
        """
        حساب المبلغ بناءً على وحدة القاعدة
        Calculate amount based on the rule's unit type
        """
        rate = rule.amount
        hours = work_record.hours_worked or 0

        if rule.unit == "hourly":
            return Decimal(str(hours)) * rate
        elif rule.unit == "daily":
            # If more than 4 hours worked, count as full day
            return rate if hours >= 4 else (rate / Decimal("2"))
        elif rule.unit == "monthly":
            return rate
        elif rule.unit == "fixed":
            return rate
        elif rule.unit == "per_km":
            # Distance would come from work_record metadata in real impl
            return rate
        elif rule.unit == "per_stay":
            return rate
        else:
            return rate

    @staticmethod
    async def get_user_entitlements(
        db: AsyncSession,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[Entitlement], int]:
        """
        جلب استحقاقات المستخدم مع فلترة وترقيم الصفحات
        Fetch user entitlements with filtering and pagination
        """
        conditions = [Entitlement.user_id == user_id]
        if project_id:
            conditions.append(Entitlement.project_id == project_id)
        if status:
            conditions.append(Entitlement.status == status)

        # Count query
        from sqlalchemy import func
        count_query = select(func.count()).select_from(Entitlement).where(and_(*conditions))
        total = (await db.execute(count_query)).scalar() or 0

        # Data query
        data_query = (
            select(Entitlement)
            .where(and_(*conditions))
            .order_by(Entitlement.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(data_query)
        entitlements = result.scalars().all()

        return list(entitlements), total

    @staticmethod
    async def approve_entitlement(
        db: AsyncSession,
        entitlement_id: UUID,
        approved_by: UUID,
        approve: bool = True,
    ) -> Entitlement:
        """
        اعتماد أو رفض استحقاق
        Approve or reject an entitlement
        """
        query = select(Entitlement).where(Entitlement.id == entitlement_id)
        result = await db.execute(query)
        entitlement = result.scalar_one_or_none()

        if not entitlement:
            raise ValueError("الاستحقاق غير موجود")

        entitlement.status = "approved" if approve else "rejected"
        entitlement.approved_by = approved_by
        entitlement.approved_at = datetime.now(timezone.utc)

        await db.flush()
        return entitlement
