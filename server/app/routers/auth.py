from fastapi import APIRouter, HTTPException, status

from app.core.database import get_connection
from app.core.security import hash_password, verify_password, create_access_token
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["Аутентификация"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: RegisterRequest):
    """Регистрация нового пользователя (гостя)."""
    async with get_connection() as conn:
        existing = await conn.fetchval(
            "SELECT id FROM users WHERE email = $1", data.email
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким email уже зарегистрирован",
            )

        pw_hash = hash_password(data.password)

        user_id = await conn.fetchval(
            """
            INSERT INTO users (email, password_hash, role)
            VALUES ($1, $2, 'guest')
            RETURNING id
            """,
            data.email, pw_hash,
        )

        await conn.execute(
            """
            INSERT INTO guest_profiles (user_id, first_name, last_name, patronymic, phone)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user_id, data.first_name, data.last_name, data.patronymic, data.phone,
        )

    token = create_access_token({"sub": str(user_id), "email": data.email, "role": "guest"})
    return TokenResponse(
        access_token=token,
        user_id=user_id,
        role="guest",
        email=data.email,
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    """Аутентификация пользователя по email и паролю."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, role, is_active FROM users WHERE email = $1",
            data.email,
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    if not row["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учётная запись заблокирована. Обратитесь к администратору.",
        )

    if not verify_password(data.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    token = create_access_token({
        "sub": str(row["id"]),
        "email": row["email"],
        "role": row["role"],
    })

    return TokenResponse(
        access_token=token,
        user_id=row["id"],
        role=row["role"],
        email=row["email"],
    )
