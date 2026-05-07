"""Поля ввода в фирменном стиле."""

from __future__ import annotations

from datetime import date

import flet as ft

from ..theme import Palette, Sizing


def text_input(
    label: str,
    *,
    p: Palette,
    value: str = "",
    password: bool = False,
    icon: str | None = None,
    helper_text: str | None = None,
    multiline: bool = False,
    on_change=None,
    width: int | None = None,
    expand: bool = False,
    keyboard_type: ft.KeyboardType = ft.KeyboardType.TEXT,
) -> ft.TextField:
    return ft.TextField(
        label=label,
        value=value,
        password=password,
        can_reveal_password=password,
        prefix_icon=icon,
        helper_text=helper_text,
        multiline=multiline,
        min_lines=1,
        max_lines=4 if multiline else 1,
        on_change=on_change,
        width=width,
        expand=expand,
        keyboard_type=keyboard_type,
        text_size=Sizing.body,
        label_style=ft.TextStyle(color=p.text_muted, size=Sizing.body),
        text_style=ft.TextStyle(color=p.text, size=Sizing.body),
        helper_style=ft.TextStyle(color=p.text_muted, size=Sizing.caption),
        border_color=p.border,
        focused_border_color=p.brand,
        bgcolor=p.surface,
        border_radius=Sizing.radius_md,
        cursor_color=p.brand,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=14),
    )


def number_input(
    label: str, *, p: Palette, value: str | int | float = "", on_change=None, helper_text: str | None = None,
    width: int | None = None,
) -> ft.TextField:
    field = text_input(
        label,
        p=p,
        value=str(value),
        on_change=on_change,
        width=width,
        helper_text=helper_text,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    return field


def select(
    label: str,
    options: list[tuple[str, str]],  # (value, text)
    *,
    p: Palette,
    value: str | None = None,
    on_change=None,
    width: int | None = None,
    expand: bool = False,
) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=value,
        on_change=on_change,
        width=width,
        expand=expand,
        text_size=Sizing.body,
        label_style=ft.TextStyle(color=p.text_muted, size=Sizing.body),
        text_style=ft.TextStyle(color=p.text, size=Sizing.body),
        border_color=p.border,
        focused_border_color=p.brand,
        bgcolor=p.surface,
        border_radius=Sizing.radius_md,
        options=[ft.dropdown.Option(key=v, text=t) for v, t in options],
    )


def date_picker(
    label: str, *, p: Palette, value: date | None = None, on_change=None, width: int | None = None,
) -> ft.Container:
    """Поле с открытием системного DatePicker."""
    text_field = ft.TextField(
        label=label,
        value=value.isoformat() if value else "",
        read_only=True,
        text_size=Sizing.body,
        label_style=ft.TextStyle(color=p.text_muted, size=Sizing.body),
        text_style=ft.TextStyle(color=p.text, size=Sizing.body),
        border_color=p.border,
        focused_border_color=p.brand,
        bgcolor=p.surface,
        border_radius=Sizing.radius_md,
        suffix_icon=ft.Icons.CALENDAR_MONTH,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=14),
        width=width,
    )

    def _open(e):
        e.control.page.open(picker)

    def _on_change(e):
        new_val = picker.value
        if new_val:
            text_field.value = new_val.date().isoformat() if hasattr(new_val, "date") else new_val.isoformat()
            text_field.update()
            if on_change:
                e.value = new_val
                on_change(e)

    picker = ft.DatePicker(on_change=_on_change, value=value)

    text_field.on_focus = _open
    text_field.on_click = _open

    container = ft.Container(content=text_field, on_click=_open)
    container.picker = picker  # type: ignore[attr-defined]
    container.text_field = text_field  # type: ignore[attr-defined]
    return container
