# ============================================
# FFCES - خدمة الموافقات (Approval Service)
# ============================================
"""
خدمة إدارة سير الموافقات متعدد المستويات
Manages multi-level approval workflows
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApprovalWorkflow, User


class ApprovalService:
    """
    خدمة الموافقات - Approval Workflow Service
    Handles multi-level approval chains based on amounts and thresholds
    """

    @staticmethod
    async def initiate_workflow(
        db: AsyncSession,
        entity_type: str,
        entity_id: UUID,
        amount: Decimal,
        initiator_id: UUID,
        org_id: Optional[UUID] = None,
    ) -> List[ApprovalWorkflow]:
        """
        بدء سير موافقة جديد بناءً على المبلغ
        Initiate a new approval workflow based on amount thresholds
        """
        from app.core.config import settings

        # Determine approval levels based on amount
        levels = ApprovalService._determine_approval_levels(amount)

        workflows = []
        for level in levels:
            # Find appropriate approver for this level
            approver = await ApprovalService._find_approver(
                db, level, initiator_id, org_id
            )
            if not approver:
                continue

            workflow = ApprovalWorkflow(
                entity_type=entity_type,
                entity_id=entity_id,
                approver_id=approver.id,
                approval_level=level["level"],
                threshold_amount=level["threshold"],
                status="pending",
                created_at=datetime.now(timezone.utc),
            )
            db.add(workflow)
            workflows.append(workflow)

        if workflows:
            await db.flush()

        return workflows

    @staticmethod
    async def approve(
        db: AsyncSession,
        workflow_id: UUID,
        approver_id: UUID,
        notes: Optional[str] = None,
    ) -> ApprovalWorkflow:
        """
        اعتماد في سير الموافقة
        Approve an approval workflow step
        """
        query = select(ApprovalWorkflow).where(
            and_(
                ApprovalWorkflow.id == workflow_id,
                ApprovalWorkflow.approver_id == approver_id,
                ApprovalWorkflow.status == "pending",
            )
        )
        result = await db.execute(query)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise ValueError("خطأ: لا يمكن العثور على طلب الموافقة أو تمت معالجته مسبقاً")

        workflow.status = "approved"
        workflow.approved_at = datetime.now(timezone.utc)
        workflow.notes = notes

        await db.flush()

        # Check if this was the last level
        await ApprovalService._check_final_approval(db, workflow)

        return workflow

    @staticmethod
    async def reject(
        db: AsyncSession,
        workflow_id: UUID,
        approver_id: UUID,
        notes: Optional[str] = None,
    ) -> ApprovalWorkflow:
        """
        رفض في سير الموافقة
        Reject an approval workflow step
        """
        query = select(ApprovalWorkflow).where(
            and_(
                ApprovalWorkflow.id == workflow_id,
                ApprovalWorkflow.approver_id == approver_id,
                ApprovalWorkflow.status == "pending",
            )
        )
        result = await db.execute(query)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise ValueError("خطأ: لا يمكن العثور على طلب الموافقة أو تمت معالجته مسبقاً")

        workflow.status = "rejected"
        workflow.rejected_at = datetime.now(timezone.utc)
        workflow.notes = notes

        # Reject all pending workflows for same entity
        other_pending = select(ApprovalWorkflow).where(
            and_(
                ApprovalWorkflow.entity_type == workflow.entity_type,
                ApprovalWorkflow.entity_id == workflow.entity_id,
                ApprovalWorkflow.status == "pending",
                ApprovalWorkflow.id != workflow.id,
            )
        )
        other_result = await db.execute(other_pending)
        for other in other_result.scalars().all():
            other.status = "rejected"
            other.rejected_at = datetime.now(timezone.utc)

        await db.flush()
        return workflow

    @staticmethod
    async def get_pending_approvals(
        db: AsyncSession,
        approver_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[ApprovalWorkflow], int]:
        """
        جلب الموافقات المعلقة لمستخدم
        Fetch pending approvals for a user
        """
        conditions = [
            ApprovalWorkflow.approver_id == approver_id,
            ApprovalWorkflow.status == "pending",
        ]

        count_query = select(func.count()).select_from(ApprovalWorkflow).where(and_(*conditions))
        total = (await db.execute(count_query)).scalar() or 0

        data_query = (
            select(ApprovalWorkflow)
            .where(and_(*conditions))
            .order_by(ApprovalWorkflow.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(data_query)
        workflows = result.scalars().all()

        return list(workflows), total

    @staticmethod
    async def get_entity_approvals(
        db: AsyncSession,
        entity_type: str,
        entity_id: UUID,
    ) -> List[ApprovalWorkflow]:
        """
        جلب حالة الموافقات لكيان معين
        Fetch approval status for a specific entity
        """
        query = select(ApprovalWorkflow).where(
            and_(
                ApprovalWorkflow.entity_type == entity_type,
                ApprovalWorkflow.entity_id == entity_id,
            )
        ).order_by(ApprovalWorkflow.approval_level.asc())

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def is_fully_approved(
        db: AsyncSession,
        entity_type: str,
        entity_id: UUID,
    ) -> bool:
        """
        التحقق من اكتمال جميع الموافقات
        Check if all approval levels are approved
        """
        workflows = await ApprovalService.get_entity_approvals(db, entity_type, entity_id)

        if not workflows:
            return False

        return all(w.status == "approved" for w in workflows)

    # ===== Private Helpers =====

    @staticmethod
    def _determine_approval_levels(amount: Decimal) -> List[Dict]:
        """تحديد مستويات الموافقة بناءً على المبلغ"""
        from app.core.config import settings

        levels = []

        # Level 1: Always required
        levels.append({
            "level": 1,
            "threshold": settings.APPROVAL_LEVEL1_THRESHOLD,
        })

        if amount > settings.APPROVAL_LEVEL1_THRESHOLD:
            levels.append({
                "level": 2,
                "threshold": settings.APPROVAL_LEVEL2_THRESHOLD,
            })

        if amount > settings.APPROVAL_LEVEL2_THRESHOLD:
            levels.append({
                "level": 3,
                "threshold": settings.APPROVAL_LEVEL3_THRESHOLD,
            })

        return levels

    @staticmethod
    async def _find_approver(
        db: AsyncSession,
        level_info: Dict,
        initiator_id: UUID,
        org_id: Optional[UUID] = None,
    ) -> Optional[User]:
        """العثور عن موافق مناسب للمستوى المحدد"""
        from app.models import User

        # Find a manager or admin in the same organization
        conditions = [
            User.is_active == True,
            User.role.in_(["admin", "manager", "accountant"]),
            User.id != initiator_id,
        ]

        if org_id:
            conditions.append(User.organization_id == org_id)

        # Higher levels need higher authority
        if level_info["level"] >= 3:
            conditions.append(User.role == "admin")
        elif level_info["level"] >= 2:
            conditions.append(User.role.in_(["admin", "manager"]))

        query = select(User).where(and_(*conditions)).limit(1)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def _check_final_approval(
        db: AsyncSession,
        workflow: ApprovalWorkflow,
    ) -> None:
        """التحقق من اكتمال آخر مستوى موافقة"""
        # Get all workflows for this entity
        workflows = await ApprovalService.get_entity_approvals(
            db, workflow.entity_type, workflow.entity_id
        )

        if all(w.status == "approved" for w in workflows):
            # Update the entity status if needed
            from app.models import Custody, Expense, Settlement, Payment

            entity_models = {
                "custody": Custody,
                "expense": Expense,
                "settlement": Settlement,
                "payment": Payment,
            }

            model = entity_models.get(workflow.entity_type)
            if model:
                entity_query = select(model).where(model.id == workflow.entity_id)
                entity_result = await db.execute(entity_query)
                entity = entity_result.scalar_one_or_none()

                if entity:
                    # Set status based on entity type
                    if hasattr(entity, "status"):
                        entity.status = "approved" if entity.status in ["pending"] else entity.status
                    await db.flush()
