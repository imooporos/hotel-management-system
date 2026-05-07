"""Схемы для бронирований и платежей."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class BookingCreateRequest(BaseModel):
    room_id: int
    check_in: date
    check_out: date
    guests_count: int = Field(default=1, ge=1, le=6)
    service_ids: list[int] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _check_dates(self) -> "BookingCreateRequest":
        if self.check_out <= self.check_in:
            raise ValueError("Дата выезда должна быть позже даты заезда")
        if self.check_in < date.today():
            raise ValueError("Дата заезда не может быть в прошлом")
        return self


class BookingResponse(BaseModel):
    booking_id: int
    room_number: str
    category_title: str
    check_in: date
    check_out: date
    nights: int
    guests_count: int
    status: str
    total_price: Decimal
    paid_total: Decimal
    amount_due: Decimal


class BookingDetailResponse(BookingResponse):
    user_id: int
    guest_name: str
    guest_email: str
    guest_phone: str | None = None
    created_at: datetime


class BookingStatusUpdateRequest(BaseModel):
    status: str = Field(pattern=r"^(confirmed|checked_in|checked_out|cancelled)$")


class CalculateRequest(BaseModel):
    room_id: int
    check_in: date
    check_out: date
    service_ids: list[int] = Field(default_factory=list)


class CalculateResponse(BaseModel):
    total_price: Decimal
    nights: int
    is_room_free: bool
