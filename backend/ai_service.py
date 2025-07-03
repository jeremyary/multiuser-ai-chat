import httpx
import asyncio
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
import sys
import os

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.models import ChatMessage, AIConfig, MessageType
from shared.config import Config


class AIService:
    def __init__(self):
        self.config = AIConfig(
            model_url=Config.AI_MODEL_URL,
            api_key=Config.AI_API_KEY
        )
        self.client = httpx.AsyncClient(timeout=Config.AI_RESPONSE_TIMEOUT)
        logger.info(f"AI Service initialized with model URL: {self.config.model_url}")
    
    async def generate_response(
        self, 
        user_message: str, 
        username: str, 
        chat_history: List[ChatMessage] = None,
        room_prompt: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Optional[str]:
        """Generate AI response to user message with chat context"""
        try:
            # Build conversation context
            messages = await self._build_conversation_context(user_message, username, chat_history, room_prompt)
            
            # Use room-specific model if provided, otherwise fall back to default
            selected_model = model_name or self.config.model_name
            
            # Log which model is being used
            if model_name:
                logger.info(f"Using room-specific model: {selected_model}")
            else:
                logger.info(f"Using default model: {selected_model}")
            
            # Prepare request payload
            payload = {
                "model": selected_model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "stream": False
            }
            
            # Add API key if provided
            headers = {"Content-Type": "application/json"}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            # Make request to AI model
            response = await self.client.post(
                f"{self.config.model_url}/v1/chat/completions",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"].strip()
                
                logger.info(f"Generated AI response for user {username}: {ai_response[:100]}...")
                return ai_response
            else:
                logger.error(f"AI API error: {response.status_code} - {response.text}")
                return "Sorry, I'm having trouble processing your request right now."
                
        except httpx.TimeoutException:
            logger.error("AI request timeout")
            return "Sorry, I'm taking too long to respond. Please try again."
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return "Sorry, I encountered an error while processing your message."
    
    async def _build_conversation_context(
        self, 
        current_message: str, 
        username: str, 
        chat_history: List[ChatMessage] = None,
        room_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Build conversation context for AI model"""
        messages = []
        
        # Add system prompt
        messages.append({
            "role": "system",
            "content": self._get_system_prompt(room_prompt)
        })
        
        # Add recent chat history for context
        if chat_history:
            for msg in chat_history[-8:]:  # Last 8 messages for context
                if msg.message_type == MessageType.USER:
                    messages.append({
                        "role": "user",
                        "content": f"{msg.sender_name}: {msg.content}"
                    })
                elif msg.message_type == MessageType.AI:
                    messages.append({
                        "role": "assistant",
                        "content": msg.content
                    })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": f"{username}: {current_message}"
        })
        
        return messages
    
    def _get_system_prompt(self, room_prompt: Optional[str] = None) -> str:
        """Get system prompt for AI model, using room-specific prompt if available"""
        
        if room_prompt:
            # Use custom room prompt but ensure Styx identity and basic guidelines
            return f"""You are Styx, an AI assistant participating in this chat room.

Room-specific instructions:
{room_prompt}

Basic guidelines:
- Your name is Styx - use this if you need to refer to yourself
- Keep responses concise but informative unless the room prompt specifies otherwise
- You can see the chat history and respond to the current conversation context
- Address users by name when appropriate
- Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Follow the room-specific instructions above while maintaining natural conversation."""
        else:
            # Default system prompt
            return f"""You are Styx, a helpful AI assistant participating in a group chat. 

Guidelines:
- Be friendly, engaging, and conversational
- Keep responses concise but informative (2-3 sentences max unless asked for details)
- You can see the chat history and respond to the current conversation context
- Address users by name when appropriate
- Your name is Styx - use this if you need to refer to yourself
- Don't overly mention that you're an AI unless specifically asked
- Be helpful but not overly formal
- You can engage in casual conversation as well as answer questions
- If someone asks about technical topics, provide accurate and helpful information

Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Respond naturally as if you're another participant in the chat."""
    
    async def generate_system_message(self, message_type: str, context: Dict[str, Any]) -> Optional[str]:
        """Generate system messages for events like user joining/leaving"""
        try:
            if message_type == "user_joined":
                username = context.get("username")
                return f"👋 Welcome to the chat, {username}! I'm Styx, here to help with questions or just chat."
            
            elif message_type == "user_left":
                username = context.get("username")
                return f"👋 See you later, {username}!"
            
            elif message_type == "room_created":
                room_name = context.get("room_name")
                return f"🎉 Welcome to {room_name}! I'm Styx, here to help with any questions or just to chat."
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating system message: {e}")
            return None
    
    async def check_health(self) -> bool:
        """Check if AI service is healthy"""
        try:
            headers = {"Content-Type": "application/json"}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            response = await self.client.get(
                f"{self.config.model_url}/v1/models",
                headers=headers,
                timeout=5.0
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.warning(f"AI health check failed: {e}")
            return False
    
    async def get_model_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the AI model"""
        try:
            headers = {"Content-Type": "application/json"}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            response = await self.client.get(
                f"{self.config.model_url}/v1/models",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    def update_config(self, **kwargs):
        """Update AI configuration"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                # SECURITY FIX: Mask sensitive values in logs
                if 'key' in key.lower() or 'token' in key.lower() or 'secret' in key.lower():
                    masked_value = f"{'*' * (len(str(value)) - 4)}{str(value)[-4:]}" if len(str(value)) > 4 else "****"
                    logger.info(f"Updated AI config: {key} = {masked_value}")
                else:
                    logger.info(f"Updated AI config: {key} = {value}")
    
    async def stream_response(
        self,
        user_message: str,
        username: str,
        chat_history: List[ChatMessage] = None
    ) -> Optional[str]:
        """Generate streaming AI response (for future enhancement)"""
        # This could be implemented for real-time streaming responses
        # For now, just use the regular generate_response method
        return await self.generate_response(user_message, username, chat_history) 