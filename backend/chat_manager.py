import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import redis.asyncio as redis
from loguru import logger
import sys
import os

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.models import ChatMessage, ChatRoom, MessageType
from shared.config import Config, RedisKeys


class ChatManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def create_room(self, room_id: str, room_name: str, description: str = None, ai_system_prompt: str = None, ai_model: str = None, created_by: str = None, voice_readback_enabled: bool = False, voice_id: str = "N2lVS1w4EtoT3dr4eOWO", is_private: bool = False, assigned_users: List[str] = None) -> ChatRoom:
        """Create a new chat room"""
        if assigned_users is None:
            assigned_users = []
            
        chat_room = ChatRoom(
            room_id=room_id,
            room_name=room_name,
            description=description,
            created_at=datetime.now(),
            ai_system_prompt=ai_system_prompt,
            ai_model=ai_model,
            created_by=created_by,
            voice_readback_enabled=voice_readback_enabled,
            voice_id=voice_id,
            is_private=is_private,
            assigned_users=assigned_users
        )
        
        # Store room info in Redis
        room_key = f"chat:room:{room_id}"
        await self.redis.hset(room_key, mapping={
            "room_id": room_id,
            "room_name": room_name,
            "description": description or "",
            "created_at": chat_room.created_at.isoformat(),
            "ai_enabled": str(chat_room.ai_enabled),
            "ai_personality": chat_room.ai_personality,
            "ai_system_prompt": ai_system_prompt or "",
            "ai_model": ai_model or "",
            "created_by": created_by or "",
            "voice_readback_enabled": str(voice_readback_enabled),
            "voice_id": voice_id,
            "is_private": str(is_private),
            "assigned_users": json.dumps(assigned_users)
        })
        
        logger.info(f"Created chat room: {room_name} ({room_id}) - Private: {is_private}")
        return chat_room
    
    async def get_room(self, room_id: str) -> Optional[ChatRoom]:
        """Get chat room info"""
        room_key = f"chat:room:{room_id}"
        room_data = await self.redis.hgetall(room_key)
        
        if not room_data:
            return None
        
        return ChatRoom(
            room_id=room_data[b"room_id"].decode(),
            room_name=room_data[b"room_name"].decode(),
            description=room_data[b"description"].decode() or None,
            created_at=datetime.fromisoformat(room_data[b"created_at"].decode()),
            ai_enabled=room_data[b"ai_enabled"].decode().lower() == "true",
            ai_personality=room_data[b"ai_personality"].decode(),
            ai_system_prompt=room_data.get(b"ai_system_prompt", b"").decode() or None,
            ai_model=room_data.get(b"ai_model", b"").decode() or None,
            created_by=room_data.get(b"created_by", b"").decode() or None,
            voice_readback_enabled=room_data.get(b"voice_readback_enabled", b"false").decode().lower() == "true",
            voice_id=room_data.get(b"voice_id", b"N2lVS1w4EtoT3dr4eOWO").decode(),
            is_private=room_data.get(b"is_private", b"false").decode().lower() == "true",
            assigned_users=json.loads(room_data.get(b"assigned_users", b"[]").decode())
        )
    
    async def update_room(self, room_id: str, room_name: str = None, description: str = None, ai_system_prompt: str = None, ai_model: str = None, voice_readback_enabled: bool = None, voice_id: str = None, is_private: bool = None, assigned_users: List[str] = None) -> Optional[ChatRoom]:
        """Update room information"""
        try:
            # Get existing room
            room = await self.get_room(room_id)
            if not room:
                return None
            
            # Update fields if provided
            if room_name is not None:
                room.room_name = room_name
            if description is not None:
                room.description = description
            if ai_system_prompt is not None:
                room.ai_system_prompt = ai_system_prompt
            if ai_model is not None:
                room.ai_model = ai_model
            if voice_readback_enabled is not None:
                room.voice_readback_enabled = voice_readback_enabled
            if voice_id is not None:
                room.voice_id = voice_id
            if is_private is not None:
                room.is_private = is_private
            if assigned_users is not None:
                room.assigned_users = assigned_users
            
            # Save updated room to Redis
            room_key = f"chat:room:{room_id}"
            await self.redis.hset(room_key, mapping={
                "room_id": room.room_id,
                "room_name": room.room_name,
                "description": room.description or "",
                "created_at": room.created_at.isoformat(),
                "ai_enabled": str(room.ai_enabled),
                "ai_personality": room.ai_personality,
                "ai_system_prompt": room.ai_system_prompt or "",
                "ai_model": room.ai_model or "",
                "created_by": room.created_by or "",
                "voice_readback_enabled": str(room.voice_readback_enabled),
                "voice_id": room.voice_id,
                "is_private": str(room.is_private),
                "assigned_users": json.dumps(room.assigned_users)
            })
            
            logger.info(f"Updated chat room: {room.room_name} ({room_id})")
            return room
            
        except Exception as e:
            logger.error(f"Error updating room {room_id}: {e}")
            return None
    
    async def delete_room(self, room_id: str) -> bool:
        """Delete a chat room and all its messages"""
        try:
            # Remove room data
            room_key = f"chat:room:{room_id}"
            await self.redis.delete(room_key)
            
            # Remove all messages for this room
            messages_key = RedisKeys.CHAT_MESSAGES.format(room_id=room_id)
            await self.redis.delete(messages_key)
            
            # Remove room users
            users_key = RedisKeys.ROOM_USERS.format(room_id=room_id)
            await self.redis.delete(users_key)
            
            # Remove individual message keys (cleanup)
            message_keys = await self.redis.keys(f"chat:message:*")
            for msg_key in message_keys:
                msg_data = await self.redis.hgetall(msg_key)
                if msg_data and msg_data.get(b"chat_room_id", b"").decode() == room_id:
                    await self.redis.delete(msg_key)
            
            logger.info(f"Deleted chat room: {room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting room {room_id}: {e}")
            return False
    
    async def store_message(self, message: ChatMessage) -> bool:
        """Store a chat message in Redis"""
        try:
            # Store in message list for the room
            messages_key = RedisKeys.CHAT_MESSAGES.format(room_id=message.chat_room_id)
            message_data = {
                "message_id": message.message_id,
                "chat_room_id": message.chat_room_id,
                "sender_id": message.sender_id,
                "sender_name": message.sender_name,
                "content": message.content,
                "message_type": message.message_type.value,
                "timestamp": message.timestamp.isoformat(),
                "metadata": json.dumps(message.metadata)
            }
            
            # Add to sorted set with timestamp as score for chronological ordering
            timestamp_score = message.timestamp.timestamp()
            await self.redis.zadd(messages_key, {json.dumps(message_data): timestamp_score})
            
            # Trim old messages to maintain max history
            await self.redis.zremrangebyrank(messages_key, 0, -(Config.MAX_CHAT_HISTORY + 1))
            
            # Store individual message for quick lookup
            msg_key = f"chat:message:{message.message_id}"
            await self.redis.hset(msg_key, mapping=message_data)
            await self.redis.expire(msg_key, 86400 * 7)  # Expire after 7 days
            
            logger.debug(f"Stored message {message.message_id} in room {message.chat_room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing message: {e}")
            return False
    
    async def get_recent_messages(self, room_id: str, limit: int = 50) -> List[ChatMessage]:
        """Get recent messages for a room"""
        try:
            messages_key = RedisKeys.CHAT_MESSAGES.format(room_id=room_id)
            
            # Get recent messages from sorted set (highest scores = most recent)
            raw_messages = await self.redis.zrevrange(messages_key, 0, limit - 1)
            
            messages = []
            for raw_msg in raw_messages:
                try:
                    msg_data = json.loads(raw_msg.decode())
                    message = ChatMessage(
                        message_id=msg_data["message_id"],
                        chat_room_id=msg_data["chat_room_id"],
                        sender_id=msg_data["sender_id"],
                        sender_name=msg_data["sender_name"],
                        content=msg_data["content"],
                        message_type=MessageType(msg_data["message_type"]),
                        timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                        metadata=json.loads(msg_data["metadata"])
                    )
                    messages.append(message)
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.warning(f"Skipping malformed message: {e}")
                    continue
            
            # Return in chronological order (oldest first)
            messages.reverse()
            return messages
            
        except Exception as e:
            logger.error(f"Error retrieving messages for room {room_id}: {e}")
            return []
    
    async def get_message(self, message_id: str) -> Optional[ChatMessage]:
        """Get a specific message by ID"""
        try:
            msg_key = f"chat:message:{message_id}"
            msg_data = await self.redis.hgetall(msg_key)
            
            if not msg_data:
                return None
            
            return ChatMessage(
                message_id=msg_data[b"message_id"].decode(),
                chat_room_id=msg_data[b"chat_room_id"].decode(),
                sender_id=msg_data[b"sender_id"].decode(),
                sender_name=msg_data[b"sender_name"].decode(),
                content=msg_data[b"content"].decode(),
                message_type=MessageType(msg_data[b"message_type"].decode()),
                timestamp=datetime.fromisoformat(msg_data[b"timestamp"].decode()),
                metadata=json.loads(msg_data[b"metadata"].decode())
            )
            
        except Exception as e:
            logger.error(f"Error retrieving message {message_id}: {e}")
            return None
    
    async def delete_message(self, message_id: str, room_id: str) -> bool:
        """Delete a message"""
        try:
            # Get the message first to find its data for removal from sorted set
            message = await self.get_message(message_id)
            if not message:
                return False
            
            # Remove from sorted set
            messages_key = RedisKeys.CHAT_MESSAGES.format(room_id=room_id)
            message_data = {
                "message_id": message.message_id,
                "chat_room_id": message.chat_room_id,
                "sender_id": message.sender_id,
                "sender_name": message.sender_name,
                "content": message.content,
                "message_type": message.message_type.value,
                "timestamp": message.timestamp.isoformat(),
                "metadata": json.dumps(message.metadata)
            }
            await self.redis.zrem(messages_key, json.dumps(message_data))
            
            # Remove individual message
            msg_key = f"chat:message:{message_id}"
            await self.redis.delete(msg_key)
            
            logger.info(f"Deleted message {message_id} from room {room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting message {message_id}: {e}")
            return False
    
    async def get_active_users(self, room_id: str) -> List[str]:
        """Get list of active users in a room"""
        try:
            users_key = RedisKeys.ROOM_USERS.format(room_id=room_id)
            users = await self.redis.smembers(users_key)
            return [user.decode() for user in users]
        except Exception as e:
            logger.error(f"Error getting active users for room {room_id}: {e}")
            return []
    
    async def add_user_to_room(self, user_id: str, room_id: str) -> bool:
        """Add user to room"""
        try:
            users_key = RedisKeys.ROOM_USERS.format(room_id=room_id)
            await self.redis.sadd(users_key, user_id)
            
            # Set user status
            status_key = RedisKeys.USER_STATUS.format(user_id=user_id)
            await self.redis.hset(status_key, mapping={
                "user_id": user_id,
                "room_id": room_id,
                "status": "online",
                "last_seen": datetime.now().isoformat()
            })
            await self.redis.expire(status_key, 86400)  # Expire after 24 hours
            
            return True
        except Exception as e:
            logger.error(f"Error adding user {user_id} to room {room_id}: {e}")
            return False
    
    async def remove_user_from_room(self, user_id: str, room_id: str) -> bool:
        """Remove user from room"""
        try:
            users_key = RedisKeys.ROOM_USERS.format(room_id=room_id)
            await self.redis.srem(users_key, user_id)
            
            # Update user status
            status_key = RedisKeys.USER_STATUS.format(user_id=user_id)
            await self.redis.hset(status_key, "status", "offline")
            await self.redis.hset(status_key, "last_seen", datetime.now().isoformat())
            
            return True
        except Exception as e:
            logger.error(f"Error removing user {user_id} from room {room_id}: {e}")
            return False
    
    async def cleanup_expired_data(self):
        """Clean up expired messages and user data"""
        try:
            # This would typically be run as a background task
            cutoff_time = datetime.now() - timedelta(days=7)
            cutoff_timestamp = cutoff_time.timestamp()
            
            # Find all message keys
            message_keys = []
            async for key in self.redis.scan_iter(match="chat:messages:*"):
                message_keys.append(key.decode())
            
            # Clean old messages from each room
            for key in message_keys:
                await self.redis.zremrangebyscore(key, 0, cutoff_timestamp)
            
            logger.info("Completed cleanup of expired chat data")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def get_room_stats(self, room_id: str) -> Dict[str, Any]:
        """Get statistics for a room"""
        try:
            messages_key = RedisKeys.CHAT_MESSAGES.format(room_id=room_id)
            users_key = RedisKeys.ROOM_USERS.format(room_id=room_id)
            
            message_count = await self.redis.zcard(messages_key)
            active_users = await self.redis.scard(users_key)
            
            # Get latest message timestamp
            latest_messages = await self.redis.zrevrange(messages_key, 0, 0, withscores=True)
            last_activity = None
            if latest_messages:
                last_activity = datetime.fromtimestamp(latest_messages[0][1]).isoformat()
            
            return {
                "room_id": room_id,
                "message_count": message_count,
                "active_users": active_users,
                "last_activity": last_activity
            }
            
        except Exception as e:
            logger.error(f"Error getting stats for room {room_id}: {e}")
            return {
                "room_id": room_id,
                "message_count": 0,
                "active_users": 0,
                "last_activity": None
            }
    
    async def can_user_access_room(self, room: ChatRoom, user_id: str, user_role: str, is_kid: bool) -> bool:
        """Check if a user can access a specific room"""
        # Admins can access any room
        if user_role == "admin":
            return True
        
        # Kid accounts can access:
        # 1. The general room (safe landing area for all users)
        # 2. Any rooms they've been explicitly assigned to
        if is_kid:
            if room.room_id == "general":
                return True
            return user_id in room.assigned_users
        
        # Regular (non-kid) users can access all non-private rooms
        # plus any private rooms they're assigned to
        if not room.is_private:
            return True
        
        # For private rooms, user must be assigned
        return user_id in room.assigned_users
    
    async def get_accessible_rooms(self, user_id: str, user_role: str, is_kid: bool) -> List[ChatRoom]:
        """Get all rooms that a user can access"""
        # Get all room keys
        room_keys = await self.redis.keys("chat:room:*")
        accessible_rooms = []
        
        logger.info(f"Filtering rooms for user {user_id} - role: {user_role}, is_kid: {is_kid}")
        
        for room_key in room_keys:
            room_id = room_key.decode().split(":")[-1]
            room = await self.get_room(room_id)
            
            if room:
                can_access = await self.can_user_access_room(room, user_id, user_role, is_kid)
                logger.info(f"Room {room_id} - private: {room.is_private}, assigned_users: {room.assigned_users}, can_access: {can_access}")
                
                if can_access:
                    accessible_rooms.append(room)
        
        logger.info(f"User {user_id} can access {len(accessible_rooms)} rooms: {[r.room_id for r in accessible_rooms]}")
        
        # Sort by last activity (most recent first)
        accessible_rooms.sort(key=lambda x: x.created_at, reverse=True)
        return accessible_rooms
    
    async def assign_user_to_room(self, room_id: str, user_id: str) -> bool:
        """Assign a user to a private room"""
        try:
            room = await self.get_room(room_id)
            if not room:
                return False
            
            if user_id not in room.assigned_users:
                room.assigned_users.append(user_id)
                await self.update_room(room_id, assigned_users=room.assigned_users)
                logger.info(f"Assigned user {user_id} to room {room_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error assigning user {user_id} to room {room_id}: {e}")
            return False
    
    async def unassign_user_from_room(self, room_id: str, user_id: str) -> bool:
        """Remove a user assignment from a private room"""
        try:
            room = await self.get_room(room_id)
            if not room:
                return False
            
            if user_id in room.assigned_users:
                room.assigned_users.remove(user_id)
                await self.update_room(room_id, assigned_users=room.assigned_users)
                logger.info(f"Unassigned user {user_id} from room {room_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error unassigning user {user_id} from room {room_id}: {e}")
            return False 