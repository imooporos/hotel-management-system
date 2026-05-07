"""Простые тосты — обёртка над SnackBar."""

from __future__ import annotations

import flet as ft

from ..theme import Palette, Sizing


def show_toast(page: ft.Page, message: str, *, p: Palette, kind: str = "info") -> None:
    color = {
        "success": p.success,
        "warning": p.warning,
        "danger": p.danger,
        "info": p.info,
    }.get(kind, p.info)
    page.open(ft.SnackBar(
        content=ft.Row(
            [
                ft.Icon(_icon(kind), color=color, size=20),
                ft.Text(message, color=p.text, size=Sizing.body),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=p.surface,
        behavior=ft.SnackBarBehavior.FLOATING,
        shape=ft.RoundedRectangleBorder(radius=Sizing.radius_md),
        duration=4000,
        elevation=4,
    ))


def _icon(kind: str) -> str:
    return {
        "success": ft.Icons.CHECK_CIRCLE_OUTLINE,
        "warning": ft.Icons.WARNING_AMBER_OUTLINED,
        "danger": ft.Icons.ERROR_OUTLINE,
        "info": ft.Icons.INFO_OUTLINE,
    }.get(kind, ft.Icons.INFO_OUTLINE)
