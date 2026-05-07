from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.database import get_connection
from app.core.security import require_role
from app.schemas.reports import RevenueByCategory, OccupancyReport, AuditLogEntry

router = APIRouter(prefix="/api/reports", tags=["Отчёты"])


@router.get("/revenue", response_model=list[RevenueByCategory])
async def revenue_by_category(
    _: dict = Depends(require_role("admin", "manager")),
):
    """Выручка по категориям номеров (из представления v_revenue_by_category)."""
    async with get_connection() as conn:
        rows = await conn.fetch("SELECT * FROM v_revenue_by_category")

    return [
        RevenueByCategory(
            category_id=r["category_id"],
            category_name=r["category_name"],
            total_bookings=r["total_bookings"],
            total_revenue=float(r["total_revenue"]),
            avg_revenue_per_booking=float(r["avg_revenue_per_booking"]),
            avg_nights=float(r["avg_nights"]),
        )
        for r in rows
    ]


@router.get("/occupancy", response_model=OccupancyReport)
async def occupancy_rate(
    start_date: date = Query(...),
    end_date: date = Query(...),
    category_id: Optional[int] = Query(None),
    _: dict = Depends(require_role("admin", "manager")),
):
    """Загрузка номерного фонда за период (из функции fn_occupancy_rate)."""
    async with get_connection() as conn:
        rate = await conn.fetchval(
            "SELECT fn_occupancy_rate($1, $2, $3)",
            start_date, end_date, category_id,
        )

        cat_name = None
        if category_id:
            cat_name = await conn.fetchval(
                "SELECT name FROM room_categories WHERE id = $1", category_id,
            )

    return OccupancyReport(
        start_date=start_date,
        end_date=end_date,
        occupancy_rate=float(rate) if rate else 0.0,
        category_id=category_id,
        category_name=cat_name,
    )


@router.get("/audit", response_model=list[AuditLogEntry])
async def audit_log(
    limit: int = Query(50, ge=1, le=500),
    _: dict = Depends(require_role("admin")),
):
    """Журнал аудита (только админ)."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT id, table_name, record_id, action,
                   old_data::TEXT, new_data::TEXT,
                   changed_by, changed_at
            FROM audit_log
            ORDER BY changed_at DESC
            LIMIT $1
            """,
            limit,
        )

    import json
    result = []
    for r in rows:
        result.append(AuditLogEntry(
            id=r["id"],
            table_name=r["table_name"],
            record_id=r["record_id"],
            action=r["action"],
            old_data=json.loads(r["old_data"]) if r["old_data"] else None,
            new_data=json.loads(r["new_data"]) if r["new_data"] else None,
            changed_by=r["changed_by"],
            changed_at=str(r["changed_at"]),
        ))
    return result


@router.get("/booking/{booking_id}/pdf")
async def booking_pdf(
    booking_id: int,
    _: dict = Depends(require_role("admin", "manager", "guest")),
):
    """Генерация PDF-бланка заказа для бронирования."""
    from app.services.pdf_generator import generate_booking_pdf

    async with get_connection() as conn:
        booking = await conn.fetchrow(
            """
            SELECT b.*, r.room_number, rc.name AS category_name, rc.base_price,
                   gp.first_name, gp.last_name, gp.patronymic, gp.phone,
                   gp.passport_series, gp.passport_number,
                   u.email
            FROM bookings b
            JOIN rooms r ON r.id = b.room_id
            JOIN room_categories rc ON rc.id = r.category_id
            JOIN users u ON u.id = b.guest_id
            LEFT JOIN guest_profiles gp ON gp.user_id = b.guest_id
            WHERE b.id = $1
            """,
            booking_id,
        )

        if booking is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Бронирование не найдено")

        services = await conn.fetch(
            """
            SELECT s.name, bs.quantity, bs.price_at_booking
            FROM booking_services bs
            JOIN services s ON s.id = bs.service_id
            WHERE bs.booking_id = $1
            """,
            booking_id,
        )

    pdf_bytes = generate_booking_pdf(dict(booking), [dict(s) for s in services])

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=booking_{booking_id}.pdf",
        },
    )
