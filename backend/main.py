from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import redis.asyncio as redis
import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Set, Optional
from loguru import logger
import sys
import os
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import re

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.models import (
    ChatMessage, User, ChatRoom, WebSocketMessage, 
    MessageType, UserStatus, ConnectionInfo
)
from shared.config import Config, RedisKeys, WSEventTypes, AI_TRIGGERS
from backend.ai_service import AIService
from backend.chat_manager import ChatManager
from backend.auth_routes import auth_router, admin_router
from backend.auth_middleware import get_current_user, authenticate_websocket_user
from backend.database import init_database, close_database, get_db_session
from backend.admin_init import initialize_admin_user
from backend.elevenlabs_service import elevenlabs_service

# Configure logging
logger.remove()
logger.add(sys.stderr, level=Config.LOG_LEVEL)

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

class ConnectionManager:
    def __init__(self):
        # WebSocket connections by user_id
        self.connections: Dict[str, WebSocket] = {}
        # User info by connection
        self.user_info: Dict[str, ConnectionInfo] = {}
        # Room memberships
        self.room_members: Dict[str, Set[str]] = {}
    
    def get_active_users_info(self, room_id: str) -> List[Dict[str, str]]:
        """Get list of active users with their info for a room"""
        active_users_info = []
        
        # Add Styx (AI assistant) first if there are human users present
        if room_id in self.room_members and self.room_members[room_id]:
            styx_data = {
                "user_id": "ai_styx",
                "username": "Styx"
            }
            active_users_info.append(styx_data)
        
        # Add human users, sorted alphabetically
        if room_id in self.room_members:
            human_users = []
            for uid in self.room_members[room_id]:
                user_info = self.user_info.get(uid)
                if user_info:
                    user_data = {
                        "user_id": uid,
                        "username": user_info.username
                    }
                    human_users.append(user_data)
            
            # Sort human users alphabetically by username
            human_users.sort(key=lambda x: x["username"].lower())
            active_users_info.extend(human_users)
        
        return active_users_info
    
    async def connect(self, websocket: WebSocket, user_id: str, username: str, room_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        # Generate unique websocket ID
        ws_id = str(uuid.uuid4())
        
        # Store connection info
        self.connections[user_id] = websocket
        self.user_info[user_id] = ConnectionInfo(
            user_id=user_id,
            username=username,
            room_id=room_id,
            websocket_id=ws_id
        )
        
        # Add to room
        if room_id not in self.room_members:
            self.room_members[room_id] = set()
        self.room_members[room_id].add(user_id)
        
        logger.info(f"User {username} ({user_id}) connected to room {room_id}")
        
        # Notify others in room
        await self.broadcast_to_room(room_id, {
            "type": WSEventTypes.USER_JOINED,
            "data": {
                "user_id": user_id,
                "username": username,
                "timestamp": datetime.now().isoformat()
            }
        }, exclude_user=user_id)
        
        # Send connection confirmation with user info
        active_users = self.get_active_users_info(room_id)
        connection_msg = {
            "type": WSEventTypes.CONNECTION_ESTABLISHED,
            "data": {
                "user_id": user_id,
                "room_id": room_id,
                "active_users": active_users
            }
        }
        await self.send_to_user(user_id, connection_msg)
        
        # Send recent message history to the new user
        try:
            recent_messages = await chat_manager.get_recent_messages(room_id, limit=50)
            for message in recent_messages:
                history_msg = {
                    "type": "message_history",  # Different event type for historical messages
                    "data": message.to_websocket_dict()
                }
                await self.send_to_user(user_id, history_msg)
        except Exception as e:
            logger.error(f"Error sending message history to user {user_id}: {e}")
        
        # Send updated user list to all users in room (including the new user)
        user_list_msg = {
            "type": WSEventTypes.USER_LIST_UPDATED,
            "data": {
                "active_users": active_users
            }
        }
        await self.broadcast_to_room(room_id, user_list_msg)
    
    async def disconnect(self, user_id: str):
        """Handle WebSocket disconnection"""
        if user_id in self.user_info:
            user_info = self.user_info[user_id]
            room_id = user_info.room_id
            username = user_info.username
            
            # Remove from connections
            self.connections.pop(user_id, None)
            self.user_info.pop(user_id, None)
            
            # Remove from room
            if room_id in self.room_members:
                self.room_members[room_id].discard(user_id)
                if not self.room_members[room_id]:
                    del self.room_members[room_id]
            
            logger.info(f"User {username} ({user_id}) disconnected from room {room_id}")
            
            # Notify others in room
            await self.broadcast_to_room(room_id, {
                "type": WSEventTypes.USER_LEFT,
                "data": {
                    "user_id": user_id,
                    "username": username,
                    "timestamp": datetime.now().isoformat()
                }
            })
            
            # Send updated user list to remaining users
            await self.broadcast_to_room(room_id, {
                "type": WSEventTypes.USER_LIST_UPDATED,
                "data": {
                    "active_users": self.get_active_users_info(room_id)
                }
            })
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to specific user"""
        if user_id in self.connections:
            try:
                await self.connections[user_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                await self.disconnect(user_id)
    
    async def broadcast_to_room(self, room_id: str, message: dict, exclude_user: str = None):
        """Broadcast message to all users in a room"""
        if room_id in self.room_members:
            for user_id in self.room_members[room_id].copy():
                if exclude_user and user_id == exclude_user:
                    continue
                await self.send_to_user(user_id, message)


# Initialize FastAPI app
app = FastAPI(title="Multi-User AI Chat Backend", version="1.0.0")

# Add rate limiting state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware - FIXED: Restrict origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",  # Localhost IP aliases (direct access for development)
        "http://daddo.hopto.org:3000",   # HTTP access via nginx
        "https://daddo.hopto.org:3443"  # HTTPS access via nginx (production)
        "http://daddo.hopto.org",        # HTTP access via nginx
        "https://daddo.hopto.org"   # HTTPS access via nginx (production)
    ],  # Restrict to specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Specific methods only
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth_router)
app.include_router(admin_router)

# Initialize services
connection_manager = ConnectionManager()
chat_manager = None
ai_service = None
redis_client = None


@app.on_event("startup")
async def startup_event():
    """Initialize Redis and services on startup"""
    global chat_manager, ai_service, redis_client
    
    logger.info("Starting Multi-User AI Chat Backend...")
    
    # Initialize database
    logger.info("Initializing database...")
    init_database()
    
    # Initialize admin user
    logger.info("Checking admin user...")
    initialize_admin_user()
    
    # Initialize Redis
    redis_client = redis.from_url(Config.get_redis_url())
    await redis_client.ping()
    logger.info("Redis connection established")
    
    # Initialize services
    chat_manager = ChatManager(redis_client)
    ai_service = AIService()
    
    # Create default chat room
    await chat_manager.create_room(
        Config.DEFAULT_ROOM_ID,
        Config.DEFAULT_ROOM_NAME,
        "Default chat room for all users",
        voice_readback_enabled=True,
        voice_id="N2lVS1w4EtoT3dr4eOWO"  # Default to Callum voice
    )
    
    logger.info("Backend services initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global redis_client
    if redis_client:
        await redis_client.close()
    
    # Close database connections
    close_database()
    
    logger.info("Backend services shut down")


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    room_id: str, 
    token: str = Query(...),
    db: Session = Depends(get_db_session)
):
    """Main WebSocket endpoint for chat communication (requires authentication)"""
    # Authenticate user
    user = authenticate_websocket_user(token, db)
    if not user:
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    # Check room access permissions
    try:
        room = await chat_manager.get_room(room_id)
        if not room:
            await websocket.close(code=4004, reason="Room not found")
            return
        
        user_id = str(user.id)
        user_role = user.role
        is_kid = getattr(user, 'is_kid_account', False)
        
        can_access = await chat_manager.can_user_access_room(room, user_id, user_role, is_kid)
        if not can_access:
            await websocket.close(code=4003, reason="Access denied to this room")
            return
            
    except Exception as e:
        logger.error(f"Error checking room access for user {user.id} in room {room_id}: {e}")
        await websocket.close(code=4005, reason="Permission check failed")
        return
    
    user_id = str(user.id)
    username = user.username
    
    await connection_manager.connect(websocket, user_id, username, room_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process message based on type
            await handle_websocket_message(
                user_id, room_id, WebSocketMessage(**message_data)
            )
            
    except WebSocketDisconnect:
        await connection_manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        await connection_manager.disconnect(user_id)


def should_trigger_ai_response(content: str) -> bool:
    """
    Check if message content should trigger an AI response.
    Handles punctuation and word boundaries properly.
    """
    content_lower = content.lower()
    
    for trigger in AI_TRIGGERS:
        trigger_lower = trigger.lower()
        
        # For @ mentions, look for start of string or whitespace before @
        if trigger_lower.startswith('@'):
            # Match @word at start or after whitespace, followed by word boundary or punctuation
            pattern = r'(^|\s)' + re.escape(trigger_lower) + r'(?=\s|[,.!?;:]|$)'
            if re.search(pattern, content_lower):
                return True
        else:
            # For phrase triggers like "hey ai", "hey bot", etc.
            # Allow punctuation after the phrase
            pattern = r'\b' + re.escape(trigger_lower) + r'(?=\s|[,.!?;:]|$)'
            if re.search(pattern, content_lower):
                return True
    
    return False


async def handle_websocket_message(user_id: str, room_id: str, ws_message: WebSocketMessage):
    """Handle incoming WebSocket messages"""
    try:
        if ws_message.type == WSEventTypes.SEND_MESSAGE:
            await handle_chat_message(user_id, room_id, ws_message.data)
        elif ws_message.type == WSEventTypes.USER_TYPING:
            await handle_user_typing(user_id, room_id, ws_message.data)
        else:
            logger.warning(f"Unknown message type: {ws_message.type}")
            
    except Exception as e:
        logger.error(f"Error handling message from user {user_id}: {e}")
        await connection_manager.send_to_user(user_id, {
            "type": WSEventTypes.ERROR,
            "data": {"error": "Failed to process message"}
        })


async def handle_chat_message(user_id: str, room_id: str, message_data: dict):
    """Handle chat message from user"""
    content = message_data.get("content", "").strip()
    if not content:
        return
    
    # Get user info
    user_info = connection_manager.user_info.get(user_id)
    if not user_info:
        return
    
    # Check for help command first
    if content.lower() == "!help":
        await handle_help_command(user_id, room_id, user_info.username)
        return
    
    # Create chat message
    chat_message = ChatMessage(
        message_id=str(uuid.uuid4()),
        chat_room_id=room_id,
        sender_id=user_id,
        sender_name=user_info.username,
        content=content,
        message_type=MessageType.USER
    )
    
    # Store message in Redis
    await chat_manager.store_message(chat_message)
    
    # Broadcast to all users in room
    await connection_manager.broadcast_to_room(room_id, {
        "type": WSEventTypes.MESSAGE_RECEIVED,
        "data": chat_message.to_websocket_dict()
    })
    
    # Check if AI should respond
    should_trigger_ai = should_trigger_ai_response(content)
    
    if should_trigger_ai:
        await handle_ai_response(room_id, content, user_info.username)


async def handle_ai_response(room_id: str, user_message: str, username: str):
    """Generate and send AI response"""
    try:
        # Notify users that AI is typing
        await connection_manager.broadcast_to_room(room_id, {
            "type": WSEventTypes.AI_TYPING,
            "data": {"typing": True}
        })
        
        # Get room information for custom prompt and model
        room = await chat_manager.get_room(room_id)
        room_prompt = room.ai_system_prompt if room else None
        room_model = room.ai_model if room else None
        
        # Get recent chat history for context (exclude the current message to avoid duplicates)
        chat_history = await chat_manager.get_recent_messages(room_id, limit=10)
        
        # Remove the current user message from history if it's the most recent one
        # (since we'll add it separately in the AI service)
        if chat_history and chat_history[-1].content == user_message and chat_history[-1].sender_name == username:
            chat_history = chat_history[:-1]
        
        # Generate AI response with room-specific prompt and model
        ai_response = await ai_service.generate_response(
            user_message, username, chat_history, room_prompt, room_model
        )
        
        if ai_response:
            # Create AI message
            ai_message = ChatMessage(
                message_id=str(uuid.uuid4()),
                chat_room_id=room_id,
                sender_id="ai_styx",
                sender_name="Styx",
                content=ai_response,
                message_type=MessageType.AI
            )
            
            # Store AI message
            await chat_manager.store_message(ai_message)
            
            # Broadcast AI response
            await connection_manager.broadcast_to_room(room_id, {
                "type": WSEventTypes.MESSAGE_RECEIVED,
                "data": ai_message.to_websocket_dict()
            })
        
        # Stop typing indicator
        await connection_manager.broadcast_to_room(room_id, {
            "type": WSEventTypes.AI_TYPING,
            "data": {"typing": False}
        })
        
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        await connection_manager.broadcast_to_room(room_id, {
            "type": WSEventTypes.AI_TYPING,
            "data": {"typing": False}
        })


async def handle_help_command(user_id: str, room_id: str, username: str):
    """Handle !help command - send help information to the user"""
    help_content = """🤖 Multi-User AI Chat Help

═══ BASIC COMMANDS ═══
• Type naturally to chat with other users
• Use !help to see this help message

═══ AI ASSISTANT (STYX) ═══
• Trigger Styx by mentioning:
  → @ai, @bot, @styx
  → hey ai, hey bot, hey styx
• Styx will respond to questions and participate in conversations
• Example: "Hey Styx, what's the weather like?"

═══ USER INTERACTION ═══
• @username - Mention specific users
• See online users in the sidebar
• Real-time typing indicators
• Message history is preserved

═══ TIPS ═══
• Be respectful and have fun!
• Styx is here to help with questions or just chat
• All messages are visible to everyone in the room

Need more help? Just ask Styx: "Hey Styx, how do I...?"
    """.strip()
    
    # Create help message
    help_message = ChatMessage(
        message_id=str(uuid.uuid4()),
        chat_room_id=room_id,
        sender_id="system",
        sender_name="System",
        content=help_content,
        message_type=MessageType.SYSTEM
    )
    
    # Send help message only to the requesting user
    await connection_manager.send_to_user(user_id, {
        "type": WSEventTypes.MESSAGE_RECEIVED,
        "data": help_message.to_websocket_dict()
    })


async def handle_user_typing(user_id: str, room_id: str, typing_data: dict):
    """Handle user typing indicator"""
    user_info = connection_manager.user_info.get(user_id)
    if not user_info:
        return
    
    # Broadcast typing status to other users
    await connection_manager.broadcast_to_room(room_id, {
        "type": WSEventTypes.USER_TYPING,
        "data": {
            "user_id": user_id,
            "username": user_info.username,
            "typing": typing_data.get("typing", False)
        }
    }, exclude_user=user_id)


@app.get("/health")
@limiter.limit("30/minute")  # Allow 30 health checks per minute
async def health_check(request: Request):
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/models")
async def get_available_models():
    """Get available AI models from the OpenAI endpoint"""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{Config.AI_MODEL_URL}/v1/models", timeout=10.0)
            if response.status_code == 200:
                models_data = response.json()
                # Filter out embedding models and format for UI
                chat_models = []
                for model in models_data.get("data", []):
                    model_id = model.get("id", "")
                    # Skip embedding models
                    if "embed" not in model_id.lower():
                        # Create a user-friendly display name
                        display_name = model_id
                        if "llama" in model_id.lower():
                            if "3.2" in model_id:
                                display_name = "Llama 3.2 (8x3B MoE)"
                            elif "3.1" in model_id:
                                display_name = "Llama 3.1 (8B)"
                        elif "deepseek" in model_id.lower():
                            display_name = "DeepSeek R1 (7B)"
                        
                        chat_models.append({
                            "id": model_id,
                            "name": display_name
                        })
                
                return {"models": chat_models}
            else:
                logger.error(f"Failed to fetch models: HTTP {response.status_code}")
                return {"models": []}
    except Exception as e:
        logger.error(f"Error fetching available models: {e}")
        # Return a fallback default model
        return {"models": [{"id": "meta-llama-3.1-8b-instruct", "name": "Llama 3.1 (8B)"}]}


@app.get("/rooms")
@limiter.limit("60/minute")  # Allow 60 room queries per minute
async def get_user_rooms(request: Request, current_user = Depends(get_current_user)):
    """Get all accessible rooms for the user based on their role and permissions"""
    try:
        user_id = str(current_user.id)
        user_role = current_user.role
        is_kid = getattr(current_user, 'is_kid_account', False)
        
        # Get rooms accessible to this user
        accessible_rooms = await chat_manager.get_accessible_rooms(user_id, user_role, is_kid)
        
        rooms = []
        for room in accessible_rooms:
            # Get recent message count and last activity
            recent_messages = await chat_manager.get_recent_messages(room.room_id, limit=1)
            last_activity = recent_messages[0].timestamp if recent_messages else room.created_at
            
            rooms.append({
                "room_id": room.room_id,
                "room_name": room.room_name,
                "description": room.description,
                "created_at": room.created_at.isoformat(),
                "last_activity": last_activity.isoformat(),
                "ai_enabled": room.ai_enabled,
                "ai_system_prompt": room.ai_system_prompt,
                "ai_model": room.ai_model,
                "created_by": room.created_by,
                "voice_readback_enabled": room.voice_readback_enabled,
                "voice_id": room.voice_id,
                "is_private": room.is_private,
                "assigned_users": room.assigned_users
            })
        
        # Sort by last activity (most recent first)
        rooms.sort(key=lambda x: x["last_activity"], reverse=True)
        return {"rooms": rooms}
        
    except Exception as e:
        logger.error(f"Error getting user rooms: {e}")
        return {"rooms": []}


@app.post("/rooms")
@limiter.limit("60/minute")  # Allow 60 room creations per minute (increased for testing)
async def create_room(
    request: Request,
    room_data: dict,
    current_user = Depends(get_current_user)
):
    """Create a new chat room"""
    try:
        room_name = (room_data.get("room_name") or "").strip()
        description = (room_data.get("description") or "").strip()
        ai_system_prompt = (room_data.get("ai_system_prompt") or "").strip()
        ai_model = (room_data.get("ai_model") or "").strip()
        voice_readback_enabled = room_data.get("voice_readback_enabled", True)
        voice_id = room_data.get("voice_id", "N2lVS1w4EtoT3dr4eOWO")
        is_private = room_data.get("is_private", False)
        assigned_users = room_data.get("assigned_users", [])
        
        if not room_name:
            raise HTTPException(status_code=400, detail="Room name is required")
        
        # Prevent kid users from creating any rooms
        is_kid = getattr(current_user, 'is_kid_account', False)
        if is_kid:
            raise HTTPException(status_code=403, detail="Kid accounts cannot create rooms")
        
        # Only admins can create private rooms with user assignments
        if is_private and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Only admins can create private rooms")
        
        # Generate room ID from name (make it URL-safe)
        import re
        room_id = re.sub(r'[^a-zA-Z0-9\-_]', '-', room_name.lower())
        room_id = re.sub(r'-+', '-', room_id).strip('-')
        
        # Ensure uniqueness by adding timestamp if needed
        existing_room = await chat_manager.get_room(room_id)
        if existing_room:
            room_id = f"{room_id}-{int(datetime.now().timestamp())}"
        
        # Create the room with all fields including private room settings
        room = await chat_manager.create_room(
            room_id=room_id, 
            room_name=room_name, 
            description=description,
            ai_system_prompt=ai_system_prompt or None,
            ai_model=ai_model or None,
            created_by=str(current_user.id),
            voice_readback_enabled=voice_readback_enabled,
            voice_id=voice_id,
            is_private=is_private,
            assigned_users=assigned_users
        )
        
        return {
            "room_id": room.room_id,
            "room_name": room.room_name,
            "description": room.description,
            "created_at": room.created_at.isoformat(),
            "ai_enabled": room.ai_enabled,
            "ai_system_prompt": room.ai_system_prompt,
            "ai_model": room.ai_model,
            "created_by": room.created_by,
            "voice_readback_enabled": room.voice_readback_enabled,
            "voice_id": room.voice_id,
            "is_private": room.is_private,
            "assigned_users": room.assigned_users
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating room: {e}")
        raise HTTPException(status_code=500, detail="Failed to create room")


@app.get("/rooms/{room_id}")
async def get_room_info(
    room_id: str,
    current_user = Depends(get_current_user)
):
    """Get information about a specific room"""
    room = await chat_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return {
        "room_id": room.room_id,
        "room_name": room.room_name,
        "description": room.description,
        "created_at": room.created_at.isoformat(),
        "ai_enabled": room.ai_enabled,
        "ai_system_prompt": room.ai_system_prompt,
        "ai_model": room.ai_model,
        "created_by": room.created_by,
        "voice_readback_enabled": room.voice_readback_enabled,
        "voice_id": room.voice_id
    }


@app.put("/rooms/{room_id}")
async def update_room(
    room_id: str,
    room_data: dict,
    current_user = Depends(get_current_user)
):
    """Update room settings (name, description, AI prompt)"""
    try:
        # Get the room to check permissions
        room = await chat_manager.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Check if user is admin or room creator
        user_is_admin = getattr(current_user, 'role', '') == 'admin'
        user_is_creator = room.created_by == str(current_user.id)
        
        if not user_is_admin and not user_is_creator:
            raise HTTPException(status_code=403, detail="Only admin or room creator can update room settings")
        
        # Extract update data
        room_name = room_data.get("room_name")
        description = room_data.get("description")
        ai_system_prompt = room_data.get("ai_system_prompt")
        ai_model = room_data.get("ai_model")
        voice_readback_enabled = room_data.get("voice_readback_enabled")
        voice_id = room_data.get("voice_id")
        
        # Update the room
        updated_room = await chat_manager.update_room(
            room_id=room_id,
            room_name=(room_name or "").strip() if room_name is not None else None,
            description=(description or "").strip() if description is not None else None,
            ai_system_prompt=(ai_system_prompt or "").strip() if ai_system_prompt is not None else None,
            ai_model=(ai_model or "").strip() if ai_model is not None else None,
            voice_readback_enabled=voice_readback_enabled,
            voice_id=voice_id
        )
        
        if not updated_room:
            raise HTTPException(status_code=500, detail="Failed to update room")
        
        return {
            "room_id": updated_room.room_id,
            "room_name": updated_room.room_name,
            "description": updated_room.description,
            "created_at": updated_room.created_at.isoformat(),
            "ai_enabled": updated_room.ai_enabled,
            "ai_system_prompt": updated_room.ai_system_prompt,
            "ai_model": updated_room.ai_model,
            "created_by": updated_room.created_by,
            "voice_readback_enabled": updated_room.voice_readback_enabled,
            "voice_id": updated_room.voice_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating room {room_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update room")


@app.delete("/rooms/{room_id}")
async def delete_room(
    room_id: str,
    current_user = Depends(get_current_user)
):
    """Delete a room (admin only)"""
    try:
        # Debug logging
        logger.info(f"Delete room request - User: {current_user.username} (ID: {current_user.id})")
        logger.info(f"User attributes: is_admin={getattr(current_user, 'is_admin', None)}, role={getattr(current_user, 'role', None)}")
        
        # Check admin status (use role field - is_admin doesn't exist in the model)
        user_is_admin = getattr(current_user, 'role', '') == 'admin'
        logger.info(f"Final admin check result: {user_is_admin}")
        
        if not user_is_admin:
            raise HTTPException(status_code=403, detail="Only admin can delete rooms")
        
        # Prevent deletion of default room
        if room_id == Config.DEFAULT_ROOM_ID:
            raise HTTPException(status_code=400, detail="Cannot delete the default room")
        
        # Check if room exists
        room = await chat_manager.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Disconnect all users from the room first
        if room_id in connection_manager.room_members:
            users_to_disconnect = list(connection_manager.room_members[room_id])
            for user_id in users_to_disconnect:
                await connection_manager.disconnect(user_id)
        
        # Delete the room
        success = await chat_manager.delete_room(room_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete room")
        
        return {"message": f"Room '{room.room_name}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting room {room_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete room")


@app.get("/rooms/{room_id}/messages")
async def get_room_messages(
    room_id: str, 
    limit: int = 50,
    current_user = Depends(get_current_user)
):
    """Get recent messages for a room (requires authentication)"""
    messages = await chat_manager.get_recent_messages(room_id, limit)
    return {"messages": [msg.to_websocket_dict() for msg in messages]}


@app.delete("/rooms/{room_id}/messages")
async def clear_room_messages(
    room_id: str,
    current_user = Depends(get_current_user)
):
    """Clear all messages from a room (admin only)"""
    try:
        # Check admin status (use role field - is_admin doesn't exist in the model)
        user_is_admin = getattr(current_user, 'role', '') == 'admin'
        
        if not user_is_admin:
            raise HTTPException(status_code=403, detail="Only admin can clear room messages")
        
        # Check if room exists
        room = await chat_manager.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Clear all messages from the room
        success = await chat_manager.clear_room_messages(room_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to clear room messages")
        
        return {"message": f"Messages cleared from room '{room.room_name}' successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing messages from room {room_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear room messages")


@app.post("/tts")
@limiter.limit("20/minute")  # Allow 20 TTS requests per minute
async def text_to_speech(
    request: Request,
    tts_data: dict,
    current_user = Depends(get_current_user)
):
    """Convert text to speech using ElevenLabs API"""
    try:
        text = tts_data.get("text", "").strip()
        voice_id = tts_data.get("voice_id")  # Optional custom voice
        
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        if len(text) > 5000:  # Limit text length
            raise HTTPException(status_code=400, detail="Text too long (max 5000 characters)")
        
        # Check if ElevenLabs is enabled
        if not elevenlabs_service.is_enabled():
            raise HTTPException(status_code=503, detail="Text-to-speech service is not available")
        
        # Generate speech
        audio_data = await elevenlabs_service.text_to_speech(text, voice_id)
        
        if not audio_data:
            raise HTTPException(status_code=500, detail="Failed to generate speech")
        
        # Return audio data
        from fastapi.responses import Response
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=speech.mp3",
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in TTS endpoint: {e}")
        raise HTTPException(status_code=500, detail="Text-to-speech conversion failed")


@app.post("/tts/{room_id}")
@limiter.limit("20/minute")  # Allow 20 TTS requests per minute
async def room_text_to_speech(
    request: Request,
    room_id: str,
    tts_data: dict,
    current_user = Depends(get_current_user)
):
    """Convert text to speech using room-specific voice"""
    try:
        text = tts_data.get("text", "").strip()
        
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        if len(text) > 5000:  # Limit text length
            raise HTTPException(status_code=400, detail="Text too long (max 5000 characters)")
        
        # Check if ElevenLabs is enabled
        if not elevenlabs_service.is_enabled():
            raise HTTPException(status_code=503, detail="Text-to-speech service is not available")
        
        # Get room to find the voice_id
        room = await chat_manager.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Use room's voice_id
        voice_id = room.voice_id
        
        # Generate speech with room's voice
        audio_data = await elevenlabs_service.text_to_speech(text, voice_id)
        
        if not audio_data:
            raise HTTPException(status_code=500, detail="Failed to generate speech")
        
        # Return audio data
        from fastapi.responses import Response
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=speech.mp3",
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in room TTS endpoint: {e}")
        raise HTTPException(status_code=500, detail="Text-to-speech conversion failed")


@app.get("/tts/voices")
async def get_available_voices(current_user = Depends(get_current_user)):
    """Get list of available ElevenLabs voices"""
    try:
        if not elevenlabs_service.is_enabled():
            return {"voices": [], "enabled": False}
        
        voices = elevenlabs_service.get_available_voices()
        return {"voices": voices, "enabled": True}
        
    except Exception as e:
        logger.error(f"Error getting voices: {e}")
        return {"voices": [], "enabled": False, "error": str(e)}


@app.get("/users")
async def get_all_users(current_user = Depends(get_current_user), db: Session = Depends(get_db_session)):
    """Get all users for admin purposes (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        from shared.auth_models import UserTable
        users = db.query(UserTable).filter(UserTable.is_active == True).all()
        
        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role,
                "is_kid_account": user.is_kid_account,
                "avatar_color": user.avatar_color
            })
        
        return {"users": user_list}
        
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail="Failed to get users")


