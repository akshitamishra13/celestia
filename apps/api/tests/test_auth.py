import os
import tempfile
from pathlib import Path

import pytest

test_database = Path(tempfile.gettempdir()) / "astrolive-auth-test.db"
test_database.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{test_database.as_posix()}"

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import engine


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()
    test_database.unlink(missing_ok=True)


def test_signup_session_and_logout(client: TestClient) -> None:
    signup = client.post("/api/auth/signup", json={"name": "Test User", "email": "test@example.com", "password": "strong-password"})
    assert signup.status_code == 201
    assert signup.json()["data"]["user"]["email"] == "test@example.com"
    assert "astrolive_session" in signup.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["data"]["user"]["name"] == "Test User"

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_login_rejects_incorrect_password(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"email": "test@example.com", "password": "incorrect"})
    assert response.status_code == 401
