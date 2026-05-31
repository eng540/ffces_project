# ============================================
# FFCES - عميل Redis (Redis Client Wrapper)
# ============================================
import json
from typing import Optional, Any

import redis.asyncio as aioredis

from app.core.config import settings


class RedisClient:
    """غلاف لعميل Redis غير المتزامن"""

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None

    async def connect(self):
        """إنشاء الاتصال بـ Redis"""
        self._client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

    async def disconnect(self):
        """إغلاق الاتصال"""
        if self._client:
            await self._client.close()
            self._client = None

    async def get(self, key: str) -> Optional[str]:
        """قراءة قيمة من Redis"""
        if not self._client:
            await self.connect()
        return await self._client.get(key)

    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        """كتابة قيمة في Redis"""
        if not self._client:
            await self.connect()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self._client.set(key, str(value), ex=expire)

    async def delete(self, key: str) -> None:
        """حذف مفتاح من Redis"""
        if not self._client:
            await self.connect()
        await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        """التحقق من وجود مفتاح"""
        if not self._client:
            await self.connect()
        return bool(await self._client.exists(key))

    async def publish(self, channel: str, message: Any) -> None:
        """نشر رسالة في قناة"""
        if not self._client:
            await self.connect()
        if isinstance(message, (dict, list)):
            message = json.dumps(message)
        await self._client.publish(channel, str(message))


# Singleton instance
redis_client = RedisClient()
