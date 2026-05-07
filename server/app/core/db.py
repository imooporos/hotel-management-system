"""Подключение к PostgreSQL: пул asyncpg, контекстные параметры сессии."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import asyncpg

from .config import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def init_pool() -> asyncpg.Pool:
    """Инициализирует пул соединений (вызывается при старте приложения)."""
    global _pool
    if _pool is None:
        logger.info("Creating asyncpg pool")
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=1,
            max_size=10,
            command_timeout=30,
        )
    return _pool


async def close_pool() -> None:
    """Закрывает пул (вызывается при остановке)."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Возвращает текущий пул, бросая ошибку если не инициализирован."""
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    return _pool


@asynccontextmanager
async def acquire_for_user(user_id: int | None) -> AsyncIterator[asyncpg.Connection]:
    """
    Берёт соединение из пула и устанавливает app.user_id / app.actor_id
    на время сессии — используется триггерами аудита и RLS-политиками.
    Возвращает соединение в пул автоматически.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        if user_id is not None:
            await conn.execute("SELECT set_config('app.user_id', $1, false)", str(user_id))
            await conn.execute("SELECT set_config('app.actor_id', $1, false)", str(user_id))
        else:
            await conn.execute("SELECT set_config('app.user_id', '', false)")
            await conn.execute("SELECT set_config('app.actor_id', '', false)")
        yield conn
