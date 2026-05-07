"""Кастомные кнопки в фирменном стиле."""

from __future__ import annotations

import flet as ft

from ..theme import Palette, Sizing


def primary_button(
    text: str, on_click=None, *, p: Palette, icon: str | None = None,
    expand: bool = False, disabled: bool = False,
) -> ft.Control:
    return ft.ElevatedButton(
        text,
        icon=icon,
        on_click=on_click,
        expand=expand,
        disabled=disabled,
        style=ft.ButtonStyle(
            bgcolor={ft.ControlState.DEFAULT: p.brand, ft.ControlState.HOVERED: p.brand_hover, ft.ControlState.DISABLED: p.border},
            color={ft.ControlState.DEFAULT: p.text_on_brand, ft.ControlState.DISABLED: p.text_muted},
            padding=ft.padding.symmetric(horizontal=Sizing.pad_lg, vertical=Sizing.pad_md),
            shape=ft.RoundedRectangleBorder(radius=Sizing.radius_md),
            elevation=0,
            text_style=ft.TextStyle(weight=ft.FontWeight.W_600, size=Sizing.body),
        ),
    )


def outline_button(
    text: str, on_click=None, *, p: Palette, icon: str | None = None, danger: bool = False,
) -> ft.Control:
    color = p.danger if danger else p.brand
    return ft.OutlinedButton(
        text,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            color={ft.ControlState.DEFAULT: color},
            side={ft.ControlState.DEFAULT: ft.BorderSide(1, color)},
            padding=ft.padding.symmetric(horizontal=Sizing.pad_lg, vertical=Sizing.pad_md),
            shape=ft.RoundedRectangleBorder(radius=Sizing.radius_md),
            text_style=ft.TextStyle(weight=ft.FontWeight.W_600, size=Sizing.body),
        ),
    )


def ghost_button(text: str, on_click=None, *, p: Palette, icon: str | None = None) -> ft.Control:
    return ft.TextButton(
        text,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            color={ft.ControlState.DEFAULT: p.text_muted, ft.ControlState.HOVERED: p.brand},
            padding=ft.padding.symmetric(horizontal=Sizing.pad_md, vertical=Sizing.pad_sm),
            shape=ft.RoundedRectangleBorder(radius=Sizing.radius_md),
            text_style=ft.TextStyle(weight=ft.FontWeight.W_500, size=Sizing.body),
        ),
    )


def icon_button(icon: str, *, p: Palette, on_click=None, tooltip: str | None = None) -> ft.Control:
    return ft.IconButton(
        icon=icon,
        on_click=on_click,
        tooltip=tooltip,
        icon_color=p.text_muted,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=Sizing.radius_md),
            overlay_color=p.brand_soft,
        ),
    )
