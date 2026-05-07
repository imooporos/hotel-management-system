"""Эндпоинты управления пользователями (для админа)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..core.db import acquire_for_user
from ..core.errors import NotFoundError
from ..core.security import CurrentUser, get_current_user, require_role

router = APIRouter(prefix="/users", tags=["users"])


class UserDTO(BaseModel):
    user_id: int
    email: str
    full_name: str
    phone: str | None = None
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserUpdateRequest(BaseModel):
    role_code: str | None = None
    is_active: bool | None = None


@router.get(
    "",
    response_model=list[UserDTO],
    dependencies=[Depends(require_role("admin"))],
)
async def list_users(user: CurrentUser = Depends(get_current_user)) -> list[UserDTO]:
    async with acquire_for_user(user.user_id) as conn:
        rows = await conn.fetch(
            """
            SELECT u.user_id, u.email, u.full_name, u.phone,
                   r.code AS role, u.is_active, u.created_at, u.last_login_at
              FROM users u
              JOIN roles r ON r.role_id = u.role_id
             ORDER BY u.user_id
            """
        )
    return [UserDTO(**dict(r)) for r in rows]


@router.patch(
    "/{user_id}",
    response_model=UserDTO,
    dependencies=[Depends(require_role("admin"))],
)
async def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> UserDTO:
    sets: list[str] = []
    args: list = []
    if payload.role_code is not None:
        async with acquire_for_user(user.user_id) as conn:
            role_id = await conn.fetchval(
                "SELECT role_id FROM roles WHERE code = $1", payload.role_code
            )
        if role_id is None:
            raise NotFoundError(f"Роль {payload.role_code} не найдена")
        args.append(role_id)
        sets.append(f"role_id = ${len(args)}")
    if payload.is_active is not None:
        args.append(payload.is_active)
        sets.append(f"is_active = ${len(args)}")

    if not sets:
        return await _fetch_user(user, user_id)

    args.append(user_id)
    async with acquire_for_user(user.user_id) as conn:
        await conn.execute(
            f"UPDATE users SET {', '.join(sets)} WHERE user_id = ${len(args)}", *args
        )
    return await _fetch_user(user, user_id)


async def _fetch_user(actor: CurrentUser, user_id: int) -> UserDTO:
    async with acquire_for_user(actor.user_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT u.user_id, u.email, u.full_name, u.phone,
                   r.code AS role, u.is_active, u.created_at, u.last_login_at
              FROM users u
              JOIN roles r ON r.role_id = u.role_id
             WHERE u.user_id = $1
            """,
            user_id,
        )
    if row is None:
        raise NotFoundError(f"Пользователь {user_id} не найден")
    return UserDTO(**dict(row))
