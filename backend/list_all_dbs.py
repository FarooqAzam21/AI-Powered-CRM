from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from auth.models import User
import os

def check_db(name):
    if not os.path.exists(name):
        print(f"File {name} does not exist.")
        return
    
    try:
        engine = create_engine(f'sqlite:///./{name}')
        Session = sessionmaker(bind=engine)
        db = Session()
        emails = [u.email for u in db.query(User).all()]
        print(f"{name}: {emails}")
        db.close()
    except Exception as e:
        print(f"Error checking {name}: {str(e)}")

if __name__ == "__main__":
    check_db("app.db")
    check_db("app_v2.db")
    check_db("app_v3.db")
