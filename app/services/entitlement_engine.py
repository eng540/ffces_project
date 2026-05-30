# ============================================================
# Entitlement Engine - Core Calculation Logic
# Calculates worker entitlements based on work records and rules
# ============================================================

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models import EntitlementRule, WorkRecord, Entitlement, Party, Project
from app.schemas import EntitlementCalculationRequest, EntitlementCreate
from app.services.ledger_service import LedgerService
from app.services.audit_service import AuditService
import logging

logger = logging.getLogger(__name__)

class EntitlementEngine:
    """
    محرك الحساب الرئيسي للاستحقاقات
    يحسب المستحقات بناءً على سجلات العمل وقواعد الحساب
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ledger = LedgerService(db)
        self.audit = AuditService(db)

    async def calculate_entitlements(
        self,
        party_id: UUID,
        project_id: UUID,
        period_start: date,
        period_end: date,
        created_by: UUID
    ) -> List[Entitlement]:
        """
        حساب جميع الاستحقاقات للعامل في الفترة المحددة
        """
        logger.info(f"Calculating entitlements for party {party_id} period {period_start} to {period_end}")

        # 1. جلب القواعد النشطة
        rules = await self._get_active_rules(party_id, project_id, period_start)

        # 2. جلب سجلات العمل المعتمدة
        work_records = await self._get_verified_work_records(
            party_id, project_id, period_start, period_end
        )

        entitlements = []

        for rule in rules:
            entitlement = await self._calculate_by_rule(
                rule, work_records, period_start, period_end, created_by
            )
            if entitlement:
                entitlements.append(entitlement)

        # 3. حفظ الاستحقاقات
        self.db.add_all(entitlements)
        await self.db.flush()

        # 4. إنشاء القيود المحاسبية
        for ent in entitlements:
            await self.ledger.create_entitlement_entry(ent, created_by)

        await self.audit.log_action(
            user_id=created_by,
            action="create",
            entity_type="entitlement_batch",
            entity_id=party_id,
            new_values={
                "count": len(entitlements),
                "period_start": str(period_start),
                "period_end": str(period_end)
            }
        )

        return entitlements

    async def _get_active_rules(
        self,
        party_id: UUID,
        project_id: UUID,
        as_of_date: date
    ) -> List[EntitlementRule]:
        """جلب القواعد النشطة للعامل"""
        query = select(EntitlementRule).where(
            and_(
                EntitlementRule.party_id == party_id,
                EntitlementRule.is_active == True,
                EntitlementRule.effective_from <= as_of_date,
                (EntitlementRule.effective_to.is_(None) | (EntitlementRule.effective_to >= as_of_date))
            )
        )
        if project_id:
            query = query.where(
                (EntitlementRule.project_id.is_(None) | (EntitlementRule.project_id == project_id))
            )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _get_verified_work_records(
        self,
        party_id: UUID,
        project_id: UUID,
        period_start: date,
        period_end: date
    ) -> List[WorkRecord]:
        """جلب سجلات العمل المعتمدة"""
        query = select(WorkRecord).where(
            and_(
                WorkRecord.party_id == party_id,
                WorkRecord.project_id == project_id,
                WorkRecord.record_date >= period_start,
                WorkRecord.record_date <= period_end,
                WorkRecord.status.in_(["verified", "approved"])
            )
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def _calculate_by_rule(
        self,
        rule: EntitlementRule,
        work_records: List[WorkRecord],
        period_start: date,
        period_end: date,
        created_by: UUID
    ) -> Optional[Entitlement]:
        """حساب الاستحقاق بناءً على نوع القاعدة"""

        if rule.calc_type == "daily":
            return await self._calculate_daily(rule, work_records, period_start, period_end, created_by)
        elif rule.calc_type == "quantity":
            return await self._calculate_quantity(rule, work_records, period_start, period_end, created_by)
        elif rule.calc_type == "monthly":
            return await self._calculate_monthly(rule, period_start, period_end, created_by)
        elif rule.calc_type == "hourly":
            return await self._calculate_hourly(rule, work_records, period_start, period_end, created_by)
        elif rule.calc_type == "lump_sum":
            return await self._calculate_lump_sum(rule, work_records, period_start, period_end, created_by)
        elif rule.calc_type == "mixed":
            return await self._calculate_mixed(rule, work_records, period_start, period_end, created_by)

        return None

    async def _calculate_daily(
        self,
        rule: EntitlementRule,
        work_records: List[WorkRecord],
        period_start: date,
        period_end: date,
        created_by: UUID
    ) -> Entitlement:
        """حساب الاستحقاق اليومي"""
        # عدد الأيام الفريدة
        unique_days = set()
        for wr in work_records:
            if wr.unit in ["day", "يوم"]:
                unique_days.add(wr.record_date)

        total_days = len(unique_days)
        amount = Decimal(str(total_days)) * Decimal(str(rule.rate))

        calculation_details = {
            "version": "1.0",
            "calc_type": "daily",
            "total_days": total_days,
            "daily_rate": float(rule.rate),
            "formula": f"{total_days} × {rule.rate}",
            "period": f"{period_start} to {period_end}",
            "work_record_ids": [str(wr.id) for wr in work_records if wr.unit in ["day", "يوم"]]
        }

        return Entitlement(
            party_id=rule.party_id,
            project_id=rule.project_id,
            rule_id=rule.id,
            amount=amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            currency="USD",
            calculation_details=calculation_details,
            period_start=period_start,
            period_end=period_end,
            status="calculated",
            paid_amount=Decimal("0"),
            created_by=created_by
        )

    async def _calculate_quantity(
        self,
        rule: EntitlementRule,
        work_records: List[WorkRecord],
        period_start: date,
        period_end: date,
        created_by: UUID
    ) -> Entitlement:
        """حساب الاستحقاق بالكمية (متر، قطعة، طن)"""
        total_qty = sum(
            Decimal(str(wr.quantity)) 
            for wr in work_records 
            if wr.unit == rule.unit
        )

        amount = total_qty * Decimal(str(rule.rate))

        # التحقق من الحدود
        if rule.min_quantity and total_qty < Decimal(str(rule.min_quantity)):
            logger.warning(f"Quantity {total_qty} below minimum {rule.min_quantity}")

        calculation_details = {
            "version": "1.0",
            "calc_type": "quantity",
            "total_quantity": float(total_qty),
            "unit": rule.unit,
            "rate": float(rule.rate),
            "formula": f"{total_qty} × {rule.rate}",
            "period": f"{period_start} to {period_end}",
            "work_record_ids": [str(wr.id) for wr in work_records if wr.unit == rule.unit],
            "min_quantity": float(rule.min_quantity) if rule.min_quantity else None,
            "max_quantity": float(rule.max_quantity) if rule.max_quantity else None
        }

        return Entitlement(
            party_id=rule.party_id,
            project_id=rule.project_id,
            rule_id=rule.id,
            amount=amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            currency="USD",
            calculation_details=calculation_details,
            period_start=period_start,
            period_end=period_end,
            status="calculated",
            paid_amount=Decimal("0"),
            created_by=created_by
        )

    async def _calculate_monthly(
        self,
        rule: EntitlementRule,
        period_start: date,
        period_end: date,
        created_by: UUID
    ) -> Entitlement:
        """حساب الاستحقاق الشهري"""
        # حساب عدد الأشهر الكاملة في الفترة
        months = (period_end.year - period_start.year) * 12 + (period_end.month - period_start.month) + 1
        amount = Decimal(str(months)) * Decimal(str(rule.rate))

        calculation_details = {
            "version": "1.0",
            "calc_type": "monthly",
            "total_months": months,
            "monthly_rate": float(rule.rate),
            "formula": f"{months} × {rule.rate}",
            "period": f"{period_start} to {period_end}"
        }

        return Entitlement(
            party_id=rule.party_id,
            project_id=rule.project_id,
            rule_id=rule.id,
            amount=amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            currency="USD",
            calculation_details=calculation_details,
            period_start=period_start,
            period_end=period_end,
            status="calculated",
            paid_amount=Decimal("0"),
            created_by=created_by
        )

    async def _calculate_hourly(
        self,
        rule: EntitlementRule,
        work_records: List[WorkRecord],
        period_start: date,
        period_end: date,
        created_by: UUID
    ) -> Entitlement:
        """حساب الاستحقاق بالساعة"""
        total_hours = sum(
            Decimal(str(wr.quantity)) 
            for wr in work_records 
            if wr.unit in ["hour", "ساعة"]
        )
        amount = total_hours * Decimal(str(rule.rate))

        calculation_details = {
            "version": "1.0",
            "calc_type": "hourly",
            "total_hours": float(total_hours),
            "hourly_rate": float(rule.rate),
            "formula": f"{total_hours} × {rule.rate}",
            "period": f"{period_start} to {period_end}",
            "work_record_ids": [str(wr.id) for wr in work_records if wr.unit in ["hour", "ساعة"]]
        }

        return Entitlement(
            party_id=rule.party_id,
            project_id=rule.project_id,
            rule_id=rule.id,
            amount=amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            currency="USD",
            calculation_details=calculation_details,
            period_start=period_start,
            period_end=period_end,
            status="calculated",
            paid_amount=Decimal("0"),
            created_by=created_by
        )

    async def _calculate_lump_sum(
        self,
        rule: EntitlementRule,
        work_records: List[WorkRecord],
        period_start: date,
        period_end: date,
        created_by: UUID
    ) -> Entitlement:
        """حساب الاستحقاق المقطوعي"""
        # المقطوعية: مبلغ ثابت مقابل عمل محدد
        amount = Decimal(str(rule.rate))

        # التحقق من وجود سجل عمل واحد على الأقل
        if not work_records:
            return None

        calculation_details = {
            "version": "1.0",
            "calc_type": "lump_sum",
            "lump_sum_amount": float(rule.rate),
            "formula": f"{rule.rate} (مقطوعية)",
            "period": f"{period_start} to {period_end}",
            "work_record_ids": [str(wr.id) for wr in work_records]
        }

        return Entitlement(
            party_id=rule.party_id,
            project_id=rule.project_id,
            rule_id=rule.id,
            amount=amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            currency="USD",
            calculation_details=calculation_details,
            period_start=period_start,
            period_end=period_end,
            status="calculated",
            paid_amount=Decimal("0"),
            created_by=created_by
        )

    async def _calculate_mixed(
        self,
        rule: EntitlementRule,
        work_records: List[WorkRecord],
        period_start: date,
        period_end: date,
        created_by: UUID
    ) -> Entitlement:
        """حساب الاستحقاق المختلط (راتب + بدلات - خصميات)"""
        components = rule.components or []
        total_amount = Decimal("0")
        detail_components = []

        for comp in components:
            comp_amount = Decimal(str(comp.get("amount", 0)))
            comp_type = comp.get("type", "")

            if comp_type in ["deduction", "خصم", "penalty"]:
                total_amount -= comp_amount
                detail_components.append({
                    "type": comp_type,
                    "description": comp.get("description", ""),
                    "amount": float(-comp_amount),
                    "operation": "subtract"
                })
            else:
                total_amount += comp_amount
                detail_components.append({
                    "type": comp_type,
                    "description": comp.get("description", ""),
                    "amount": float(comp_amount),
                    "operation": "add"
                })

        calculation_details = {
            "version": "1.0",
            "calc_type": "mixed",
            "components": detail_components,
            "total": float(total_amount),
            "formula": "مجموع المكونات",
            "period": f"{period_start} to {period_end}"
        }

        return Entitlement(
            party_id=rule.party_id,
            project_id=rule.project_id,
            rule_id=rule.id,
            amount=total_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            currency="USD",
            calculation_details=calculation_details,
            period_start=period_start,
            period_end=period_end,
            status="calculated",
            paid_amount=Decimal("0"),
            created_by=created_by
        )
