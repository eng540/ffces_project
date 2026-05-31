# ============================================
# FFCES - قاعدة البيانات غير المتزامنة (Async Database)
# ============================================
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings

# محرك قاعدة البيانات - Database Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    poolclass=NullPool if settings.DEBUG else None,
)

# مصنع الجلسات - Session Factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# نموذج القاعدة الأساسي - Base Model (Single Source of Truth)
class Base(DeclarativeBase):
    pass


# تابع التبعية للحصول على جلسة قاعدة البيانات
async def get_db():
    """
    Dependency: yields an async database session.
    Commits on success, rolls back on error, always closes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
