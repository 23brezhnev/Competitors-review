"""Grant admin access by inserting a user.

Usage:
    python -m scripts.create_user admin@example.com 'strong-password'
"""
import sys

from app.auth import hash_password
from app.db import Base, SessionLocal, engine
from app.models import User


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m scripts.create_user <email> <password>")
        raise SystemExit(1)

    email, password = sys.argv[1], sys.argv[2]
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            existing.hashed_password = hash_password(password)
            existing.is_active = True
            print(f"Updated password for {email}")
        else:
            db.add(User(email=email, hashed_password=hash_password(password)))
            print(f"Created user {email}")
        db.commit()


if __name__ == "__main__":
    main()
