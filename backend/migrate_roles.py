import asyncio
import os
from sqlalchemy.orm import Session
from database import SessionLocal
from auth.models import User, Workspace, APIKey
from auth.rbac import Role
from datetime import datetime

def migrate_data():
    db = SessionLocal()
    
    # 1. Create a Default Workspace if none exists
    default_workspace = db.query(Workspace).filter(Workspace.name == "Default Workspace").first()
    if not default_workspace:
        default_workspace = Workspace(name="Default Workspace")
        db.add(default_workspace)
        db.commit()
        db.refresh(default_workspace)
        print("Created Default Workspace")

    # 2. Migrate Users
    users = db.query(User).all()
    for user in users:
        # Migrate Workspace
        if not user.workspace_id:
            user.workspace_id = default_workspace.id
        
        # Migrate Roles
        if user.role == "admin":
            user.role = Role.SUPER_ADMIN
        elif user.role == "agent":
            user.role = Role.SECURITY_ANALYST
        elif user.role == "user":
            user.role = Role.VIEWER
            
    db.commit()
    print(f"Migrated {len(users)} users.")

    # 3. Create a test API Key for the Workspace Admin
    admin_user = db.query(User).filter(User.role == Role.SUPER_ADMIN).first()
    if admin_user:
        api_key_str = "sk-test-enterprise-key-12345"
        existing_key = db.query(APIKey).filter(APIKey.key == api_key_str).first()
        if not existing_key:
            api_key = APIKey(
                workspace_id=default_workspace.id,
                key=api_key_str,
                name="Test Enterprise Key"
            )
            db.add(api_key)
            db.commit()
            print("Created Test API Key: sk-test-enterprise-key-12345")
            
    db.close()

if __name__ == "__main__":
    migrate_data()
