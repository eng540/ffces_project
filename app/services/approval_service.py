# ============================================================
# Approval Workflow Service
# ============================================================

from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models import ApprovalWorkflow, User, Expense, Custody, Payment
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class ApprovalService:
    """
    خدمة الموافقات
    تحدد من يوافق بناءً على الدور والمبلغ
    """

    APPROVAL_RULES = {
        "expense": [
            {"max_amount": 100, "approvers": ["field_supervisor"], "levels": 1},
            {"max_amount": 500, "approvers": ["accountant"], "levels": 1},
            {"max_amount": 1000, "approvers": ["financial_manager"], "levels": 1},
            {"max_amount": float("inf"), "approvers": ["financial_manager", "super_admin"], "levels": 2}
        ],
        "custody": [
            {"max_amount": 500, "approvers": ["accountant"], "levels": 1},
            {"max_amount": 2000, "approvers": ["financial_manager"], "levels": 1},
            {"max_amount": float("inf"), "approvers": ["financial_manager", "super_admin"], "levels": 2}
        ],
        "payment": [
            {"max_amount": 200, "approvers": ["accountant"], "levels": 1},
            {"max_amount": 1000, "approvers": ["financial_manager"], "levels": 1},
            {"max_amount": float("inf"), "approvers": ["financial_manager", "super_admin"], "levels": 2}
        ]
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_required_approvers(self, entity_type: str, amount: Decimal, org_id: UUID) -> List[str]:
        """تحديد المطلوبين للموافقة بناءً على المبلغ"""
        rules = self.APPROVAL_RULES.get(entity_type, [])
        for rule in rules:
            if amount <= Decimal(str(rule["max_amount"])):
                return rule["approvers"]
        return ["financial_manager"]

    async def create_approval_workflow(
        self,
        entity_type: str,
        entity_id: UUID,
        amount: Decimal,
        org_id: UUID,
        requested_by: UUID
    ) -> List[ApprovalWorkflow]:
        """إنشاء سير موافقة جديد"""
        approver_roles = await self.get_required_approvers(entity_type, amount, org_id)

        # جلب المستخدمين بالأدوار المطلوبة
        workflows = []
        for level, role in enumerate(approver_roles, 1):
            users_query = select(User).where(
                and_(
                    User.organization_id == org_id,
                    User.role == role,
                    User.is_active == True
                )
            )
            result = await self.db.execute(users_query)
            users = result.scalars().all()

            for user in users:
                workflow = ApprovalWorkflow(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    approver_id=user.id,
                    approval_level=level,
                    status="pending",
                    threshold_amount=amount
                )
                self.db.add(workflow)
                workflows.append(workflow)

        await self.db.flush()
        return workflows

    async def approve(self, workflow_id: UUID, approver_id: UUID, notes: Optional[str] = None) -> ApprovalWorkflow:
        """موافقة على طلب"""
        query = select(ApprovalWorkflow).where(
            and_(
                ApprovalWorkflow.id == workflow_id,
                ApprovalWorkflow.approver_id == approver_id,
                ApprovalWorkflow.status == "pending"
            )
        )
        result = await self.db.execute(query)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise ValueError("Workflow not found or already processed")

        workflow.status = "approved"
        workflow.approved_at = datetime.now()
        workflow.notes = notes

        await self.db.flush()

        # التحقق من اكتمال جميع مستويات الموافقة
        await self._check_completion(workflow.entity_type, workflow.entity_id)

        return workflow

    async def reject(self, workflow_id: UUID, approver_id: UUID, notes: Optional[str] = None) -> ApprovalWorkflow:
        """رفض طلب"""
        query = select(ApprovalWorkflow).where(
            and_(
                ApprovalWorkflow.id == workflow_id,
                ApprovalWorkflow.approver_id == approver_id,
                ApprovalWorkflow.status == "pending"
            )
        )
        result = await self.db.execute(query)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise ValueError("Workflow not found or already processed")

        workflow.status = "rejected"
        workflow.rejected_at = datetime.now()
        workflow.notes = notes

        # رفض الكيان المرتبط
        await self._reject_entity(workflow.entity_type, workflow.entity_id)

        await self.db.flush()
        return workflow

    async def _check_completion(self, entity_type: str, entity_id: UUID):
        """التحقق من اكتمال الموافقات"""
        pending_query = select(ApprovalWorkflow).where(
            and_(
                ApprovalWorkflow.entity_type == entity_type,
                ApprovalWorkflow.entity_id == entity_id,
                ApprovalWorkflow.status == "pending"
            )
        )
        result = await self.db.execute(pending_query)
        pending = result.scalars().all()

        if not pending:
            # جميع الموافقات مكتملة
            await self._approve_entity(entity_type, entity_id)

    async def _approve_entity(self, entity_type: str, entity_id: UUID):
        """تحديث حالة الكيان إلى معتمد"""
        if entity_type == "expense":
            query = select(Expense).where(Expense.id == entity_id)
            result = await self.db.execute(query)
            entity = result.scalar_one_or_none()
            if entity:
                entity.status = "approved"
        elif entity_type == "custody":
            query = select(Custody).where(Custody.id == entity_id)
            result = await self.db.execute(query)
            entity = result.scalar_one_or_none()
            if entity:
                entity.status = "open"
        elif entity_type == "payment":
            query = select(Payment).where(Payment.id == entity_id)
            result = await self.db.execute(query)
            entity = result.scalar_one_or_none()
            if entity:
                pass  # Payments don't change status

    async def _reject_entity(self, entity_type: str, entity_id: UUID):
        """تحديث حالة الكيان إلى مرفوض"""
        if entity_type == "expense":
            query = select(Expense).where(Expense.id == entity_id)
            result = await self.db.execute(query)
            entity = result.scalar_one_or_none()
            if entity:
                entity.status = "rejected"
        elif entity_type == "custody":
            query = select(Custody).where(Custody.id == entity_id)
            result = await self.db.execute(query)
            entity = result.scalar_one_or_none()
            if entity:
                entity.status = "cancelled"

from datetime import datetime
