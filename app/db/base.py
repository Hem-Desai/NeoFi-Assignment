from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


if settings.DATABASE_URL.startswith("sqlite"):
    DATABASE_URL = settings.DATABASE_URL.replace(
        "sqlite:///", "sqlite+aiosqlite:///"
    )
else:
    DATABASE_URL = settings.DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://"
    )

engine = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_db():
    """
    Dependency for getting async DB session
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
