# ============================================================
# Ledger Service - Double-Entry Bookkeeping
# Immutable financial entries
# ============================================================

from decimal import Decimal
from typing import Optional
from uuid import UUID
from datetime import date
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import LedgerEntry, Account, Custody, Expense, Payment, Entitlement, Settlement
from app.schemas import LedgerEntry as LedgerEntrySchema
import logging

logger = logging.getLogger(__name__)

class LedgerService:
    """
    خدمة القيود المحاسبية
    تنفذ نظام القيد المزدوج مع حماية كاملة من التلاعب
    """

    # Chart of Accounts Mapping
    ACCOUNTS = {
        "cash": "1100",           # الصندوق
        "custody_outstanding": "1200",  # عهدة قيد التحصيل
        "accounts_receivable": "1300",  # ذمم مدينة
        "accounts_payable": "2100",     # ذمم دائنة
        "workers_entitlements": "2200", # مستحقات العمال
        "custody_received": "2300",     # عهدة مستلمة
        "materials_expense": "5100",    # مصروفات مواد
        "labor_expense": "5200",        # مصروفات عمال
        "transport_expense": "5300",    # مصروفات نقل
        "equipment_expense": "5400",    # مصروفات معدات
        "services_expense": "5500",     # مصروفات خدمات
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_account_by_code(self, org_id: UUID, code: str) -> Optional[Account]:
        """جلب الحساب حسب الكود"""
        query = select(Account).where(
            Account.organization_id == org_id,
            Account.code == code
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _generate_hash(self, entry: LedgerEntry) -> str:
        """توليد hash للقيد لمنع التلاعب"""
        data = f"{entry.reference_id}:{entry.reference_type}:{entry.amount}:{entry.entry_date}:{entry.created_at}"
        return hashlib.sha256(data.encode()).hexdigest()

    async def _get_previous_hash(self, org_id: UUID) -> Optional[str]:
        """جلب hash آخر قيد"""
        query = select(LedgerEntry).where(
            LedgerEntry.organization_id == org_id
        ).order_by(LedgerEntry.created_at.desc()).limit(1)
        result = await self.db.execute(query)
        last_entry = result.scalar_one_or_none()
        return last_entry.immutable_hash if last_entry else None

    async def create_custody_issued_entry(self, custody: Custody, user_id: UUID) -> LedgerEntry:
        """
        قيد: تسليم العهدة
        مدين: عهدة قيد التحصيل (1200)
        دائن: الصندوق (1100)
        """
        debit_acc = await self._get_account_by_code(custody.holder.organization_id, self.ACCOUNTS["custody_outstanding"])
        credit_acc = await self._get_account_by_code(custody.holder.organization_id, self.ACCOUNTS["cash"])

        entry = LedgerEntry(
            organization_id=custody.holder.organization_id,
            entry_type="custody_issued",
            reference_id=custody.id,
            reference_type="custody",
            debit_account_id=debit_acc.id,
            credit_account_id=credit_acc.id,
            amount=custody.amount,
            currency=custody.currency,
            entry_date=date.today(),
            description=f"تسليم عهدة رقم {custody.custody_number} للمندوب {custody.holder.full_name}",
            immutable_hash="",  # Will be set after creation
            previous_hash=await self._get_previous_hash(custody.holder.organization_id),
            created_by=user_id
        )
        entry.immutable_hash = await self._generate_hash(entry)

        self.db.add(entry)
        await self.db.flush()
        logger.info(f"Ledger entry created for custody {custody.custody_number}")
        return entry

    async def create_expense_entry(self, expense: Expense, user_id: UUID) -> LedgerEntry:
        """
        قيد: تسجيل مصروف
        مدين: حساب المصروف (حسب الفئة)
        دائن: عهدة المندوب (1200) أو الصندوق
        """
        # Map expense category to account
        category_map = {
            "materials": "materials_expense",
            "labor": "labor_expense",
            "transport": "transport_expense",
            "equipment": "equipment_expense",
            "services": "services_expense"
        }
        account_key = category_map.get(expense.category, "services_expense")

        debit_acc = await self._get_account_by_code(expense.custody.holder.organization_id, self.ACCOUNTS[account_key])
        credit_acc = await self._get_account_by_code(expense.custody.holder.organization_id, self.ACCOUNTS["custody_outstanding"])

        entry = LedgerEntry(
            organization_id=expense.custody.holder.organization_id,
            entry_type="expense",
            reference_id=expense.id,
            reference_type="expense",
            debit_account_id=debit_acc.id,
            credit_account_id=credit_acc.id,
            amount=expense.amount,
            currency=expense.currency,
            entry_date=expense.expense_date,
            description=f"مصروف {expense.category}: {expense.description}",
            immutable_hash="",
            previous_hash=await self._get_previous_hash(expense.custody.holder.organization_id),
            created_by=user_id
        )
        entry.immutable_hash = await self._generate_hash(entry)

        self.db.add(entry)
        await self.db.flush()
        return entry

    async def create_payment_entry(self, payment: Payment, user_id: UUID) -> LedgerEntry:
        """
        قيد: تسجيل دفعة
        مدين: مستحقات العمال (2200) أو الصندوق
        دائن: الصندوق (1100)
        """
        org_id = payment.party.organization_id

        if payment.payment_type in ["advance", "salary", "entitlement_settlement"]:
            debit_acc = await self._get_account_by_code(org_id, self.ACCOUNTS["workers_entitlements"])
        else:
            debit_acc = await self._get_account_by_code(org_id, self.ACCOUNTS["services_expense"])

        credit_acc = await self._get_account_by_code(org_id, self.ACCOUNTS["cash"])

        entry = LedgerEntry(
            organization_id=org_id,
            entry_type="payment",
            reference_id=payment.id,
            reference_type="payment",
            debit_account_id=debit_acc.id,
            credit_account_id=credit_acc.id,
            amount=payment.amount,
            currency=payment.currency,
            entry_date=payment.paid_at.date(),
            description=f"دفعة {payment.payment_type} للعامل {payment.party.full_name}",
            immutable_hash="",
            previous_hash=await self._get_previous_hash(org_id),
            created_by=user_id
        )
        entry.immutable_hash = await self._generate_hash(entry)

        self.db.add(entry)
        await self.db.flush()
        return entry

    async def create_entitlement_entry(self, entitlement, user_id: UUID) -> LedgerEntry:
        """
        قيد: تسجيل استحقاق
        مدين: مصروفات عمال (5200)
        دائن: مستحقات العمال (2200)
        """
        org_id = entitlement.party.organization_id

        debit_acc = await self._get_account_by_code(org_id, self.ACCOUNTS["labor_expense"])
        credit_acc = await self._get_account_by_code(org_id, self.ACCOUNTS["workers_entitlements"])

        entry = LedgerEntry(
            organization_id=org_id,
            entry_type="entitlement",
            reference_id=entitlement.id,
            reference_type="entitlement",
            debit_account_id=debit_acc.id,
            credit_account_id=credit_acc.id,
            amount=entitlement.amount,
            currency=entitlement.currency,
            entry_date=entitlement.period_end,
            description=f"استحقاق {entitlement.party.full_name} للفترة {entitlement.period_start} إلى {entitlement.period_end}",
            immutable_hash="",
            previous_hash=await self._get_previous_hash(org_id),
            created_by=user_id
        )
        entry.immutable_hash = await self._generate_hash(entry)

        self.db.add(entry)
        await self.db.flush()
        return entry

    async def create_settlement_entry(self, settlement: Settlement, user_id: UUID) -> LedgerEntry:
        """
        قيد: تسوية العهدة
        حسب نوع التسوية:
        - إعادة نقد: مدين الصندوق، دائن عهدة
        - خصم: مدين مصروف، دائن عهدة
        """
        org_id = settlement.custody.holder.organization_id

        if settlement.settlement_type == "cash_return":
            debit_acc = await self._get_account_by_code(org_id, self.ACCOUNTS["cash"])
            credit_acc = await self._get_account_by_code(org_id, self.ACCOUNTS["custody_outstanding"])
        elif settlement.settlement_type == "deduction":
            debit_acc = await self._get_account_by_code(org_id, self.ACCOUNTS["labor_expense"])
            credit_acc = await self._get_account_by_code(org_id, self.ACCOUNTS["custody_outstanding"])
        else:
            debit_acc = await self._get_account_by_code(org_id, self.ACCOUNTS["cash"])
            credit_acc = await self._get_account_by_code(org_id, self.ACCOUNTS["custody_outstanding"])

        entry = LedgerEntry(
            organization_id=org_id,
            entry_type="settlement",
            reference_id=settlement.id,
            reference_type="settlement",
            debit_account_id=debit_acc.id,
            credit_account_id=credit_acc.id,
            amount=settlement.amount,
            currency=settlement.currency,
            entry_date=date.today(),
            description=f"تسوية عهدة {settlement.custody.custody_number}: {settlement.settlement_type}",
            immutable_hash="",
            previous_hash=await self._get_previous_hash(org_id),
            created_by=user_id
        )
        entry.immutable_hash = await self._generate_hash(entry)

        self.db.add(entry)
        await self.db.flush()
        return entry
