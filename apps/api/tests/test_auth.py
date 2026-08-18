from fastapi.testclient import TestClient


def test_signup_bearer_token_and_logout(client: TestClient) -> None:
    client.headers.pop("Authorization", None)
    signup = client.post("/api/auth/signup", json={"name": "Test User", "email": "test@example.com", "password": "strong-password"})
    assert signup.status_code == 201
    assert signup.json()["data"]["user"]["email"] == "test@example.com"
    token = signup.json()["data"]["access_token"]
    assert signup.json()["data"]["token_type"] == "bearer"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["user"]["name"] == "Test User"

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200
    client.headers.pop("Authorization", None)
    assert client.get("/api/auth/me").status_code == 401


def test_login_rejects_incorrect_password(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"email": "test@example.com", "password": "incorrect"})
    assert response.status_code == 401
