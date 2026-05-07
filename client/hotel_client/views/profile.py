"""Профиль пользователя."""

from __future__ import annotations

import flet as ft

from ..api import ApiError
from ..components.buttons import primary_button
from ..components.cards import card_container, section_header
from ..components.inputs import text_input
from ..components.toasts import show_toast
from ..state import AppState, CurrentUser
from ..theme import Palette, Sizing


def profile_view(state: AppState, p: Palette) -> ft.Control:
    user = state.current_user
    assert user is not None

    full_name = text_input("ФИО", p=p, value=user.full_name, icon=ft.Icons.PERSON_OUTLINE)
    phone = text_input("Телефон", p=p, value=user.phone or "", icon=ft.Icons.PHONE_OUTLINED)
    email = text_input("Email", p=p, value=user.email, icon=ft.Icons.MAIL_OUTLINE)
    email.read_only = True
    email.disabled = True

    def save(e):
        try:
            data = state.api.update_profile(
                full_name=full_name.value,
                phone=(phone.value or "").strip() or None,
            )
        except ApiError as exc:
            show_toast(state.page, exc.message, p=p, kind="danger")
            return
        state.current_user = CurrentUser(**{k: data.get(k) for k in CurrentUser.__dataclass_fields__})
        show_toast(state.page, "Профиль сохранён", p=p, kind="success")

    return ft.Column(
        [
            section_header("Профиль", p=p),
            ft.Container(height=Sizing.pad_md),
            card_container(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.CircleAvatar(
                                    content=ft.Text(
                                        (user.full_name[:1] or "?").upper(),
                                        size=24, color=p.text_on_brand,
                                    ),
                                    radius=32,
                                    bgcolor=p.brand,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(user.full_name, size=Sizing.h2, weight=ft.FontWeight.W_700, color=p.text),
                                        ft.Text(user.email, color=p.text_muted),
                                        ft.Container(height=2),
                                        ft.Row(
                                            [
                                                ft.Container(
                                                    content=ft.Text(_role_label(user.role), color=p.brand, size=Sizing.caption, weight=ft.FontWeight.W_600),
                                                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                                    bgcolor=p.brand_soft,
                                                    border_radius=999,
                                                ),
                                            ],
                                        ),
                                    ],
                                    spacing=2,
                                ),
                            ],
                            spacing=Sizing.pad_md,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(height=Sizing.pad_md),
                        ft.Divider(color=p.border, height=1),
                        ft.Container(height=Sizing.pad_md),
                        ft.Text("Контактные данные", size=Sizing.h3, weight=ft.FontWeight.W_600, color=p.text),
                        ft.Container(height=Sizing.pad_sm),
                        ft.Row(
                            [
                                ft.Container(content=full_name, expand=True),
                                ft.Container(content=phone, expand=True),
                            ],
                            spacing=Sizing.pad_md,
                        ),
                        email,
                        ft.Container(height=Sizing.pad_md),
                        ft.Row(
                            [
                                primary_button("Сохранить изменения", save, p=p, icon=ft.Icons.SAVE_OUTLINED),
                            ],
                        ),
                    ],
                    spacing=0,
                ),
                p=p,
            ),
        ],
        spacing=0,
        expand=True,
    )


def _role_label(role: str) -> str:
    return {"guest": "Гость", "manager": "Менеджер", "admin": "Администратор"}.get(role, role)
