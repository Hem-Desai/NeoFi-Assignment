from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import re


class RecurrencePattern(BaseModel):
    """Schema for event recurrence pattern"""
    frequency: str = Field(..., description="Frequency of recurrence: daily, weekly, monthly, yearly")
    interval: int = Field(1, description="Interval between recurrences (e.g., every 2 weeks)")
    until: Optional[datetime] = Field(None, description="Date until which the event recurs")
    count: Optional[int] = Field(None, description="Number of occurrences")
    by_day: Optional[List[str]] = Field(None, description="Days of the week (MO, TU, WE, TH, FR, SA, SU)")
    by_month_day: Optional[List[int]] = Field(None, description="Days of the month (1-31)")
    by_month: Optional[List[int]] = Field(None, description="Months of the year (1-12)")
    
    @validator('frequency')
    def validate_frequency(cls, v):
        allowed = ['daily', 'weekly', 'monthly', 'yearly']
        if v.lower() not in allowed:
            raise ValueError(f"Frequency must be one of: {', '.join(allowed)}")
        return v.lower()
    
    @validator('by_day')
    def validate_by_day(cls, v):
        if v is not None:
            allowed = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']
            for day in v:
                if day not in allowed:
                    raise ValueError(f"Days must be one of: {', '.join(allowed)}")
        return v


class EventBase(BaseModel):
    """Base schema for event data"""
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[RecurrencePattern] = None
    
    @validator('end_time')
    def end_time_after_start_time(cls, v, values):
        if 'start_time' in values and v < values['start_time']:
            raise ValueError('End time must be after start time')
        return v


class EventCreate(EventBase):
    """Schema for creating a new event"""
    pass


class EventUpdate(BaseModel):
    """Schema for updating an event"""
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurrence_pattern: Optional[RecurrencePattern] = None
    
    @validator('end_time')
    def end_time_after_start_time(cls, v, values):
        if v is not None and 'start_time' in values and values['start_time'] is not None and v < values['start_time']:
            raise ValueError('End time must be after start time')
        return v


class EventInDB(EventBase):
    """Schema for event data from the database"""
    id: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    current_version: int = 1

    class Config:
        from_attributes = True


class Event(EventInDB):
    """Schema for event data returned to clients"""
    pass


class EventBatch(BaseModel):
    """Schema for batch event creation"""
    events: List[EventCreate]


class EventPermissionBase(BaseModel):
    """Base schema for event permission data"""
    role: str = Field(..., description="Role: OWNER, EDITOR, VIEWER")
    
    @validator('role')
    def validate_role(cls, v):
        allowed = ['OWNER', 'EDITOR', 'VIEWER']
        if v not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(allowed)}")
        return v


class EventPermissionCreate(EventPermissionBase):
    """Schema for creating a new event permission"""
    user_id: str


class EventPermissionUpdate(EventPermissionBase):
    """Schema for updating an event permission"""
    pass


class EventPermissionInDB(EventPermissionBase):
    """Schema for event permission data from the database"""
    id: str
    event_id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EventPermission(EventPermissionInDB):
    """Schema for event permission data returned to clients"""
    pass


class EventVersionBase(BaseModel):
    """Base schema for event version data"""
    version_number: int
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[RecurrencePattern] = None
    change_comment: Optional[str] = None


class EventVersionInDB(EventVersionBase):
    """Schema for event version data from the database"""
    id: str
    event_id: str
    changed_by: str
    changed_at: datetime

    class Config:
        from_attributes = True


class EventVersion(EventVersionInDB):
    """Schema for event version data returned to clients"""
    pass


class EventDiff(BaseModel):
    """Schema for event diff between versions"""
    field: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None


class EventChangelog(BaseModel):
    """Schema for event changelog"""
    version_number: int
    changed_by: str
    changed_at: datetime
    change_comment: Optional[str] = None
    changes: List[EventDiff]


class EventShare(BaseModel):
    """Schema for sharing an event with users"""
    users: List[EventPermissionCreate]
