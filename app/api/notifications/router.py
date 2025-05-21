from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, List, Dict, Optional

from app.core.security import get_current_user
from app.db.base import get_db
from app.db.models.user import User
from app.services.notification import get_notification_service, NotificationService

router = APIRouter()


@router.get("", response_model=List[Dict[str, Any]])
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> Any:
    """
    Get all notifications for the current user
    """
    notifications = await notification_service.get_notifications(current_user.id)
    return notifications


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_as_read(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Mark all notifications as read
    """
    background_tasks.add_task(
        notification_service.mark_as_read,
        user_id=current_user.id
    )


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_as_read(
    notification_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Mark a notification as read
    """
    background_tasks.add_task(
        notification_service.mark_as_read,
        user_id=current_user.id,
        notification_id=notification_id
    )
