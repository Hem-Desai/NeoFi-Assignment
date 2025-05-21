from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, List, Optional
from datetime import datetime

from app.core.security import get_current_user
from app.db.base import get_db
from app.db.models.user import User
from app.db.repositories.event import EventRepository
from app.db.repositories.permission import PermissionRepository
from app.services.notification import get_notification_service, NotificationService
from app.schemas.event import (
    Event, 
    EventCreate, 
    EventUpdate, 
    EventBatch,
    EventPermission,
    EventShare,
    EventVersion,
    EventChangelog,
    EventDiff
)
from app.core.exceptions import ResourceNotFoundError, AuthorizationError, ConflictError

router = APIRouter()


@router.post("", response_model=Event, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_in: EventCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> Any:
    """
    Create a new event
    """
    event_repo = EventRepository()
    
    
    conflicts = await event_repo.check_event_conflicts(
        db,
        user_id=current_user.id,
        start_time=event_in.start_time,
        end_time=event_in.end_time
    )
    
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Event conflicts with {len(conflicts)} existing events",
        )
    
    
    event = await event_repo.create_with_owner(
        db,
        obj_in=event_in,
        user_id=current_user.id
    )
    

    background_tasks.add_task(
        notification_service.notify_event_created,
        event_id=event.id,
        event_title=event.title,
        creator_id=current_user.id,
        db=db
    )
    
    return event


@router.get("", response_model=List[Event])
async def get_events(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get all events the user has access to
    """
    event_repo = EventRepository()
    
    events = await event_repo.get_events_for_user(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        start_date=start_date,
        end_date=end_date
    )
    
    return events


@router.get("/{event_id}", response_model=Event)
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get a specific event by ID
    """
    event_repo = EventRepository()
    
    event, role = await event_repo.get_by_id_with_permissions(
        db,
        event_id=event_id,
        user_id=current_user.id
    )
    
    if not event or not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or you don't have permission to access it",
        )
    
    return event


@router.put("/{event_id}", response_model=Event)
async def update_event(
    event_id: str,
    event_in: EventUpdate,
    background_tasks: BackgroundTasks,
    change_comment: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> Any:
    """
    Update an event
    """
    event_repo = EventRepository()
    permission_repo = PermissionRepository()
    
    
    event, role = await event_repo.get_by_id_with_permissions(
        db,
        event_id=event_id,
        user_id=current_user.id
    )
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if event_in.start_time or event_in.end_time:
        start_time = event_in.start_time or event.start_time
        end_time = event_in.end_time or event.end_time
        
        conflicts = await event_repo.check_event_conflicts(
            db,
            user_id=current_user.id,
            start_time=start_time,
            end_time=end_time,
            event_id=event_id
        )
        
        if conflicts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Event conflicts with {len(conflicts)} existing events",
            )
    
 
    if not await permission_repo.check_permission(
        db,
        event_id=event_id,
        user_id=current_user.id,
        required_role="EDITOR"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    event = await event_repo.update_with_version(
        db,
        db_obj=event,
        obj_in=event_in,
        user_id=current_user.id,
        change_comment=change_comment
    )
    
    background_tasks.add_task(
        notification_service.notify_event_updated,
        event_id=event.id,
        event_title=event.title,
        updater_id=current_user.id,
        db=db
    )
    
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Delete an event
    """
    event_repo = EventRepository()
    permission_repo = PermissionRepository()
    
    event, role = await event_repo.get_by_id_with_permissions(
        db,
        event_id=event_id,
        user_id=current_user.id
    )
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if role != "OWNER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    permissions = await permission_repo.get_by_event(db, event_id=event_id)
    affected_users = [permission.user_id for permission in permissions]
    
    event_title = event.title
    
    await event_repo.delete(db, id=event_id)
    
    background_tasks.add_task(
        notification_service.notify_event_deleted,
        event_id=event_id,
        event_title=event_title,
        deleter_id=current_user.id,
        affected_users=affected_users,
        db=db
    )


@router.post("/batch", response_model=List[Event], status_code=status.HTTP_201_CREATED)
async def create_batch_events(
    events_in: EventBatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create multiple events in a single request
    """
    event_repo = EventRepository()
    created_events = []
    
    for event_in in events_in.events:
        conflicts = await event_repo.check_event_conflicts(
            db,
            user_id=current_user.id,
            start_time=event_in.start_time,
            end_time=event_in.end_time
        )
        
        if conflicts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Event conflicts with existing events: {event_in.title}",
            )
    
    for event_in in events_in.events:
        event = await event_repo.create_with_owner(
            db,
            obj_in=event_in,
            user_id=current_user.id
        )
        created_events.append(event)
    
    return created_events


