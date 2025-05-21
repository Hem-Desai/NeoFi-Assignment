from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    """schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """schema for token payload"""
    sub: Optional[str] = None
    exp: int
    type: str


class RefreshToken(BaseModel):
    """schema for refresh token request"""
    refresh_token: str
