from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from auth.models import User, Base
import os

DATABASE_URL = "sqlite:///./app_v3.db"

def list_users():
    if not os.path.exists("./app_v3.db"):
        print("❌ Database file not found.")
        return

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        users = session.query(User).all()
        if not users:
            print("📭 No users found in database.")
        else:
            print(f"👥 Found {len(users)} users:")
            for u in users:
                print(f"- {u.name} ({u.email}) [Verified: {u.is_verified}, Gmail: {u.gmail_connected}]")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    list_users()
