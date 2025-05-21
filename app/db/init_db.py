import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import SessionLocal
from app.db.repositories.user import UserRepository
from app.schemas.user import UserCreate
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_db() -> None:
    """
    Initialize the database with initial data
    """
    async with SessionLocal() as db:
        try:
            await create_superuser(db)
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise


async def create_superuser(db: AsyncSession) -> None:
    """
    Create a superuser for testing
    """
    user_repo = UserRepository()
    

    user = await user_repo.get_by_email(db, email="admin@example.com")
    if user:
        logger.info("Superuser already exists")
        return
    

    user_in = UserCreate(
        username="admin",
        email="admin@example.com",
        password="adminpassword",
        is_active=True
    )
    
    user = await user_repo.create(db, obj_in=user_in)
    user.is_superuser = True
    db.add(user)
    await db.commit()
    
    logger.info("Superuser created successfully")


if __name__ == "__main__":
    asyncio.run(init_db())
