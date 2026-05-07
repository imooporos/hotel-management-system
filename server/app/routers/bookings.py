from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.core.database import get_connection
from app.core.security import get_current_user, require_role
from app.schemas.bookings import (
    BookingCreate, BookingResponse, BookingStatusUpdate, BookingServiceAdd,
)

router = APIRouter(prefix="/api/bookings", tags=["Бронирования"])


async def _fetch_booking(conn, booking_id: int) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT b.id, b.guest_id, b.room_id, r.room_number,
               rc.name AS category_name,
               b.check_in_date, b.check_out_date,
               (b.check_out_date - b.check_in_date) AS nights,
               b.status::TEXT AS status, b.guests_count, b.total_amount,
               b.notes, b.created_at,
               gp.first_name || ' ' || gp.last_name AS guest_name,
               u.email AS guest_email
        FROM bookings b
        JOIN rooms r ON r.id = b.room_id
        JOIN room_categories rc ON rc.id = r.category_id
        JOIN users u ON u.id = b.guest_id
        LEFT JOIN guest_profiles gp ON gp.user_id = b.guest_id
        WHERE b.id = $1
        """,
        booking_id,
    )
    if row is None:
        return None

    services = await conn.fetch(
        """
        SELECT s.id, s.name, bs.quantity, bs.price_at_booking
        FROM booking_services bs
        JOIN services s ON s.id = bs.service_id
        WHERE bs.booking_id = $1
        """,
        booking_id,
    )

    data = dict(row)
    data["services"] = [
        {"id": s["id"], "name": s["name"], "quantity": s["quantity"], "price": float(s["price_at_booking"])}
        for s in services
    ]
    return data


@router.post("/", response_model=BookingResponse, status_code=201)
async def create_booking(
    data: BookingCreate,
    current_user: dict = Depends(get_current_user),
):
    """Создание бронирования."""
    if data.check_out_date <= data.check_in_date:
        raise HTTPException(status_code=400, detail="Дата выезда должна быть позже даты заезда")

    async with get_connection() as conn:
        room = await conn.fetchrow(
            """
            SELECT r.id, rc.base_price, rc.capacity
            FROM rooms r JOIN room_categories rc ON rc.id = r.category_id
            WHERE r.id = $1 AND r.is_active = TRUE
            """,
            data.room_id,
        )
        if room is None:
            raise HTTPException(status_code=404, detail="Номер не найден или неактивен")

        if data.guests_count > room["capacity"]:
            raise HTTPException(
                status_code=400,
                detail=f"Превышена вместимость номера ({room['capacity']} чел.)",
            )

        is_free = await conn.fetchval(
            "SELECT fn_room_is_free($1, $2, $3)",
            data.room_id, data.check_in_date, data.check_out_date,
        )
        if not is_free:
            raise HTTPException(status_code=409, detail="Номер занят на выбранные даты")

        nights = (data.check_out_date - data.check_in_date).days
        total = float(room["base_price"]) * nights

        booking_id = await conn.fetchval(
            """
            INSERT INTO bookings (guest_id, room_id, check_in_date, check_out_date,
                                  guests_count, total_amount, notes)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            current_user["id"], data.room_id, data.check_in_date,
            data.check_out_date, data.guests_count, total, data.notes,
        )

        for sid in data.service_ids:
            svc = await conn.fetchrow(
                "SELECT id, price FROM services WHERE id = $1 AND is_active = TRUE", sid,
            )
            if svc:
                await conn.execute(
                    """
                    INSERT INTO booking_services (booking_id, service_id, quantity, price_at_booking)
                    VALUES ($1, $2, 1, $3)
                    """,
                    booking_id, svc["id"], svc["price"],
                )

        new_total = await conn.fetchval("SELECT fn_calculate_booking_total($1)", booking_id)
        await conn.execute(
            "UPDATE bookings SET total_amount = $1 WHERE id = $2", new_total, booking_id,
        )

        result = await _fetch_booking(conn, booking_id)

    return BookingResponse(**result)


