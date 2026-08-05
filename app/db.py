import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./monitor.db")

# SQLite needs check_same_thread=False when used from the web server threads.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# On serverless (Vercel) every invocation is a fresh process, so a local pool is
# useless and would exhaust Postgres connections. Pool on long-lived hosts only.
is_serverless = bool(os.getenv("VERCEL"))
engine_kwargs = {"poolclass": NullPool} if is_serverless else {"pool_pre_ping": True}

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
