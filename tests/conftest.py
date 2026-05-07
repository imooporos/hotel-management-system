"""Общие фикстуры pytest для интеграционных тестов."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import httpx
import pytest

# Добавляем server/ в sys.path, чтобы импортировать модули backend для unit-тестов.
ROOT = Path(__file__).resolve().parents[1]
SERVER_DIR = ROOT / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))


API_URL = os.environ.get("HOTEL_API_URL", "http://77.221.151.85").rstrip("/")


@pytest.fixture(scope="session")
def api_url() -> str:
    return API_URL


@pytest.fixture()
def http() -> httpx.Client:
    """Чистый HTTP-клиент без авторизации."""
    with httpx.Client(base_url=API_URL, timeout=30.0) as client:
        yield client


def _login(client: httpx.Client, email: str, password: str) -> str:
    resp = client.post("/auth/login-json", json={"email": email, "password": password})
    resp.raise_for_status()
    return resp.json()["access_token"]


@pytest.fixture()
def admin_token(http: httpx.Client) -> str:
    return _login(http, "admin@hotel.local", "Admin_2026!")


@pytest.fixture()
def manager_token(http: httpx.Client) -> str:
    return _login(http, "manager@hotel.local", "Manager_2026!")


@pytest.fixture()
def guest_token(http: httpx.Client) -> str:
    return _login(http, "ivanov@example.com", "Guest_2026!")


@pytest.fixture()
def fresh_guest(http: httpx.Client) -> dict:
    """Регистрирует уникального тестового пользователя."""
    suffix = uuid.uuid4().hex[:8]
    email = f"test_{suffix}@example.com"
    password = "Test_Pass_2026!"
    resp = http.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": f"Тест Юзер {suffix}"},
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    return {"email": email, "password": password, "token": token}


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
