"""Админ-панель: пользователи, бронирования, аудит, отчёты."""

from __future__ import annotations

import os
import tempfile
from datetime import date, timedelta

import flet as ft

from ..api import ApiError
from ..components.cards import card_container, fmt_money, section_header, status_chip
from ..components.toasts import show_toast
from ..state import AppState
from ..theme import Palette, Sizing


def admin_view(state: AppState, p: Palette) -> ft.Control:
    """Админ-панель с табами."""
    return ft.Column(
        [
            section_header("Администрирование", p=p),
            ft.Container(height=Sizing.pad_md),
            ft.Tabs(
                selected_index=0,
                indicator_color=p.brand,
                label_color=p.brand,
                unselected_label_color=p.text_muted,
                divider_color=p.border,
                indicator_padding=ft.padding.only(bottom=4),
                indicator_thickness=3,
                tabs=[
                    ft.Tab(text="Бронирования", content=_bookings_tab(state, p)),
                    ft.Tab(text="Пользователи", content=_users_tab(state, p)),
                    ft.Tab(text="Отчёты", content=_reports_tab(state, p)),
                    ft.Tab(text="Журнал аудита", content=_audit_tab(state, p)),
                ],
                expand=True,
            ),
        ],
        spacing=0,
        expand=True,
    )


# ---------------------------------------------------------------------------
# Бронирования
# ---------------------------------------------------------------------------


def _bookings_tab(state: AppState, p: Palette) -> ft.Control:
    table = ft.DataTable(
        columns=[
            ft.DataColumn(label=ft.Text("№", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Гость", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Номер", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Заезд", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Выезд", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Статус", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Сумма", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Действия", color=p.text_muted)),
        ],
        rows=[],
        heading_row_color=p.surface_alt,
        data_row_color={ft.ControlState.HOVERED: p.surface_alt},
        border=ft.border.all(1, p.border),
        border_radius=Sizing.radius_md,
        column_spacing=20,
    )

    def reload():
        try:
            bookings = state.api.all_bookings()
        except ApiError as exc:
            show_toast(state.page, exc.message, p=p, kind="danger")
            return
        rows = []
        for b in bookings:
            actions: list[ft.Control] = []
            if b["status"] == "pending":
                actions.append(_action_btn(p, "Подтвердить", ft.Icons.CHECK,
                                           lambda e, bid=b["booking_id"]: _change_status(state, p, bid, "confirmed", reload)))
            if b["status"] == "confirmed":
                actions.append(_action_btn(p, "Заселить", ft.Icons.LOGIN,
                                           lambda e, bid=b["booking_id"]: _change_status(state, p, bid, "checked_in", reload)))
            if b["status"] == "checked_in":
                actions.append(_action_btn(p, "Выписать", ft.Icons.LOGOUT,
                                           lambda e, bid=b["booking_id"]: _change_status(state, p, bid, "checked_out", reload)))
            if b["status"] in ("pending", "confirmed"):
                actions.append(_action_btn(p, "Отменить", ft.Icons.CLOSE,
                                           lambda e, bid=b["booking_id"]: _change_status(state, p, bid, "cancelled", reload),
                                           danger=True))
            rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(b["booking_id"]), color=p.text)),
                    ft.DataCell(ft.Column(
                        [ft.Text(b["guest_name"], color=p.text, size=Sizing.body),
                         ft.Text(b["guest_email"], color=p.text_muted, size=Sizing.caption)],
                        spacing=0,
                    )),
                    ft.DataCell(ft.Text(f"{b['room_number']} · {b['category_title']}", color=p.text)),
                    ft.DataCell(ft.Text(_fmt_date(b["check_in"]), color=p.text)),
                    ft.DataCell(ft.Text(_fmt_date(b["check_out"]), color=p.text)),
                    ft.DataCell(_status_cell(b["status"], p)),
                    ft.DataCell(ft.Text(fmt_money(b["total_price"]), color=p.text, weight=ft.FontWeight.W_600)),
                    ft.DataCell(ft.Row(actions, spacing=4)),
                ])
            )
        table.rows = rows
        if table.page is not None:
            table.update()

    body = ft.Column(
        [
            ft.Container(height=Sizing.pad_md),
            ft.Row([
                ft.TextButton(
                    "Обновить",
                    icon=ft.Icons.REFRESH,
                    on_click=lambda e: reload(),
                    style=ft.ButtonStyle(color=p.text_muted),
                ),
            ]),
            ft.Container(content=ft.Row([table], scroll=ft.ScrollMode.AUTO), expand=True),
        ],
        spacing=Sizing.pad_md,
        expand=True,
    )
    reload()
    return body


