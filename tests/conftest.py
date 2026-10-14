"""Test setup: point the app at a throwaway SQLite file BEFORE it is imported."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="walkguide-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import User
from app.security import hash_password


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add(User(email="editor@example.com", hashed_password=hash_password("pw-123456")))
    db.commit()
    db.close()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(client):
    r = client.post("/auth/login", json={"email": "editor@example.com", "password": "pw-123456"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
