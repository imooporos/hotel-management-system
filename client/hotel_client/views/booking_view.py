"""Экран создания бронирования."""

import flet as ft
from datetime import date, timedelta
from hotel_client.theme import PRIMARY, ERROR, BG_COLOR, TEXT_SECONDARY, SECONDARY


def booking_view(page: ft.Page, api, room_id: int, on_back, on_booked):
    room_info = ft.Column()
    services_col = ft.Column()
    selected_services: list[int] = []
    loading = ft.ProgressRing(visible=False, width=20, height=20)
    error_text = ft.Text("", color=ERROR, size=13, visible=False)

    today = date.today()
    tomorrow = today + timedelta(days=1)

    check_in_field = ft.TextField(
        label="Дата заезда (ГГГГ-ММ-ДД)", value=str(today),
        border_radius=10, width=200,
        prefix_icon=ft.Icons.CALENDAR_TODAY,
    )
    check_out_field = ft.TextField(
        label="Дата выезда (ГГГГ-ММ-ДД)", value=str(tomorrow),
        border_radius=10, width=200,
        prefix_icon=ft.Icons.CALENDAR_MONTH,
    )
    guests_field = ft.TextField(
        label="Кол-во гостей", value="1",
        border_radius=10, width=120,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    notes_field = ft.TextField(
        label="Примечание (необязательно)",
        border_radius=10, width=420, multiline=True, max_lines=3,
    )

    async def load_data():
        try:
            rm = await api.get_room(room_id)
            room_info.controls = [
                ft.Row([
                    ft.Icon(ft.Icons.MEETING_ROOM, color=PRIMARY, size=24),
                    ft.Text(f"Номер {rm['room_number']}", size=20, weight=ft.FontWeight.BOLD),
                ]),
                ft.Text(f"Категория: {rm.get('category_name', '—')}", size=14, color=TEXT_SECONDARY),
                ft.Text(f"Цена: {rm.get('base_price', 0):.0f} ₽/ночь", size=16,
                        weight=ft.FontWeight.W_600, color=SECONDARY),
                ft.Text(f"Вместимость: {rm.get('capacity', '—')} чел.", size=14, color=TEXT_SECONDARY),
            ]

            svcs = await api.get_services()
            services_col.controls = [
                ft.Text("Дополнительные услуги:", size=14, weight=ft.FontWeight.W_600),
            ]
            for s in svcs:
                cb = ft.Checkbox(
                    label=f"{s['name']} — {s['price']:.0f} ₽",
                    value=False,
                    data=s["id"],
                    on_change=lambda e: _toggle_service(e),
                )
                services_col.controls.append(cb)

            page.update()
        except Exception as ex:
            room_info.controls = [ft.Text(f"Ошибка: {ex}", color=ERROR)]
            page.update()

    def _toggle_service(e):
        sid = e.control.data
        if e.control.value:
            if sid not in selected_services:
                selected_services.append(sid)
        else:
            if sid in selected_services:
                selected_services.remove(sid)

    async def handle_book(e):
        ci = check_in_field.value.strip()
        co = check_out_field.value.strip()
        gc = guests_field.value.strip()

        if not ci or not co:
            error_text.value = "Укажите даты заезда и выезда"
            error_text.visible = True
            page.update()
            return

        try:
            guests_count = int(gc) if gc else 1
        except ValueError:
            error_text.value = "Количество гостей должно быть числом"
            error_text.visible = True
            page.update()
            return

        loading.visible = True
        error_text.visible = False
        page.update()

        try:
            result = await api.create_booking(
                room_id=room_id,
                check_in=ci, check_out=co,
                guests_count=guests_count,
                notes=notes_field.value.strip(),
                service_ids=selected_services,
            )
            page.open(ft.SnackBar(
                content=ft.Text(f"Бронирование #{result['id']} создано! Сумма: {result['total_amount']:.0f} ₽"),
                bgcolor="#2e7d32",
            ))
            await on_booked()
        except Exception as ex:
            msg = str(ex)
            if "409" in msg:
                error_text.value = "Номер занят на выбранные даты"
            elif "400" in msg:
                error_text.value = "Проверьте корректность данных"
            else:
                error_text.value = f"Ошибка: {msg[:80]}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    page.run_task(load_data)

    book_btn = ft.ElevatedButton(
        text="Забронировать",
        icon=ft.Icons.BOOK_ONLINE,
        bgcolor=PRIMARY,
        color="#ffffff",
        width=200, height=48,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        on_click=handle_book,
    )

    back_btn = ft.TextButton(
        text="← Назад к каталогу",
        on_click=lambda _: on_back(),
    )

    return ft.Container(
        content=ft.Column([
            back_btn,
            ft.Text("Бронирование номера", size=24, weight=ft.FontWeight.BOLD, color=PRIMARY),
            ft.Divider(height=6, color="transparent"),
            ft.Card(
                content=ft.Container(content=room_info, padding=16, border_radius=12),
                elevation=2,
            ),
            ft.Divider(height=10, color="transparent"),
            ft.Row([check_in_field, check_out_field, guests_field], wrap=True, spacing=10),
            notes_field,
            ft.Divider(height=6, color="transparent"),
            services_col,
            error_text,
            ft.Row([loading], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(height=6, color="transparent"),
            ft.Row([book_btn], alignment=ft.MainAxisAlignment.CENTER),
        ], scroll=ft.ScrollMode.AUTO, expand=True),
        padding=20,
        expand=True,
        bgcolor=BG_COLOR,
    )
