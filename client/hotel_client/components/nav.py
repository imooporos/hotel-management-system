"""Навигационная шапка."""

from __future__ import annotations

import flet as ft

from ..theme import Palette, Sizing


def app_bar(
    *,
    p: Palette,
    user_label: str | None = None,
    role_label: str | None = None,
    on_home=None,
    on_my_bookings=None,
    on_admin=None,
    on_profile=None,
    on_logout=None,
    on_toggle_theme=None,
    is_dark: bool = False,
    is_staff: bool = False,
) -> ft.Container:
    nav_buttons: list[ft.Control] = []

    def _link(label: str, icon: str, handler):
        return ft.TextButton(
            label,
            icon=icon,
            on_click=handler,
            style=ft.ButtonStyle(
                color={ft.ControlState.DEFAULT: p.text, ft.ControlState.HOVERED: p.brand},
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                shape=ft.RoundedRectangleBorder(radius=Sizing.radius_md),
                text_style=ft.TextStyle(weight=ft.FontWeight.W_500, size=Sizing.body),
            ),
        )

    if on_home:
        nav_buttons.append(_link("Номера", ft.Icons.HOTEL, on_home))
    if on_my_bookings:
        nav_buttons.append(_link("Мои брони", ft.Icons.RECEIPT_LONG, on_my_bookings))
    if is_staff and on_admin:
        nav_buttons.append(_link("Администрирование", ft.Icons.ADMIN_PANEL_SETTINGS, on_admin))

    right_side: list[ft.Control] = []

    if on_toggle_theme:
        right_side.append(
            ft.IconButton(
                ft.Icons.LIGHT_MODE if is_dark else ft.Icons.DARK_MODE,
                tooltip="Сменить тему",
                on_click=on_toggle_theme,
                icon_color=p.text_muted,
            )
        )

    if user_label:
        right_side.append(
            ft.PopupMenuButton(
                content=ft.Container(
                    content=ft.Row(
                        [
                            ft.CircleAvatar(
                                content=ft.Text((user_label[:1] or "?").upper(), color=p.text_on_brand),
                                bgcolor=p.brand,
                                radius=14,
                            ),
                            ft.Column(
                                [
                                    ft.Text(user_label, size=Sizing.body, weight=ft.FontWeight.W_500, color=p.text),
                                    ft.Text(role_label or "", size=Sizing.caption, color=p.text_muted),
                                ],
                                spacing=0,
                            ),
                            ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=16, color=p.text_muted),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    border_radius=Sizing.radius_md,
                ),
                items=[
                    ft.PopupMenuItem(text="Профиль", icon=ft.Icons.PERSON_OUTLINE, on_click=on_profile),
                    ft.PopupMenuItem(),
                    ft.PopupMenuItem(text="Выйти", icon=ft.Icons.LOGOUT, on_click=on_logout),
                ],
            )
        )

    return ft.Container(
        content=ft.Row(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.APARTMENT, color=p.brand, size=22),
                        ft.Text(
                            "Velmar Hotel",
                            size=Sizing.h3,
                            weight=ft.FontWeight.W_700,
                            color=p.text,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(width=Sizing.pad_xl),
                ft.Row(nav_buttons, spacing=4),
                ft.Container(expand=True),
                ft.Row(right_side, spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=p.surface,
        padding=ft.padding.symmetric(horizontal=Sizing.pad_lg, vertical=Sizing.pad_md),
        border=ft.border.only(bottom=ft.BorderSide(1, p.border)),
    )
