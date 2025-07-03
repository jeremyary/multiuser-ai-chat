import os
import sys
from loguru import logger
from sqlalchemy.orm import Session

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.auth_service import auth_service
from backend.database import get_database_manager
from shared.auth_models import UserRole

def initialize_admin_user():
    """Initialize default admin user if none exists"""
    try:
        db_manager = get_database_manager()
        
        with db_manager.get_session_context() as db:
            # Check if any admin users exist
            from shared.auth_models import UserTable
            admin_user = db.query(UserTable).filter_by(role=UserRole.ADMIN.value).first()
            
            if admin_user is None:
                logger.info("No admin users found. Creating default admin user...")
                
                # Get admin credentials from environment or use defaults
                admin_username = os.getenv("ADMIN_USERNAME", "admin")
                admin_password = os.getenv("ADMIN_PASSWORD", "admin123!")
                admin_full_name = os.getenv("ADMIN_FULL_NAME", "System Administrator")
                
                # Create admin user
                try:
                    admin_user = auth_service.create_admin_user(
                        db=db,
                        username=admin_username,
                        password=admin_password,
                        full_name=admin_full_name
                    )
                    
                    logger.info(f"✅ Default admin user created: {admin_username}")
                    
                    # SECURITY FIX: Never log actual passwords - only warn about default usage
                    if admin_password == "admin123!":
                        logger.warning("🚨 Using default admin password! Please change it immediately!")
                        logger.warning("🔑 Login with default credentials and change password in settings")
                    
                    return admin_user
                    
                except Exception as e:
                    logger.error(f"❌ Failed to create admin user: {e}")
                    raise
            else:
                logger.info("✅ Admin user already exists")
                return None
                
    except Exception as e:
        logger.error(f"❌ Error initializing admin user: {e}")
        raise

def create_admin_user_interactive():
    """Create admin user interactively (for CLI usage)"""
    import getpass
    
    print("🔐 Creating new admin user...")
    
    username = input("Username: ").strip()
    full_name = input("Full Name (optional): ").strip() or None
    
    while True:
        password = getpass.getpass("Password: ")
        confirm_password = getpass.getpass("Confirm Password: ")
        
        if password == confirm_password:
            break
        else:
            print("❌ Passwords don't match. Please try again.")
    
    try:
        db_manager = get_database_manager()
        
        with db_manager.get_session_context() as db:
            admin_user = auth_service.create_admin_user(
                db=db,
                username=username,
                password=password,
                full_name=full_name
            )
            
            print(f"✅ Admin user created: {username}")
            return admin_user
            
    except Exception as e:
        print(f"❌ Failed to create admin user: {e}")
        raise

if __name__ == "__main__":
    # Allow running this script directly to create admin user
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize admin user")
    parser.add_argument("--interactive", "-i", action="store_true", help="Create admin user interactively")
    parser.add_argument("--force", "-f", action="store_true", help="Force create default admin user")
    
    args = parser.parse_args()
    
    if args.interactive:
        create_admin_user_interactive()
    else:
        initialize_admin_user() 