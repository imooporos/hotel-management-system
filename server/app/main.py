"""Точка входа FastAPI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.db import close_pool, get_pool, init_pool
from .core.errors import install_exception_handlers
from .routers import admin as admin_router
from .routers import auth as auth_router
from .routers import bookings as bookings_router
from .routers import reports as reports_router
from .routers import rooms as rooms_router
from .routers import users as users_router

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=settings.log_level,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        description=(
            "REST API информационной системы управления гостиницей.\n"
            "Курсовой проект по дисциплине «Технология разработки и защиты баз данных»."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_exception_handlers(app)

    app.include_router(auth_router.router)
    app.include_router(rooms_router.router)
    app.include_router(bookings_router.router)
    app.include_router(users_router.router)
    app.include_router(reports_router.router)
    app.include_router(admin_router.router)

    @app.get("/", tags=["meta"])
    async def root():
        return {
            "service": "Hotel Management API",
            "version": settings.app_version,
            "docs": "/docs",
        }

    @app.get("/health", tags=["meta"])
    async def health():
        try:
            pool = get_pool()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return {"status": "ok"}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "detail": str(exc)}

    return app


app = create_app()
