"""Аутентификация: bcrypt, JWT, RBAC dependency."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .config import settings
from .db import acquire_for_user
from .errors import AuthError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# Пароли
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """bcrypt-хэширование пароля. cost=12."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Постоянное по времени сравнение пароля с хэшем."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_access_token(*, user_id: int, role: str) -> str:
    """Создаёт JWT с user_id и ролью."""
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Расшифровывает JWT. Бросает AuthError при ошибке."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Срок действия токена истёк") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Неверный токен") from exc


# ---------------------------------------------------------------------------
# Зависимости FastAPI
# ---------------------------------------------------------------------------

class CurrentUser:
    """Облегчённое представление текущего пользователя."""

    __slots__ = ("user_id", "role", "email", "full_name")

    def __init__(self, user_id: int, role: str, email: str, full_name: str) -> None:
        self.user_id = user_id
        self.role = role
        self.email = email
        self.full_name = full_name


async def get_current_user(token: str | None = Depends(oauth2_scheme)) -> CurrentUser:
    """Извлекает пользователя из JWT, проверяет, что он активен."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise AuthError("Некорректный токен") from exc

    async with acquire_for_user(user_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT u.user_id, u.email, u.full_name, u.is_active, r.code AS role
              FROM users u
              JOIN roles r ON r.role_id = u.role_id
             WHERE u.user_id = $1
            """,
            user_id,
        )

    if row is None or not row["is_active"]:
        raise AuthError("Учётная запись не найдена или заблокирована")

    return CurrentUser(
        user_id=row["user_id"],
        role=row["role"],
        email=row["email"],
        full_name=row["full_name"],
    )


def require_role(*allowed: str):
    """
    Зависимость, которая разрешает запрос только пользователям с указанными ролями.
    Использование:  @router.get(..., dependencies=[Depends(require_role("admin"))])
    """

    async def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Доступ только для ролей: {', '.join(allowed)}",
            )
        return user

    return dependency
