"""
数据库连接和会话管理

使用 SQLAlchemy 2.0 风格，支持同步和异步两种模式。
"""
from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# 同步引擎（用于所有请求处理）
sync_engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

# 异步引擎（仅 PostgreSQL 使用）
async_engine = None
if settings.DB_TYPE == "postgres":
    from sqlalchemy.ext.asyncio import create_async_engine as _create_async_engine
    async_engine = _create_async_engine(
        settings.ASYNC_DATABASE_URL,
        pool_pre_ping=True,
        echo=settings.DEBUG
    )

# 同步 Session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
    expire_on_commit=False
)

# 声明式基类
Base = declarative_base()


def get_db() -> Generator:
    """
    获取数据库会话（同步）
    
    用于 FastAPI 依赖注入。
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator:
    """
    获取数据库会话（异步）

    仅 PostgreSQL 模式可用。用于 FastAPI 依赖注入。
    """
    if async_engine is None:
        raise RuntimeError("异步数据库仅在 postgres 模式下可用")
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    _AsyncSessionLocal = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )
    async with _AsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise


def init_db():
    """创建所有数据表"""
    Base.metadata.create_all(bind=sync_engine)
