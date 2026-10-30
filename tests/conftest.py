"""Test setup. Runs against a throw-away SQLite file - never touches your MySQL database."""
import os
import tempfile

# Must be set BEFORE the app is imported (settings are read at import time).
_DB_FILE = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_FILE}"
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-not-used-anywhere-else-0123456789"
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["ALLOW_OPEN_ROLE_REGISTRATION"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from database.connection import Base, SessionLocal, engine  # noqa: E402
from database.models import UserRole  # noqa: E402
from main import app  # noqa: E402
from services import user as user_service  # noqa: E402

PASSWORD = "Password@123"


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def make_user():
    """Create a user directly in the DB (public register can't make admins/managers)."""
    def _make(email, role="user", name="Test User", password=PASSWORD, is_active=True):
        with SessionLocal() as db:
            u = user_service.create_user(db, name=name, email=email, password=password,
                                         role=UserRole(role), is_active=is_active)
            return u.user_id
    return _make


@pytest.fixture
def login(client):
    def _login(email, password=PASSWORD):
        r = client.post("/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return _login


@pytest.fixture
def admin(make_user, login):
    make_user("admin@example.com", "admin", "Admin One")
    return login("admin@example.com")


@pytest.fixture
def manager(make_user, login):
    make_user("manager@example.com", "manager", "Manager One")
    return login("manager@example.com")


@pytest.fixture
def user(make_user, login):
    make_user("user@example.com", "user", "Normal User")
    return login("user@example.com")


@pytest.fixture
def me_id(client):
    """user_id of whoever owns the given auth headers."""
    return lambda headers: client.get("/auth/me", headers=headers).json()["user_id"]
