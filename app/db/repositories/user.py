from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.repositories.base import BaseRepository
from app.db.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.utils import get_password_hash


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """
    Repository for user-related database operations
    """
    
    def __init__(self):
        super().__init__(User)
    
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """
        Get a user by email
        """
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        return result.scalars().first()
    
    async def get_by_username(self, db: AsyncSession, *, username: str) -> Optional[User]:
        """
        Get a user by username
        """
        query = select(User).where(User.username == username)
        result = await db.execute(query)
        return result.scalars().first()
    
    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """
        Create a new user with hashed password
        """
        db_obj = User(
            username=obj_in.username,
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            is_active=obj_in.is_active
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self, 
        db: AsyncSession, 
        *, 
        db_obj: User, 
        obj_in: UserUpdate
    ) -> User:
        """
        Update a user, handling password hashing if needed
        """
        update_data = obj_in.dict(exclude_unset=True)
        
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data["password"])
            del update_data["password"]
        
        return await super().update(db, db_obj=db_obj, obj_in=update_data)
