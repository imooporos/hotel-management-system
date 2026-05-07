"""Экран «Мои бронирования»."""

import flet as ft
from hotel_client.theme import PRIMARY, ERROR, BG_COLOR, TEXT_SECONDARY, SECONDARY, status_chip


def my_bookings_view(page: ft.Page, api):
    bookings_col = ft.Column(spacing=10)
    loading = ft.ProgressRing(visible=False, width=24, height=24)
    no_results = ft.Text("У вас пока нет бронирований", size=14, color=TEXT_SECONDARY, visible=False)

    async def load_bookings(e=None):
        loading.visible = True
        no_results.visible = False
        bookings_col.controls.clear()
        page.update()

        try:
            bookings = await api.get_my_bookings()
            if not bookings:
                no_results.visible = True
            else:
                for b in bookings:
                    services_text = ", ".join(s["name"] for s in b.get("services", []))

                    cancel_btn = ft.TextButton(
                        "Отменить",
                        icon=ft.Icons.CANCEL,
                        style=ft.ButtonStyle(color="#c62828"),
                        on_click=lambda _, bid=b["id"]: page.run_task(lambda: cancel(bid)),
                        visible=b["status"] in ("pending", "confirmed"),
                    )

                    pdf_btn = ft.TextButton(
                        "PDF",
                        icon=ft.Icons.PICTURE_AS_PDF,
                        style=ft.ButtonStyle(color=PRIMARY),
                        on_click=lambda _, bid=b["id"]: page.run_task(lambda: download_pdf(bid)),
                    )

                    card = ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(f"Бронирование #{b['id']}", size=16,
                                            weight=ft.FontWeight.BOLD),
                                    status_chip(b["status"]),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Row([
                                    ft.Icon(ft.Icons.MEETING_ROOM, size=14, color=TEXT_SECONDARY),
                                    ft.Text(f"Номер {b.get('room_number', '—')} ({b.get('category_name', '')})",
                                            size=13, color=TEXT_SECONDARY),
                                ], spacing=4),
                                ft.Row([
                                    ft.Icon(ft.Icons.DATE_RANGE, size=14, color=TEXT_SECONDARY),
                                    ft.Text(f"{b['check_in_date']} → {b['check_out_date']} ({b.get('nights', '—')} ночей)",
                                            size=13, color=TEXT_SECONDARY),
                                ], spacing=4),
                                ft.Text(f"Сумма: {b['total_amount']:.0f} ₽",
                                        size=15, weight=ft.FontWeight.W_600, color=SECONDARY),
                                ft.Text(f"Услуги: {services_text}", size=12, color=TEXT_SECONDARY,
                                        italic=True) if services_text else ft.Container(),
                                ft.Row([pdf_btn, cancel_btn],
                                       alignment=ft.MainAxisAlignment.END),
                            ], spacing=6),
                            padding=14,
                            border_radius=12,
                        ),
                        elevation=2,
                    )
                    bookings_col.controls.append(card)
        except Exception as ex:
            bookings_col.controls.append(ft.Text(f"Ошибка: {ex}", color=ERROR))
        finally:
            loading.visible = False
            page.update()

    async def cancel(booking_id: int):
        try:
            await api.cancel_booking(booking_id)
            page.open(ft.SnackBar(content=ft.Text("Бронирование отменено"), bgcolor="#2e7d32"))
            await load_bookings()
        except Exception as ex:
            page.open(ft.SnackBar(content=ft.Text(f"Ошибка: {ex}"), bgcolor="#c62828"))
            page.update()

    async def download_pdf(booking_id: int):
        try:
            pdf_data = await api.download_booking_pdf(booking_id)
            path = f"/tmp/booking_{booking_id}.pdf"
            with open(path, "wb") as f:
                f.write(pdf_data)
            page.open(ft.SnackBar(
                content=ft.Text(f"PDF сохранён: {path}"),
                bgcolor="#1a237e",
            ))
            page.update()
        except Exception as ex:
            page.open(ft.SnackBar(content=ft.Text(f"Ошибка: {ex}"), bgcolor="#c62828"))
            page.update()

    page.run_task(load_bookings)

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Мои бронирования", size=24, weight=ft.FontWeight.BOLD, color=PRIMARY),
                ft.IconButton(icon=ft.Icons.REFRESH, on_click=load_bookings, tooltip="Обновить"),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([loading], alignment=ft.MainAxisAlignment.CENTER),
            no_results,
            bookings_col,
        ], scroll=ft.ScrollMode.AUTO, expand=True),
        padding=20,
        expand=True,
        bgcolor=BG_COLOR,
    )
