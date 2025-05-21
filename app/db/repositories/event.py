from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, between
from datetime import datetime

from app.db.repositories.base import BaseRepository
from app.db.models.event import Event, EventPermission, EventVersion
from app.schemas.event import EventCreate, EventUpdate, EventVersionBase
from app.core.exceptions import ResourceNotFoundError, AuthorizationError, ConflictError


class EventRepository(BaseRepository[Event, EventCreate, EventUpdate]):
    """
    Repository for event-related database operations
    """
    
    def __init__(self):
        super().__init__(Event)
    
    async def get_by_id_with_permissions(
        self, 
        db: AsyncSession, 
        *, 
        event_id: str, 
        user_id: str
    ) -> Tuple[Optional[Event], Optional[str]]:
        """
        Get an event by ID with permission check
        Returns (event, role) or (None, None) if not found or no permission
        """
        query = select(Event, EventPermission.role).join(
            EventPermission, 
            and_(
                EventPermission.event_id == Event.id,
                EventPermission.user_id == user_id
            ),
            isouter=True
        ).where(Event.id == event_id)
        
        result = await db.execute(query)
        row = result.first()
        
        if not row:
            return None, None
        
        return row[0], row[1]
    
    async def get_events_for_user(
        self, 
        db: AsyncSession, 
        *, 
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Event]:
        """
        Get all events that the user has access to
        """
        query = select(Event).join(
            EventPermission,
            and_(
                EventPermission.event_id == Event.id,
                EventPermission.user_id == user_id
            )
        )
        
        # Apply date filtering if provided
        if start_date and end_date:
            query = query.where(
                or_(
                    # Event starts within the range
                    between(Event.start_time, start_date, end_date),
                    # Event ends within the range
                    between(Event.end_time, start_date, end_date),
                    # Event spans the entire range
                    and_(
                        Event.start_time <= start_date,
                        Event.end_time >= end_date
                    )
                )
            )
        elif start_date:
            query = query.where(Event.end_time >= start_date)
        elif end_date:
            query = query.where(Event.start_time <= end_date)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create_with_owner(
        self, 
        db: AsyncSession, 
        *, 
        obj_in: EventCreate, 
        user_id: str
    ) -> Event:
        """
        Create a new event with the user as owner
        """
        # Create the event
        event = await self.create(db, obj_in=obj_in, created_by=user_id)
        
        # Create owner permission
        permission = EventPermission(
            event_id=event.id,
            user_id=user_id,
            role="OWNER"
        )
        db.add(permission)
        
        # Create initial version
        version = EventVersion(
            event_id=event.id,
            version_number=1,
            title=event.title,
            description=event.description,
            start_time=event.start_time,
            end_time=event.end_time,
            location=event.location,
            is_recurring=event.is_recurring,
            recurrence_pattern=event.recurrence_pattern,
            changed_by=user_id,
            change_comment="Initial creation"
        )
        db.add(version)
        
        await db.commit()
        await db.refresh(event)
        return event
    
    async def update_with_version(
        self, 
        db: AsyncSession, 
        *, 
        db_obj: Event, 
        obj_in: EventUpdate, 
        user_id: str,
        change_comment: Optional[str] = None
    ) -> Event:
        """
        Update an event and create a new version
        """
        # Get current version number
        new_version_number = db_obj.current_version + 1
        
        # Create a version record of the current state before updating
        version = EventVersion(
            event_id=db_obj.id,
            version_number=new_version_number,
            title=db_obj.title if obj_in.title is None else obj_in.title,
            description=db_obj.description if obj_in.description is None else obj_in.description,
            start_time=db_obj.start_time if obj_in.start_time is None else obj_in.start_time,
            end_time=db_obj.end_time if obj_in.end_time is None else obj_in.end_time,
            location=db_obj.location if obj_in.location is None else obj_in.location,
            is_recurring=db_obj.is_recurring if obj_in.is_recurring is None else obj_in.is_recurring,
            recurrence_pattern=db_obj.recurrence_pattern if obj_in.recurrence_pattern is None else (
                obj_in.recurrence_pattern.dict() if obj_in.recurrence_pattern else None
            ),
            changed_by=user_id,
            change_comment=change_comment
        )
        db.add(version)
        
        # Update the event
        update_data = obj_in.dict(exclude_unset=True)
        
        # Handle recurrence pattern conversion
        if "recurrence_pattern" in update_data and update_data["recurrence_pattern"]:
            update_data["recurrence_pattern"] = update_data["recurrence_pattern"].dict()
        
        # Update current version number
        update_data["current_version"] = new_version_number
        
        # Update the event
        updated_event = await super().update(db, db_obj=db_obj, obj_in=update_data)
        return updated_event
    
    async def check_event_conflicts(
        self, 
        db: AsyncSession, 
        *, 
        user_id: str,
        start_time: datetime,
        end_time: datetime,
        event_id: Optional[str] = None
    ) -> List[Event]:
        """
        Check for conflicting events for a user
        """
        query = select(Event).join(
            EventPermission,
            and_(
                EventPermission.event_id == Event.id,
                EventPermission.user_id == user_id
            )
        ).where(
            or_(
                # Event starts during another event
                and_(
                    Event.start_time <= start_time,
                    Event.end_time > start_time
                ),
                # Event ends during another event
                and_(
                    Event.start_time < end_time,
                    Event.end_time >= end_time
                ),
                # Event completely contains another event
                and_(
                    Event.start_time >= start_time,
                    Event.end_time <= end_time
                )
            )
        )
        
        # Exclude the current event if updating
        if event_id:
            query = query.where(Event.id != event_id)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_version(
        self, 
        db: AsyncSession, 
        *, 
        event_id: str, 
        version_number: int
    ) -> Optional[EventVersion]:
        """
        Get a specific version of an event
        """
        query = select(EventVersion).where(
            and_(
                EventVersion.event_id == event_id,
                EventVersion.version_number == version_number
            )
        )
        result = await db.execute(query)
        return result.scalars().first()
    
    async def get_versions(
        self, 
        db: AsyncSession, 
        *, 
        event_id: str
    ) -> List[EventVersion]:
        """
        Get all versions of an event
        """
        query = select(EventVersion).where(
            EventVersion.event_id == event_id
        ).order_by(EventVersion.version_number)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def rollback_to_version(
        self, 
        db: AsyncSession, 
        *, 
        event_id: str, 
        version_number: int, 
        user_id: str
    ) -> Event:
        """
        Rollback an event to a previous version
        """
        # Get the event
        event = await self.get_by_id(db, id=event_id)
        if not event:
            raise ResourceNotFoundError("Event not found")
        
        # Get the version
        version = await self.get_version(db, event_id=event_id, version_number=version_number)
        if not version:
            raise ResourceNotFoundError("Version not found")
        
        # Create a new version (current state before rollback)
        new_version_number = event.current_version + 1
        
        # Update the event with the version data
        event.title = version.title
        event.description = version.description
        event.start_time = version.start_time
        event.end_time = version.end_time
        event.location = version.location
        event.is_recurring = version.is_recurring
        event.recurrence_pattern = version.recurrence_pattern
        event.current_version = new_version_number
        
        # Create a new version record
        rollback_version = EventVersion(
            event_id=event.id,
            version_number=new_version_number,
            title=version.title,
            description=version.description,
            start_time=version.start_time,
            end_time=version.end_time,
            location=version.location,
            is_recurring=version.is_recurring,
            recurrence_pattern=version.recurrence_pattern,
            changed_by=user_id,
            change_comment=f"Rollback to version {version_number}"
        )
        db.add(rollback_version)
        
        # Save changes
        db.add(event)
        await db.commit()
        await db.refresh(event)
        
        return event
