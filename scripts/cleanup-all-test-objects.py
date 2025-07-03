#!/usr/bin/env python3
"""
Comprehensive cleanup script for AI Chat Workspace.

This script combines the functionality of:
- cleanup_rooms.sh - Redis room cleanup (preserving 'general' room)
- cleanup_test_users.py - Database test user cleanup
- redis_cleanup.lua - Redis cleanup with proper counting

Usage:
    python cleanup_all.py [--redis-only] [--db-only] [--dry-run]
"""

import os
import sys
import json
import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger
import redis

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from shared.auth_models import UserTable, Base
from shared.config import Config

class ComprehensiveCleanup:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.redis_client = None
        self.db_session = None
        
        # Initialize Redis connection
        self._init_redis()
        
        # Initialize database connection
        self._init_database()
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No actual cleanup will be performed")
        
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            # Try Docker Redis first, then localhost
            redis_configs = [
                {"host": "localhost", "port": 6379, "db": 0},  # Docker Redis
                {"host": "127.0.0.1", "port": 6379, "db": 0}   # Local Redis
            ]
            
            for config in redis_configs:
                try:
                    self.redis_client = redis.Redis(**config, decode_responses=True)
                    self.redis_client.ping()
                    logger.info(f"✅ Connected to Redis at {config['host']}:{config['port']}")
                    break
                except:
                    continue
            
            if not self.redis_client:
                raise Exception("Could not connect to Redis")
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
    
    def _init_database(self):
        """Initialize database connection"""
        try:
            # Connect to SQLite database
            data_dir = os.path.join(os.path.dirname(__file__), 'data')
            database_url = f"sqlite:///{data_dir}/chat_app.db"
            
            # Create engine with SQLite-specific configurations
            engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                echo=False
            )
            
            # Create session factory
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            self.db_session = SessionLocal()
            
            logger.info(f"✅ Connected to database: {database_url}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    def cleanup_redis_rooms(self):
        """Clean up Redis rooms (preserving 'general' room)"""
        logger.info("🧹 Cleaning up Redis rooms...")
        
        try:
            # Get all room keys
            room_keys = self.redis_client.keys('chat:room:*')
            deleted_rooms = 0
            preserved_rooms = []
            
            for room_key in room_keys:
                # Extract room_id from key
                room_id = room_key.replace('chat:room:', '')
                
                # Skip general room
                if room_id == 'general':
                    preserved_rooms.append(room_id)
                    continue
                
                if not self.dry_run:
                    # Delete room data
                    self.redis_client.delete(room_key)
                    
                    # Delete room messages
                    self.redis_client.delete(f'chat:messages:{room_id}')
                    
                    # Delete room users
                    self.redis_client.delete(f'chat:room_users:{room_id}')
                
                deleted_rooms += 1
                logger.info(f"  {'[DRY RUN] Would delete' if self.dry_run else '✅ Deleted'} room: {room_id}")
            
            # Clean up orphaned individual message keys
            message_keys = self.redis_client.keys('chat:message:*')
            deleted_messages = 0
            
            for msg_key in message_keys:
                msg_data = self.redis_client.hgetall(msg_key)
                if msg_data:
                    room_id = msg_data.get('chat_room_id')
                    if room_id and room_id != 'general':
                        if not self.dry_run:
                            self.redis_client.delete(msg_key)
                        deleted_messages += 1
                else:
                    # Delete empty message keys
                    if not self.dry_run:
                        self.redis_client.delete(msg_key)
                    deleted_messages += 1
            
            logger.info(f"  {'[DRY RUN] Would delete' if self.dry_run else '✅ Deleted'} {deleted_rooms} rooms")
            logger.info(f"  {'[DRY RUN] Would delete' if self.dry_run else '✅ Deleted'} {deleted_messages} orphaned messages")
            logger.info(f"  🛡️  Preserved rooms: {preserved_rooms}")
            
            return deleted_rooms, deleted_messages
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up Redis rooms: {e}")
            raise
    
    def cleanup_test_users(self):
        """Clean up inactive test users from database"""
        logger.info("👥 Cleaning up test users...")
        
        try:
            # Find all inactive test users
            test_users = self.db_session.query(UserTable).filter(
                UserTable.username.like('test_%'),
                UserTable.is_active == False
            ).all()
            
            if not test_users:
                logger.info("  ✅ No inactive test users found")
                return 0
            
            logger.info(f"  📋 Found {len(test_users)} inactive test users:")
            
            # Show what we're about to delete
            for user in test_users:
                logger.info(f"    - {user.username} (ID: {user.id})")
            
            if not self.dry_run:
                # Delete the users
                deleted_count = self.db_session.query(UserTable).filter(
                    UserTable.username.like('test_%'),
                    UserTable.is_active == False
                ).delete(synchronize_session=False)
                
                self.db_session.commit()
                logger.success(f"  ✅ Successfully deleted {deleted_count} inactive test users")
            else:
                logger.info(f"  [DRY RUN] Would delete {len(test_users)} inactive test users")
            
            # Verify cleanup
            remaining_test_users = self.db_session.query(UserTable).filter(
                UserTable.username.like('test_%')
            ).all()
            
            if remaining_test_users:
                logger.warning(f"  ⚠️  Still have {len(remaining_test_users)} test users remaining:")
                for user in remaining_test_users:
                    status = "active" if user.is_active else "inactive"
                    logger.info(f"    - {user.username} (ID: {user.id}, {status})")
            else:
                logger.success("  ✅ All test users have been removed")
            
            return len(test_users)
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up test users: {e}")
            raise
    
    def get_redis_stats(self):
        """Get current Redis statistics"""
        try:
            room_keys = self.redis_client.keys('chat:room:*')
            message_keys = self.redis_client.keys('chat:message:*')
            
            rooms = []
            for room_key in room_keys:
                room_id = room_key.replace('chat:room:', '')
                room_data = self.redis_client.hgetall(room_key)
                rooms.append({
                    'id': room_id,
                    'name': room_data.get('room_name', 'Unknown'),
                    'messages': len(self.redis_client.zrange(f'chat:messages:{room_id}', 0, -1))
                })
            
            return {
                'rooms': rooms,
                'total_rooms': len(room_keys),
                'total_messages': len(message_keys)
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting Redis stats: {e}")
            return {}
    
    def get_database_stats(self):
        """Get current database statistics"""
        try:
            # Get all users
            all_users = self.db_session.query(UserTable).all()
            active_users = [u for u in all_users if u.is_active]
            inactive_users = [u for u in all_users if not u.is_active]
            test_users = [u for u in all_users if u.username.startswith('test_')]
            
            return {
                'total_users': len(all_users),
                'active_users': len(active_users),
                'inactive_users': len(inactive_users),
                'test_users': len(test_users),
                'user_breakdown': {
                    'active': [{'id': u.id, 'username': u.username, 'role': u.role} for u in active_users],
                    'inactive': [{'id': u.id, 'username': u.username, 'role': u.role} for u in inactive_users],
                    'test': [{'id': u.id, 'username': u.username, 'active': u.is_active} for u in test_users]
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting database stats: {e}")
            return {}
    
    def run_cleanup(self, redis_only=False, db_only=False):
        """Run the cleanup process"""
        logger.info("🚀 Starting comprehensive cleanup...")
        
        # Get initial stats
        logger.info("📊 Getting initial statistics...")
        initial_redis_stats = self.get_redis_stats()
        initial_db_stats = self.get_database_stats()
        
        logger.info(f"  📈 Redis: {initial_redis_stats.get('total_rooms', 0)} rooms, {initial_redis_stats.get('total_messages', 0)} messages")
        logger.info(f"  📈 Database: {initial_db_stats.get('total_users', 0)} users ({initial_db_stats.get('active_users', 0)} active, {initial_db_stats.get('test_users', 0)} test users)")
        
        # Run cleanup
        deleted_rooms = deleted_messages = deleted_users = 0
        
        if not db_only:
            deleted_rooms, deleted_messages = self.cleanup_redis_rooms()
        
        if not redis_only:
            deleted_users = self.cleanup_test_users()
        
        # Get final stats
        logger.info("📊 Getting final statistics...")
        final_redis_stats = self.get_redis_stats()
        final_db_stats = self.get_database_stats()
        
        logger.info(f"  📈 Redis: {final_redis_stats.get('total_rooms', 0)} rooms, {final_redis_stats.get('total_messages', 0)} messages")
        logger.info(f"  📈 Database: {final_db_stats.get('total_users', 0)} users ({final_db_stats.get('active_users', 0)} active, {final_db_stats.get('test_users', 0)} test users)")
        
        # Summary
        logger.info("🎯 Cleanup Summary:")
        logger.info(f"  🏠 Rooms deleted: {deleted_rooms}")
        logger.info(f"  💬 Messages deleted: {deleted_messages}")
        logger.info(f"  👥 Users deleted: {deleted_users}")
        
        if not self.dry_run:
            logger.success("✅ Cleanup completed successfully!")
        else:
            logger.info("🔍 Dry run completed - no actual changes made")
    
    def close(self):
        """Close connections"""
        if self.db_session:
            self.db_session.close()
        if self.redis_client:
            self.redis_client.close()

def main():
    parser = argparse.ArgumentParser(description="Comprehensive cleanup for AI Chat Workspace")
    parser.add_argument("--redis-only", action="store_true", help="Only clean Redis data")
    parser.add_argument("--db-only", action="store_true", help="Only clean database data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be cleaned without actually doing it")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    cleanup = None
    try:
        cleanup = ComprehensiveCleanup(dry_run=args.dry_run)
        cleanup.run_cleanup(redis_only=args.redis_only, db_only=args.db_only)
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        sys.exit(1)
    finally:
        if cleanup:
            cleanup.close()

if __name__ == "__main__":
    main() 