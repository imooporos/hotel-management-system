import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://hotel_app:AppHotelStrong_pass_2026@localhost:5432/hotel_db"
    JWT_SECRET: str = "super-secret-jwt-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    APP_TITLE: str = "Hotel Management API"
    APP_VERSION: str = "1.0.0"
    CORS_ORIGINS: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
