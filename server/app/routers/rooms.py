from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import get_connection
from app.core.security import get_current_user, require_role
from app.schemas.rooms import (
    RoomResponse, RoomCreate, RoomUpdate,
    RoomCategoryResponse, RoomCategoryCreate, RoomCategoryUpdate,
    AmenityResponse,
)

router = APIRouter(prefix="/api/rooms", tags=["Номера"])


@router.get("/categories", response_model=list[RoomCategoryResponse])
async def list_categories():
    """Список категорий номеров."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            "SELECT id, name, description, base_price, capacity FROM room_categories ORDER BY base_price"
        )
    return [RoomCategoryResponse(**dict(r)) for r in rows]


@router.post("/categories", response_model=RoomCategoryResponse, status_code=201)
async def create_category(
    data: RoomCategoryCreate,
    _: dict = Depends(require_role("admin")),
):
    """Создание категории номеров (только админ)."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO room_categories (name, description, base_price, capacity)
            VALUES ($1, $2, $3, $4)
            RETURNING id, name, description, base_price, capacity
            """,
            data.name, data.description, data.base_price, data.capacity,
        )
    return RoomCategoryResponse(**dict(row))


@router.put("/categories/{cat_id}", response_model=RoomCategoryResponse)
async def update_category(
    cat_id: int,
    data: RoomCategoryUpdate,
    _: dict = Depends(require_role("admin")),
):
    """Обновление категории номеров (только админ)."""
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")

    set_parts = []
    values = []
    for i, (key, val) in enumerate(updates.items(), 1):
        set_parts.append(f"{key} = ${i}")
        values.append(val)

    values.append(cat_id)
    query = f"""
        UPDATE room_categories SET {', '.join(set_parts)}
        WHERE id = ${len(values)}
        RETURNING id, name, description, base_price, capacity
    """

    async with get_connection() as conn:
        row = await conn.fetchrow(query, *values)
        if row is None:
            raise HTTPException(status_code=404, detail="Категория не найдена")
    return RoomCategoryResponse(**dict(row))


@router.get("/amenities", response_model=list[AmenityResponse])
async def list_amenities():
    """Список всех удобств."""
    async with get_connection() as conn:
        rows = await conn.fetch("SELECT id, name, icon FROM amenities ORDER BY name")
    return [AmenityResponse(**dict(r)) for r in rows]


@router.get("/", response_model=list[RoomResponse])
async def list_rooms(
    check_in: Optional[date] = Query(None),
    check_out: Optional[date] = Query(None),
    category_id: Optional[int] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    capacity: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
):
    """Список номеров с фильтрами (каталог)."""
    conditions = ["r.is_active = TRUE"]
    values = []
    idx = 1

    if category_id is not None:
        conditions.append(f"r.category_id = ${idx}")
        values.append(category_id)
        idx += 1
    if min_price is not None:
        conditions.append(f"rc.base_price >= ${idx}")
        values.append(min_price)
        idx += 1
    if max_price is not None:
        conditions.append(f"rc.base_price <= ${idx}")
        values.append(max_price)
        idx += 1
    if capacity is not None:
        conditions.append(f"rc.capacity >= ${idx}")
        values.append(capacity)
        idx += 1
    if status is not None:
        conditions.append(f"r.status = ${idx}::room_status")
        values.append(status)
        idx += 1

    where_clause = " AND ".join(conditions)

    async with get_connection() as conn:
        rows = await conn.fetch(
            f"""
            SELECT r.id, r.room_number, r.category_id, rc.name AS category_name,
                   rc.base_price, rc.capacity, r.floor, r.status::TEXT AS status,
                   r.description, r.is_active
            FROM rooms r
            JOIN room_categories rc ON rc.id = r.category_id
            WHERE {where_clause}
            ORDER BY r.room_number
            """,
            *values,
        )

        result = []
        for r in rows:
            room_data = dict(r)

            amenity_rows = await conn.fetch(
                """
                SELECT a.id, a.name, a.icon
                FROM room_amenities ra JOIN amenities a ON a.id = ra.amenity_id
                WHERE ra.room_id = $1 ORDER BY a.name
                """,
                r["id"],
            )
            room_data["amenities"] = [AmenityResponse(**dict(a)) for a in amenity_rows]

            is_free = True
            if check_in and check_out:
                overlap = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM bookings b
                        WHERE b.room_id = $1
                          AND b.status NOT IN ('cancelled', 'checked_out')
                          AND daterange(b.check_in_date, b.check_out_date, '[)')
                              && daterange($2, $3, '[)')
                    )
                    """,
                    r["id"], check_in, check_out,
                )
                is_free = not overlap
            elif r["status"] != "available":
                is_free = False

            room_data["is_free_today"] = is_free
            result.append(RoomResponse(**room_data))

    return result


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(room_id: int):
    """Детальная информация о номере."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT r.id, r.room_number, r.category_id, rc.name AS category_name,
                   rc.base_price, rc.capacity, r.floor, r.status::TEXT AS status,
                   r.description, r.is_active
            FROM rooms r
            JOIN room_categories rc ON rc.id = r.category_id
            WHERE r.id = $1
            """,
            room_id,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Номер не найден")

        amenity_rows = await conn.fetch(
            """
            SELECT a.id, a.name, a.icon
            FROM room_amenities ra JOIN amenities a ON a.id = ra.amenity_id
            WHERE ra.room_id = $1 ORDER BY a.name
            """,
            room_id,
        )

    room_data = dict(row)
    room_data["amenities"] = [AmenityResponse(**dict(a)) for a in amenity_rows]
    return RoomResponse(**room_data)


@router.post("/", response_model=RoomResponse, status_code=201)
async def create_room(
    data: RoomCreate,
    _: dict = Depends(require_role("admin")),
):
    """Создание номера (только админ)."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO rooms (room_number, category_id, floor, description)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            data.room_number, data.category_id, data.floor, data.description,
        )

    return await get_room(row["id"])


@router.put("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: int,
    data: RoomUpdate,
    _: dict = Depends(require_role("admin", "manager")),
):
    """Обновление номера (админ или менеджер)."""
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")

    set_parts = []
    values = []
    for i, (key, val) in enumerate(updates.items(), 1):
        if key == "status":
            set_parts.append(f"{key} = ${i}::room_status")
        else:
            set_parts.append(f"{key} = ${i}")
        values.append(val)

    values.append(room_id)
    query = f"""
        UPDATE rooms SET {', '.join(set_parts)}, updated_at = NOW()
        WHERE id = ${len(values)}
    """

    async with get_connection() as conn:
        result = await conn.execute(query, *values)
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Номер не найден")

    return await get_room(room_id)


@router.put("/{room_id}/amenities")
async def set_room_amenities(
    room_id: int,
    amenity_ids: list[int],
    _: dict = Depends(require_role("admin")),
):
    """Установить список удобств номера (только админ)."""
    async with get_connection() as conn:
        exists = await conn.fetchval("SELECT 1 FROM rooms WHERE id = $1", room_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Номер не найден")

        await conn.execute("DELETE FROM room_amenities WHERE room_id = $1", room_id)
        for aid in amenity_ids:
            await conn.execute(
                "INSERT INTO room_amenities (room_id, amenity_id) VALUES ($1, $2)",
                room_id, aid,
            )

    return {"detail": f"Удобства номера {room_id} обновлены"}
