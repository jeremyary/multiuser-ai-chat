import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from loguru import logger
import secrets

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.auth_models import (
    UserTable, SessionTable, UserCreate, UserUpdate, UserInDB, 
    TokenData, UserRole, LoginResponse, UserResponse
)
from backend.database import get_database_manager

class AuthService:
    def __init__(self):
        # Password hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # JWT Configuration
        self.SECRET_KEY = os.getenv("JWT_SECRET_KEY", self._generate_secret_key())
        self.ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours
        
        # Store secret key warning if auto-generated
        if "JWT_SECRET_KEY" not in os.environ:
            logger.warning("JWT_SECRET_KEY not set in environment. Using auto-generated key.")
            logger.warning("For production, set JWT_SECRET_KEY environment variable!")
    
    def _generate_secret_key(self) -> str:
        """Generate a random secret key"""
        return secrets.token_urlsafe(32)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> TokenData:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            username: str = payload.get("sub")
            user_id: int = payload.get("user_id")
            
            if username is None or user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return TokenData(username=username, user_id=user_id)
        
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def get_user_by_username(self, db: Session, username: str) -> Optional[UserTable]:
        """Get user by username"""
        return db.query(UserTable).filter(UserTable.username == username).first()
    

    
    def get_user_by_id(self, db: Session, user_id: int) -> Optional[UserTable]:
        """Get user by ID"""
        return db.query(UserTable).filter(UserTable.id == user_id).first()
    
    def authenticate_user(self, db: Session, username: str, password: str) -> Union[UserTable, bool]:
        """Authenticate user with username/password"""
        user = self.get_user_by_username(db, username)
        
        # SECURITY FIX: Prevent timing attacks by always performing password verification
        # Use a dummy hash if user doesn't exist to maintain consistent timing
        if user:
            password_valid = self.verify_password(password, user.hashed_password)
        else:
            # Use a dummy bcrypt hash to maintain consistent timing
            dummy_hash = "$2b$12$dummy.hash.to.prevent.timing.attacks.and.username.enumeration"
            self.verify_password(password, dummy_hash)
            password_valid = False
        
        # Return False if user doesn't exist, password is wrong, or user is inactive
        if not user or not password_valid or not user.is_active:
            return False
        
        # Update last login only if authentication successful
        user.last_login = datetime.utcnow()
        user.last_activity = datetime.utcnow()
        db.commit()
        
        return user
    
    def create_user(self, db: Session, user: UserCreate) -> UserTable:
        """Create a new user"""
        # Check if username already exists
        if self.get_user_by_username(db, user.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Create user
        hashed_password = self.get_password_hash(user.password)
        db_user = UserTable(
            username=user.username,
            hashed_password=hashed_password,
            full_name=user.full_name,
            role=user.role.value,
            avatar_color=user.avatar_color,
            is_kid_account=user.is_kid_account
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"Created new user: {user.username}")
        return db_user
    
    def update_user(self, db: Session, user_id: int, user_update: UserUpdate) -> UserTable:
        """Update user information"""
        user = self.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields if provided
        if user_update.full_name is not None:
            user.full_name = user_update.full_name
        
        if user_update.avatar_color is not None:
            user.avatar_color = user_update.avatar_color
        
        if user_update.role is not None:
            user.role = user_update.role.value
        
        if user_update.is_active is not None:
            user.is_active = user_update.is_active
        
        if user_update.is_kid_account is not None:
            user.is_kid_account = user_update.is_kid_account
        
        user.last_activity = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        logger.info(f"Updated user: {user.username}")
        return user
    
    def change_password(self, db: Session, user_id: int, current_password: str, new_password: str) -> bool:
        """Change user password"""
        user = self.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not self.verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        user.hashed_password = self.get_password_hash(new_password)
        user.last_activity = datetime.utcnow()
        db.commit()
        
        logger.info(f"Password changed for user: {user.username}")
        return True
    
    def delete_user(self, db: Session, user_id: int) -> bool:
        """Delete user (soft delete by deactivating)"""
        user = self.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.is_active = False
        user.last_activity = datetime.utcnow()
        db.commit()
        
        logger.info(f"Deactivated user: {user.username}")
        return True
    
    def get_all_users(self, db: Session, skip: int = 0, limit: int = 100) -> list[UserTable]:
        """Get all users (admin only)"""
        return db.query(UserTable).offset(skip).limit(limit).all()
    
    def create_admin_user(self, db: Session, username: str, password: str, full_name: str = None) -> UserTable:
        """Create admin user"""
        admin_user = UserCreate(
            username=username,
            password=password,
            full_name=full_name or "Administrator",
            role=UserRole.ADMIN,
            avatar_color="#e74c3c"  # Red color for admin
        )
        
        return self.create_user(db, admin_user)
    
    def login(self, db: Session, username: str, password: str) -> LoginResponse:
        """Login user and return token"""
        user = self.authenticate_user(db, username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": user.username, "user_id": user.id}, 
            expires_delta=access_token_expires
        )
        
        # Create session record
        session_token = secrets.token_urlsafe(32)
        session = SessionTable(
            user_id=user.id,
            session_token=session_token,
            expires_at=datetime.utcnow() + access_token_expires
        )
        db.add(session)
        db.commit()
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=self.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.from_orm(user)
        )

# Global auth service instance
auth_service = AuthService() 