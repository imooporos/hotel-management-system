"""Эндпоинты каталога номеров и категорий."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query

from ..core.db import acquire_for_user
from ..core.errors import NotFoundError
from ..core.security import CurrentUser, get_current_user, require_role
from ..schemas.rooms import (
    CategoryDTO,
    RoomAvailability,
    RoomCard,
    RoomCreateRequest,
    RoomUpdateRequest,
    ServiceCreateRequest,
    ServiceDTO,
)

router = APIRouter(tags=["rooms"])


# ---------------------------------------------------------------------------
# Категории
# ---------------------------------------------------------------------------


@router.get("/categories", response_model=list[CategoryDTO])
async def list_categories() -> list[CategoryDTO]:
    async with acquire_for_user(None) as conn:
        rows = await conn.fetch(
            "SELECT category_id, code, title, description, base_price, capacity "
            "FROM room_categories ORDER BY base_price"
        )
    return [CategoryDTO(**dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Номера
# ---------------------------------------------------------------------------


@router.get("/rooms", response_model=list[RoomCard])
async def list_rooms(
    category_id: int | None = Query(default=None),
    min_price: Decimal | None = Query(default=None),
    max_price: Decimal | None = Query(default=None),
    capacity_min: int | None = Query(default=None, ge=1, le=6),
    free_from: date | None = Query(default=None, description="Дата заезда для проверки свободы"),
    free_to: date | None = Query(default=None, description="Дата выезда для проверки свободы"),
) -> list[RoomCard]:
    """
    Каталог номеров. Если переданы free_from / free_to — фильтрует только свободные
    в указанный диапазон (используя fn_room_is_free).
    """
    where = ["is_active = TRUE"]
    args: list = []

    if category_id is not None:
        args.append(category_id)
        where.append(f"category_id = ${len(args)}")

    if min_price is not None:
        args.append(min_price)
        where.append(f"price_per_night >= ${len(args)}")

    if max_price is not None:
        args.append(max_price)
        where.append(f"price_per_night <= ${len(args)}")

    if capacity_min is not None:
        args.append(capacity_min)
        where.append(f"capacity >= ${len(args)}")

    sql = (
        "SELECT room_id, room_number, floor, category_id, category_code, category_title, "
        "       capacity, price_per_night, status, description, is_active, amenities "
        "  FROM v_room_availability"
        " WHERE " + " AND ".join(where) +
        " ORDER BY floor, room_number"
    )

    async with acquire_for_user(None) as conn:
        rows = await conn.fetch(sql, *args)

        if free_from and free_to:
            # отфильтруем по доступности через функцию БД
            free_rooms: list[dict] = []
            for r in rows:
                is_free = await conn.fetchval(
                    "SELECT fn_room_is_free($1, $2, $3)", r["room_id"], free_from, free_to
                )
                if is_free:
                    free_rooms.append(dict(r))
            return [RoomCard(**r) for r in free_rooms]

    return [RoomCard(**dict(r)) for r in rows]


@router.get("/rooms/{room_id}", response_model=RoomCard)
async def get_room(room_id: int) -> RoomCard:
    async with acquire_for_user(None) as conn:
        row = await conn.fetchrow(
            "SELECT room_id, room_number, floor, category_id, category_code, category_title, "
            "       capacity, price_per_night, status, description, is_active, amenities "
            "  FROM v_room_availability WHERE room_id = $1",
            room_id,
        )
    if row is None:
        raise NotFoundError(f"Номер с id={room_id} не найден")
    return RoomCard(**dict(row))


@router.get("/rooms/{room_id}/availability", response_model=RoomAvailability)
async def check_availability(room_id: int, check_in: date, check_out: date) -> RoomAvailability:
    async with acquire_for_user(None) as conn:
        is_free = await conn.fetchval(
            "SELECT fn_room_is_free($1, $2, $3)", room_id, check_in, check_out
        )
    return RoomAvailability(
        room_id=room_id, is_free=bool(is_free), check_in=check_in, check_out=check_out
    )


@router.post(
    "/rooms",
    response_model=RoomCard,
    status_code=201,
    dependencies=[Depends(require_role("admin"))],
)
async def create_room(payload: RoomCreateRequest, user: CurrentUser = Depends(get_current_user)) -> RoomCard:
    async with acquire_for_user(user.user_id) as conn:
        room_id = await conn.fetchval(
            """
            INSERT INTO rooms (room_number, floor, category_id, price_modifier, description)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING room_id
            """,
            payload.room_number,
            payload.floor,
            payload.category_id,
            payload.price_modifier,
            payload.description,
        )
        row = await conn.fetchrow(
            "SELECT * FROM v_room_availability WHERE room_id = $1", room_id
        )
    assert row is not None
    return RoomCard(**dict(row))


@router.patch(
    "/rooms/{room_id}",
    response_model=RoomCard,
    dependencies=[Depends(require_role("admin", "manager"))],
)
async def update_room(
    room_id: int,
    payload: RoomUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> RoomCard:
    fields_map = {
        "room_number": payload.room_number,
        "floor": payload.floor,
        "category_id": payload.category_id,
        "price_modifier": payload.price_modifier,
        "description": payload.description,
        "status": payload.status,
        "is_active": payload.is_active,
    }
    updates = [(k, v) for k, v in fields_map.items() if v is not None]
    if not updates:
        return await get_room(room_id)

    sets = []
    args: list = []
    for k, v in updates:
        args.append(v)
        sets.append(f"{k} = ${len(args)}")
    args.append(room_id)

    async with acquire_for_user(user.user_id) as conn:
        await conn.execute(
            f"UPDATE rooms SET {', '.join(sets)} WHERE room_id = ${len(args)}",
            *args,
        )
        row = await conn.fetchrow(
            "SELECT * FROM v_room_availability WHERE room_id = $1", room_id
        )
    if row is None:
        raise NotFoundError(f"Номер с id={room_id} не найден")
    return RoomCard(**dict(row))


@router.delete(
    "/rooms/{room_id}", status_code=204, dependencies=[Depends(require_role("admin"))]
)
async def delete_room(room_id: int, user: CurrentUser = Depends(get_current_user)) -> None:
    """Soft-delete номера: помечает is_active = FALSE."""
    async with acquire_for_user(user.user_id) as conn:
        result = await conn.execute(
            "UPDATE rooms SET is_active = FALSE WHERE room_id = $1", room_id
        )
    if result.endswith(" 0"):
        raise NotFoundError(f"Номер с id={room_id} не найден")


# ---------------------------------------------------------------------------
# Услуги
# ---------------------------------------------------------------------------


@router.get("/services", response_model=list[ServiceDTO])
async def list_services() -> list[ServiceDTO]:
    async with acquire_for_user(None) as conn:
        rows = await conn.fetch(
            "SELECT service_id, code, title, description, price, is_active "
            "FROM services ORDER BY title"
        )
    return [ServiceDTO(**dict(r)) for r in rows]


@router.post(
    "/services",
    response_model=ServiceDTO,
    status_code=201,
    dependencies=[Depends(require_role("admin"))],
)
async def create_service(payload: ServiceCreateRequest, user: CurrentUser = Depends(get_current_user)) -> ServiceDTO:
    async with acquire_for_user(user.user_id) as conn:
        sid = await conn.fetchval(
            """
            INSERT INTO services (code, title, description, price)
            VALUES ($1, $2, $3, $4)
            RETURNING service_id
            """,
            payload.code,
            payload.title,
            payload.description,
            payload.price,
        )
        row = await conn.fetchrow(
            "SELECT service_id, code, title, description, price, is_active "
            "FROM services WHERE service_id = $1",
            sid,
        )
    assert row is not None
    return ServiceDTO(**dict(row))
