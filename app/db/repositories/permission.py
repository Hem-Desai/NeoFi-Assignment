from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from app.db.repositories.base import BaseRepository
from app.db.models.event import EventPermission
from app.schemas.event import EventPermissionCreate, EventPermissionUpdate
from app.core.exceptions import ResourceNotFoundError, AuthorizationError


class PermissionRepository(BaseRepository[EventPermission, EventPermissionCreate, EventPermissionUpdate]):
    """
    Repository for event permission-related database operations
    """
    
    def __init__(self):
        super().__init__(EventPermission)
    
    async def get_by_event_and_user(
        self, 
        db: AsyncSession, 
        *, 
        event_id: str, 
        user_id: str
    ) -> Optional[EventPermission]:
        """
        Get a permission by event ID and user ID
        """
        query = select(EventPermission).where(
            and_(
                EventPermission.event_id == event_id,
                EventPermission.user_id == user_id
            )
        )
        result = await db.execute(query)
        return result.scalars().first()
    
    async def get_by_event(
        self, 
        db: AsyncSession, 
        *, 
        event_id: str
    ) -> List[EventPermission]:
        """
        Get all permissions for an event
        """
        query = select(EventPermission).where(EventPermission.event_id == event_id)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create_permission(
        self, 
        db: AsyncSession, 
        *, 
        event_id: str, 
        user_id: str, 
        role: str
    ) -> EventPermission:
        """
        Create a new permission
        """
        # Check if permission already exists
        existing = await self.get_by_event_and_user(db, event_id=event_id, user_id=user_id)
        if existing:
            # Update the role if it exists
            existing.role = role
            db.add(existing)
            await db.commit()
            await db.refresh(existing)
            return existing
        
        # Create new permission
        permission = EventPermission(
            event_id=event_id,
            user_id=user_id,
            role=role
        )
        db.add(permission)
        await db.commit()
        await db.refresh(permission)
        return permission
    
    async def update_permission(
        self, 
        db: AsyncSession, 
        *, 
        event_id: str, 
        user_id: str, 
        role: str
    ) -> EventPermission:
        """
        Update a permission
        """
        permission = await self.get_by_event_and_user(db, event_id=event_id, user_id=user_id)
        if not permission:
            raise ResourceNotFoundError("Permission not found")
        
        permission.role = role
        db.add(permission)
        await db.commit()
        await db.refresh(permission)
        return permission
    
    async def delete_permission(
        self, 
        db: AsyncSession, 
        *, 
        event_id: str, 
        user_id: str
    ) -> bool:
        """
        Delete a permission
        """
        permission = await self.get_by_event_and_user(db, event_id=event_id, user_id=user_id)
        if not permission:
            return False
        
        await db.delete(permission)
        await db.commit()
        return True
    
    async def check_permission(
        self, 
        db: AsyncSession, 
        *, 
        event_id: str, 
        user_id: str, 
        required_role: str
    ) -> bool:
        """
        Check if a user has the required permission for an event
        """
        permission = await self.get_by_event_and_user(db, event_id=event_id, user_id=user_id)
        if not permission:
            return False
        
        # Role hierarchy: OWNER > EDITOR > VIEWER
        role_hierarchy = {
            "OWNER": 3,
            "EDITOR": 2,
            "VIEWER": 1
        }
        
        return role_hierarchy.get(permission.role, 0) >= role_hierarchy.get(required_role, 0)