@app.post("/rooms/{room_id}/assign-users")
async def assign_users_to_room(
    room_id: str,
    assignment_data: dict,
    current_user = Depends(get_current_user)
):
    """Assign users to a private room (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        user_ids = assignment_data.get("user_ids", [])
        
        # Get the room to verify it exists
        room = await chat_manager.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Update room with new assigned users
        updated_room = await chat_manager.update_room(
            room_id=room_id,
            assigned_users=user_ids
        )
        
        if not updated_room:
            raise HTTPException(status_code=500, detail="Failed to update room assignments")
        
        return {
            "message": f"Users assigned to room '{room.room_name}'",
            "assigned_users": updated_room.assigned_users
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning users to room {room_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign users to room")


@app.get("/rooms/{room_id}/access-check")
async def check_room_access(room_id: str, current_user = Depends(get_current_user)):
    """Check if current user can access a specific room"""
    try:
        room = await chat_manager.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        user_id = str(current_user.id)
        user_role = current_user.role
        is_kid = getattr(current_user, 'is_kid_account', False)
        
        can_access = await chat_manager.can_user_access_room(room, user_id, user_role, is_kid)
        
        return {
            "can_access": can_access,
            "room_id": room_id,
            "is_private": room.is_private,
            "user_role": user_role,
            "is_kid": is_kid
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking room access for {room_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to check room access")


if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level=Config.LOG_LEVEL)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=Config.BACKEND_PORT,
        reload=Config.DEBUG,
        log_level=Config.LOG_LEVEL.lower()
    ) 