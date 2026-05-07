"""Юнит-тесты модуля core.security."""

from __future__ import annotations

import os
import time

import pytest

# для тестов JWT нужно минимально проинициализировать настройки
os.environ.setdefault("DATABASE_URL", "postgresql://x:y@localhost:5432/x")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production")

from app.core import security  # noqa: E402  (sys.path настроен в conftest)


# ---------------------------------------------------------------------------
# Юнит-тест №1
# ---------------------------------------------------------------------------


def test_password_hash_and_verify():
    """bcrypt хеш должен быть детерминированно проверяем и не равен исходному."""
    plain = "Strong_Password_2026!"
    hashed = security.hash_password(plain)

    assert hashed != plain
    assert hashed.startswith("$2b$")  # bcrypt prefix
    assert security.verify_password(plain, hashed) is True
    assert security.verify_password("wrong", hashed) is False


# ---------------------------------------------------------------------------
# Юнит-тест №2
# ---------------------------------------------------------------------------


def test_jwt_round_trip():
    """JWT, выпущенный create_access_token, должен корректно декодироваться."""
    token = security.create_access_token(user_id=42, role="manager")
    payload = security.decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "manager"
    assert payload["exp"] > int(time.time())

    # повреждённый токен должен бросать AuthError
    with pytest.raises(security.AuthError):
        security.decode_token(token + "broken")
