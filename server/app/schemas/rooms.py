from pydantic import BaseModel, Field
from datetime import date


class RoomCategoryResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    base_price: float
    capacity: int


class RoomCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    base_price: float = Field(..., gt=0)
    capacity: int = Field(..., ge=1, le=10)


class RoomCategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    base_price: float | None = Field(None, gt=0)
    capacity: int | None = Field(None, ge=1, le=10)


class AmenityResponse(BaseModel):
    id: int
    name: str
    icon: str | None = None


class RoomResponse(BaseModel):
    id: int
    room_number: str
    category_id: int
    category_name: str | None = None
    base_price: float | None = None
    capacity: int | None = None
    floor: int
    status: str
    description: str | None = None
    is_active: bool
    amenities: list[AmenityResponse] = []
    is_free_today: bool | None = None


class RoomCreate(BaseModel):
    room_number: str = Field(..., min_length=1, max_length=10)
    category_id: int
    floor: int = Field(..., ge=1, le=50)
    description: str | None = None


class RoomUpdate(BaseModel):
    category_id: int | None = None
    floor: int | None = Field(None, ge=1, le=50)
    status: str | None = None
    description: str | None = None
    is_active: bool | None = None


class RoomAvailabilityQuery(BaseModel):
    check_in: date
    check_out: date
    category_id: int | None = None
    min_price: float | None = None
    max_price: float | None = None
    capacity: int | None = None
