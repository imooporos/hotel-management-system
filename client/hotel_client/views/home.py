"""Главный экран — каталог номеров."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Callable

import flet as ft

from ..api import ApiError
from ..components.cards import card_container, fmt_money, room_card, section_header
from ..components.inputs import select, text_input
from ..components.toasts import show_toast
from ..state import AppState
from ..theme import Palette, Sizing


def home_view(
    state: AppState,
    p: Palette,
    *,
    on_book: Callable[[dict], None],
    on_open_room: Callable[[dict], None],
) -> ft.Control:
    grid = ft.GridView(
        expand=True,
        runs_count=3,
        max_extent=420,
        spacing=Sizing.pad_md,
        run_spacing=Sizing.pad_md,
        child_aspect_ratio=1.05,
        controls=[],
    )

    # Filters state
    f_state = {
        "category_id": None,
        "capacity_min": None,
        "min_price": None,
        "max_price": None,
        "free_from": None,
        "free_to": None,
    }

    def load_data():
        try:
            categories = state.api.list_categories()
            rooms = state.api.list_rooms(
                category_id=f_state["category_id"],
                capacity_min=f_state["capacity_min"],
                min_price=f_state["min_price"],
                max_price=f_state["max_price"],
                free_from=f_state["free_from"],
                free_to=f_state["free_to"],
            )
        except ApiError as exc:
            show_toast(state.page, exc.message, p=p, kind="danger")
            return [], []
        return categories, rooms

    def render_rooms(rooms: list[dict]):
        grid.controls = [
            room_card(
                r,
                p=p,
                on_book=lambda e, room=r: on_book(room),
                on_open=lambda e, room=r: on_open_room(room),
            )
            for r in rooms
        ]
        if not rooms:
            grid.controls = [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.BEDROOM_PARENT, size=48, color=p.text_muted),
                            ft.Text(
                                "Под фильтры ничего не подходит",
                                size=Sizing.body,
                                color=p.text_muted,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=Sizing.pad_xl,
                    alignment=ft.alignment.center,
                )
            ]
        # обновлять можно только после монтирования в page
        if grid.page is not None:
            grid.update()

    # ---- Filters UI ----

    cat_select = select(
        "Категория",
        options=[("", "Все категории")],
        p=p,
        value="",
    )
    capacity_select = select(
        "Гостей",
        options=[("", "Любое"), ("1", "1+"), ("2", "2+"), ("3", "3+"), ("4", "4+")],
        p=p,
        value="",
    )
    min_price_field = text_input("Цена от", p=p, keyboard_type=ft.KeyboardType.NUMBER)
    max_price_field = text_input("Цена до", p=p, keyboard_type=ft.KeyboardType.NUMBER)

    today = date.today()
    free_from_field = ft.TextField(
        label="Заезд",
        value="",
        read_only=True,
        suffix_icon=ft.Icons.CALENDAR_MONTH,
        border_color=p.border,
        bgcolor=p.surface,
        border_radius=Sizing.radius_md,
        text_size=Sizing.body,
        label_style=ft.TextStyle(color=p.text_muted, size=Sizing.body),
        text_style=ft.TextStyle(color=p.text, size=Sizing.body),
    )
    free_to_field = ft.TextField(
        label="Выезд",
        value="",
        read_only=True,
        suffix_icon=ft.Icons.CALENDAR_MONTH,
        border_color=p.border,
        bgcolor=p.surface,
        border_radius=Sizing.radius_md,
        text_size=Sizing.body,
        label_style=ft.TextStyle(color=p.text_muted, size=Sizing.body),
        text_style=ft.TextStyle(color=p.text, size=Sizing.body),
    )

    def open_picker_from(e):
        state.page.open(picker_from)

    def open_picker_to(e):
        state.page.open(picker_to)

    def on_pick_from(e):
        if picker_from.value:
            d = picker_from.value.date() if hasattr(picker_from.value, "date") else picker_from.value
            f_state["free_from"] = d
            free_from_field.value = d.strftime("%d.%m.%Y")
            free_from_field.update()

    def on_pick_to(e):
        if picker_to.value:
            d = picker_to.value.date() if hasattr(picker_to.value, "date") else picker_to.value
            f_state["free_to"] = d
            free_to_field.value = d.strftime("%d.%m.%Y")
            free_to_field.update()

    picker_from = ft.DatePicker(
        on_change=on_pick_from,
        first_date=today,
        last_date=today + timedelta(days=365),
    )
    picker_to = ft.DatePicker(
        on_change=on_pick_to,
        first_date=today,
        last_date=today + timedelta(days=365),
    )
    state.page.overlay.append(picker_from)
    state.page.overlay.append(picker_to)
    free_from_field.on_focus = open_picker_from
    free_from_field.on_click = open_picker_from
    free_to_field.on_focus = open_picker_to
    free_to_field.on_click = open_picker_to

    def reset_filters(e):
        for field in (cat_select, capacity_select):
            field.value = ""
        for field in (min_price_field, max_price_field, free_from_field, free_to_field):
            field.value = ""
        for k in f_state:
            f_state[k] = None
        cat_select.update(); capacity_select.update()
        min_price_field.update(); max_price_field.update()
        free_from_field.update(); free_to_field.update()
        apply_filters(None)

    def apply_filters(e):
        f_state["category_id"] = int(cat_select.value) if cat_select.value else None
        f_state["capacity_min"] = int(capacity_select.value) if capacity_select.value else None
        try:
            f_state["min_price"] = float(min_price_field.value) if (min_price_field.value or "").strip() else None
            f_state["max_price"] = float(max_price_field.value) if (max_price_field.value or "").strip() else None
        except ValueError:
            show_toast(state.page, "Цена указана в неверном формате", p=p, kind="warning")
            return
        _, rooms = load_data()
        render_rooms(rooms)

    filters = card_container(
        ft.Column(
            [
                section_header(
                    "Фильтры", p=p,
                    action=ft.TextButton(
                        "Сбросить",
                        icon=ft.Icons.REFRESH,
                        on_click=reset_filters,
                        style=ft.ButtonStyle(color=p.text_muted),
                    ),
                ),
                ft.Container(height=8),
                ft.Row(
                    [cat_select, capacity_select, min_price_field, max_price_field],
                    spacing=Sizing.pad_md,
                    wrap=True,
                ),
                ft.Container(height=4),
                ft.Row(
                    [
                        ft.Container(content=free_from_field, expand=1),
                        ft.Container(content=free_to_field, expand=1),
                        ft.Container(
                            content=ft.ElevatedButton(
                                "Найти",
                                icon=ft.Icons.SEARCH,
                                on_click=apply_filters,
                                style=ft.ButtonStyle(
                                    bgcolor=p.brand,
                                    color=p.text_on_brand,
                                    shape=ft.RoundedRectangleBorder(radius=Sizing.radius_md),
                                    padding=ft.padding.symmetric(horizontal=24, vertical=18),
                                ),
                            ),
                            expand=1,
                        ),
                    ],
                    spacing=Sizing.pad_md,
                ),
            ],
            spacing=Sizing.pad_md,
        ),
        p=p,
    )

    body = ft.Column(
        [
            filters,
            ft.Container(height=Sizing.pad_md),
            section_header("Каталог номеров", p=p),
            ft.Container(height=Sizing.pad_sm),
            ft.Container(content=grid, expand=True),
        ],
        spacing=0,
        expand=True,
    )

    # initial load
    cats, rooms = load_data()
    cat_select.options = [ft.dropdown.Option(key="", text="Все категории")] + [
        ft.dropdown.Option(key=str(c["category_id"]), text=f"{c['title']} · от {fmt_money(c['base_price'])}")
        for c in cats
    ]
    render_rooms(rooms)

    return body
