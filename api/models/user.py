from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    growid: Optional[str] = Field(None, min_length=3, max_length=30)
    role: UserRole = Field(default=UserRole.USER)
    status: UserStatus = Field(default=UserStatus.ACTIVE)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

class UserResponse(UserBase):
    id: str
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "usr_123456",
                "username": "player123",
                "email": "player@example.com",
                "growid": "PLAYER123",
                "role": "user",
                "status": "active",
                "created_at": "2025-05-26T06:17:09",
                "last_login": "2025-05-28T14:40:00"
            }
        }

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    growid: Optional[str] = Field(None, min_length=3, max_length=30)
    current_password: Optional[str] = None
    new_password: Optional[str] = None
    confirm_new_password: Optional[str] = None
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and values['new_password'] and v != values['new_password']:
            raise ValueError('New passwords do not match')
        return v