"""Экраны входа и регистрации."""

from __future__ import annotations

from typing import Callable

import flet as ft

from ..api import ApiError
from ..components.buttons import ghost_button, primary_button
from ..components.inputs import text_input
from ..components.toasts import show_toast
from ..state import AppState, CurrentUser
from ..theme import Palette, Sizing


def login_view(state: AppState, p: Palette, *, on_success: Callable[[], None], go_register: Callable[[], None]) -> ft.Control:
    email = text_input("Электронная почта", p=p, icon=ft.Icons.MAIL_OUTLINE)
    password = text_input("Пароль", p=p, password=True, icon=ft.Icons.LOCK_OUTLINE)
    error_text = ft.Text("", color=p.danger, size=Sizing.caption)

    def submit(e):
        error_text.value = ""
        if not email.value or not password.value:
            error_text.value = "Заполните email и пароль"
            error_text.update()
            return
        try:
            state.api.login(email.value.strip(), password.value)
            data = state.api.me()
            state.login(
                CurrentUser(**{k: data.get(k) for k in CurrentUser.__dataclass_fields__}),
                state.api.token or "",
            )
            on_success()
        except ApiError as exc:
            error_text.value = exc.message
            error_text.update()
            show_toast(state.page, exc.message, p=p, kind="danger")

    return _auth_layout(
        p=p,
        title="Добро пожаловать",
        subtitle="Войдите в свою учётную запись",
        controls=[
            email,
            password,
            error_text,
            primary_button("Войти", submit, p=p, expand=True),
            ft.Container(height=Sizing.pad_sm),
            ft.Row(
                [
                    ft.Text("Нет аккаунта?", size=Sizing.body, color=p.text_muted),
                    ghost_button("Зарегистрироваться", lambda e: go_register(), p=p),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=4,
            ),
        ],
    )


def register_view(state: AppState, p: Palette, *, on_success: Callable[[], None], go_login: Callable[[], None]) -> ft.Control:
    full_name = text_input("ФИО", p=p, icon=ft.Icons.PERSON_OUTLINE)
    email = text_input("Электронная почта", p=p, icon=ft.Icons.MAIL_OUTLINE)
    phone = text_input("Телефон (необязательно)", p=p, icon=ft.Icons.PHONE_OUTLINED)
    password = text_input("Пароль (мин. 8 символов)", p=p, password=True, icon=ft.Icons.LOCK_OUTLINE)
    confirm = text_input("Повторите пароль", p=p, password=True, icon=ft.Icons.LOCK_OUTLINE)
    error_text = ft.Text("", color=p.danger, size=Sizing.caption)

    def submit(e):
        error_text.value = ""
        if not full_name.value or not email.value or not password.value:
            error_text.value = "Заполните обязательные поля"
            error_text.update()
            return
        if password.value != confirm.value:
            error_text.value = "Пароли не совпадают"
            error_text.update()
            return
        if len(password.value or "") < 8:
            error_text.value = "Пароль должен быть не короче 8 символов"
            error_text.update()
            return
        try:
            state.api.register(
                email=email.value.strip(),
                password=password.value,
                full_name=full_name.value.strip(),
                phone=(phone.value or "").strip() or None,
            )
            data = state.api.me()
            state.login(
                CurrentUser(**{k: data.get(k) for k in CurrentUser.__dataclass_fields__}),
                state.api.token or "",
            )
            on_success()
        except ApiError as exc:
            error_text.value = exc.message
            error_text.update()
            show_toast(state.page, exc.message, p=p, kind="danger")

    return _auth_layout(
        p=p,
        title="Создание аккаунта",
        subtitle="Регистрация занимает меньше минуты",
        controls=[
            full_name,
            email,
            phone,
            password,
            confirm,
            error_text,
            primary_button("Создать аккаунт", submit, p=p, expand=True),
            ft.Container(height=Sizing.pad_sm),
            ft.Row(
                [
                    ft.Text("Уже есть аккаунт?", size=Sizing.body, color=p.text_muted),
                    ghost_button("Войти", lambda e: go_login(), p=p),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=4,
            ),
        ],
    )


def _auth_layout(*, p: Palette, title: str, subtitle: str, controls: list[ft.Control]) -> ft.Control:
    card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.APARTMENT, size=28, color=p.brand),
                        ft.Text("Velmar Hotel", size=Sizing.h2, weight=ft.FontWeight.W_700, color=p.text),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=Sizing.pad_md),
                ft.Text(title, size=Sizing.h1, weight=ft.FontWeight.W_700, color=p.text),
                ft.Text(subtitle, size=Sizing.body, color=p.text_muted),
                ft.Container(height=Sizing.pad_lg),
                *controls,
            ],
            spacing=Sizing.pad_md,
            tight=True,
        ),
        bgcolor=p.surface,
        padding=Sizing.pad_xl,
        width=440,
        border_radius=Sizing.radius_lg,
        border=ft.border.all(1, p.border),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=24,
            color=ft.Colors.with_opacity(0.08, ft.Colors.BLACK),
            offset=ft.Offset(0, 8),
        ),
    )

    side_panel = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "Гостиничный сервис нового поколения",
                    size=Sizing.h1,
                    weight=ft.FontWeight.W_700,
                    color=p.text_on_brand,
                ),
                ft.Container(height=Sizing.pad_md),
                ft.Text(
                    "Бронирование номеров, управление заселением и выручкой "
                    "в одном современном решении на базе PostgreSQL.",
                    size=Sizing.h3,
                    color=ft.Colors.with_opacity(0.85, p.text_on_brand),
                ),
                ft.Container(height=Sizing.pad_xl),
                _feature_row(p, ft.Icons.HOTEL, "11 таблиц БД, RLS, аудит"),
                _feature_row(p, ft.Icons.CALENDAR_TODAY, "Защита от пересечений диапазонов"),
                _feature_row(p, ft.Icons.PICTURE_AS_PDF, "PDF-бланки заказов и отчёты"),
                _feature_row(p, ft.Icons.SECURITY, "Ролевой доступ guest / manager / admin"),
            ],
            spacing=4,
        ),
        bgcolor=p.brand,
        padding=Sizing.pad_xl * 1.5,
        expand=True,
        height=720,
    )

    return ft.Container(
        content=ft.Row(
            [
                ft.Container(content=ft.Column([side_panel], expand=True), expand=2),
                ft.Container(
                    content=ft.Column(
                        [card],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        expand=True,
                    ),
                    expand=3,
                ),
            ],
            expand=True,
        ),
        expand=True,
        bgcolor=p.bg,
    )


def _feature_row(p: Palette, icon: str, text: str) -> ft.Row:
    return ft.Row(
        [
            ft.Icon(icon, color=p.text_on_brand, size=18),
            ft.Text(text, color=ft.Colors.with_opacity(0.92, p.text_on_brand), size=Sizing.body),
        ],
        spacing=10,
    )
