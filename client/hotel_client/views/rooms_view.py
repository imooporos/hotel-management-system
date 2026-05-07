"""Каталог номеров."""

import flet as ft
from hotel_client.theme import (
    PRIMARY, SECONDARY, BG_COLOR, CARD_BG, TEXT_SECONDARY,
    SUCCESS, WARNING, page_title, status_chip, styled_card,
)


def rooms_view(page: ft.Page, api, on_book_room):
    rooms_list = ft.Column(spacing=12)
    category_dd = ft.Dropdown(
        label="Категория", width=200, border_radius=10,
        options=[ft.dropdown.Option(key="", text="Все категории")],
    )
    capacity_dd = ft.Dropdown(
        label="Гостей", width=120, border_radius=10,
        options=[ft.dropdown.Option(key="", text="Любое")] +
                [ft.dropdown.Option(key=str(i), text=str(i)) for i in range(1, 7)],
    )
    loading = ft.ProgressRing(visible=False, width=24, height=24)
    no_results = ft.Text("Номера не найдены", size=14, color=TEXT_SECONDARY, visible=False)

    async def load_categories():
        try:
            cats = await api.get_categories()
            category_dd.options = [ft.dropdown.Option(key="", text="Все категории")]
            for c in cats:
                category_dd.options.append(
                    ft.dropdown.Option(key=str(c["id"]), text=f"{c['name']} — {c['base_price']:.0f} ₽")
                )
            page.update()
        except Exception:
            pass

    async def load_rooms(e=None):
        loading.visible = True
        no_results.visible = False
        rooms_list.controls.clear()
        page.update()

        try:
            params = {}
            if category_dd.value:
                params["category_id"] = int(category_dd.value)
            if capacity_dd.value:
                params["capacity"] = int(capacity_dd.value)

            rooms = await api.get_rooms(**params)

            if not rooms:
                no_results.visible = True
            else:
                for rm in rooms:
                    amenities_text = ", ".join(a["name"] for a in rm.get("amenities", []))
                    is_free = rm.get("is_free_today", True)

                    room_card = ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Column([
                                        ft.Row([
                                            ft.Icon(ft.Icons.MEETING_ROOM, color=PRIMARY, size=20),
                                            ft.Text(f"Номер {rm['room_number']}", size=18,
                                                    weight=ft.FontWeight.BOLD),
                                        ]),
                                        ft.Text(rm.get("category_name", ""), size=14, color=TEXT_SECONDARY),
                                    ], expand=True),
                                    ft.Column([
                                        ft.Text(f"{rm.get('base_price', 0):.0f} ₽/ночь",
                                                size=18, weight=ft.FontWeight.BOLD, color=SECONDARY),
                                        status_chip("available" if is_free else "occupied"),
                                    ], horizontal_alignment=ft.CrossAxisAlignment.END),
                                ]),
                                ft.Row([
                                    ft.Icon(ft.Icons.LAYERS, size=14, color=TEXT_SECONDARY),
                                    ft.Text(f"Этаж: {rm.get('floor', '—')}", size=13, color=TEXT_SECONDARY),
                                    ft.Icon(ft.Icons.PEOPLE, size=14, color=TEXT_SECONDARY),
                                    ft.Text(f"Мест: {rm.get('capacity', '—')}", size=13, color=TEXT_SECONDARY),
                                ], spacing=6),
                                ft.Text(amenities_text, size=12, color=TEXT_SECONDARY, italic=True)
                                    if amenities_text else ft.Container(),
                                ft.Row([
                                    ft.ElevatedButton(
                                        "Забронировать",
                                        icon=ft.Icons.BOOK_ONLINE,
                                        bgcolor=PRIMARY if is_free else "#bdbdbd",
                                        color="#ffffff",
                                        disabled=not is_free,
                                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                                        on_click=lambda _, rid=rm["id"]: on_book_room(rid),
                                    ),
                                ], alignment=ft.MainAxisAlignment.END),
                            ], spacing=8),
                            padding=16,
                            border_radius=12,
                        ),
                        elevation=2,
                    )
                    rooms_list.controls.append(room_card)
        except Exception as ex:
            rooms_list.controls.append(
                ft.Text(f"Ошибка загрузки: {ex}", color="#c62828")
            )
        finally:
            loading.visible = False
            page.update()

    search_btn = ft.IconButton(
        icon=ft.Icons.SEARCH,
        icon_color=PRIMARY,
        tooltip="Найти",
        on_click=load_rooms,
    )
    reset_btn = ft.TextButton("Сбросить", on_click=lambda _: _reset())

    def _reset():
        category_dd.value = ""
        capacity_dd.value = ""
        page.update()

    page.run_task(load_categories)
    page.run_task(load_rooms)

    return ft.Container(
        content=ft.Column([
            page_title("Каталог номеров"),
            ft.Divider(height=10, color="transparent"),
            ft.Row([category_dd, capacity_dd, search_btn, reset_btn], spacing=10,
                   wrap=True),
            ft.Row([loading], alignment=ft.MainAxisAlignment.CENTER),
            no_results,
            rooms_list,
        ], scroll=ft.ScrollMode.AUTO, expand=True),
        padding=20,
        expand=True,
        bgcolor=BG_COLOR,
    )
