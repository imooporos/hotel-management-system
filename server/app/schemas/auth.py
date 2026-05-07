"""Схемы для эндпоинтов аутентификации."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

PHONE_RE = re.compile(r"^\+?[0-9 \-\(\)]{10,32}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


class _EmailMixin:
    """Простая валидация email (RFC-совместимая, без проверки deliverability)."""

    @classmethod
    def _validate_email(cls, value: str) -> str:
        if not isinstance(value, str) or not EMAIL_RE.match(value.strip()):
            raise ValueError("Некорректный формат email")
        return value.strip().lower()


class RegisterRequest(BaseModel, _EmailMixin):
    email: str
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=128)
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("email")
    @classmethod
    def _email_format(cls, v: str) -> str:
        return cls._validate_email(v)

    @field_validator("phone")
    @classmethod
    def _phone_format(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        if not PHONE_RE.match(v):
            raise ValueError("Телефон должен содержать 10–15 цифр; допустимы +, -, скобки, пробелы")
        return v


class LoginRequest(BaseModel, _EmailMixin):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email_format(cls, v: str) -> str:
        return cls._validate_email(v)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class CurrentUserResponse(BaseModel):
    user_id: int
    email: str
    full_name: str
    phone: str | None = None
    role: str
    is_active: bool


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=128)
    phone: str | None = Field(default=None, max_length=32)
    passport_series: str | None = Field(default=None, max_length=12)
    passport_number: str | None = Field(default=None, max_length=20)
    passport_issued: str | None = Field(default=None, max_length=255)
    birth_date: str | None = None  # ISO date
    address: str | None = Field(default=None, max_length=500)

    @field_validator("phone")
    @classmethod
    def _phone_format(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        if not PHONE_RE.match(v):
            raise ValueError("Телефон должен содержать 10–15 цифр")
        return v
