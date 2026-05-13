from database import SessionLocal
from auth.models import User

def check_user(email):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user:
        print(f"User: {user.email}")
        print(f"Gmail Connected: {user.gmail_connected}")
        print(f"Access Token: {user.google_access_token[:10] if user.google_access_token else 'None'}...")
        print(f"Refresh Token: {user.google_refresh_token[:10] if user.google_refresh_token else 'None'}...")
    else:
        print(f"User {email} NOT FOUND in database.")
    db.close()

if __name__ == "__main__":
    check_user("azamfarooq891@gmail.com")
