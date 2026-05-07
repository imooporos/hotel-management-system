"""Тема и цветовая палитра приложения."""

import flet as ft

PRIMARY = "#1a237e"
PRIMARY_LIGHT = "#534bae"
SECONDARY = "#ff6f00"
SECONDARY_LIGHT = "#ffa040"
BG_COLOR = "#f5f5f5"
CARD_BG = "#ffffff"
TEXT_PRIMARY = "#212121"
TEXT_SECONDARY = "#757575"
SUCCESS = "#2e7d32"
ERROR = "#c62828"
WARNING = "#f57f17"
DIVIDER = "#e0e0e0"


def get_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=PRIMARY,
        font_family="Roboto",
        visual_density=ft.VisualDensity.COMFORTABLE,
    )


def styled_card(content: ft.Control, **kwargs) -> ft.Card:
    return ft.Card(
        content=ft.Container(
            content=content,
            padding=20,
            border_radius=12,
        ),
        elevation=2,
        **kwargs,
    )


def page_title(text: str) -> ft.Text:
    return ft.Text(text, size=24, weight=ft.FontWeight.BOLD, color=PRIMARY)


def section_title(text: str) -> ft.Text:
    return ft.Text(text, size=18, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY)


def status_chip(status: str) -> ft.Container:
    color_map = {
        "pending": WARNING,
        "confirmed": PRIMARY,
        "checked_in": SUCCESS,
        "checked_out": TEXT_SECONDARY,
        "cancelled": ERROR,
        "available": SUCCESS,
        "occupied": ERROR,
        "maintenance": WARNING,
    }
    label_map = {
        "pending": "Ожидает",
        "confirmed": "Подтверждено",
        "checked_in": "Заселён",
        "checked_out": "Выехал",
        "cancelled": "Отменено",
        "available": "Свободен",
        "occupied": "Занят",
        "maintenance": "Ремонт",
    }
    bg = color_map.get(status, TEXT_SECONDARY)
    label = label_map.get(status, status)

    return ft.Container(
        content=ft.Text(label, size=11, color="#ffffff", weight=ft.FontWeight.W_500),
        bgcolor=bg,
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
        border_radius=12,
    )
