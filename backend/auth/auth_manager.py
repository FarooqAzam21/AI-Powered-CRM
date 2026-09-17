from sqlalchemy.orm import Session
from auth.models import User
from database import SessionLocal

from auth.jwt import verify_password

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def find_user_by_email(email: str, db: Session = None):
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    user = db.query(User).filter(User.email == email).first()
    if close_db:
        db.close()
    return user

def create_user(user_data: dict, db: Session = None):
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    if close_db:
        db.close()
    return user

def authenticate(email, password):
    user = find_user_by_email(email)
    if not user or not verify_password(password, user.password):
        return None
    return {
        "email": user.email,
        "name": user.name,
        "role": user.role
    }
