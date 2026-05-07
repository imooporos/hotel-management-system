"""Экран входа в систему."""

import flet as ft
from hotel_client.theme import PRIMARY, PRIMARY_LIGHT, ERROR, CARD_BG, BG_COLOR


def login_view(page: ft.Page, api, on_login, on_register_click):
    email_field = ft.TextField(
        label="Email",
        prefix_icon=ft.Icons.EMAIL_OUTLINED,
        border_radius=10,
        width=340,
        keyboard_type=ft.KeyboardType.EMAIL,
    )
    password_field = ft.TextField(
        label="Пароль",
        prefix_icon=ft.Icons.LOCK_OUTLINED,
        password=True,
        can_reveal_password=True,
        border_radius=10,
        width=340,
    )
    error_text = ft.Text("", color=ERROR, size=13, visible=False)
    loading = ft.ProgressRing(visible=False, width=20, height=20, stroke_width=2)

    async def handle_login(e):
        email = email_field.value.strip()
        pwd = password_field.value.strip()
        if not email or not pwd:
            error_text.value = "Заполните все поля"
            error_text.visible = True
            page.update()
            return

        loading.visible = True
        error_text.visible = False
        page.update()

        try:
            await api.login(email, pwd)
            await on_login()
        except Exception as ex:
            msg = str(ex)
            if "401" in msg:
                error_text.value = "Неверный email или пароль"
            elif "403" in msg:
                error_text.value = "Учётная запись заблокирована"
            else:
                error_text.value = f"Ошибка подключения: {msg[:80]}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    login_btn = ft.ElevatedButton(
        text="Войти",
        icon=ft.Icons.LOGIN,
        bgcolor=PRIMARY,
        color="#ffffff",
        width=340,
        height=48,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        on_click=handle_login,
    )

    register_link = ft.TextButton(
        text="Нет аккаунта? Зарегистрироваться",
        on_click=lambda _: on_register_click(),
        style=ft.ButtonStyle(color=PRIMARY_LIGHT),
    )

    card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.HOTEL, size=48, color=PRIMARY),
                ft.Text("Гранд Отель", size=28, weight=ft.FontWeight.BOLD, color=PRIMARY),
                ft.Text("Вход в систему", size=14, color="#757575"),
                ft.Divider(height=20, color="transparent"),
                email_field,
                password_field,
                error_text,
                ft.Row([loading], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=10, color="transparent"),
                login_btn,
                register_link,
            ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            padding=40,
            width=400,
            border_radius=16,
        ),
        elevation=4,
    )

    return ft.Container(
        content=card,
        alignment=ft.alignment.center,
        expand=True,
        bgcolor=BG_COLOR,
    )
