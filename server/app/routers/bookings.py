"""Эндпоинты бронирований."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..core.db import acquire_for_user
from ..core.errors import ConflictError, NotFoundError
from ..core.security import CurrentUser, get_current_user, require_role
from ..schemas.bookings import (
    BookingCreateRequest,
    BookingDetailResponse,
    BookingResponse,
    BookingStatusUpdateRequest,
    CalculateRequest,
    CalculateResponse,
)
from ..services.pdf import generate_booking_receipt

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("/me", response_model=list[BookingResponse])
async def my_bookings(user: CurrentUser = Depends(get_current_user)) -> list[BookingResponse]:
    """Бронирования текущего пользователя."""
    async with acquire_for_user(user.user_id) as conn:
        rows = await conn.fetch("SELECT * FROM sp_get_user_bookings($1)", user.user_id)
    return [BookingResponse(**dict(r)) for r in rows]


@router.get(
    "",
    response_model=list[BookingDetailResponse],
    dependencies=[Depends(require_role("manager", "admin"))],
)
async def list_all_bookings(user: CurrentUser = Depends(get_current_user)) -> list[BookingDetailResponse]:
    async with acquire_for_user(user.user_id) as conn:
        rows = await conn.fetch(
            "SELECT * FROM v_guest_bookings ORDER BY check_in DESC LIMIT 200"
        )
    return [BookingDetailResponse(**dict(r)) for r in rows]


@router.post("/calculate", response_model=CalculateResponse)
async def calculate(payload: CalculateRequest) -> CalculateResponse:
    """Вычисляет стоимость без создания брони, проверяет свободу."""
    nights = (payload.check_out - payload.check_in).days
    async with acquire_for_user(None) as conn:
        is_free = await conn.fetchval(
            "SELECT fn_room_is_free($1, $2, $3)",
            payload.room_id,
            payload.check_in,
            payload.check_out,
        )
        total = await conn.fetchval(
            "SELECT fn_calculate_booking_total($1, $2, $3, $4::int[])",
            payload.room_id,
            payload.check_in,
            payload.check_out,
            payload.service_ids or None,
        )
    return CalculateResponse(total_price=total, nights=nights, is_room_free=bool(is_free))


@router.post("", response_model=BookingResponse, status_code=201)
async def create_booking(
    payload: BookingCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> BookingResponse:
    async with acquire_for_user(user.user_id) as conn:
        # Используем функциональную обёртку fn_create_booking,
        # которая под капотом вызывает sp_create_booking.
        row = await conn.fetchrow(
            """
            SELECT booking_id, total_price
              FROM fn_create_booking($1, $2, $3, $4, $5::smallint, $6::int[])
            """,
            user.user_id,
            payload.room_id,
            payload.check_in,
            payload.check_out,
            payload.guests_count,
            payload.service_ids or None,
        )
        if row is None:
            raise ConflictError("Не удалось создать бронирование")
        booking_id = row["booking_id"]

        # пишем заметку (не передаётся в процедуру)
        if payload.notes:
            await conn.execute(
                "UPDATE bookings SET notes = $1 WHERE booking_id = $2",
                payload.notes,
                booking_id,
            )

        full = await conn.fetchrow(
            "SELECT * FROM v_guest_bookings WHERE booking_id = $1", booking_id
        )
    assert full is not None
    return BookingResponse(**{k: full[k] for k in BookingResponse.model_fields})


@router.patch(
    "/{booking_id}/status",
    response_model=BookingResponse,
    dependencies=[Depends(require_role("manager", "admin"))],
)
async def update_status(
    booking_id: int,
    payload: BookingStatusUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> BookingResponse:
    async with acquire_for_user(user.user_id) as conn:
        await conn.execute(
            "CALL sp_update_booking_status($1, $2::booking_status, $3)",
            booking_id,
            payload.status,
            user.user_id,
        )
        row = await conn.fetchrow(
            "SELECT * FROM v_guest_bookings WHERE booking_id = $1", booking_id
        )
    if row is None:
        raise NotFoundError(f"Бронирование {booking_id} не найдено")
    return BookingResponse(**{k: row[k] for k in BookingResponse.model_fields})


@router.delete("/{booking_id}", response_model=BookingResponse)
async def cancel_booking(
    booking_id: int, user: CurrentUser = Depends(get_current_user)
) -> BookingResponse:
    """Гость может отменять только свои бронирования; персонал — любые."""
    async with acquire_for_user(user.user_id) as conn:
        owner = await conn.fetchval(
            "SELECT user_id FROM bookings WHERE booking_id = $1", booking_id
        )
        if owner is None:
            raise NotFoundError(f"Бронирование {booking_id} не найдено")
        if user.role == "guest" and owner != user.user_id:
            raise NotFoundError(f"Бронирование {booking_id} не найдено")

        await conn.execute(
            "CALL sp_cancel_booking($1, $2)", booking_id, user.user_id
        )
        row = await conn.fetchrow(
            "SELECT * FROM v_guest_bookings WHERE booking_id = $1", booking_id
        )
    assert row is not None
    return BookingResponse(**{k: row[k] for k in BookingResponse.model_fields})


@router.get("/{booking_id}/receipt.pdf")
async def get_receipt(booking_id: int, user: CurrentUser = Depends(get_current_user)):
    """Печатный бланк заказа в PDF."""
    async with acquire_for_user(user.user_id) as conn:
        row = await conn.fetchrow(
            "SELECT * FROM v_guest_bookings WHERE booking_id = $1", booking_id
        )
        if row is None:
            raise NotFoundError(f"Бронирование {booking_id} не найдено")
        if user.role == "guest" and row["user_id"] != user.user_id:
            raise NotFoundError(f"Бронирование {booking_id} не найдено")

        services = await conn.fetch(
            """
            SELECT s.title, bs.quantity, bs.unit_price
              FROM booking_services bs
              JOIN services s ON s.service_id = bs.service_id
             WHERE bs.booking_id = $1
            """,
            booking_id,
        )

    pdf_bytes = generate_booking_receipt(dict(row), [dict(s) for s in services])
    headers = {"Content-Disposition": f'inline; filename="booking_{booking_id}.pdf"'}
    return StreamingResponse(iter([pdf_bytes]), media_type="application/pdf", headers=headers)
