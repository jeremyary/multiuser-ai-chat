import os
import io
from typing import Optional
from loguru import logger
from elevenlabs.client import ElevenLabs
from shared.config import Config


class ElevenLabsService:
    """Service for ElevenLabs text-to-speech functionality"""
    
    def __init__(self):
        """Initialize ElevenLabs service"""
        self.api_key = Config.ELEVENLABS_API_KEY
        self.voice_id = Config.ELEVENLABS_VOICE_ID
        self.model = Config.ELEVENLABS_MODEL
        self.enabled = bool(self.api_key)
        self.client = None
        
        if self.enabled:
            try:
                self.client = ElevenLabs(api_key=self.api_key)
                logger.info(f"ElevenLabs service initialized with voice: {self.voice_id} and model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize ElevenLabs: {e}")
                self.enabled = False
        else:
            logger.warning("ElevenLabs API key not provided - TTS disabled")
    
    def is_enabled(self) -> bool:
        """Check if ElevenLabs service is enabled and configured"""
        return self.enabled
    
    async def text_to_speech(self, text: str, voice_id: Optional[str] = None) -> Optional[bytes]:
        """
        Convert text to speech using ElevenLabs API
        
        Args:
            text: Text to convert to speech
            voice_id: Optional voice ID (uses default if not provided)
            
        Returns:
            Audio data as bytes or None if failed
        """
        if not self.enabled or not self.client:
            logger.warning("ElevenLabs service not enabled")
            return None
        
        if not text or not text.strip():
            logger.warning("Empty text provided to TTS")
            return None
        
        # Use provided voice ID or default
        selected_voice_id = voice_id or self.voice_id
        
        try:
            logger.info(f"Generating speech for text: '{text[:50]}...' with voice: {selected_voice_id} and model: {self.model}")
            
            # Clean the text for better speech synthesis
            cleaned_text = self._clean_text_for_speech(text)
            
            # Generate speech using ElevenLabs new client API
            audio = self.client.text_to_speech.convert(
                text=cleaned_text,
                voice_id=selected_voice_id,
                model_id=self.model,
                output_format="mp3_44100_128"
            )
            
            # Convert generator to bytes if needed
            if hasattr(audio, '__iter__') and not isinstance(audio, (bytes, bytearray)):
                audio_bytes = b''.join(audio)
            else:
                audio_bytes = audio
            
            logger.info(f"Successfully generated {len(audio_bytes)} bytes of audio")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Failed to generate speech: {e}")
            return None
    
    def _clean_text_for_speech(self, text: str) -> str:
        """
        Clean text for better speech synthesis
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text suitable for TTS
        """
        # Remove HTML tags
        import re
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove @username mentions (but preserve emails)
        # This matches @username but not user@domain.com
        text = re.sub(r'(?<!\w)@([a-zA-Z0-9_.-]+)(?!\.[a-zA-Z]{2,})', '', text)
        
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
        text = re.sub(r'`(.*?)`', r'\1', text)        # Code
        text = re.sub(r'#{1,6}\s*(.*?)(?:\n|$)', r'\1. ', text)  # Headers
        
        # Replace multiple newlines with periods for natural pauses
        text = re.sub(r'\n\s*\n', '. ', text)
        text = re.sub(r'\n', ' ', text)
        
        # Clean up multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Ensure text ends with proper punctuation
        text = text.strip()
        if text and text[-1] not in '.!?':
            text += '.'
        
        return text
    
    def get_available_voices(self) -> list:
        """
        Get list of available voices from ElevenLabs
        
        Returns:
            List of voice information or empty list if failed
        """
        if not self.enabled or not self.client:
            return []
        
        try:
            voice_response = self.client.voices.search()
            return [{"id": voice.voice_id, "name": voice.name} for voice in voice_response.voices]
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            return []


# Global instance
elevenlabs_service = ElevenLabsService() 