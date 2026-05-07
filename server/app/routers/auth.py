"""Эндпоинты аутентификации и личного кабинета."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from ..core.config import settings
from ..core.db import acquire_for_user
from ..core.errors import AuthError, NotFoundError
from ..core.security import (
    CurrentUser,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from ..schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest) -> TokenResponse:
    """Регистрация нового гостя. Сразу возвращает JWT."""
    pwd_hash = hash_password(payload.password)
    async with acquire_for_user(None) as conn:
        # вызов хранимой процедуры регистрации
        await conn.execute(
            "CALL sp_register_user($1, $2, $3, $4, 'guest')",
            payload.email,
            pwd_hash,
            payload.full_name,
            payload.phone,
        )
        row = await conn.fetchrow(
            """
            SELECT u.user_id, r.code AS role
              FROM users u
              JOIN roles r ON r.role_id = u.role_id
             WHERE u.email = $1
            """,
            payload.email,
        )
    assert row is not None
    token = create_access_token(user_id=row["user_id"], role=row["role"])
    return TokenResponse(access_token=token, expires_in=settings.jwt_expire_minutes * 60)


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    """OAuth2 password flow. username = email."""
    return await _authenticate(form.username, form.password)


@router.post("/login-json", response_model=TokenResponse)
async def login_json(payload: LoginRequest) -> TokenResponse:
    """JSON-вариант логина (для клиентов, которым неудобен form-data)."""
    return await _authenticate(payload.email, payload.password)


async def _authenticate(email: str, password: str) -> TokenResponse:
    async with acquire_for_user(None) as conn:
        row = await conn.fetchrow(
            """
            SELECT u.user_id, u.password_hash, u.is_active, r.code AS role
              FROM users u
              JOIN roles r ON r.role_id = u.role_id
             WHERE lower(u.email) = lower($1)
            """,
            email,
        )
        if row is None or not row["is_active"] or not verify_password(password, row["password_hash"]):
            raise AuthError("Неверный email или пароль")

        await conn.execute(
            "UPDATE users SET last_login_at = now() WHERE user_id = $1",
            row["user_id"],
        )

    token = create_access_token(user_id=row["user_id"], role=row["role"])
    return TokenResponse(access_token=token, expires_in=settings.jwt_expire_minutes * 60)


@router.get("/me", response_model=CurrentUserResponse)
async def me(user: CurrentUser = Depends(get_current_user)) -> CurrentUserResponse:
    async with acquire_for_user(user.user_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT u.user_id, u.email, u.full_name, u.phone, u.is_active, r.code AS role
              FROM users u
              JOIN roles r ON r.role_id = u.role_id
             WHERE u.user_id = $1
            """,
            user.user_id,
        )
    if row is None:
        raise NotFoundError("Пользователь не найден")
    return CurrentUserResponse(**dict(row))


@router.patch("/me", response_model=CurrentUserResponse)
async def update_profile(
    payload: UpdateProfileRequest,
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUserResponse:
    """Обновляет данные пользователя и его guest_profile."""
    async with acquire_for_user(user.user_id) as conn:
        async with conn.transaction():
            updates = []
            args: list = []
            if payload.full_name is not None:
                args.append(payload.full_name)
                updates.append(f"full_name = ${len(args)}")
            if payload.phone is not None:
                args.append(payload.phone)
                updates.append(f"phone = ${len(args)}")
            if updates:
                args.append(user.user_id)
                await conn.execute(
                    f"UPDATE users SET {', '.join(updates)} WHERE user_id = ${len(args)}",
                    *args,
                )

            # Обновим профиль (только если он есть, например для guest)
            if any(
                getattr(payload, f) is not None
                for f in ("passport_series", "passport_number", "passport_issued", "birth_date", "address")
            ):
                # ensure profile exists
                await conn.execute(
                    "INSERT INTO guest_profiles (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
                    user.user_id,
                )
                from datetime import date as _date

                birth_date_value = None
                if payload.birth_date:
                    try:
                        birth_date_value = _date.fromisoformat(payload.birth_date)
                    except ValueError as exc:
                        raise AuthError("Дата рождения должна быть в формате YYYY-MM-DD") from exc

                await conn.execute(
                    """
                    UPDATE guest_profiles
                       SET passport_series = COALESCE($2, passport_series),
                           passport_number = COALESCE($3, passport_number),
                           passport_issued = COALESCE($4, passport_issued),
                           birth_date      = COALESCE($5, birth_date),
                           address         = COALESCE($6, address)
                     WHERE user_id = $1
                    """,
                    user.user_id,
                    payload.passport_series,
                    payload.passport_number,
                    payload.passport_issued,
                    birth_date_value,
                    payload.address,
                )

        row = await conn.fetchrow(
            """
            SELECT u.user_id, u.email, u.full_name, u.phone, u.is_active, r.code AS role
              FROM users u
              JOIN roles r ON r.role_id = u.role_id
             WHERE u.user_id = $1
            """,
            user.user_id,
        )
    assert row is not None
    return CurrentUserResponse(**dict(row))
