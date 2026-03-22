from app.core.config import settings


async def test_dev_auth_login_roundtrip(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", False)

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "ytkim@amic.kr", "password": "1111"},
    )

    assert login_resp.status_code == 200
    assert login_resp.json()["message"] == "Login successful"

    me_resp = await client.get("/api/v1/auth/me")

    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "ytkim@amic.kr"
    assert me_resp.json()["role"] == "ADMIN"


async def test_dev_auth_invalid_credentials(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", False)

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "ytkim@amic.kr", "password": "wrong"},
    )

    assert resp.status_code == 401


async def test_dev_auth_logout_clears_session(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", False)

    await client.post(
        "/api/v1/auth/login",
        json={"email": "ytkim@amic.kr", "password": "1111"},
    )

    logout_resp = await client.post("/api/v1/auth/logout")
    me_resp = await client.get("/api/v1/auth/me")

    assert logout_resp.status_code == 200
    assert me_resp.status_code == 401


async def test_dev_auth_hidden_when_auth_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "ytkim@amic.kr", "password": "1111"},
    )

    assert resp.status_code == 404