def _change_status(state: AppState, p: Palette, booking_id: int, new_status: str, reload):
    try:
        if new_status == "cancelled":
            state.api.cancel_booking(booking_id)
        else:
            state.api.update_booking_status(booking_id, new_status)
    except ApiError as exc:
        show_toast(state.page, exc.message, p=p, kind="danger")
        return
    show_toast(state.page, f"Бронь №{booking_id}: статус → {new_status}", p=p, kind="success")
    reload()


def _action_btn(p: Palette, text: str, icon: str, handler, *, danger: bool = False) -> ft.Control:
    color = p.danger if danger else p.brand
    return ft.TextButton(
        text=text,
        icon=icon,
        on_click=handler,
        style=ft.ButtonStyle(
            color={ft.ControlState.DEFAULT: color},
            text_style=ft.TextStyle(weight=ft.FontWeight.W_500, size=Sizing.caption),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
        ),
    )


# ---------------------------------------------------------------------------
# Пользователи
# ---------------------------------------------------------------------------


def _users_tab(state: AppState, p: Palette) -> ft.Control:
    table = ft.DataTable(
        columns=[
            ft.DataColumn(label=ft.Text("ID", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Email", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("ФИО", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Телефон", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Роль", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Статус", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Действия", color=p.text_muted)),
        ],
        rows=[],
        heading_row_color=p.surface_alt,
        data_row_color={ft.ControlState.HOVERED: p.surface_alt},
        border=ft.border.all(1, p.border),
        border_radius=Sizing.radius_md,
        column_spacing=20,
    )

    if not state.current_user or state.current_user.role != "admin":
        return ft.Container(
            content=ft.Text("Управление пользователями доступно только администратору.", color=p.text_muted),
            padding=Sizing.pad_lg,
        )

    def reload():
        try:
            users = state.api.list_users()
        except ApiError as exc:
            show_toast(state.page, exc.message, p=p, kind="danger")
            return
        rows = []
        for u in users:
            role_dropdown = ft.Dropdown(
                value=u["role"],
                width=140,
                bgcolor=p.surface,
                border_color=p.border,
                border_radius=Sizing.radius_md,
                text_style=ft.TextStyle(color=p.text, size=Sizing.body),
                options=[
                    ft.dropdown.Option(key="guest", text="Гость"),
                    ft.dropdown.Option(key="manager", text="Менеджер"),
                    ft.dropdown.Option(key="admin", text="Админ"),
                ],
            )
            active_switch = ft.Switch(value=u["is_active"], active_color=p.brand)

            def save(e, uid=u["user_id"], rd=role_dropdown, sw=active_switch):
                try:
                    state.api.update_user(uid, role_code=rd.value, is_active=sw.value)
                except ApiError as exc:
                    show_toast(state.page, exc.message, p=p, kind="danger")
                    return
                show_toast(state.page, "Сохранено", p=p, kind="success")
                reload()

            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(u["user_id"]), color=p.text)),
                ft.DataCell(ft.Text(u["email"], color=p.text)),
                ft.DataCell(ft.Text(u["full_name"], color=p.text)),
                ft.DataCell(ft.Text(u.get("phone") or "—", color=p.text_muted)),
                ft.DataCell(role_dropdown),
                ft.DataCell(active_switch),
                ft.DataCell(_action_btn(p, "Сохранить", ft.Icons.SAVE_OUTLINED, save)),
            ]))
        table.rows = rows
        if table.page is not None:
            table.update()

    body = ft.Column(
        [
            ft.Container(height=Sizing.pad_md),
            ft.Row([
                ft.TextButton(
                    "Обновить",
                    icon=ft.Icons.REFRESH,
                    on_click=lambda e: reload(),
                    style=ft.ButtonStyle(color=p.text_muted),
                ),
            ]),
            ft.Container(content=ft.Row([table], scroll=ft.ScrollMode.AUTO), expand=True),
        ],
        spacing=Sizing.pad_md,
        expand=True,
    )
    reload()
    return body


