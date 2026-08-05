import bcrypt
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.requests import Request

from app.db import SessionLocal
from app.models import User

# bcrypt only hashes the first 72 bytes; truncate explicitly so long passwords
# raise no error and behave consistently.
_MAX_BCRYPT_BYTES = 72


def _prepare(plain: str) -> bytes:
    return plain.encode("utf-8")[:_MAX_BCRYPT_BYTES]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_prepare(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(plain), hashed.encode("utf-8"))
    except ValueError:
        return False


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
