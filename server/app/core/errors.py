"""Кастомные исключения и единая обработка ошибок API."""

from __future__ import annotations

import logging
from typing import Any

from asyncpg import PostgresError, exceptions
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Базовые исключения приложения
# ---------------------------------------------------------------------------


class AppError(Exception):
    """Базовый класс ошибок приложения."""

    status_code: int = 400
    code: str = "app_error"

    def __init__(self, message: str, *, details: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class AuthError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "auth_error"


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ValidationAppError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"


# ---------------------------------------------------------------------------
# Регистрация обработчиков
# ---------------------------------------------------------------------------


def _format(status_code: int, code: str, message: str, details: Any | None = None) -> JSONResponse:
    payload: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        payload["details"] = details
    return JSONResponse(status_code=status_code, content=payload)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _on_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _format(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(HTTPException)
    async def _on_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        return _format(
            exc.status_code,
            "http_error",
            str(exc.detail) if exc.detail else "HTTP error",
        )

    @app.exception_handler(RequestValidationError)
    async def _on_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _format(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "Ошибка валидации входных данных",
            details=exc.errors(),
        )

    @app.exception_handler(exceptions.UniqueViolationError)
    async def _on_unique(_: Request, exc: exceptions.UniqueViolationError) -> JSONResponse:
        return _format(
            status.HTTP_409_CONFLICT,
            "conflict",
            "Запись с такими уникальными полями уже существует",
            details={"constraint": exc.constraint_name},
        )

    @app.exception_handler(exceptions.CheckViolationError)
    async def _on_check(_: Request, exc: exceptions.CheckViolationError) -> JSONResponse:
        return _format(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "check_violation",
            "Нарушено ограничение целостности",
            details={"constraint": exc.constraint_name, "detail": exc.detail},
        )

    @app.exception_handler(exceptions.ExclusionViolationError)
    async def _on_exclude(_: Request, exc: exceptions.ExclusionViolationError) -> JSONResponse:
        return _format(
            status.HTTP_409_CONFLICT,
            "exclusion",
            "Конфликт диапазонов: номер уже занят на пересекающиеся даты",
            details={"detail": exc.detail},
        )

    @app.exception_handler(exceptions.RaiseError)
    async def _on_raise(_: Request, exc: exceptions.RaiseError) -> JSONResponse:
        # RAISE EXCEPTION в plpgsql
        return _format(status.HTTP_400_BAD_REQUEST, "db_business_error", str(exc))

    @app.exception_handler(PostgresError)
    async def _on_pg(_: Request, exc: PostgresError) -> JSONResponse:
        logger.exception("Unhandled PostgresError")
        return _format(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "database_error",
            "Внутренняя ошибка базы данных",
            details={"sqlstate": getattr(exc, "sqlstate", None)},
        )

    @app.exception_handler(Exception)
    async def _on_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return _format(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "Внутренняя ошибка сервера",
        )
