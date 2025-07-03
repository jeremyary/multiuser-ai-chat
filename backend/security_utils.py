"""
Security utilities for credential handling and validation
"""
import re
import secrets
import hashlib
from typing import Tuple
from loguru import logger


def validate_password_strength(password: str, min_length: int = 8, require_strong: bool = True) -> Tuple[bool, str]:
    """
    Validate password meets security requirements
    Returns (is_valid, error_message)
    """
    if not require_strong:
        return True, ""
    
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long"
    
    # Check for required character types
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    # Check for common weak patterns
    weak_passwords = [
        'password', '123456', '12345678', 'qwerty', 'abc123',
        'admin', 'admin123', 'admin123!', 'password123', 'letmein'
    ]
    
    if password.lower() in weak_passwords:
        return False, "Password is too common and easily guessed"
    
    # Check for repeated characters
    if len(set(password)) < len(password) / 2:
        return False, "Password contains too many repeated characters"
    
    return True, ""


def mask_sensitive_value(value: str, mask_char: str = "*", show_last: int = 4) -> str:
    """
    Mask sensitive values for logging (API keys, tokens, etc.)
    Shows only the last few characters
    """
    if not value or len(value) <= show_last:
        return mask_char * 8  # Return fixed length mask for short values
    
    return mask_char * (len(value) - show_last) + value[-show_last:]


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token"""
    return secrets.token_urlsafe(length)


def constant_time_compare(a: str, b: str) -> bool:
    """
    Constant time string comparison to prevent timing attacks
    Note: For production, use hmac.compare_digest() for cryptographic comparisons
    """
    if len(a) != len(b):
        return False
    
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    
    return result == 0


def log_security_event(event_type: str, details: dict, user_id: str = None, ip_address: str = None):
    """
    Log security-related events for audit purposes
    """
    # Sanitize details to prevent credential leakage
    safe_details = {}
    for key, value in details.items():
        if any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key', 'token']):
            safe_details[key] = "[REDACTED]"
        else:
            safe_details[key] = str(value)
    
    log_entry = {
        "event_type": event_type,
        "user_id": user_id,
        "ip_address": ip_address,
        "details": safe_details
    }
    
    logger.info(f"SECURITY_EVENT: {log_entry}")


def validate_jwt_secret_strength(secret: str) -> Tuple[bool, str]:
    """
    Validate JWT secret key strength
    """
    if len(secret) < 32:
        return False, "JWT secret must be at least 32 characters long"
    
    # Check entropy - secret should not be easily guessable
    if secret in ['your-secret-key', 'dev-secret', 'test', 'secret']:
        return False, "JWT secret is too predictable"
    
    # Calculate approximate entropy
    unique_chars = len(set(secret))
    if unique_chars < 10:
        return False, "JWT secret has insufficient character diversity"
    
    return True, ""


def check_for_credential_leakage(text: str) -> bool:
    """
    Check if text contains potential credential patterns
    Returns True if potential credentials found
    """
    # Common credential patterns
    patterns = [
        r'password\s*[=:]\s*[\'"]?([^\s\'"]+)',
        r'api[_-]?key\s*[=:]\s*[\'"]?([^\s\'"]+)',
        r'secret\s*[=:]\s*[\'"]?([^\s\'"]+)',
        r'token\s*[=:]\s*[\'"]?([^\s\'"]+)',
        r'Bearer\s+([A-Za-z0-9\-_]+)',
        r'sk-[A-Za-z0-9]{20,}',  # OpenAI API key pattern
    ]
    
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False 