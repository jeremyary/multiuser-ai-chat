from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json


class MessageType(str, Enum):
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class UserStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"


class User(BaseModel):
    user_id: str
    username: str
    status: UserStatus = UserStatus.ONLINE
    joined_at: datetime = Field(default_factory=datetime.now)
    avatar_color: str = "#3498db"  # Default blue color
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class ChatMessage(BaseModel):
    message_id: str
    chat_room_id: str
    sender_id: str
    sender_name: str
    content: str
    message_type: MessageType
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
    
    def to_websocket_dict(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for WebSocket transmission"""
        data = self.dict()
        data['timestamp'] = self.timestamp.isoformat()
        return data


class ChatRoom(BaseModel):
    room_id: str
    room_name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    active_users: List[str] = Field(default_factory=list)
    ai_enabled: bool = True
    ai_personality: str = "helpful"  # Can be customized
    ai_system_prompt: Optional[str] = None  # Custom AI prompt for this room
    ai_model: Optional[str] = None  # AI model to use for this room
    created_by: Optional[str] = None  # User ID who created the room
    voice_readback_enabled: bool = False  # Enable voice readback for AI responses
    voice_id: str = "N2lVS1w4EtoT3dr4eOWO"  # ElevenLabs voice ID (default: Callum)
    is_private: bool = False  # Whether this is a private room
    assigned_users: List[str] = Field(default_factory=list)  # User IDs assigned to private room
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class AIConfig(BaseModel):
    model_url: str = "http://localhost:1234"
    api_key: Optional[str] = None
    model_name: str = "meta-llama-3.1-8b-instruct"
    system_prompt: str = "You are a helpful AI assistant participating in a group chat. Be friendly and engaging."
    temperature: float = 0.7
    max_tokens: int = 512


class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    room_id: Optional[str] = None
    user_id: Optional[str] = None


class ConnectionInfo(BaseModel):
    user_id: str
    username: str
    room_id: str
    websocket_id: str 