# ============================================
# FFCES - خدمة دفتر الأستاذ (Ledger Service)
# ============================================
"""
خدمة إدارة القيود المحاسبية
Manages double-entry accounting ledger entries
"""
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LedgerEntry, Account, Custody, Expense, Settlement, Payment, User


class LedgerService:
    """
    خدمة دفتر الأستاذ - Ledger Entry Service
    Handles double-entry bookkeeping for all financial transactions
    """

    @staticmethod
    async def create_entry(
        db: AsyncSession,
        debit_account_id: UUID,
        credit_account_id: UUID,
        amount: Decimal,
        description: str,
        reference_type: str,
        reference_id: UUID,
        created_by: UUID,
        org_id: UUID,
        currency: str = "SAR",
        journal_number: Optional[str] = None,
    ) -> LedgerEntry:
        """
        إنشاء قيد محاسبي مزدوج
        Create a double-entry ledger record
        """
        entry = LedgerEntry(
            debit_account_id=debit_account_id,
            credit_account_id=credit_account_id,
            amount=amount,
            currency=currency,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=created_by,
            organization_id=org_id,
            journal_number=journal_number or LedgerService._generate_journal_number(),
            entry_date=datetime.now(timezone.utc),
        )
        db.add(entry)

        # Update account balances
        await LedgerService._update_account_balance(db, debit_account_id, amount, "debit")
        await LedgerService._update_account_balance(db, credit_account_id, amount, "credit")

        await db.flush()
        return entry

    @staticmethod
    async def create_custody_entry(
        db: AsyncSession,
        custody: Custody,
        created_by: UUID,
        org_id: UUID,
    ) -> LedgerEntry:
        """
        إنشاء قيد عند إصدار عهدة
        Create ledger entry when custody is issued
        """
        # Find accounts: debit custody holder, credit cash/bank
        custody_account = await LedgerService._find_account(db, org_id, "custody_receivable")
        cash_account = await LedgerService._find_account(db, org_id, "cash")

        return await LedgerService.create_entry(
            db=db,
            debit_account_id=custody_account.id if custody_account else uuid.UUID("00000000-0000-0000-0000-000000000001"),
            credit_account_id=cash_account.id if cash_account else uuid.UUID("00000000-0000-0000-0000-000000000002"),
            amount=custody.amount,
            description=f"إصدار عهدة - {custody.purpose}",
            reference_type="custody",
            reference_id=custody.id,
            created_by=created_by,
            org_id=org_id,
        )

    @staticmethod
    async def create_expense_entry(
        db: AsyncSession,
        expense: Expense,
        org_id: UUID,
    ) -> LedgerEntry:
        """
        إنشاء قيد عند تسجيل مصروف
        Create ledger entry when expense is recorded
        """
        # Find accounts based on expense category
        expense_account = await LedgerService._find_account(db, org_id, "expenses", expense.category)
        custody_account = await LedgerService._find_account(db, org_id, "custody_receivable")

        return await LedgerService.create_entry(
            db=db,
            debit_account_id=expense_account.id if expense_account else uuid.UUID("00000000-0000-0000-0000-000000000003"),
            credit_account_id=custody_account.id if custody_account else uuid.UUID("00000000-0000-0000-0000-000000000001"),
            amount=expense.amount,
            description=f"مصروف - {expense.category} - {expense.description}",
            reference_type="expense",
            reference_id=expense.id,
            created_by=expense.created_by,
            org_id=org_id,
        )

    @staticmethod
    async def create_settlement_entry(
        db: AsyncSession,
        settlement: Settlement,
        org_id: UUID,
    ) -> LedgerEntry:
        """
        إنشاء قيد عند التسوية
        Create ledger entry when settlement is processed
        """
        cash_account = await LedgerService._find_account(db, org_id, "cash")
        custody_account = await LedgerService._find_account(db, org_id, "custody_receivable")

        # If there's a refund, debit cash, credit custody
        # If settlement covers expenses exactly, it's zero
        if settlement.refund_amount and settlement.refund_amount > 0:
            return await LedgerService.create_entry(
                db=db,
                debit_account_id=cash_account.id if cash_account else uuid.UUID("00000000-0000-0000-0000-000000000002"),
                credit_account_id=custody_account.id if custody_account else uuid.UUID("00000000-0000-0000-0000-000000000001"),
                amount=settlement.refund_amount,
                description=f"استرداد من تسوية عهدة",
                reference_type="settlement",
                reference_id=settlement.id,
                created_by=settlement.user_id,
                org_id=org_id,
            )

        # Otherwise close the custody
        return await LedgerService.create_entry(
            db=db,
            debit_account_id=cash_account.id if cash_account else uuid.UUID("00000000-0000-0000-0000-000000000002"),
            credit_account_id=custody_account.id if custody_account else uuid.UUID("00000000-0000-0000-0000-000000000001"),
            amount=settlement.amount,
            description=f"تسوية عهدة",
            reference_type="settlement",
            reference_id=settlement.id,
            created_by=settlement.user_id,
            org_id=org_id,
        )

    @staticmethod
    async def create_payment_entry(
        db: AsyncSession,
        payment: Payment,
        org_id: UUID,
    ) -> LedgerEntry:
        """
        إنشاء قيد عند الدفع
        Create ledger entry when payment is processed
        """
        payee_account = await LedgerService._find_account(db, org_id, "accounts_payable")
        cash_account = await LedgerService._find_account(db, org_id, "cash")

        return await LedgerService.create_entry(
            db=db,
            debit_account_id=payee_account.id if payee_account else uuid.UUID("00000000-0000-0000-0000-000000000004"),
            credit_account_id=cash_account.id if cash_account else uuid.UUID("00000000-0000-0000-0000-000000000002"),
            amount=payment.amount,
            description=f"دفعة - {payment.description or 'بدون وصف'}",
            reference_type="payment",
            reference_id=payment.id,
            created_by=payment.created_by,
            org_id=org_id,
        )

    @staticmethod
    async def get_account_balance(
        db: AsyncSession,
        account_id: UUID,
    ) -> Decimal:
        """
        جلب رصيد الحساب الحالي
        Get current account balance
        """
        query = select(Account).where(Account.id == account_id)
        result = await db.execute(query)
        account = result.scalar_one_or_none()
        return account.balance if account else Decimal("0")

    @staticmethod
    async def get_account_ledger(
        db: AsyncSession,
        account_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[LedgerEntry], int]:
        """
        جلب قيود الحساب
        Get ledger entries for an account
        """
        from sqlalchemy import or_

        conditions = or_(
            LedgerEntry.debit_account_id == account_id,
            LedgerEntry.credit_account_id == account_id,
        )

        count_query = select(func.count()).select_from(LedgerEntry).where(conditions)
        total = (await db.execute(count_query)).scalar() or 0

        data_query = (
            select(LedgerEntry)
            .where(conditions)
            .order_by(LedgerEntry.entry_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(data_query)
        entries = result.scalars().all()

        return list(entries), total

    # ===== Private Helpers =====

    @staticmethod
    async def _update_account_balance(
        db: AsyncSession,
        account_id: UUID,
        amount: Decimal,
        entry_type: str,
    ) -> None:
        """تحديث رصيد الحساب"""
        query = select(Account).where(Account.id == account_id)
        result = await db.execute(query)
        account = result.scalar_one_or_none()

        if account:
            if entry_type == "debit":
                account.balance += amount
            else:
                account.balance -= amount

    @staticmethod
    async def _find_account(
        db: AsyncSession,
        org_id: UUID,
        account_type: str,
        sub_type: Optional[str] = None,
    ) -> Optional[Account]:
        """البحث عن حساب في شجرة الحسابات"""
        conditions = [
            Account.organization_id == org_id,
            Account.is_active == True,
        ]

        if sub_type:
            conditions.append(Account.name.ilike(f"%{sub_type}%"))

        # Fallback: find by type
        query = select(Account).where(and_(*conditions)).limit(1)
        result = await db.execute(query)
        account = result.scalar_one_or_none()

        if not account and not sub_type:
            # Try to find any account of this type
            query = select(Account).where(
                and_(
                    Account.organization_id == org_id,
                    Account.is_active == True,
                    Account.account_type == account_type,
                )
            ).limit(1)
            result = await db.execute(query)
            account = result.scalar_one_or_none()

        return account

    @staticmethod
    def _generate_journal_number() -> str:
        """توليد رقم قيد محاسبي"""
        now = datetime.now(timezone.utc)
        return f"JE-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
