from pydantic import BaseModel, Field
from datetime import date, datetime


class BookingCreate(BaseModel):
    room_id: int
    check_in_date: date
    check_out_date: date
    guests_count: int = Field(1, ge=1)
    notes: str | None = None
    service_ids: list[int] = []


class BookingResponse(BaseModel):
    id: int
    guest_id: int
    room_id: int
    room_number: str | None = None
    category_name: str | None = None
    check_in_date: date
    check_out_date: date
    nights: int | None = None
    status: str
    guests_count: int
    total_amount: float
    notes: str | None = None
    created_at: datetime
    services: list[dict] = []
    guest_name: str | None = None
    guest_email: str | None = None


class BookingStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r'^(pending|confirmed|checked_in|checked_out|cancelled)$')


class BookingServiceAdd(BaseModel):
    service_id: int
    quantity: int = Field(1, ge=1)
