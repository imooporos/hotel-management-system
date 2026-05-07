"""Маршрутизация Flet-приложения."""

from __future__ import annotations

import flet as ft

from .components.nav import app_bar
from .state import AppState
from .theme import Sizing, get_palette, make_flet_theme
from .views.admin import admin_view
from .views.auth import login_view, register_view
from .views.booking import booking_view
from .views.home import home_view
from .views.my_bookings import my_bookings_view
from .views.profile import profile_view


def build_app(page: ft.Page):
    page.title = "Velmar Hotel · Управление гостиницей"
    page.padding = 0
    page.spacing = 0
    page.fonts = {
        "Inter": "https://rsms.me/inter/font-files/Inter-Regular.woff2",
    }
    page.theme_mode = ft.ThemeMode.LIGHT

    state = AppState(page)
    state.restore_theme()
    page.theme = make_flet_theme(get_palette(page.theme_mode))
    page.dark_theme = make_flet_theme(get_palette(ft.ThemeMode.DARK))
    page.bgcolor = get_palette(page.theme_mode).bg

    # ------------------------------------------------------------------
    # Helpers for switching screens
    # ------------------------------------------------------------------

    def palette():
        return get_palette(page.theme_mode)

    def show(screen: str, **kwargs):
        page.controls.clear()
        p = palette()
        page.theme = make_flet_theme(p)
        page.bgcolor = p.bg

        if screen == "login":
            page.add(login_view(state, p, on_success=lambda: show("home"), go_register=lambda: show("register")))
            page.update()
            return
        if screen == "register":
            page.add(register_view(state, p, on_success=lambda: show("home"), go_login=lambda: show("login")))
            page.update()
            return

        # Authenticated screens have a top bar.
        bar = app_bar(
            p=p,
            user_label=state.current_user.full_name if state.current_user else None,
            role_label=_role_label(state.current_user.role) if state.current_user else None,
            on_home=lambda e: show("home"),
            on_my_bookings=lambda e: show("my_bookings"),
            on_admin=(lambda e: show("admin")) if state.current_user and state.current_user.is_staff else None,
            on_profile=lambda e: show("profile"),
            on_logout=lambda e: handle_logout(),
            on_toggle_theme=lambda e: handle_toggle_theme(),
            is_dark=page.theme_mode == ft.ThemeMode.DARK,
            is_staff=bool(state.current_user and state.current_user.is_staff),
        )

        if screen == "home":
            content = home_view(
                state, p,
                on_book=lambda room: show("booking", room=room),
                on_open_room=lambda room: show("booking", room=room),
            )
        elif screen == "my_bookings":
            content = my_bookings_view(state, p)
        elif screen == "profile":
            content = profile_view(state, p)
        elif screen == "admin":
            content = admin_view(state, p)
        elif screen == "booking":
            room = kwargs["room"]
            content = booking_view(
                state, p, room,
                on_done=lambda: show("my_bookings"),
                on_back=lambda: show("home"),
            )
        else:
            content = ft.Text(f"Неизвестный экран: {screen}")

        page.add(
            ft.Column(
                [
                    bar,
                    ft.Container(
                        content=content,
                        padding=ft.padding.symmetric(horizontal=Sizing.pad_lg, vertical=Sizing.pad_lg),
                        expand=True,
                    ),
                ],
                spacing=0,
                expand=True,
            )
        )
        page.update()

    def handle_logout():
        state.logout()
        show("login")

    def handle_toggle_theme():
        state.toggle_theme()
        # Re-render current screen — re-show "home" for simplicity if logged in.
        show("home" if state.current_user else "login")

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    if state.restore_session():
        show("home")
    else:
        show("login")


def _role_label(role: str) -> str:
    return {"guest": "Гость", "manager": "Менеджер", "admin": "Администратор"}.get(role, role)
