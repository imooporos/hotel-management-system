"""Список бронирований текущего пользователя."""

from __future__ import annotations

import os
import tempfile

import flet as ft

from ..api import ApiError
from ..components.cards import booking_card, section_header
from ..components.toasts import show_toast
from ..state import AppState
from ..theme import Palette, Sizing


def my_bookings_view(state: AppState, p: Palette) -> ft.Control:
    container = ft.Column(spacing=Sizing.pad_md, expand=True)

    def reload():
        try:
            bookings = state.api.my_bookings()
        except ApiError as exc:
            show_toast(state.page, exc.message, p=p, kind="danger")
            return
        if not bookings:
            container.controls = [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, size=48, color=p.text_muted),
                            ft.Text("У вас пока нет бронирований", color=p.text_muted, size=Sizing.body),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=Sizing.pad_xl,
                    alignment=ft.alignment.center,
                )
            ]
        else:
            container.controls = [
                booking_card(
                    b,
                    p=p,
                    on_pdf=lambda e, bid=b["booking_id"]: download_pdf(bid),
                    on_cancel=lambda e, bid=b["booking_id"]: cancel(bid),
                )
                for b in bookings
            ]
        container.update()

    def download_pdf(booking_id: int):
        try:
            data = state.api.receipt_pdf(booking_id)
        except ApiError as exc:
            show_toast(state.page, exc.message, p=p, kind="danger")
            return
        downloads = os.path.expanduser("~/Downloads")
        if not os.path.isdir(downloads):
            downloads = tempfile.gettempdir()
        path = os.path.join(downloads, f"booking_{booking_id}.pdf")
        with open(path, "wb") as fh:
            fh.write(data)
        show_toast(state.page, f"PDF сохранён: {path}", p=p, kind="success")

    def cancel(booking_id: int):
        def confirm(e):
            state.page.close(dialog)
            try:
                state.api.cancel_booking(booking_id)
            except ApiError as exc:
                show_toast(state.page, exc.message, p=p, kind="danger")
                return
            show_toast(state.page, f"Бронь №{booking_id} отменена", p=p, kind="success")
            reload()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Отменить бронирование №{booking_id}?"),
            content=ft.Text("Это действие нельзя отменить."),
            actions=[
                ft.TextButton("Не отменять", on_click=lambda e: state.page.close(dialog)),
                ft.ElevatedButton(
                    "Отменить бронь",
                    icon=ft.Icons.CLOSE,
                    on_click=confirm,
                    style=ft.ButtonStyle(
                        bgcolor=p.danger,
                        color=p.text_on_brand,
                        shape=ft.RoundedRectangleBorder(radius=Sizing.radius_md),
                    ),
                ),
            ],
        )
        state.page.open(dialog)

    body = ft.Column(
        [
            section_header(
                "Мои бронирования", p=p,
                action=ft.TextButton(
                    "Обновить",
                    icon=ft.Icons.REFRESH,
                    on_click=lambda e: reload(),
                    style=ft.ButtonStyle(color=p.text_muted),
                ),
            ),
            ft.Container(height=Sizing.pad_md),
            container,
        ],
        spacing=0,
        expand=True,
    )
    reload()
    return body
