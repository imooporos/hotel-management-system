"""Глобальное состояние клиентского приложения."""

from __future__ import annotations

from dataclasses import dataclass

import flet as ft

from .api import ApiClient


@dataclass
class CurrentUser:
    user_id: int
    email: str
    full_name: str
    role: str
    phone: str | None = None
    is_active: bool = True

    @property
    def is_staff(self) -> bool:
        return self.role in ("manager", "admin")

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class AppState:
    """Хранит текущего пользователя, тему и API-клиент."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.api = ApiClient()
        self.current_user: CurrentUser | None = None
        self.theme_mode: ft.ThemeMode = ft.ThemeMode.LIGHT

    # ---- Авторизация ----
    def login(self, user: CurrentUser, token: str) -> None:
        self.current_user = user
        self.api.token = token
        if self.page.client_storage:
            self.page.client_storage.set("token", token)

    def logout(self) -> None:
        self.current_user = None
        self.api.logout()
        if self.page.client_storage:
            try:
                self.page.client_storage.remove("token")
            except Exception:  # noqa: BLE001
                pass

    def restore_session(self) -> bool:
        """Пытается восстановить сессию из client_storage. Возвращает True при успехе."""
        if not self.page.client_storage:
            return False
        try:
            token = self.page.client_storage.get("token")
        except Exception:  # noqa: BLE001
            return False
        if not token:
            return False
        self.api.token = token
        try:
            data = self.api.me()
            self.current_user = CurrentUser(**{k: data.get(k) for k in CurrentUser.__dataclass_fields__})
            return True
        except Exception:  # noqa: BLE001
            self.api.token = None
            return False

    # ---- Тема ----
    def toggle_theme(self) -> None:
        self.theme_mode = (
            ft.ThemeMode.DARK if self.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        )
        self.page.theme_mode = self.theme_mode
        if self.page.client_storage:
            self.page.client_storage.set("theme", self.theme_mode.value if hasattr(self.theme_mode, "value") else str(self.theme_mode))
        self.page.update()

    def restore_theme(self) -> None:
        if not self.page.client_storage:
            return
        try:
            stored = self.page.client_storage.get("theme")
        except Exception:  # noqa: BLE001
            return
        if stored == "dark":
            self.theme_mode = ft.ThemeMode.DARK
        elif stored == "light":
            self.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme_mode = self.theme_mode
