# ============================================================
# Redis Client - Cache, Queue, Pub/Sub
# ============================================================

import redis.asyncio as redis
from app.core.config import settings

class RedisClient:
    def __init__(self):
        self.client = None

    async def connect(self):
        self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def disconnect(self):
        if self.client:
            await self.client.close()

    async def get(self, key: str):
        return await self.client.get(key)

    async def set(self, key: str, value: str, expire: int = 3600):
        await self.client.set(key, value, ex=expire)

    async def delete(self, key: str):
        await self.client.delete(key)

    async def publish(self, channel: str, message: str):
        await self.client.publish(channel, message)

    async def subscribe(self, channel: str):
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

redis_client = RedisClient()
