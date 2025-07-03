import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger
from contextlib import contextmanager
from typing import Generator

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.auth_models import Base, UserTable, SessionTable
from shared.config import Config

class DatabaseManager:
    def __init__(self, database_url: str = None):
        if database_url is None:
            # Default to SQLite database in data directory
            data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
            os.makedirs(data_dir, exist_ok=True)
            database_url = f"sqlite:///{data_dir}/chat_app.db"
        
        self.database_url = database_url
        
        # Create engine with SQLite-specific configurations
        self.engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
            echo=Config.DEBUG,  # Log SQL queries in debug mode
            pool_size=20,  # Increased from default 5
            max_overflow=30,  # Increased from default 10
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_pre_ping=True  # Verify connections before use
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables if they don't exist
        self.create_tables()
        
        logger.info(f"Database initialized: {database_url}")
    
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()
    
    @contextmanager
    def get_session_context(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        except Exception:
            # Rollback for any other exception but don't log as database error
            session.rollback()
            raise
        finally:
            session.close()
    
    def close(self):
        """Close database connections"""
        self.engine.dispose()
        logger.info("Database connections closed")

# Global database manager instance
db_manager = None

def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager

def get_db_session() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session"""
    manager = get_database_manager()
    with manager.get_session_context() as session:
        yield session

def init_database():
    """Initialize database on startup"""
    global db_manager
    db_manager = DatabaseManager()
    return db_manager

def close_database():
    """Close database on shutdown"""
    global db_manager
    if db_manager:
        db_manager.close()
        db_manager = None 