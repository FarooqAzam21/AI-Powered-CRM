"""
Minimal Database Initialization
Direct SQLite operations without complex ORM imports
"""
import sqlite3
from pathlib import Path
import hashlib
import os

DB_PATH = Path("data/app.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def hash_password(password: str) -> str:
    """Simple password hash using bcrypt-style (actual bcrypt in app)"""
    # Note: This is a simple representation. Real app uses bcrypt.
    import subprocess
    try:
        # Try to use Python's passlib if available
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(password)
    except:
        # Fallback: just return a simple hash
        return f"$2b$12${hashlib.sha256(password.encode()).hexdigest()}"

def init_database():
    """Initialize SQLite database with proper schema"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            is_verified INTEGER DEFAULT 1,
            verification_token TEXT,
            google_access_token TEXT,
            google_refresh_token TEXT,
            gmail_connected INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create emails table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            gmail_message_id TEXT UNIQUE,
            sender TEXT NOT NULL,
            subject TEXT,
            body TEXT,
            category TEXT,
            confidence REAL,
            action TEXT,
            reason TEXT,
            draft_reply TEXT,
            status TEXT DEFAULT 'PENDING',
            received_at TIMESTAMP,
            processed_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Create notifications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    print("✅ Database schema created/verified")
    conn.close()

def setup_test_user():
    """Create test user with proper password"""
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = pwd_context.hash("123456")
    except ImportError:
        print("⚠️  passlib not available, using fallback hash")
        hashed = hash_password("123456")
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Delete if exists and create fresh
    cursor.execute("DELETE FROM users WHERE email = ?", ("azamfarooq891@gmail.com",))
    
    cursor.execute('''
        INSERT INTO users (name, email, password, role, is_verified)
        VALUES (?, ?, ?, ?, ?)
    ''', ("Azam Farooq", "azamfarooq891@gmail.com", hashed, "admin", 1))
    
    conn.commit()
    
    # Verify it was created
    cursor.execute("SELECT id, email, name FROM users WHERE email = ?", ("azamfarooq891@gmail.com",))
    user = cursor.fetchone()
    
    if user:
        print(f"✅ Test user created: {user}")
    else:
        print("❌ Failed to create test user")
    
    conn.close()

def setup_admin_user():
    """Create admin user"""
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = pwd_context.hash("admin123")
    except ImportError:
        print("⚠️  passlib not available")
        hashed = hash_password("admin123")
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Delete if exists and create fresh
    cursor.execute("DELETE FROM users WHERE email = ?", ("admin@company.com",))
    
    cursor.execute('''
        INSERT INTO users (name, email, password, role, is_verified)
        VALUES (?, ?, ?, ?, ?)
    ''', ("System Admin", "admin@company.com", hashed, "admin", 1))
    
    conn.commit()
    
    # Verify it was created
    cursor.execute("SELECT id, email, name FROM users WHERE email = ?", ("admin@company.com",))
    user = cursor.fetchone()
    
    if user:
        print(f"✅ Admin user created: {user}")
    else:
        print("❌ Failed to create admin user")
    
    conn.close()

def list_users():
    """List all users"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name, role FROM users")
    users = cursor.fetchall()
    
    print("\n📋 Users in database:")
    if not users:
        print("  (No users found)")
    else:
        for user in users:
            print(f"  - ID:{user[0]} | {user[1]} | {user[2]} | Role:{user[3]}")
    
    conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE INITIALIZATION")
    print("=" * 60)
    
    if DB_PATH.exists():
        print(f"\n📂 Database exists at: {DB_PATH.absolute()}")
        print(f"   Size: {DB_PATH.stat().st_size} bytes")
    else:
        print(f"\n📂 Creating new database at: {DB_PATH.absolute()}")
    
    print("\n1️⃣ Initializing database schema...")
    init_database()
    
    print("\n2️⃣ Setting up test user...")
    setup_test_user()
    
    print("\n3️⃣ Setting up admin user...")
    setup_admin_user()
    
    print("\n4️⃣ Listing all users...")
    list_users()
    
    print("\n" + "=" * 60)
    print("✅ Database initialization complete!")
    print("=" * 60)
    print("\n🔐 Test Credentials:")
    print("   Email: azamfarooq891@gmail.com")
    print("   Password: 123456")
    print("\n📌 Admin Credentials:")
    print("   Email: admin@company.com")
    print("   Password: admin123")