# ---------------------------------------------------------------------------
# Отчёты
# ---------------------------------------------------------------------------


def _reports_tab(state: AppState, p: Palette) -> ft.Control:
    revenue_table = ft.DataTable(
        columns=[
            ft.DataColumn(label=ft.Text("Категория", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Бронирований", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Выручка", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Оплачено", color=p.text_muted)),
        ],
        rows=[],
        heading_row_color=p.surface_alt,
        border=ft.border.all(1, p.border),
        border_radius=Sizing.radius_md,
        column_spacing=24,
    )

    occupancy_text = ft.Text("—", size=Sizing.h1, weight=ft.FontWeight.W_700, color=p.text)
    occupancy_meta = ft.Text("Загрузка номерного фонда", size=Sizing.body, color=p.text_muted)

    today = date.today()
    period_start = ft.TextField(
        label="С",
        value=(today - timedelta(days=30)).strftime("%d.%m.%Y"),
        read_only=True,
        suffix_icon=ft.Icons.CALENDAR_MONTH,
        bgcolor=p.surface, border_color=p.border, border_radius=Sizing.radius_md,
        text_style=ft.TextStyle(color=p.text, size=Sizing.body),
        label_style=ft.TextStyle(color=p.text_muted, size=Sizing.body),
    )
    period_end = ft.TextField(
        label="По",
        value=today.strftime("%d.%m.%Y"),
        read_only=True,
        suffix_icon=ft.Icons.CALENDAR_MONTH,
        bgcolor=p.surface, border_color=p.border, border_radius=Sizing.radius_md,
        text_style=ft.TextStyle(color=p.text, size=Sizing.body),
        label_style=ft.TextStyle(color=p.text_muted, size=Sizing.body),
    )
    state_dates = {"start": today - timedelta(days=30), "end": today}

    def load_revenue():
        try:
            data = state.api.revenue_report()
        except ApiError as exc:
            show_toast(state.page, exc.message, p=p, kind="danger")
            return
        revenue_table.rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(r["category_title"], color=p.text)),
                ft.DataCell(ft.Text(str(r["bookings_count"]), color=p.text)),
                ft.DataCell(ft.Text(fmt_money(r["revenue_total"]), color=p.text, weight=ft.FontWeight.W_600)),
                ft.DataCell(ft.Text(fmt_money(r["revenue_paid"]), color=p.text_muted)),
            ]) for r in data
        ]
        if revenue_table.page is not None:
            revenue_table.update()

    def load_occupancy():
        try:
            data = state.api.occupancy_report(state_dates["start"], state_dates["end"])
        except ApiError as exc:
            show_toast(state.page, exc.message, p=p, kind="danger")
            return
        occupancy_text.value = f"{data['occupancy_pct']:.1f}%"
        if occupancy_text.page is not None:
            occupancy_text.update()
        occupancy_meta.value = (
            f"за период {data['period_start']} — {data['period_end']}"
        )
        if occupancy_meta.page is not None:
            occupancy_meta.update()

    def download(kind: str, e):
        try:
            if kind == "revenue":
                data = state.api.revenue_pdf()
                name = "revenue_report.pdf"
            else:
                data = state.api.occupancy_pdf(state_dates["start"], state_dates["end"])
                name = "occupancy_report.pdf"
        except ApiError as exc:
            show_toast(state.page, exc.message, p=p, kind="danger")
            return
        downloads = os.path.expanduser("~/Downloads")
        if not os.path.isdir(downloads):
            downloads = tempfile.gettempdir()
        path = os.path.join(downloads, name)
        with open(path, "wb") as fh:
            fh.write(data)
        show_toast(state.page, f"PDF сохранён: {path}", p=p, kind="success")

    pick_start = ft.DatePicker(
        first_date=today - timedelta(days=365),
        last_date=today,
        on_change=lambda e: _on_pick(period_start, "start", state_dates, pick_start, load_occupancy),
    )
    pick_end = ft.DatePicker(
        first_date=today - timedelta(days=365),
        last_date=today,
        on_change=lambda e: _on_pick(period_end, "end", state_dates, pick_end, load_occupancy),
    )
    state.page.overlay.append(pick_start)
    state.page.overlay.append(pick_end)
    period_start.on_focus = lambda e: state.page.open(pick_start)
    period_start.on_click = lambda e: state.page.open(pick_start)
    period_end.on_focus = lambda e: state.page.open(pick_end)
    period_end.on_click = lambda e: state.page.open(pick_end)

    body = ft.Column(
        [
            ft.Container(height=Sizing.pad_md),
            ft.Row([
                ft.Container(
                    content=ft.Column([
                        ft.Text("Загрузка фонда", size=Sizing.h3, weight=ft.FontWeight.W_600, color=p.text),
                        ft.Container(height=4),
                        occupancy_meta,
                        ft.Container(height=12),
                        occupancy_text,
                        ft.Container(height=12),
                        ft.Row([period_start, period_end], spacing=12),
                        ft.Container(height=12),
                        ft.OutlinedButton(
                            "Скачать PDF",
                            icon=ft.Icons.DOWNLOAD,
                            on_click=lambda e: download("occupancy", e),
                            style=ft.ButtonStyle(
                                color=p.brand,
                                side=ft.BorderSide(1, p.brand),
                                shape=ft.RoundedRectangleBorder(radius=Sizing.radius_md),
                            ),
                        ),
                    ], spacing=0),
                    bgcolor=p.surface,
                    padding=Sizing.pad_lg,
                    border_radius=Sizing.radius_lg,
                    border=ft.border.all(1, p.border),
                    expand=1,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("Выручка по категориям", size=Sizing.h3, weight=ft.FontWeight.W_600, color=p.text),
                            ft.Container(expand=True),
                            ft.OutlinedButton(
                                "Скачать PDF",
                                icon=ft.Icons.DOWNLOAD,
                                on_click=lambda e: download("revenue", e),
                                style=ft.ButtonStyle(
                                    color=p.brand,
                                    side=ft.BorderSide(1, p.brand),
                                    shape=ft.RoundedRectangleBorder(radius=Sizing.radius_md),
                                ),
                            ),
                        ]),
                        ft.Container(height=12),
                        ft.Container(content=ft.Row([revenue_table], scroll=ft.ScrollMode.AUTO)),
                    ]),
                    bgcolor=p.surface,
                    padding=Sizing.pad_lg,
                    border_radius=Sizing.radius_lg,
                    border=ft.border.all(1, p.border),
                    expand=2,
                ),
            ], spacing=Sizing.pad_md, vertical_alignment=ft.CrossAxisAlignment.START),
        ],
        spacing=Sizing.pad_md,
        expand=True,
    )

    load_revenue()
    load_occupancy()
    return body


