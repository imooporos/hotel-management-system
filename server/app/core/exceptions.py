from fastapi import Request
from fastapi.responses import JSONResponse
import asyncpg
import logging

logger = logging.getLogger("hotel")


class AppException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


class NotFoundException(AppException):
    def __init__(self, detail: str = "Запись не найдена"):
        super().__init__(404, detail)


class ConflictException(AppException):
    def __init__(self, detail: str = "Конфликт данных"):
        super().__init__(409, detail)


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Доступ запрещён"):
        super().__init__(403, detail)


class ValidationException(AppException):
    def __init__(self, detail: str = "Ошибка валидации данных"):
        super().__init__(422, detail)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def asyncpg_exception_handler(
    request: Request, exc: asyncpg.PostgresError
) -> JSONResponse:
    logger.error(f"Database error: {exc}")
    detail = str(exc)
    if isinstance(exc, asyncpg.UniqueViolationError):
        return JSONResponse(status_code=409, content={"detail": f"Запись уже существует: {detail}"})
    if isinstance(exc, asyncpg.ForeignKeyViolationError):
        return JSONResponse(status_code=400, content={"detail": f"Нарушение ссылочной целостности: {detail}"})
    if isinstance(exc, asyncpg.CheckViolationError):
        return JSONResponse(status_code=400, content={"detail": f"Нарушение ограничения: {detail}"})
    if isinstance(exc, asyncpg.RaiseError):
        return JSONResponse(status_code=400, content={"detail": detail})
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка базы данных"})


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера"},
    )
