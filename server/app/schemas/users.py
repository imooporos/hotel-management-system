from pydantic import BaseModel, Field
from datetime import date, datetime


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str
    patronymic: str | None = None
    phone: str | None = None
    passport_series: str | None = None
    passport_number: str | None = None
    birth_date: date | None = None
    email: str | None = None
    role: str | None = None
    created_at: datetime | None = None


class ProfileUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    patronymic: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, pattern=r'^\+?[0-9]{10,15}$')
    passport_series: str | None = Field(None, pattern=r'^\d{4}$')
    passport_number: str | None = Field(None, pattern=r'^\d{6}$')
    birth_date: date | None = None


class UserListResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    first_name: str | None = None
    last_name: str | None = None
    created_at: datetime


class UserRoleUpdate(BaseModel):
    role: str = Field(..., pattern=r'^(guest|manager|admin)$')


class UserBlockUpdate(BaseModel):
    is_active: bool
