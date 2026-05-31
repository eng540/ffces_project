# ============================================
# FFCES - خدمة التدقيق (Audit Service)
# ============================================
"""
خدمة تسجيل ومراجعة أحداث التدقيق
Records and reviews audit trail events
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


class AuditService:
    """
    خدمة التدقيق - Audit Trail Service
    Records all significant actions for compliance and traceability
    """

    @staticmethod
    async def log_action(
        db: AsyncSession,
        user_id: UUID,
        action: str,
        entity_type: str,
        entity_id: UUID,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        تسجيل إجراء في سجل التدقيق
        Log an action to the audit trail
        """
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.now(timezone.utc),
        )
        db.add(log_entry)
        await db.flush()
        return log_entry

    @staticmethod
    async def get_entity_history(
        db: AsyncSession,
        entity_type: str,
        entity_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[AuditLog], int]:
        """
        جلب تاريخ تغييرات كيان معين
        Fetch the change history of a specific entity
        """
        conditions = [
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id,
        ]

        count_query = select(func.count()).select_from(AuditLog).where(and_(*conditions))
        total = (await db.execute(count_query)).scalar() or 0

        data_query = (
            select(AuditLog)
            .where(and_(*conditions))
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(data_query)
        entries = result.scalars().all()

        return list(entries), total

    @staticmethod
    async def get_user_activity(
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[AuditLog], int]:
        """
        جلب نشاط مستخدم معين
        Fetch activity log for a specific user
        """
        conditions = [AuditLog.user_id == user_id]

        count_query = select(func.count()).select_from(AuditLog).where(and_(*conditions))
        total = (await db.execute(count_query)).scalar() or 0

        data_query = (
            select(AuditLog)
            .where(and_(*conditions))
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(data_query)
        entries = result.scalars().all()

        return list(entries), total

    @staticmethod
    async def get_audit_summary(
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        ملخص التدقيق (عدد العمليات حسب النوع والكيان)
        Audit summary (operation counts by type and entity)
        """
        conditions = []
        if start_date:
            conditions.append(AuditLog.created_at >= start_date)
        if end_date:
            conditions.append(AuditLog.created_at <= end_date)

        where_clause = and_(*conditions) if conditions else True

        # Total actions
        total_query = select(func.count()).select_from(AuditLog).where(where_clause)
        total = (await db.execute(total_query)).scalar() or 0

        # By action type
        action_query = (
            select(AuditLog.action, func.count().label("count"))
            .where(where_clause)
            .group_by(AuditLog.action)
        )
        action_result = await db.execute(action_query)
        by_action = {row.action: row.count for row in action_result}

        # By entity type
        entity_query = (
            select(AuditLog.entity_type, func.count().label("count"))
            .where(where_clause)
            .group_by(AuditLog.entity_type)
        )
        entity_result = await db.execute(entity_query)
        by_entity = {row.entity_type: row.count for row in entity_result}

        return {
            "total_actions": total,
            "by_action": by_action,
            "by_entity": by_entity,
        }
