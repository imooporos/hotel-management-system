"""Отчётные эндпоинты."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..core.db import acquire_for_user
from ..core.security import CurrentUser, get_current_user, require_role
from ..services.pdf import generate_occupancy_report, generate_revenue_report

router = APIRouter(prefix="/reports", tags=["reports"])


class RevenueRow(BaseModel):
    category_id: int
    category_code: str
    category_title: str
    bookings_count: int
    revenue_total: float
    revenue_paid: float


class OccupancyResponse(BaseModel):
    period_start: date
    period_end: date
    occupancy_rate: float
    occupancy_pct: float


@router.get(
    "/revenue",
    response_model=list[RevenueRow],
    dependencies=[Depends(require_role("manager", "admin"))],
)
async def revenue(user: CurrentUser = Depends(get_current_user)) -> list[RevenueRow]:
    async with acquire_for_user(user.user_id) as conn:
        rows = await conn.fetch("SELECT * FROM v_revenue_by_category ORDER BY revenue_total DESC")
    return [RevenueRow(**{k: float(v) if hasattr(v, "to_eng_string") else v for k, v in dict(r).items()}) for r in rows]


@router.get(
    "/revenue.pdf",
    dependencies=[Depends(require_role("manager", "admin"))],
)
async def revenue_pdf(user: CurrentUser = Depends(get_current_user)):
    async with acquire_for_user(user.user_id) as conn:
        rows = await conn.fetch("SELECT * FROM v_revenue_by_category ORDER BY revenue_total DESC")
    pdf_bytes = generate_revenue_report([dict(r) for r in rows])
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="revenue_report.pdf"'},
    )


@router.get(
    "/occupancy",
    response_model=OccupancyResponse,
    dependencies=[Depends(require_role("manager", "admin"))],
)
async def occupancy(
    period_start: date = Query(..., alias="from"),
    period_end: date = Query(..., alias="to"),
    user: CurrentUser = Depends(get_current_user),
) -> OccupancyResponse:
    async with acquire_for_user(user.user_id) as conn:
        rate = await conn.fetchval(
            "SELECT fn_occupancy_rate($1, $2)", period_start, period_end
        )
    return OccupancyResponse(
        period_start=period_start,
        period_end=period_end,
        occupancy_rate=float(rate or 0),
        occupancy_pct=round(float(rate or 0) * 100, 2),
    )


@router.get(
    "/occupancy.pdf",
    dependencies=[Depends(require_role("manager", "admin"))],
)
async def occupancy_pdf(
    period_start: date = Query(..., alias="from"),
    period_end: date = Query(..., alias="to"),
    user: CurrentUser = Depends(get_current_user),
):
    async with acquire_for_user(user.user_id) as conn:
        rate = await conn.fetchval(
            "SELECT fn_occupancy_rate($1, $2)", period_start, period_end
        )
        active = await conn.fetch("SELECT * FROM v_active_bookings ORDER BY check_in")
    pdf_bytes = generate_occupancy_report(
        period_start=period_start,
        period_end=period_end,
        rate=float(rate or 0),
        active_bookings=[dict(r) for r in active],
    )
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="occupancy_report.pdf"'},
    )
