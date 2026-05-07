"""Схемы для номеров и услуг."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class RoomCard(BaseModel):
    """Карточка номера в каталоге (берётся из v_room_availability)."""

    room_id: int
    room_number: str
    floor: int
    category_id: int
    category_code: str
    category_title: str
    capacity: int
    price_per_night: Decimal
    status: str
    description: str | None = None
    is_active: bool = True
    amenities: list[str] = Field(default_factory=list)


class RoomAvailability(BaseModel):
    room_id: int
    is_free: bool
    check_in: date
    check_out: date


class RoomCreateRequest(BaseModel):
    room_number: str = Field(min_length=1, max_length=16)
    floor: int = Field(ge=-1, le=50)
    category_id: int
    price_modifier: Decimal = Decimal(0)
    description: str | None = None


class RoomUpdateRequest(BaseModel):
    room_number: str | None = None
    floor: int | None = None
    category_id: int | None = None
    price_modifier: Decimal | None = None
    description: str | None = None
    status: str | None = None
    is_active: bool | None = None


class CategoryDTO(BaseModel):
    category_id: int
    code: str
    title: str
    description: str | None = None
    base_price: Decimal
    capacity: int


class ServiceDTO(BaseModel):
    service_id: int
    code: str
    title: str
    description: str | None = None
    price: Decimal
    is_active: bool


class ServiceCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    title: str = Field(min_length=2, max_length=96)
    description: str | None = None
    price: Decimal = Field(ge=0)
