"""
Hotel Management API — главный модуль FastAPI-приложения.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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


# Веб-клиент: отдаём статические файлы из web/
WEB_DIR = Path(__file__).resolve().parent.parent.parent / "web"
if not WEB_DIR.exists():
    WEB_DIR = Path(os.environ.get("WEB_DIR", "/root/web"))

if WEB_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(WEB_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(WEB_DIR / "js")), name="js")

    @app.get("/", tags=["Веб-клиент"], include_in_schema=False)
    async def serve_index():
        return FileResponse(str(WEB_DIR / "index.html"))
else:
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
