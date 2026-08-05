import os

from dotenv import load_dotenv
from fastapi import FastAPI
from sqladmin import Admin

from app.admin import ALL_VIEWS
from app.auth import AdminAuth
from app.db import Base, engine

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-please")

# Dev convenience: create tables if missing. In prod prefer Alembic migrations.
Base.metadata.create_all(engine)

app = FastAPI(title="Competitor Monitor")

authentication_backend = AdminAuth(secret_key=SECRET_KEY)
admin = Admin(
    app,
    engine,
    authentication_backend=authentication_backend,
    title="Competitor Monitor",
)

for view in ALL_VIEWS:
    admin.add_view(view)


@app.get("/")
def root():
    return {"status": "ok", "admin": "/admin"}
