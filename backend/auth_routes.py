import os
import sys
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.auth_models import (
    LoginRequest, LoginResponse, UserCreate, UserResponse, UserUpdate,
    PasswordChangeRequest, AdminUserCreateRequest, UserRole
)
from backend.auth_service import auth_service
from backend.auth_middleware import get_current_user, get_current_admin_user
from backend.database import get_db_session

# Create router for authentication endpoints
auth_router = APIRouter(prefix="/auth", tags=["authentication"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])

@auth_router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db_session)
):
    """Login user and return access token"""
    return auth_service.login(db, login_data.username, login_data.password)

@auth_router.post("/logout")
async def logout(
    current_user = Depends(get_current_user)
):
    """Logout user (client should discard token)"""
    return {"message": "Successfully logged out"}

@auth_router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse.from_orm(current_user)

@auth_router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update current user information"""
    # Users can't change their own role
    if user_update.role is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change your own role"
        )
    
    updated_user = auth_service.update_user(db, current_user.id, user_update)
    return UserResponse.from_orm(updated_user)

@auth_router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Change user password"""
    auth_service.change_password(
        db, 
        current_user.id, 
        password_data.current_password, 
        password_data.new_password
    )
    return {"message": "Password changed successfully"}

# Admin routes
@admin_router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Get all users (admin only)"""
    users = auth_service.get_all_users(db, skip=skip, limit=limit)
    return [UserResponse.from_orm(user) for user in users]

@admin_router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: AdminUserCreateRequest,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Create new user (admin only)"""
    new_user = UserCreate(
        username=user_data.username,
        password=user_data.password,
        full_name=user_data.full_name,
        role=user_data.role,
        avatar_color=user_data.avatar_color,
        is_kid_account=user_data.is_kid_account
    )
    
    created_user = auth_service.create_user(db, new_user)
    return UserResponse.from_orm(created_user)

@admin_router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Update user (admin only)"""
    updated_user = auth_service.update_user(db, user_id, user_update)
    return UserResponse.from_orm(updated_user)

@admin_router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Delete/deactivate user (admin only)"""
    # Prevent admin from deleting themselves
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    auth_service.delete_user(db, user_id)
    return {"message": "User deleted successfully"}

@admin_router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    new_password: str = Body(..., embed=True),
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db_session)
):
    """Reset user password (admin only)"""
    user = auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password directly (bypass current password check)
    user.hashed_password = auth_service.get_password_hash(new_password)
    db.commit()
    
    return {"message": "Password reset successfully"}

# Health check for authentication system
@auth_router.get("/health")
async def auth_health_check():
    """Authentication system health check"""
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": "2025-01-11T02:24:00Z"
    } 