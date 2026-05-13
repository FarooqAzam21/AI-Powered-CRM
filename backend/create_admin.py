from database import SessionLocal
from auth.models import User
from auth.jwt import get_password_hash

def create_admin():
    db = SessionLocal()
    email = "admin@company.com"
    
    # Check if exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        print(f"User {email} already exists. Updating to Admin...")
        existing.role = "admin"
        existing.password = get_password_hash("admin123")
        db.commit()
    else:
        print(f"Creating new Admin user: {email}")
        new_admin = User(
            name="System Admin",
            email=email,
            password=get_password_hash("admin123"),
            role="admin"
        )
        db.add(new_admin)
        db.commit()
    
    print("Admin created successfully!")
    print(f"Email: {email}")
    print(f"Password: admin123")
    db.close()

if __name__ == "__main__":
    create_admin()
