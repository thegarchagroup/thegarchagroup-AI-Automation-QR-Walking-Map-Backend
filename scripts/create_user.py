"""
Create (or update the password of) an editor account.

Usage (from the backend/ directory, with the virtualenv active):
    python -m scripts.create_user
"""
import sys
import getpass
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.database import Base, engine, SessionLocal
from app.models import User
from app.security import hash_password


def main():
    Base.metadata.create_all(bind=engine)

    email = input("Email for this editor account: ").strip().lower()
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        print("Passwords didn't match — nothing was created.")
        return

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            existing.hashed_password = hash_password(password)
            db.commit()
            print(f"Updated password for {email}.")
        else:
            user = User(email=email, hashed_password=hash_password(password))
            db.add(user)
            db.commit()
            print(f"Created editor account for {email}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
