"""Экран создания бронирования."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Callable

import flet as ft

from ..api import ApiError
from ..components.cards import card_container, fmt_money, section_header, status_chip
from ..components.toasts import show_toast
from ..state import AppState
from ..theme import Palette, Sizing


def booking_view(
    state: AppState, p: Palette, room: dict, *, on_done: Callable[[], None], on_back: Callable[[], None]
) -> ft.Control:
    today = date.today()
    selected = {
        "check_in": today + timedelta(days=1),
        "check_out": today + timedelta(days=3),
        "guests": 1,
        "service_ids": set(),
    }

    services = []
    try:
        services = state.api.list_services()
    except ApiError as exc:
        show_toast(state.page, exc.message, p=p, kind="danger")

    summary_text = ft.Text("", color=p.text, size=Sizing.body)
    is_free_chip = ft.Container(content=ft.Text("Проверяем...", size=Sizing.caption, color=p.text_muted))
    nights_text = ft.Text("", color=p.text_muted, size=Sizing.body)
    total_text = ft.Text("0 ₽", size=28, weight=ft.FontWeight.W_700, color=p.text)

    # ---- Date pickers ----
    check_in_field = _date_text(p, selected["check_in"])
    check_out_field = _date_text(p, selected["check_out"])

    def on_pick_in(e):
        if picker_in.value:
            d = picker_in.value.date() if hasattr(picker_in.value, "date") else picker_in.value
            selected["check_in"] = d
            check_in_field.value = d.strftime("%d.%m.%Y")
            check_in_field.update()
            recalc()

    def on_pick_out(e):
        if picker_out.value:
            d = picker_out.value.date() if hasattr(picker_out.value, "date") else picker_out.value
            selected["check_out"] = d
            check_out_field.value = d.strftime("%d.%m.%Y")
            check_out_field.update()
            recalc()

    picker_in = ft.DatePicker(on_change=on_pick_in, first_date=today, last_date=today + timedelta(days=365), value=selected["check_in"])
    picker_out = ft.DatePicker(on_change=on_pick_out, first_date=today + timedelta(days=1), last_date=today + timedelta(days=365), value=selected["check_out"])
    state.page.overlay.append(picker_in)
    state.page.overlay.append(picker_out)

    def open_in(e):
        state.page.open(picker_in)

    def open_out(e):
        state.page.open(picker_out)

    check_in_field.on_focus = open_in
    check_in_field.on_click = open_in
    check_out_field.on_focus = open_out
    check_out_field.on_click = open_out

    # ---- Guests selector ----

    guests = ft.Dropdown(
        label="Количество гостей",
        value="1",
        options=[ft.dropdown.Option(str(i)) for i in range(1, room["capacity"] + 1)],
        text_size=Sizing.body,
        bgcolor=p.surface,
        border_radius=Sizing.radius_md,
        border_color=p.border,
        focused_border_color=p.brand,
        label_style=ft.TextStyle(color=p.text_muted, size=Sizing.body),
        text_style=ft.TextStyle(color=p.text, size=Sizing.body),
        on_change=lambda e: (selected.__setitem__("guests", int(guests.value)), recalc()),
    )

    # ---- Services list (checkboxes) ----

    def toggle_service(svc_id: int):
        def _handler(e):
            if e.control.value:
                selected["service_ids"].add(svc_id)
            else:
                selected["service_ids"].discard(svc_id)
            recalc()
        return _handler

    service_rows = [
        ft.Row(
            [
                ft.Checkbox(
                    value=False,
                    on_change=toggle_service(svc["service_id"]),
                    fill_color=p.brand,
                    check_color=p.text_on_brand,
                ),
                ft.Column(
                    [
                        ft.Text(svc["title"], size=Sizing.body, color=p.text, weight=ft.FontWeight.W_500),
                        ft.Text(svc.get("description") or "—", size=Sizing.caption, color=p.text_muted),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Text(fmt_money(svc["price"]), size=Sizing.body, weight=ft.FontWeight.W_600, color=p.text),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        for svc in services
        if svc.get("is_active", True)
    ]

    notes_field = ft.TextField(
        label="Комментарий администратору (необязательно)",
        multiline=True,
        min_lines=2,
        max_lines=4,
        border_color=p.border,
        focused_border_color=p.brand,
        bgcolor=p.surface,
        border_radius=Sizing.radius_md,
        text_size=Sizing.body,
        label_style=ft.TextStyle(color=p.text_muted, size=Sizing.body),
        text_style=ft.TextStyle(color=p.text, size=Sizing.body),
    )

    error_text = ft.Text("", color=p.danger, size=Sizing.caption)

    # ---- Recalculate ----

    def recalc():
        if selected["check_out"] <= selected["check_in"]:
            is_free_chip.content = ft.Text("Дата выезда должна быть позже заезда", color=p.danger, size=Sizing.caption)
            is_free_chip.update()
            total_text.value = "—"
            total_text.update()
            return
        try:
            data = state.api.calculate_booking(
                room_id=room["room_id"],
                check_in=selected["check_in"],
                check_out=selected["check_out"],
                service_ids=list(selected["service_ids"]),
            )
        except ApiError as exc:
            is_free_chip.content = ft.Text(exc.message, color=p.danger, size=Sizing.caption)
            is_free_chip.update()
            return

        nights = data["nights"]
        is_free_chip.content = (
            status_chip("Свободно", p=p, kind="success") if data["is_room_free"]
            else status_chip("Занято — выберите другие даты", p=p, kind="danger")
        )
        is_free_chip.update()
        nights_text.value = f"{nights} ночей × {fmt_money(room['price_per_night'])}"
        nights_text.update()
        total_text.value = fmt_money(data["total_price"])
        total_text.update()

    def submit(e):
        error_text.value = ""
        try:
            booking = state.api.create_booking(
                room_id=room["room_id"],
                check_in=selected["check_in"],
                check_out=selected["check_out"],
                guests_count=int(guests.value),
                service_ids=list(selected["service_ids"]),
                notes=notes_field.value or None,
            )
        except ApiError as exc:
            error_text.value = exc.message
            error_text.update()
            show_toast(state.page, exc.message, p=p, kind="danger")
            return
        show_toast(state.page, f"Бронь №{booking['booking_id']} создана", p=p, kind="success")
        on_done()

    # ---- Layout ----

    left_col = ft.Column(
        [
            section_header(
                f"Бронирование номера {room['room_number']}", p=p,
                action=ft.TextButton(
                    "Назад", icon=ft.Icons.ARROW_BACK, on_click=lambda e: on_back(),
                    style=ft.ButtonStyle(color=p.text_muted),
                ),
            ),
            ft.Text(room["category_title"], size=Sizing.h3, color=p.text_muted),
            ft.Container(height=Sizing.pad_md),
            card_container(
                ft.Column(
                    [
                        ft.Text("Период проживания", size=Sizing.h3, weight=ft.FontWeight.W_600, color=p.text),
                        ft.Container(height=8),
                        ft.Row(
                            [
                                ft.Container(content=check_in_field, expand=1),
                                ft.Container(content=check_out_field, expand=1),
                                ft.Container(content=guests, expand=1),
                            ],
                            spacing=Sizing.pad_md,
                        ),
                    ],
                    spacing=4,
                ),
                p=p,
            ),
            ft.Container(height=Sizing.pad_md),
            card_container(
                ft.Column(
                    [
                        ft.Text("Дополнительные услуги", size=Sizing.h3, weight=ft.FontWeight.W_600, color=p.text),
                        ft.Container(height=4),
                        *(service_rows or [ft.Text("Нет доступных услуг", color=p.text_muted)]),
                    ],
                    spacing=8,
                ),
                p=p,
            ),
            ft.Container(height=Sizing.pad_md),
            card_container(notes_field, p=p),
        ],
        spacing=0,
        expand=True,
    )

    right_col = ft.Container(
        content=ft.Column(
            [
                ft.Text("Сводка заказа", size=Sizing.h3, weight=ft.FontWeight.W_600, color=p.text),
                ft.Container(height=Sizing.pad_md),
                ft.Row(
                    [
                        ft.Text("Доступность:", color=p.text_muted),
                        is_free_chip,
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=4),
                nights_text,
                ft.Container(height=Sizing.pad_md),
                ft.Divider(color=p.border, height=1),
                ft.Container(height=Sizing.pad_md),
                ft.Row(
                    [
                        ft.Text("Итого", color=p.text_muted, size=Sizing.body),
                        ft.Container(expand=True),
                        total_text,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=Sizing.pad_md),
                error_text,
                ft.ElevatedButton(
                    "Подтвердить бронирование",
                    icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                    on_click=submit,
                    style=ft.ButtonStyle(
                        bgcolor=p.brand,
                        color=p.text_on_brand,
                        padding=ft.padding.symmetric(horizontal=24, vertical=18),
                        shape=ft.RoundedRectangleBorder(radius=Sizing.radius_md),
                        text_style=ft.TextStyle(weight=ft.FontWeight.W_600, size=Sizing.body),
                    ),
                ),
            ],
            spacing=0,
        ),
        bgcolor=p.surface,
        padding=Sizing.pad_lg,
        border_radius=Sizing.radius_lg,
        border=ft.border.all(1, p.border),
        width=380,
    )

    layout = ft.Row(
        [
            ft.Container(content=left_col, expand=True),
            right_col,
        ],
        spacing=Sizing.pad_lg,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    recalc()
    return layout


def _date_text(p: Palette, value: date) -> ft.TextField:
    return ft.TextField(
        label="Дата",
        value=value.strftime("%d.%m.%Y"),
        read_only=True,
        suffix_icon=ft.Icons.CALENDAR_MONTH,
        text_size=Sizing.body,
        bgcolor=p.surface,
        border_color=p.border,
        focused_border_color=p.brand,
        border_radius=Sizing.radius_md,
        label_style=ft.TextStyle(color=p.text_muted, size=Sizing.body),
        text_style=ft.TextStyle(color=p.text, size=Sizing.body),
    )
