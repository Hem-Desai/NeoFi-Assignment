from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.base import Base


class Event(Base):
    """event model for the event management system"""
    
    __tablename__ = "events"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    location = Column(String, nullable=True)
    
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(JSON, nullable=True)
    
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    current_version = Column(Integer, default=1)
    
    creator = relationship("User", foreign_keys=[created_by], backref="created_events")
    permissions = relationship("EventPermission", back_populates="event", cascade="all, delete-orphan")
    versions = relationship("EventVersion", back_populates="event", cascade="all, delete-orphan")


class EventPermission(Base):
    """model for event permissions and sharing"""
    
    __tablename__ = "event_permissions"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    event = relationship("Event", back_populates="permissions")
    user = relationship("User")


class EventVersion(Base):
    """model for event versioning and history"""
    
    __tablename__ = "event_versions"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    location = Column(String, nullable=True)
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(JSON, nullable=True)
    
    changed_by = Column(String, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    change_comment = Column(Text, nullable=True)
    
    event = relationship("Event", back_populates="versions")
    user = relationship("User", foreign_keys=[changed_by])
