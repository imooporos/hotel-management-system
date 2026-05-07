"""
Главный модуль Flet-приложения «Гранд Отель».
Кроссплатформенный клиент (Desktop / Web / Mobile).
"""

import flet as ft
import os

from hotel_client.api_client import ApiClient
from hotel_client.theme import PRIMARY, BG_COLOR, get_theme
from hotel_client.views.login_view import login_view
from hotel_client.views.register_view import register_view
from hotel_client.views.rooms_view import rooms_view
from hotel_client.views.booking_view import booking_view
from hotel_client.views.profile_view import profile_view
from hotel_client.views.my_bookings_view import my_bookings_view
from hotel_client.views.admin_view import admin_view

API_URL = os.environ.get("HOTEL_API_URL", "http://77.221.151.85:8000")


async def main(page: ft.Page):
    page.title = "Гранд Отель — Система управления"
    page.theme = get_theme()
    page.bgcolor = BG_COLOR
    page.window.width = 1100
    page.window.height = 750
    page.padding = 0

    api = ApiClient(base_url=API_URL)
    current_view = "login"

    def clear_and_set(view_control: ft.Control):
        page.controls.clear()
        page.controls.append(view_control)
        page.update()

    # ── Навигация ─────────────────────────────────────────────────────────

    def build_nav_rail():
        destinations = [
            ft.NavigationRailDestination(
                icon=ft.Icons.MEETING_ROOM_OUTLINED,
                selected_icon=ft.Icons.MEETING_ROOM,
                label="Номера",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.BOOK_OUTLINED,
                selected_icon=ft.Icons.BOOK,
                label="Бронирования",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.PERSON_OUTLINED,
                selected_icon=ft.Icons.PERSON,
                label="Профиль",
            ),
        ]

        if api.user_role in ("admin", "manager"):
            destinations.append(ft.NavigationRailDestination(
                icon=ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
                selected_icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                label="Управление",
            ))

        return ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=80,
            min_extended_width=180,
            leading=ft.Column([
                ft.Icon(ft.Icons.HOTEL, color=PRIMARY, size=32),
                ft.Text("Гранд Отель", size=11, weight=ft.FontWeight.BOLD, color=PRIMARY),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
            trailing=ft.Column([
                ft.IconButton(
                    icon=ft.Icons.LOGOUT,
                    tooltip="Выйти",
                    icon_color="#c62828",
                    on_click=lambda _: page.run_task(handle_logout),
                ),
            ]),
            destinations=destinations,
            on_change=lambda e: page.run_task(lambda: navigate(e.control.selected_index)),
            bgcolor="#ffffff",
        )

    async def navigate(index: int):
        nonlocal current_view
        content_area.controls.clear()

        if index == 0:
            current_view = "rooms"
            content_area.controls.append(
                rooms_view(page, api, on_book_room=lambda rid: page.run_task(
                    lambda: show_booking(rid)))
            )
        elif index == 1:
            current_view = "my_bookings"
            content_area.controls.append(my_bookings_view(page, api))
        elif index == 2:
            current_view = "profile"
            content_area.controls.append(profile_view(page, api))
        elif index == 3:
            current_view = "admin"
            content_area.controls.append(admin_view(page, api))

        page.update()

    async def show_booking(room_id: int):
        content_area.controls.clear()
        content_area.controls.append(
            booking_view(
                page, api, room_id,
                on_back=lambda: page.run_task(lambda: navigate(0)),
                on_booked=lambda: page.run_task(lambda: navigate(1)),
            )
        )
        page.update()

    content_area = ft.Column(expand=True)

    # ── Экраны авторизации ────────────────────────────────────────────────

    async def show_login():
        clear_and_set(login_view(
            page, api,
            on_login=show_main,
            on_register_click=lambda: page.run_task(show_register),
        ))

    async def show_register():
        clear_and_set(register_view(
            page, api,
            on_registered=show_main,
            on_login_click=lambda: page.run_task(show_login),
        ))

    async def show_main():
        nav = build_nav_rail()
        content_area.controls.clear()
        content_area.controls.append(
            rooms_view(page, api, on_book_room=lambda rid: page.run_task(
                lambda: show_booking(rid)))
        )

        layout = ft.Row([
            nav,
            ft.VerticalDivider(width=1),
            ft.Container(content=content_area, expand=True),
        ], expand=True)

        clear_and_set(layout)

    async def handle_logout():
        api.logout()
        await show_login()

    await show_login()


def run():
    ft.app(target=main)


if __name__ == "__main__":
    run()