@router.post("/{event_id}/share", response_model=List[EventPermission])
async def share_event(
    event_id: str,
    share_data: EventShare,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> Any:
    """
    Share an event with other users
    """
    event_repo = EventRepository()
    permission_repo = PermissionRepository()
    
    event, role = await event_repo.get_by_id_with_permissions(
        db,
        event_id=event_id,
        user_id=current_user.id
    )
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if not await permission_repo.check_permission(db, event_id=event_id, user_id=current_user.id, required_role="OWNER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    permissions = []
    for user_permission in share_data.users:
        permission = await permission_repo.create_permission(
            db,
            event_id=event_id,
            user_id=user_permission.user_id,
            role=user_permission.role
        )
        permissions.append(permission)
        
        background_tasks.add_task(
            notification_service.notify_permission_changed,
            event_id=event_id,
            event_title=event.title,
            user_id=user_permission.user_id,
            role=user_permission.role,
            changer_id=current_user.id,
            db=db
        )
    
    return permissions


@router.get("/{event_id}/permissions", response_model=List[EventPermission])
async def get_event_permissions(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get all permissions for an event
    """
    event_repo = EventRepository()
    permission_repo = PermissionRepository()
    
    event, role = await event_repo.get_by_id_with_permissions(
        db,
        event_id=event_id,
        user_id=current_user.id
    )
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if role != "OWNER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    permissions = await permission_repo.get_by_event(db, event_id=event_id)
    
    return permissions


@router.put("/{event_id}/permissions/{user_id}", response_model=EventPermission)
async def update_event_permission(
    event_id: str,
    user_id: str,
    background_tasks: BackgroundTasks,
    role: str = Query(..., description="Role: OWNER, EDITOR, VIEWER"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> Any:
    """
    Update permissions for a user
    """
    event_repo = EventRepository()
    permission_repo = PermissionRepository()
    
    event, current_role = await event_repo.get_by_id_with_permissions(
        db,
        event_id=event_id,
        user_id=current_user.id
    )
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if current_role != "OWNER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    if role not in ["OWNER", "EDITOR", "VIEWER"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role",
        )
    

    try:
        permission = await permission_repo.update_permission(
            db,
            event_id=event_id,
            user_id=user_id,
            role=role
        )
        
        background_tasks.add_task(
            notification_service.notify_permission_changed,
            event_id=event_id,
            event_title=event.title,
            user_id=user_id,
            role=role,
            changer_id=current_user.id,
            db=db
        )
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )
    
    return permission


@router.delete("/{event_id}/permissions/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event_permission(
    event_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove access for a user
    """
    event_repo = EventRepository()
    permission_repo = PermissionRepository()
    
    event, role = await event_repo.get_by_id_with_permissions(
        db,
        event_id=event_id,
        user_id=current_user.id
    )
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if role != "OWNER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    if user_id == event.created_by:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove owner's permission",
        )
    
    success = await permission_repo.delete_permission(
        db,
        event_id=event_id,
        user_id=user_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )


@router.get("/{event_id}/history/{version_id}", response_model=EventVersion)
async def get_event_version(
    event_id: str,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get a specific version of an event
    """
    event_repo = EventRepository()
    permission_repo = PermissionRepository()
    
    event, role = await event_repo.get_by_id_with_permissions(
        db,
        event_id=event_id,
        user_id=current_user.id
    )
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    version = await event_repo.get_version(
        db,
        event_id=event_id,
        version_number=version_id
    )
    
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )
    
    return version


@router.post("/{event_id}/rollback/{version_id}", response_model=Event)
async def rollback_event(
    event_id: str,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Rollback to a previous version
    """
    event_repo = EventRepository()
    permission_repo = PermissionRepository()
    
    event, role = await event_repo.get_by_id_with_permissions(
        db,
        event_id=event_id,
        user_id=current_user.id
    )
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if not await permission_repo.check_permission(
        db,
        event_id=event_id,
        user_id=current_user.id,
        required_role="EDITOR"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    try:
        event = await event_repo.rollback_to_version(
            db,
            event_id=event_id,
            version_number=version_id,
            user_id=current_user.id
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return event


@router.get("/{event_id}/changelog", response_model=List[EventChangelog])
async def get_event_changelog(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get a chronological log of all changes to an event
    """
    event_repo = EventRepository()
    permission_repo = PermissionRepository()
    
    
    event, role = await event_repo.get_by_id_with_permissions(
        db,
        event_id=event_id,
        user_id=current_user.id
    )
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    versions = await event_repo.get_versions(db, event_id=event_id)
    
    changelog = []
    prev_version = None
    
    for version in versions:
        if prev_version is None:
            prev_version = version
            continue
        
        changes = []
        
        for field in ["title", "description", "start_time", "end_time", "location", "is_recurring", "recurrence_pattern"]:
            old_value = getattr(prev_version, field)
            new_value = getattr(version, field)
            
            if old_value != new_value:
                changes.append(EventDiff(
                    field=field,
                    old_value=old_value,
                    new_value=new_value
                ))
        
        if changes:
            changelog.append(EventChangelog(
                version_number=version.version_number,
                changed_by=version.changed_by,
                changed_at=version.changed_at,
                change_comment=version.change_comment,
                changes=changes
            ))
        
        prev_version = version
    
    return changelog


@router.get("/{event_id}/diff/{version_id1}/{version_id2}", response_model=List[EventDiff])
async def get_event_diff(
    event_id: str,
    version_id1: int,
    version_id2: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get a diff between two versions
    """
    event_repo = EventRepository()
    permission_repo = PermissionRepository()
    
    event, role = await event_repo.get_by_id_with_permissions(
        db,
        event_id=event_id,
        user_id=current_user.id
    )
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    version1 = await event_repo.get_version(
        db,
        event_id=event_id,
        version_number=version_id1
    )
    
    version2 = await event_repo.get_version(
        db,
        event_id=event_id,
        version_number=version_id2
    )
    
    if not version1 or not version2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )
    
    changes = []
    for field in ["title", "description", "start_time", "end_time", "location", "is_recurring", "recurrence_pattern"]:
        old_value = getattr(version1, field)
        new_value = getattr(version2, field)
        
        if old_value != new_value:
            changes.append(EventDiff(
                field=field,
                old_value=old_value,
                new_value=new_value
            ))
    
    return changes
