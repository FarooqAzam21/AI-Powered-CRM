import os
import sys
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Add current directory to path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from auth.models import User
from gmail_service import get_gmail_service

def check_gmail_connectivity():
    load_dotenv()
    
    print("🔍 AI Gmail Automation - API Diagnostic Tool")
    print("-" * 50)
    
    # 1. Check Credentials
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id or "apps.googleusercontent.com" not in client_id:
        print("❌ Error: GOOGLE_CLIENT_ID is missing or invalid in .env")
    else:
        print("✅ GOOGLE_CLIENT_ID is configured.")
        
    if not client_secret or client_secret == "your_client_secret_here":
        print("⚠️ Warning: System is in SIMULATION MODE (Client Secret is default/missing).")
    else:
        print("✅ GOOGLE_CLIENT_SECRET is configured.")

    # 2. Check Database for Connected Users
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.gmail_connected == True).all()
        if not users:
            print("❌ No users found in database with 'gmail_connected=True'.")
            print("   Action: Go to the dashboard and 'Sign in with Google' first.")
            return
        
        print(f"✅ Found {len(users)} connected user(s) in database.")
        
        # 3. Test API connectivity for the first user
        test_user = users[0]
        print(f"\n📡 Testing API for: {test_user.email}")
        
        try:
            service = get_gmail_service(test_user)
            # Try a simple lightweight call (list labels)
            results = service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            if labels:
                print(f"✅ SUCCESS! Gmail API is working.")
                print(f"   Found {len(labels)} labels in your inbox.")
            else:
                print("⚠️ API connected but no labels found (highly unusual).")
                
        except Exception as e:
            print(f"❌ API Connection Failed: {str(e)}")
            if "invalid_grant" in str(e).lower():
                print("   Reason: Your Google token has expired or been revoked.")
                print("   Action: Logout and log back in on the dashboard.")
            elif "403" in str(e):
                print("   Reason: Gmail API is not enabled in Google Cloud Console.")
                print("   Action: Enable 'Gmail API' at https://console.cloud.google.com/")
                
    finally:
        db.close()

if __name__ == "__main__":
    check_gmail_connectivity()
