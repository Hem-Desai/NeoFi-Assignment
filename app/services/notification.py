from typing import List, Dict, Any, Optional
import json
import logging
from datetime import datetime
from fastapi import BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import get_db
from app.db.models.event import EventPermission
from app.db.repositories.permission import PermissionRepository

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for handling real-time notifications
    
    This service can be configured to use different notification backends:
    - In-memory (default): Stores notifications in memory (for development)
    - Redis: Uses Redis pub/sub for real-time notifications (for production)
    """
    
    def __init__(self):
        self.backend = "in-memory"  
        self.notifications = {}  
        
        if settings.REDIS_URL:
            try:
                import redis
                self.redis = redis.from_url(settings.REDIS_URL)
                self.backend = "redis"
                logger.info("Using Redis for notifications")
            except (ImportError, Exception) as e:
                logger.warning(f"Failed to initialize Redis: {e}")
                logger.warning("Falling back to in-memory notifications")
    
    async def notify_event_created(
        self, 
        event_id: str, 
        event_title: str, 
        creator_id: str,
        db: AsyncSession = Depends(get_db)
    ):
        """
        Notify users about a new event
        """
        notification = {
            "type": "event_created",
            "event_id": event_id,
            "event_title": event_title,
            "timestamp": datetime.now().isoformat(),
            "message": f"You created a new event: {event_title}"
        }
        
        await self._send_notification(creator_id, notification)
    
    async def notify_event_updated(
        self, 
        event_id: str, 
        event_title: str, 
        updater_id: str,
        db: AsyncSession = Depends(get_db)
    ):
        """
        Notify users about an event update
        """
        
        permission_repo = PermissionRepository()
        permissions = await permission_repo.get_by_event(db, event_id=event_id)
        
        
        notification = {
            "type": "event_updated",
            "event_id": event_id,
            "event_title": event_title,
            "updater_id": updater_id,
            "timestamp": datetime.now().isoformat(),
            "message": f"Event updated: {event_title}"
        }
        
        for permission in permissions:
            if permission.user_id != updater_id:
                notification_for_user = notification.copy()
                notification_for_user["message"] = f"Event '{event_title}' was updated by another user"
                await self._send_notification(permission.user_id, notification_for_user)
        
        notification["message"] = f"You updated the event: {event_title}"
        await self._send_notification(updater_id, notification)
    
    async def notify_event_deleted(
        self, 
        event_id: str, 
        event_title: str, 
        deleter_id: str,
        affected_users: List[str],
        db: AsyncSession = Depends(get_db)
    ):
        """
        Notify users about an event deletion
        """
        notification = {
            "type": "event_deleted",
            "event_id": event_id,
            "event_title": event_title,
            "deleter_id": deleter_id,
            "timestamp": datetime.now().isoformat(),
            "message": f"Event deleted: {event_title}"
        }
        
        for user_id in affected_users:
            if user_id != deleter_id:
                notification_for_user = notification.copy()
                notification_for_user["message"] = f"Event '{event_title}' was deleted by another user"
                await self._send_notification(user_id, notification_for_user)
        
        notification["message"] = f"You deleted the event: {event_title}"
        await self._send_notification(deleter_id, notification)
    
    async def notify_permission_changed(
        self, 
        event_id: str, 
        event_title: str, 
        user_id: str, 
        role: str,
        changer_id: str,
        db: AsyncSession = Depends(get_db)
    ):
        """
        Notify a user about a permission change
        """
        notification = {
            "type": "permission_changed",
            "event_id": event_id,
            "event_title": event_title,
            "role": role,
            "changer_id": changer_id,
            "timestamp": datetime.now().isoformat(),
            "message": f"Your permission for event '{event_title}' was changed to {role}"
        }
        
        await self._send_notification(user_id, notification)
        
        if user_id != changer_id:
            notification_for_changer = {
                "type": "permission_changed",
                "event_id": event_id,
                "event_title": event_title,
                "user_id": user_id,
                "role": role,
                "timestamp": datetime.now().isoformat(),
                "message": f"You changed permission for event '{event_title}'"
            }
            await self._send_notification(changer_id, notification_for_changer)
    
    async def get_notifications(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all notifications for a user
        """
        if self.backend == "redis":
            try:
                notifications_json = self.redis.get(f"notifications:{user_id}")
                if notifications_json:
                    return json.loads(notifications_json)
                return []
            except Exception as e:
                logger.error(f"Error getting notifications from Redis: {e}")
                return []
        else:
            return self.notifications.get(user_id, [])
    
    async def mark_as_read(self, user_id: str, notification_id: Optional[str] = None):
        """
        Mark notifications as read
        
        If notification_id is None, mark all notifications as read
        """
        if self.backend == "redis":
            try:
                notifications_json = self.redis.get(f"notifications:{user_id}")
                if notifications_json:
                    notifications = json.loads(notifications_json)
                    if notification_id:
                        for notification in notifications:
                            if notification.get("id") == notification_id:
                                notification["read"] = True
                                break
                    else:
                        for notification in notifications:
                            notification["read"] = True
                    
                    self.redis.set(f"notifications:{user_id}", json.dumps(notifications))
            except Exception as e:
                logger.error(f"Error marking notifications as read in Redis: {e}")
        else:
            if user_id in self.notifications:
                if notification_id:
                    for notification in self.notifications[user_id]:
                        if notification.get("id") == notification_id:
                            notification["read"] = True
                            break
                else:
                    for notification in self.notifications[user_id]:
                        notification["read"] = True
    
    async def _send_notification(self, user_id: str, notification: Dict[str, Any]):
        """
        Send a notification to a user
        """
        notification["read"] = False
        notification["id"] = f"{notification['type']}_{notification['timestamp']}"
        
        if self.backend == "redis":
            try:
                notifications_json = self.redis.get(f"notifications:{user_id}")
                if notifications_json:
                    notifications = json.loads(notifications_json)
                else:
                    notifications = []
                
                notifications.append(notification)
                self.redis.set(f"notifications:{user_id}", json.dumps(notifications))
                
                self.redis.publish(f"user:{user_id}:notifications", json.dumps(notification))
            except Exception as e:
                logger.error(f"Error sending notification via Redis: {e}")
        else:
            if user_id not in self.notifications:
                self.notifications[user_id] = []
            
            self.notifications[user_id].append(notification)


notification_service = NotificationService()


def get_notification_service():
    return notification_service
