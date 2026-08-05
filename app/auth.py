from passlib.context import CryptContext
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.requests import Request

from app.db import SessionLocal
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


class AdminAuth(AuthenticationBackend):
    """Session login backed by the `users` table. Grant access = insert a user row."""

    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = (form.get("username") or "").strip()
        password = form.get("password") or ""
        with SessionLocal() as db:
            user = db.scalar(
                select(User).where(User.email == email, User.is_active.is_(True))
            )
            if user and verify_password(password, user.hashed_password):
                request.session.update({"user": user.email})
                return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return "user" in request.session
