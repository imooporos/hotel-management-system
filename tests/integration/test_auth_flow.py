"""Тест-кейс 1: регистрация → логин → /auth/me → обновление профиля."""

from __future__ import annotations

import uuid

import httpx


def test_registration_login_me_update(http: httpx.Client):
    suffix = uuid.uuid4().hex[:8]
    email = f"flow_{suffix}@example.com"
    password = "Test_Pass_2026!"
    full_name = f"Тест Поток {suffix}"

    # 1) регистрация
    resp = http.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert resp.status_code == 201, resp.text
    token1 = resp.json()["access_token"]
    assert resp.json()["token_type"] == "bearer"

    # 2) повторный login
    resp = http.post("/auth/login-json", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token2 = resp.json()["access_token"]
    assert token2  # JWT issued

    # 3) /auth/me с новым токеном
    me = http.get("/auth/me", headers={"Authorization": f"Bearer {token2}"}).json()
    assert me["email"] == email
    assert me["full_name"] == full_name
    assert me["role"] == "guest"
    assert me["is_active"] is True

    # 4) изменяем профиль
    resp = http.patch(
        "/auth/me",
        headers={"Authorization": f"Bearer {token2}"},
        json={"full_name": full_name + " ✏"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["full_name"].endswith("✏")

    # 5) попытка логина с неверным паролем — 401
    resp = http.post("/auth/login-json", json={"email": email, "password": "wrong-pass"})
    assert resp.status_code == 401
