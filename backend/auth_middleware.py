import os
import sys
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.auth_models import UserTable, UserRole
from backend.auth_service import auth_service
from backend.database import get_db_session

# Security scheme for Bearer tokens
security = HTTPBearer(auto_error=False)

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db_session)
) -> UserTable:
    """Get current authenticated user"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token
    token_data = auth_service.verify_token(credentials.credentials)
    
    # Get user from database
    user = auth_service.get_user_by_id(db, token_data.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

async def get_current_admin_user(
    current_user: UserTable = Depends(get_current_user)
) -> UserTable:
    """Get current authenticated admin user"""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user

async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db_session)
) -> Optional[UserTable]:
    """Get current user if authenticated, otherwise None"""
    if not credentials:
        return None
    
    try:
        token_data = auth_service.verify_token(credentials.credentials)
        user = auth_service.get_user_by_id(db, token_data.user_id)
        
        if user and user.is_active:
            return user
        
    except HTTPException:
        pass
    
    return None

# WebSocket authentication helper
def authenticate_websocket_user(token: str, db: Session) -> Optional[UserTable]:
    """Authenticate user for WebSocket connection"""
    try:
        token_data = auth_service.verify_token(token)
        user = auth_service.get_user_by_id(db, token_data.user_id)
        
        if user and user.is_active:
            return user
            
    except HTTPException:
        pass
    
    return None 