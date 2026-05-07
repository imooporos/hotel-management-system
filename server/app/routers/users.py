from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_connection
from app.core.security import get_current_user, require_role, hash_password
from app.schemas.users import (
    ProfileResponse, ProfileUpdate, UserListResponse,
    UserRoleUpdate, UserBlockUpdate,
)

router = APIRouter(prefix="/api/users", tags=["Пользователи"])


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Получение профиля текущего пользователя."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT gp.*, u.email, u.role, u.created_at AS user_created_at
            FROM guest_profiles gp
            JOIN users u ON u.id = gp.user_id
            WHERE gp.user_id = $1
            """,
            current_user["id"],
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    return ProfileResponse(
        id=row["id"],
        user_id=row["user_id"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        patronymic=row["patronymic"],
        phone=row["phone"],
        passport_series=row["passport_series"],
        passport_number=row["passport_number"],
        birth_date=row["birth_date"],
        email=row["email"],
        role=row["role"],
        created_at=row["user_created_at"],
    )


@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    data: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Обновление профиля текущего пользователя."""
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")

    set_parts = []
    values = []
    idx = 1
    for key, val in updates.items():
        set_parts.append(f"{key} = ${idx}")
        values.append(val)
        idx += 1

    values.append(current_user["id"])
    query = f"""
        UPDATE guest_profiles
        SET {', '.join(set_parts)}, updated_at = NOW()
        WHERE user_id = ${idx}
    """

    async with get_connection() as conn:
        await conn.execute(query, *values)

    return await get_my_profile(current_user)


@router.put("/me/password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: dict = Depends(get_current_user),
):
    """Смена пароля текущего пользователя."""
    from app.core.security import verify_password

    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT password_hash FROM users WHERE id = $1",
            current_user["id"],
        )
        if not verify_password(old_password, row["password_hash"]):
            raise HTTPException(status_code=400, detail="Неверный текущий пароль")

        new_hash = hash_password(new_password)
        await conn.execute(
            "UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2",
            new_hash, current_user["id"],
        )

    return {"detail": "Пароль успешно изменён"}


# ─── Админские эндпоинты ─────────────────────────────────────────────────────

@router.get("/", response_model=list[UserListResponse])
async def list_users(
    current_user: dict = Depends(require_role("admin", "manager")),
):
    """Список всех пользователей (для админа/менеджера)."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT u.id, u.email, u.role, u.is_active, u.created_at,
                   gp.first_name, gp.last_name
            FROM users u
            LEFT JOIN guest_profiles gp ON gp.user_id = u.id
            ORDER BY u.created_at DESC
            """
        )

    return [
        UserListResponse(
            id=r["id"], email=r["email"], role=r["role"],
            is_active=r["is_active"], first_name=r["first_name"],
            last_name=r["last_name"], created_at=r["created_at"],
        )
        for r in rows
    ]


@router.put("/{user_id}/role")
async def update_user_role(
    user_id: int,
    data: UserRoleUpdate,
    current_user: dict = Depends(require_role("admin")),
):
    """Изменение роли пользователя (только админ)."""
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Нельзя изменить свою роль")

    async with get_connection() as conn:
        result = await conn.execute(
            "UPDATE users SET role = $1, updated_at = NOW() WHERE id = $2",
            data.role, user_id,
        )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Пользователь не найден")

    return {"detail": f"Роль пользователя {user_id} изменена на {data.role}"}


@router.put("/{user_id}/block")
async def block_user(
    user_id: int,
    data: UserBlockUpdate,
    current_user: dict = Depends(require_role("admin")),
):
    """Блокировка/разблокировка пользователя (только админ)."""
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Нельзя заблокировать себя")

    async with get_connection() as conn:
        result = await conn.execute(
            "UPDATE users SET is_active = $1, updated_at = NOW() WHERE id = $2",
            data.is_active, user_id,
        )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Пользователь не найден")

    action = "разблокирован" if data.is_active else "заблокирован"
    return {"detail": f"Пользователь {user_id} {action}"}
