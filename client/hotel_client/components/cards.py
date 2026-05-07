"""Карточки в фирменном стиле — для номеров, бронирований и т. п."""

from __future__ import annotations

from decimal import Decimal

import flet as ft

from ..theme import Palette, Sizing


def card_container(content: ft.Control, *, p: Palette, padding: int = Sizing.pad_lg) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=p.surface,
        padding=padding,
        border_radius=Sizing.radius_lg,
        border=ft.border.all(1, p.border),
    )


def section_header(title: str, *, p: Palette, action: ft.Control | None = None) -> ft.Row:
    return ft.Row(
        controls=[
            ft.Text(title, size=Sizing.h2, weight=ft.FontWeight.W_700, color=p.text),
            ft.Container(expand=True),
            action or ft.Container(),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def status_chip(text: str, *, p: Palette, kind: str = "info") -> ft.Container:
    color_map = {
        "success": p.success,
        "warning": p.warning,
        "danger": p.danger,
        "info": p.info,
        "neutral": p.text_muted,
    }
    fg = color_map.get(kind, p.info)
    return ft.Container(
        content=ft.Text(text, size=Sizing.caption, color=fg, weight=ft.FontWeight.W_600),
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
        bgcolor=ft.Colors.with_opacity(0.12, fg),
        border_radius=999,
    )


def fmt_money(value) -> str:
    if value is None:
        return "—"
    try:
        amount = Decimal(value)
    except Exception:  # noqa: BLE001
        return str(value)
    return f"{amount:,.0f} ₽".replace(",", " ")


# ---------------------------------------------------------------------------
# Карточка номера
# ---------------------------------------------------------------------------


def room_card(room: dict, *, p: Palette, on_book=None, on_open=None) -> ft.Container:
    amenities = room.get("amenities") or []
    amenity_chips = [
        ft.Container(
            content=ft.Text(_amenity_title(a), size=Sizing.caption, color=p.text_muted),
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
            bgcolor=p.surface_alt,
            border_radius=999,
        )
        for a in amenities[:5]
    ]
    if len(amenities) > 5:
        amenity_chips.append(
            ft.Container(
                content=ft.Text(f"+{len(amenities) - 5}", size=Sizing.caption, color=p.text_muted),
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                bgcolor=p.surface_alt,
                border_radius=999,
            )
        )

    status_color = {
        "available": "success",
        "occupied": "danger",
        "reserved": "warning",
        "cleaning": "info",
        "maintenance": "neutral",
    }.get(room["status"], "neutral")

    actions = []
    if on_open:
        actions.append(ft.TextButton("Подробнее", on_click=on_open, style=ft.ButtonStyle(color=p.brand)))
    if on_book:
        actions.append(
            ft.ElevatedButton(
                "Забронировать",
                icon=ft.Icons.CALENDAR_TODAY,
                on_click=on_book,
                style=ft.ButtonStyle(
                    bgcolor=p.brand,
                    color=p.text_on_brand,
                    shape=ft.RoundedRectangleBorder(radius=Sizing.radius_md),
                    padding=ft.padding.symmetric(horizontal=18, vertical=12),
                ),
            )
        )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    f"№ {room['room_number']} · {_floor_label(room['floor'])}",
                                    size=Sizing.caption,
                                    color=p.text_muted,
                                ),
                                ft.Text(
                                    room["category_title"],
                                    size=Sizing.h3,
                                    weight=ft.FontWeight.W_600,
                                    color=p.text,
                                ),
                            ],
                            spacing=2,
                        ),
                        ft.Container(expand=True),
                        status_chip(_status_label(room["status"]), p=p, kind=status_color),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Container(height=8),
                ft.Row(
                    [
                        ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=16, color=p.text_muted),
                        ft.Text(f"до {room['capacity']} гостей", color=p.text_muted, size=Sizing.body),
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=8),
                ft.Row(amenity_chips, wrap=True, spacing=6, run_spacing=6),
                ft.Container(height=12),
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Цена за ночь", size=Sizing.caption, color=p.text_muted),
                                ft.Text(
                                    fmt_money(room["price_per_night"]),
                                    size=Sizing.h2,
                                    weight=ft.FontWeight.W_700,
                                    color=p.text,
                                ),
                            ],
                            spacing=2,
                        ),
                        ft.Container(expand=True),
                        ft.Row(actions, spacing=6),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=4,
        ),
        bgcolor=p.surface,
        padding=Sizing.pad_lg,
        border_radius=Sizing.radius_lg,
        border=ft.border.all(1, p.border),
    )


def _floor_label(floor: int) -> str:
    return f"{floor}-й этаж"


