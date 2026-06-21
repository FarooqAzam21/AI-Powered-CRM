"""
Test Authentication Flow
"""
import sqlite3
from pathlib import Path
from passlib.context import CryptContext

DB_PATH = Path("data/app.db")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def test_password_verification():
    """Test if password verification works"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Get test user
    cursor.execute("SELECT email, password FROM users WHERE email = ?", ("azamfarooq891@gmail.com",))
    user = cursor.fetchone()
    
    if not user:
        print("❌ User not found")
        conn.close()
        return False
    
    email, hashed_password = user
    test_password = "123456"
    
    print(f"✅ User found: {email}")
    print(f"🔒 Password hash in DB: {hashed_password[:50]}...")
    
    # Test password verification
    is_valid = pwd_context.verify(test_password, hashed_password)
    
    if is_valid:
        print(f"✅ Password verification PASSED for '{test_password}'")
    else:
        print(f"❌ Password verification FAILED for '{test_password}'")
    
    conn.close()
    return is_valid

def test_jwt_token():
    """Test JWT token creation and decoding"""
    from auth.jwt import create_access_token, SECRET_KEY, ALGORITHM
    from jose import jwt
    from datetime import timedelta
    
    # Create a token
    data = {"sub": "azamfarooq891@gmail.com", "role": "admin"}
    token = create_access_token(data, timedelta(days=1))
    
    print(f"\n✅ JWT Token created: {token[:50]}...")
    
    # Decode the token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"✅ JWT Token decoded successfully:")
        print(f"   - Email (sub): {payload.get('sub')}")
        print(f"   - Role: {payload.get('role')}")
        return True
    except Exception as e:
        print(f"❌ JWT decoding failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("AUTHENTICATION FLOW TEST")
    print("=" * 60)
    
    print("\n1️⃣ Testing password verification...")
    pwd_valid = test_password_verification()
    
    print("\n2️⃣ Testing JWT token creation...")
    jwt_valid = test_jwt_token()
    
    print("\n" + "=" * 60)
    if pwd_valid and jwt_valid:
        print("✅ All tests PASSED!")
        print("=" * 60)
        print("\n🚀 Ready to start backend server")
        print("   Run: python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000")
    else:
        print("❌ Some tests FAILED")
        print("=" * 60)
