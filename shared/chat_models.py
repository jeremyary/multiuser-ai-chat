from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum

# Import the existing Base from auth_models to ensure same declarative base
from .auth_models import Base

class ChatRoomTable(Base):
    __tablename__ = "chat_rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String(50), unique=True, index=True, nullable=False)
    room_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    ai_enabled = Column(Boolean, default=True, nullable=False)
    ai_personality = Column(String(50), default="helpful", nullable=False)
    ai_system_prompt = Column(Text, nullable=True)
    ai_model = Column(String(100), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    voice_readback_enabled = Column(Boolean, default=False, nullable=False)
    voice_id = Column(String(100), default="N2lVS1w4EtoT3dr4eOWO", nullable=False)  # Default to Callum voice
    
    # Relationships
    creator = relationship("UserTable", backref="created_rooms")
    messages = relationship("ChatMessageTable", back_populates="room", cascade="all, delete-orphan")

class ChatMessageTable(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(50), unique=True, index=True, nullable=False)
    chat_room_id = Column(String(50), ForeignKey("chat_rooms.room_id"), nullable=False)
    sender_id = Column(String(50), nullable=False)  # Can be user ID or AI identifier
    sender_name = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="user", nullable=False)  # user, ai, system
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    metadata = Column(JSON, nullable=True)  # Store additional metadata as JSON
    
    # Relationships
    room = relationship("ChatRoomTable", back_populates="messages")

# Pydantic Models for API responses
class ChatRoomResponse(BaseModel):
    id: int
    room_id: str
    room_name: str
    description: Optional[str]
    created_at: datetime
    ai_enabled: bool
    ai_personality: str
    ai_system_prompt: Optional[str]
    ai_model: Optional[str]
    created_by: Optional[int]
    voice_readback_enabled: bool
    voice_id: str
    
    class Config:
        from_attributes = True

class ChatMessageResponse(BaseModel):
    id: int
    message_id: str
    chat_room_id: str
    sender_id: str
    sender_name: str
    content: str
    message_type: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True

class ChatRoomCreate(BaseModel):
    room_name: str
    description: Optional[str] = None
    ai_enabled: bool = True
    ai_personality: str = "helpful"
    ai_system_prompt: Optional[str] = None
    ai_model: Optional[str] = None
    voice_readback_enabled: bool = False
    voice_id: str = "N2lVS1w4EtoT3dr4eOWO"  # Default to Callum voice

class ChatRoomUpdate(BaseModel):
    room_name: Optional[str] = None
    description: Optional[str] = None
    ai_enabled: Optional[bool] = None
    ai_personality: Optional[str] = None
    ai_system_prompt: Optional[str] = None
    ai_model: Optional[str] = None 
    voice_readback_enabled: Optional[bool] = None
    voice_id: Optional[str] = None 