def _status_label(status: str) -> str:
    return {
        "available": "Свободен",
        "occupied": "Занят",
        "reserved": "Забронирован",
        "cleaning": "Уборка",
        "maintenance": "Ремонт",
    }.get(status, status)


def _amenity_title(code: str) -> str:
    return {
        "wifi": "Wi-Fi",
        "air_cond": "Кондиционер",
        "mini_bar": "Мини-бар",
        "safe": "Сейф",
        "tv": "ТВ",
        "balcony": "Балкон",
        "bath_tub": "Ванна",
        "coffee_maker": "Кофемашина",
        "view_river": "Вид на реку",
        "soundproof": "Звукоизоляция",
    }.get(code, code)


# ---------------------------------------------------------------------------
# Карточка бронирования
# ---------------------------------------------------------------------------

def booking_card(booking: dict, *, p: Palette, on_pdf=None, on_cancel=None) -> ft.Control:
    status_kind = {
        "pending": "warning",
        "confirmed": "info",
        "checked_in": "success",
        "checked_out": "neutral",
        "cancelled": "danger",
    }.get(booking["status"], "neutral")
    status_label = {
        "pending": "Ожидает подтверждения",
        "confirmed": "Подтверждено",
        "checked_in": "Заселён",
        "checked_out": "Завершено",
        "cancelled": "Отменено",
    }.get(booking["status"], booking["status"])

    actions: list[ft.Control] = []
    if on_pdf:
        actions.append(
            ft.OutlinedButton(
                "Скачать PDF",
                icon=ft.Icons.DOWNLOAD,
                on_click=on_pdf,
                style=ft.ButtonStyle(
                    color=p.brand,
                    side=ft.BorderSide(1, p.brand),
                    shape=ft.RoundedRectangleBorder(radius=Sizing.radius_md),
                ),
            )
        )
    if on_cancel and booking["status"] in ("pending", "confirmed"):
        actions.append(
            ft.OutlinedButton(
                "Отменить",
                icon=ft.Icons.CLOSE,
                on_click=on_cancel,
                style=ft.ButtonStyle(
                    color=p.danger,
                    side=ft.BorderSide(1, p.danger),
                    shape=ft.RoundedRectangleBorder(radius=Sizing.radius_md),
                ),
            )
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    f"Бронь №{booking['booking_id']}",
                                    size=Sizing.caption,
                                    color=p.text_muted,
                                ),
                                ft.Text(
                                    f"Номер {booking['room_number']} · {booking['category_title']}",
                                    size=Sizing.h3,
                                    weight=ft.FontWeight.W_600,
                                    color=p.text,
                                ),
                            ],
                            spacing=2,
                        ),
                        ft.Container(expand=True),
                        status_chip(status_label, p=p, kind=status_kind),
                    ],
                ),
                ft.Container(height=10),
                ft.Row(
                    [
                        _kv("Заезд", _ru_date(booking["check_in"]), p),
                        _kv("Выезд", _ru_date(booking["check_out"]), p),
                        _kv("Ночей", str(booking["nights"]), p),
                        _kv("Гостей", str(booking.get("guests_count", "—")), p),
                    ],
                    spacing=20,
                    wrap=True,
                ),
                ft.Container(height=14),
                ft.Row(
                    [
                        _kv("Сумма", fmt_money(booking["total_price"]), p, large=True),
                        _kv("Оплачено", fmt_money(booking["paid_total"]), p, large=True),
                        _kv("К оплате", fmt_money(booking["amount_due"]), p, large=True, accent=True),
                    ],
                    spacing=20,
                    wrap=True,
                ),
                ft.Container(height=12),
                ft.Row(actions, spacing=10),
            ],
            spacing=2,
        ),
        bgcolor=p.surface,
        padding=Sizing.pad_lg,
        border_radius=Sizing.radius_lg,
        border=ft.border.all(1, p.border),
    )


def _kv(label: str, value: str, p: Palette, *, large: bool = False, accent: bool = False) -> ft.Column:
    return ft.Column(
        [
            ft.Text(label, size=Sizing.caption, color=p.text_muted),
            ft.Text(
                value,
                size=Sizing.h3 if large else Sizing.body,
                weight=ft.FontWeight.W_700 if large else ft.FontWeight.W_500,
                color=p.brand if accent else p.text,
            ),
        ],
        spacing=2,
    )


def _ru_date(value) -> str:
    from datetime import date as _date, datetime as _dt
    if isinstance(value, str):
        try:
            value = _date.fromisoformat(value)
        except ValueError:
            return value
    if isinstance(value, (_date, _dt)):
        return value.strftime("%d.%m.%Y")
    return str(value)
