"""
Database Check and Fix Script
Verifies and fixes user accounts, passwords, and database integrity
"""
from database import SessionLocal, engine, Base
from auth.models import User, Email, Notification
from auth.jwt import get_password_hash, verify_password

def init_database():
    """Initialize the database schema"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database schema initialized")

def check_user_exists(email: str):
    """Check if user exists"""
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    db.close()
    return user

def create_or_fix_user(name: str, email: str, password: str, role: str = "user"):
    """Create or update a user with correct password hash"""
    db = SessionLocal()
    
    user = db.query(User).filter(User.email == email).first()
    
    if user:
        print(f"✏️ User {email} exists. Updating password...")
        user.password = get_password_hash(password)
        user.role = role
        user.is_verified = True
        db.commit()
        print(f"✅ User {email} password updated successfully!")
    else:
        print(f"➕ Creating new user: {email}")
        new_user = User(
            name=name,
            email=email,
            password=get_password_hash(password),
            role=role,
            is_verified=True
        )
        db.add(new_user)
        db.commit()
        print(f"✅ User {email} created successfully!")
        user = new_user
    
    db.close()
    return user

def verify_login(email: str, password: str):
    """Test if login works"""
    user = check_user_exists(email)
    if not user:
        print(f"❌ User {email} does not exist")
        return False
    
    if not verify_password(password, user.password):
        print(f"❌ Password verification failed for {email}")
        return False
    
    print(f"✅ Login verification passed for {email}")
    return True

def list_all_users():
    """List all users in database"""
    db = SessionLocal()
    users = db.query(User).all()
    print("\n📋 Users in database:")
    if not users:
        print("  (No users found)")
    else:
        for user in users:
            print(f"  - {user.email} (name: {user.name}, role: {user.role}, verified: {user.is_verified})")
    db.close()

def delete_user(email: str):
    """Delete a user from database"""
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user:
        db.delete(user)
        db.commit()
        print(f"🗑️ User {email} deleted successfully")
    else:
        print(f"❌ User {email} not found")
    db.close()

def clear_all_users():
    """Clear all users (dangerous!)"""
    db = SessionLocal()
    db.query(User).delete()
    db.commit()
    print("🗑️ All users deleted from database")
    db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE CHECK & FIX TOOL")
    print("=" * 60)
    
    # 1. Initialize database
    init_database()
    
    # 2. List existing users
    list_all_users()
    
    # 3. Fix the main test user
    print("\n📝 Setting up test user...")
    create_or_fix_user(
        name="Azam Farooq",
        email="azamfarooq891@gmail.com",
        password="123456",
        role="admin"
    )
    
    # 4. Create admin user
    print("\n📝 Setting up admin user...")
    create_or_fix_user(
        name="System Admin",
        email="admin@company.com",
        password="admin123",
        role="admin"
    )
    
    # 5. Verify logins
    print("\n🔐 Testing logins...")
    verify_login("azamfarooq891@gmail.com", "123456")
    verify_login("admin@company.com", "admin123")
    
    # 6. Final user list
    print()
    list_all_users()
    
    print("\n" + "=" * 60)
    print("✅ Database check and fix complete!")
    print("=" * 60)
