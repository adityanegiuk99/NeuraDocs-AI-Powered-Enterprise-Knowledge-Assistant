"""
Authentication request/response schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: str = Field(..., min_length=5, max_length=255, examples=["user@company.com"])
    username: str = Field(..., min_length=3, max_length=100, examples=["john_doe"])
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="engineer", pattern="^(admin|hr|engineer)$")


class UserLogin(BaseModel):
    email: str = Field(..., examples=["user@company.com"])
    password: str = Field(...)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenRefresh(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = Field(None, pattern="^(admin|hr|engineer)$")
    is_active: Optional[bool] = None