@router.get("/my", response_model=list[BookingResponse])
async def my_bookings(
    status: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Бронирования текущего пользователя."""
    async with get_connection() as conn:
        conditions = ["b.guest_id = $1"]
        values = [current_user["id"]]
        idx = 2

        if status:
            conditions.append(f"b.status = ${idx}::booking_status")
            values.append(status)

        rows = await conn.fetch(
            f"""
            SELECT b.id, b.guest_id, b.room_id, r.room_number,
                   rc.name AS category_name,
                   b.check_in_date, b.check_out_date,
                   (b.check_out_date - b.check_in_date) AS nights,
                   b.status::TEXT AS status, b.guests_count, b.total_amount,
                   b.notes, b.created_at,
                   gp.first_name || ' ' || gp.last_name AS guest_name,
                   u.email AS guest_email
            FROM bookings b
            JOIN rooms r ON r.id = b.room_id
            JOIN room_categories rc ON rc.id = r.category_id
            JOIN users u ON u.id = b.guest_id
            LEFT JOIN guest_profiles gp ON gp.user_id = b.guest_id
            WHERE {' AND '.join(conditions)}
            ORDER BY b.created_at DESC
            """,
            *values,
        )

        result = []
        for row in rows:
            data = dict(row)
            services = await conn.fetch(
                """
                SELECT s.id, s.name, bs.quantity, bs.price_at_booking
                FROM booking_services bs
                JOIN services s ON s.id = bs.service_id
                WHERE bs.booking_id = $1
                """,
                row["id"],
            )
            data["services"] = [
                {"id": s["id"], "name": s["name"], "quantity": s["quantity"], "price": float(s["price_at_booking"])}
                for s in services
            ]
            result.append(BookingResponse(**data))

    return result


@router.get("/all", response_model=list[BookingResponse])
async def all_bookings(
    status: Optional[str] = Query(None),
    current_user: dict = Depends(require_role("admin", "manager")),
):
    """Все бронирования (для менеджера/админа)."""
    async with get_connection() as conn:
        conditions = []
        values = []
        idx = 1

        if status:
            conditions.append(f"b.status = ${idx}::booking_status")
            values.append(status)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        rows = await conn.fetch(
            f"""
            SELECT b.id, b.guest_id, b.room_id, r.room_number,
                   rc.name AS category_name,
                   b.check_in_date, b.check_out_date,
                   (b.check_out_date - b.check_in_date) AS nights,
                   b.status::TEXT AS status, b.guests_count, b.total_amount,
                   b.notes, b.created_at,
                   gp.first_name || ' ' || gp.last_name AS guest_name,
                   u.email AS guest_email
            FROM bookings b
            JOIN rooms r ON r.id = b.room_id
            JOIN room_categories rc ON rc.id = r.category_id
            JOIN users u ON u.id = b.guest_id
            LEFT JOIN guest_profiles gp ON gp.user_id = b.guest_id
            {where}
            ORDER BY b.created_at DESC
            """,
            *values,
        )

        result = []
        for row in rows:
            data = dict(row)
            services = await conn.fetch(
                """
                SELECT s.id, s.name, bs.quantity, bs.price_at_booking
                FROM booking_services bs JOIN services s ON s.id = bs.service_id
                WHERE bs.booking_id = $1
                """,
                row["id"],
            )
            data["services"] = [
                {"id": s["id"], "name": s["name"], "quantity": s["quantity"], "price": float(s["price_at_booking"])}
                for s in services
            ]
            result.append(BookingResponse(**data))

    return result


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Получение бронирования по ID."""
    async with get_connection() as conn:
        data = await _fetch_booking(conn, booking_id)

    if data is None:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")

    if current_user["role"] == "guest" and data["guest_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    return BookingResponse(**data)


@router.put("/{booking_id}/status")
async def update_booking_status(
    booking_id: int,
    data: BookingStatusUpdate,
    current_user: dict = Depends(require_role("admin", "manager")),
):
    """Обновление статуса бронирования (менеджер/админ)."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT id, status::TEXT AS status FROM bookings WHERE id = $1", booking_id,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Бронирование не найдено")

        if row["status"] == "cancelled":
            raise HTTPException(status_code=400, detail="Невозможно изменить статус отменённого бронирования")

        await conn.execute(
            "UPDATE bookings SET status = $1::booking_status, updated_at = NOW() WHERE id = $2",
            data.status, booking_id,
        )

    return {"detail": f"Статус бронирования {booking_id} изменён на {data.status}"}


@router.post("/{booking_id}/cancel")
async def cancel_booking(
    booking_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Отмена бронирования."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT id, guest_id, status::TEXT AS status FROM bookings WHERE id = $1",
            booking_id,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Бронирование не найдено")

        if current_user["role"] == "guest" and row["guest_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Доступ запрещён")

        if row["status"] in ("checked_out", "cancelled"):
            raise HTTPException(status_code=400, detail=f"Невозможно отменить бронирование в статусе {row['status']}")

        await conn.execute(
            "UPDATE bookings SET status = 'cancelled', updated_at = NOW() WHERE id = $1",
            booking_id,
        )

    return {"detail": "Бронирование отменено"}


@router.post("/{booking_id}/services")
async def add_service_to_booking(
    booking_id: int,
    data: BookingServiceAdd,
    current_user: dict = Depends(get_current_user),
):
    """Добавление услуги к бронированию."""
    async with get_connection() as conn:
        booking = await conn.fetchrow(
            "SELECT id, guest_id, status::TEXT AS status FROM bookings WHERE id = $1",
            booking_id,
        )
        if booking is None:
            raise HTTPException(status_code=404, detail="Бронирование не найдено")

        if current_user["role"] == "guest" and booking["guest_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Доступ запрещён")

        if booking["status"] in ("checked_out", "cancelled"):
            raise HTTPException(status_code=400, detail="Нельзя добавить услугу к завершённому бронированию")

        svc = await conn.fetchrow(
            "SELECT id, price FROM services WHERE id = $1 AND is_active = TRUE",
            data.service_id,
        )
        if svc is None:
            raise HTTPException(status_code=404, detail="Услуга не найдена")

        existing = await conn.fetchrow(
            "SELECT id FROM booking_services WHERE booking_id = $1 AND service_id = $2",
            booking_id, data.service_id,
        )
        if existing:
            await conn.execute(
                "UPDATE booking_services SET quantity = quantity + $1 WHERE id = $2",
                data.quantity, existing["id"],
            )
        else:
            await conn.execute(
                """
                INSERT INTO booking_services (booking_id, service_id, quantity, price_at_booking)
                VALUES ($1, $2, $3, $4)
                """,
                booking_id, data.service_id, data.quantity, svc["price"],
            )

        new_total = await conn.fetchval("SELECT fn_calculate_booking_total($1)", booking_id)
        await conn.execute(
            "UPDATE bookings SET total_amount = $1 WHERE id = $2", new_total, booking_id,
        )

    return {"detail": "Услуга добавлена к бронированию"}
