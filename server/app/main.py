"""
Hotel Management API — главный модуль FastAPI-приложения.
"""

import logging
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_pool, close_pool
from app.core.exceptions import (
    AppException, app_exception_handler,
    asyncpg_exception_handler, generic_exception_handler,
)
from app.routers import auth, users, rooms, bookings, services, reports

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("hotel")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Подключение к базе данных...")
    await create_pool(settings.DATABASE_URL)
    logger.info("Пул подключений к БД создан")
    yield
    logger.info("Закрытие пула подключений...")
    await close_pool()
    logger.info("Пул подключений закрыт")


app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="REST API для информационной системы управления гостиницей",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(asyncpg.PostgresError, asyncpg_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(rooms.router)
app.include_router(bookings.router)
app.include_router(services.router)
app.include_router(reports.router)


@app.get("/", tags=["Здоровье"])
async def root():
    return {
        "service": "Hotel Management API",
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health", tags=["Здоровье"])
async def health():
    from app.core.database import get_pool
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}
