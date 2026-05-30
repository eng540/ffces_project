# ============================================================
# Audit Service - Immutable Audit Trail
# ============================================================

from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AuditLog
import logging

logger = logging.getLogger(__name__)

class AuditService:
    """
    خدمة التدقيق
    تسجل كل عملية: من، ماذا، متى، من أين
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_action(
        self,
        user_id: Optional[UUID],
        action: str,
        entity_type: str,
        entity_id: UUID,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        organization_id: Optional[UUID] = None
    ) -> AuditLog:
        """تسجيل عملية في سجل التدقيق"""
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            organization_id=organization_id
        )
        self.db.add(log)
        await self.db.flush()
        logger.info(f"Audit logged: {action} on {entity_type} {entity_id}")
        return log

    async def log_create(self, user_id: UUID, entity_type: str, entity_id: UUID, 
                         data: Dict[str, Any], **kwargs) -> AuditLog:
        """تسجيل عملية إنشاء"""
        return await self.log_action(
            user_id=user_id,
            action="create",
            entity_type=entity_type,
            entity_id=entity_id,
            new_values=data,
            **kwargs
        )

    async def log_update(self, user_id: UUID, entity_type: str, entity_id: UUID,
                         old_data: Dict[str, Any], new_data: Dict[str, Any], **kwargs) -> AuditLog:
        """تسجيل عملية تحديث"""
        return await self.log_action(
            user_id=user_id,
            action="update",
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_data,
            new_values=new_data,
            **kwargs
        )

    async def log_delete(self, user_id: UUID, entity_type: str, entity_id: UUID,
                         old_data: Dict[str, Any], **kwargs) -> AuditLog:
        """تسجيل عملية حذف"""
        return await self.log_action(
            user_id=user_id,
            action="delete",
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_data,
            **kwargs
        )

    async def log_approve(self, user_id: UUID, entity_type: str, entity_id: UUID,
                          data: Dict[str, Any], **kwargs) -> AuditLog:
        """تسجيل عملية موافقة"""
        return await self.log_action(
            user_id=user_id,
            action="approve",
            entity_type=entity_type,
            entity_id=entity_id,
            new_values=data,
            **kwargs
        )
