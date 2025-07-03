from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from enum import Enum

Base = declarative_base()

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class UserTable(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(String(20), default=UserRole.USER.value, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_kid_account = Column(Boolean, default=False, nullable=False)
    avatar_color = Column(String(7), default="#3498db", nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_login = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, default=func.now(), nullable=False)

class SessionTable(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_activity = Column(DateTime, default=func.now(), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    user = relationship("UserTable", backref="sessions")

# Pydantic Models for API
class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None
    avatar_color: str = "#3498db"

class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.USER
    is_kid_account: bool = False

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_color: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    is_kid_account: Optional[bool] = None

class UserInDB(UserBase):
    id: int
    role: UserRole
    is_active: bool
    is_kid_account: bool
    created_at: datetime
    last_login: Optional[datetime]
    last_activity: datetime
    
    class Config:
        from_attributes = True

class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    is_kid_account: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class AdminUserCreateRequest(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER
    is_kid_account: bool = False
    avatar_color: str = "#3498db"

 