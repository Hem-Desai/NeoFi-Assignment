from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base schema for user data"""
    username: str
    email: EmailStr
    is_active: Optional[bool] = True


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    """Schema for user data from the database"""
    id: str
    is_superuser: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class User(UserInDB):
    """Schema for user data returned to clients"""
    pass
