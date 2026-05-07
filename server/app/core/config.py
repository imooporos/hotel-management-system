"""Конфигурация приложения через переменные окружения."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения. Подгружаются из .env."""

    database_url: str = Field(
        default="postgresql://hotel_app:AppHotelStrong_pass_2026@localhost:5432/hotel_db",
    )
    jwt_secret: str = Field(default="change_me_to_a_long_random_secret")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=720)
    cors_origins: str = Field(default="*")
    log_level: str = Field(default="INFO")
    app_title: str = Field(default="Hotel Management API")
    app_version: str = Field(default="1.0.0")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