def _on_pick(field, key: str, state_dates: dict, picker: ft.DatePicker, callback):
    if picker.value:
        d = picker.value.date() if hasattr(picker.value, "date") else picker.value
        state_dates[key] = d
        field.value = d.strftime("%d.%m.%Y")
        field.update()
        callback()


# ---------------------------------------------------------------------------
# Аудит
# ---------------------------------------------------------------------------


def _audit_tab(state: AppState, p: Palette) -> ft.Control:
    if not state.current_user or state.current_user.role != "admin":
        return ft.Container(
            content=ft.Text("Журнал аудита доступен только администратору.", color=p.text_muted),
            padding=Sizing.pad_lg,
        )

    table = ft.DataTable(
        columns=[
            ft.DataColumn(label=ft.Text("Когда", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Таблица", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Запись", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Действие", color=p.text_muted)),
            ft.DataColumn(label=ft.Text("Пользователь", color=p.text_muted)),
        ],
        rows=[],
        heading_row_color=p.surface_alt,
        border=ft.border.all(1, p.border),
        border_radius=Sizing.radius_md,
        column_spacing=24,
    )
    table_select = ft.Dropdown(
        label="Таблица",
        value="",
        width=200,
        bgcolor=p.surface, border_color=p.border, border_radius=Sizing.radius_md,
        text_style=ft.TextStyle(color=p.text, size=Sizing.body),
        label_style=ft.TextStyle(color=p.text_muted, size=Sizing.body),
        options=[
            ft.dropdown.Option(key="", text="Все таблицы"),
            ft.dropdown.Option(key="bookings", text="bookings"),
            ft.dropdown.Option(key="users", text="users"),
            ft.dropdown.Option(key="rooms", text="rooms"),
        ],
    )

    def reload():
        try:
            entries = state.api.audit_log(table_name=(table_select.value or None), limit=200)
        except ApiError as exc:
            show_toast(state.page, exc.message, p=p, kind="danger")
            return
        rows = []
        for entry in entries:
            kind = {
                "INSERT": "success",
                "UPDATE": "info",
                "DELETE": "danger",
            }.get(entry["action"], "neutral")
            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(_fmt_dt(entry["happened_at"]), color=p.text)),
                ft.DataCell(ft.Text(entry["table_name"], color=p.text)),
                ft.DataCell(ft.Text(entry["row_pk"], color=p.text_muted)),
                ft.DataCell(status_chip(entry["action"], p=p, kind=kind)),
                ft.DataCell(ft.Text(entry.get("actor_name") or "—", color=p.text)),
            ]))
        table.rows = rows
        if table.page is not None:
            table.update()

    table_select.on_change = lambda e: reload()
    body = ft.Column(
        [
            ft.Container(height=Sizing.pad_md),
            ft.Row([
                table_select,
                ft.Container(expand=True),
                ft.TextButton(
                    "Обновить",
                    icon=ft.Icons.REFRESH,
                    on_click=lambda e: reload(),
                    style=ft.ButtonStyle(color=p.text_muted),
                ),
            ]),
            ft.Container(content=ft.Row([table], scroll=ft.ScrollMode.AUTO), expand=True),
        ],
        spacing=Sizing.pad_md,
        expand=True,
    )
    reload()
    return body


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _status_cell(status: str, p: Palette) -> ft.Control:
    kind = {
        "pending": "warning",
        "confirmed": "info",
        "checked_in": "success",
        "checked_out": "neutral",
        "cancelled": "danger",
    }.get(status, "neutral")
    label = {
        "pending": "Ожидает",
        "confirmed": "Подтверждено",
        "checked_in": "Заселён",
        "checked_out": "Выписан",
        "cancelled": "Отменено",
    }.get(status, status)
    return status_chip(label, p=p, kind=kind)


def _fmt_date(value) -> str:
    from datetime import date as _date, datetime as _dt
    if isinstance(value, str):
        try:
            return _date.fromisoformat(value).strftime("%d.%m.%Y")
        except ValueError:
            return value
    if isinstance(value, (_date, _dt)):
        return value.strftime("%d.%m.%Y")
    return str(value)


def _fmt_dt(value) -> str:
    from datetime import datetime as _dt
    if isinstance(value, str):
        try:
            return _dt.fromisoformat(value.replace("Z", "+00:00")).strftime("%d.%m.%Y %H:%M")
        except ValueError:
            return value
    if isinstance(value, _dt):
        return value.strftime("%d.%m.%Y %H:%M")
    return str(value)
