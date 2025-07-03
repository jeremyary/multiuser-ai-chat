import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class Config:
    # Redis Configuration
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    # Backend Configuration
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "localhost")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    
    # AI Model Configuration
    AI_MODEL_URL: str = os.getenv("AI_MODEL_URL", "http://localhost:1234")
    AI_API_KEY: Optional[str] = os.getenv("AI_API_KEY")
    
    # ElevenLabs Text-to-Speech Configuration
    ELEVENLABS_API_KEY: Optional[str] = os.getenv("ELEVENLABS_API_KEY")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "N2lVS1w4EtoT3dr4eOWO")  # Callum voice
    ELEVENLABS_MODEL: str = os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5")
    
    # Application Configuration
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Chat Configuration
    MAX_MESSAGE_LENGTH: int = int(os.getenv("MAX_MESSAGE_LENGTH", "2000"))
    MAX_CHAT_HISTORY: int = int(os.getenv("MAX_CHAT_HISTORY", "100"))
    AI_RESPONSE_TIMEOUT: int = int(os.getenv("AI_RESPONSE_TIMEOUT", "30"))
    
    # Security Configuration
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://daddo.hopto.org:3000,https://daddo.hopto.org:3443").split(",")
    SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "480"))
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOGIN_ATTEMPT_WINDOW_MINUTES: int = int(os.getenv("LOGIN_ATTEMPT_WINDOW_MINUTES", "15"))
    REQUIRE_STRONG_PASSWORDS: bool = os.getenv("REQUIRE_STRONG_PASSWORDS", "true").lower() == "true"
    MIN_PASSWORD_LENGTH: int = int(os.getenv("MIN_PASSWORD_LENGTH", "8"))
    ENABLE_AUDIT_LOGGING: bool = os.getenv("ENABLE_AUDIT_LOGGING", "true").lower() == "true"
    
    # Rate Limiting Configuration
    API_RATE_LIMIT: str = os.getenv("API_RATE_LIMIT", "100/minute")
    WS_RATE_LIMIT: str = os.getenv("WS_RATE_LIMIT", "30/minute")
    AUTH_RATE_LIMIT: str = os.getenv("AUTH_RATE_LIMIT", "5/minute")
    
    # Default Chat Room
    DEFAULT_ROOM_ID: str = "general"
    DEFAULT_ROOM_NAME: str = "General Chat"
    
    @classmethod
    def get_redis_url(cls) -> str:
        """Get Redis connection URL"""
        # Use REDIS_URL if provided (for Docker containers)
        if cls.REDIS_URL:
            return cls.REDIS_URL
        
        # Otherwise build from individual components
        if cls.REDIS_PASSWORD:
            return f"redis://:{cls.REDIS_PASSWORD}@{cls.REDIS_HOST}:{cls.REDIS_PORT}/{cls.REDIS_DB}"
        return f"redis://{cls.REDIS_HOST}:{cls.REDIS_PORT}/{cls.REDIS_DB}"
    
    @classmethod
    def get_backend_url(cls) -> str:
        """Get backend WebSocket URL"""
        return f"ws://{cls.BACKEND_HOST}:{cls.BACKEND_PORT}"
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment"""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    @classmethod
    def get_security_headers(cls) -> dict:
        """Get security headers for HTTP responses"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';",
        }


# Redis Keys
class RedisKeys:
    CHAT_MESSAGES = "chat:messages:{room_id}"
    USER_CONNECTIONS = "chat:connections"
    ROOM_USERS = "chat:room_users:{room_id}"
    USER_STATUS = "chat:user_status:{user_id}"
    AI_QUEUE = "chat:ai_queue"
    MESSAGE_QUEUE = "chat:message_queue:{room_id}"


# WebSocket Event Types
class WSEventTypes:
    # Client to Server
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    SEND_MESSAGE = "send_message"
    USER_TYPING = "user_typing"
    
    # Server to Client
    MESSAGE_RECEIVED = "message_received"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    USER_LIST_UPDATED = "user_list_updated"
    AI_TYPING = "ai_typing"
    CONNECTION_ESTABLISHED = "connection_established"
    ERROR = "error"


# AI Trigger Keywords
AI_TRIGGERS = [
    "@ai",
    "@assistant", 
    "@bot",
    "@styx",
    "hey ai",
    "hey styx",
    "ai help",
    "ai:",
] 