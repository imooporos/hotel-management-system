"""Дизайн-токены: цвета, типографика, отступы, радиусы.

Идея — собственная палитра вместо стандартных Material синих, чтобы интерфейс
не выглядел шаблонным. Брендовая основа — глубокий тил (#0F766E) с тёплыми
акцентами и нейтральной серой шкалой.
"""

from __future__ import annotations

from dataclasses import dataclass

import flet as ft


# --------------------------------------------------------------------------
# Палитра — две темы (light/dark) на основе одинаковых акцентов.
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Palette:
    # Брендовый акцент
    brand: str
    brand_hover: str
    brand_soft: str

    # Семантика
    success: str
    warning: str
    danger: str
    info: str

    # Поверхности
    bg: str          # фон страницы
    surface: str     # карточки
    surface_alt: str # выделенные строки таблицы
    border: str

    # Типографика
    text: str
    text_muted: str
    text_on_brand: str


LIGHT = Palette(
    brand="#0F766E",
    brand_hover="#115E59",
    brand_soft="#CCFBF1",
    success="#15803D",
    warning="#D97706",
    danger="#DC2626",
    info="#2563EB",
    bg="#F8FAFC",
    surface="#FFFFFF",
    surface_alt="#F1F5F9",
    border="#E2E8F0",
    text="#0F172A",
    text_muted="#475569",
    text_on_brand="#FFFFFF",
)


DARK = Palette(
    brand="#2DD4BF",
    brand_hover="#5EEAD4",
    brand_soft="#134E4A",
    success="#22C55E",
    warning="#F59E0B",
    danger="#F87171",
    info="#60A5FA",
    bg="#0B1220",
    surface="#111A2C",
    surface_alt="#172033",
    border="#1F2A44",
    text="#E2E8F0",
    text_muted="#94A3B8",
    text_on_brand="#0B1220",
)


# --------------------------------------------------------------------------
# Размеры
# --------------------------------------------------------------------------

class Sizing:
    radius_sm = 8
    radius_md = 12
    radius_lg = 20
    pad_xs = 4
    pad_sm = 8
    pad_md = 16
    pad_lg = 24
    pad_xl = 32

    h1 = 28
    h2 = 22
    h3 = 18
    body = 14
    caption = 12

    container_max = 1240


# --------------------------------------------------------------------------
# Общие стили текста
# --------------------------------------------------------------------------

def heading(text: str, p: Palette, *, size: int = Sizing.h2, weight: str = ft.FontWeight.W_600) -> ft.Text:
    return ft.Text(text, size=size, weight=weight, color=p.text)


def body_text(text: str, p: Palette, *, muted: bool = False, size: int | None = None) -> ft.Text:
    return ft.Text(
        text,
        size=size or Sizing.body,
        color=p.text_muted if muted else p.text,
    )


# --------------------------------------------------------------------------
# Тема Flet (для системных контролов)
# --------------------------------------------------------------------------


def make_flet_theme(p: Palette) -> ft.Theme:
    return ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=p.brand,
            on_primary=p.text_on_brand,
            secondary=p.brand_hover,
            on_secondary=p.text_on_brand,
            surface=p.surface,
            on_surface=p.text,
            background=p.bg,
            on_background=p.text,
            error=p.danger,
            outline=p.border,
        ),
        font_family="Inter",
        use_material3=True,
    )


def get_palette(theme_mode: ft.ThemeMode) -> Palette:
    return DARK if theme_mode == ft.ThemeMode.DARK else LIGHT
