"""Экран регистрации."""

import flet as ft
from hotel_client.theme import PRIMARY, PRIMARY_LIGHT, ERROR, BG_COLOR


def register_view(page: ft.Page, api, on_registered, on_login_click):
    first_name = ft.TextField(label="Имя", prefix_icon=ft.Icons.PERSON, border_radius=10, width=340)
    last_name = ft.TextField(label="Фамилия", prefix_icon=ft.Icons.PERSON_OUTLINE, border_radius=10, width=340)
    patronymic = ft.TextField(label="Отчество (необязательно)", border_radius=10, width=340)
    email_field = ft.TextField(label="Email", prefix_icon=ft.Icons.EMAIL_OUTLINED, border_radius=10, width=340,
                               keyboard_type=ft.KeyboardType.EMAIL)
    phone_field = ft.TextField(label="Телефон (необязательно)", prefix_icon=ft.Icons.PHONE, border_radius=10,
                               width=340)
    password_field = ft.TextField(label="Пароль (мин. 6 символов)", prefix_icon=ft.Icons.LOCK_OUTLINED,
                                  password=True, can_reveal_password=True, border_radius=10, width=340)
    password2_field = ft.TextField(label="Подтвердите пароль", prefix_icon=ft.Icons.LOCK,
                                   password=True, can_reveal_password=True, border_radius=10, width=340)
    error_text = ft.Text("", color=ERROR, size=13, visible=False)
    loading = ft.ProgressRing(visible=False, width=20, height=20, stroke_width=2)

    async def handle_register(e):
        fn = first_name.value.strip()
        ln = last_name.value.strip()
        em = email_field.value.strip()
        pw = password_field.value.strip()
        pw2 = password2_field.value.strip()

        if not fn or not ln or not em or not pw:
            error_text.value = "Заполните обязательные поля"
            error_text.visible = True
            page.update()
            return
        if pw != pw2:
            error_text.value = "Пароли не совпадают"
            error_text.visible = True
            page.update()
            return
        if len(pw) < 6:
            error_text.value = "Пароль должен содержать минимум 6 символов"
            error_text.visible = True
            page.update()
            return

        loading.visible = True
        error_text.visible = False
        page.update()

        try:
            await api.register(
                email=em, password=pw,
                first_name=fn, last_name=ln,
                patronymic=patronymic.value.strip(),
                phone=phone_field.value.strip(),
            )
            await on_registered()
        except Exception as ex:
            msg = str(ex)
            if "409" in msg:
                error_text.value = "Пользователь с таким email уже существует"
            else:
                error_text.value = f"Ошибка: {msg[:80]}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    register_btn = ft.ElevatedButton(
        text="Зарегистрироваться",
        icon=ft.Icons.PERSON_ADD,
        bgcolor=PRIMARY,
        color="#ffffff",
        width=340,
        height=48,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        on_click=handle_register,
    )

    login_link = ft.TextButton(
        text="Уже есть аккаунт? Войти",
        on_click=lambda _: on_login_click(),
        style=ft.ButtonStyle(color=PRIMARY_LIGHT),
    )

    card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.HOTEL, size=40, color=PRIMARY),
                ft.Text("Регистрация", size=24, weight=ft.FontWeight.BOLD, color=PRIMARY),
                ft.Divider(height=10, color="transparent"),
                last_name,
                first_name,
                patronymic,
                email_field,
                phone_field,
                password_field,
                password2_field,
                error_text,
                ft.Row([loading], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=6, color="transparent"),
                register_btn,
                login_link,
            ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
            ),
            padding=30,
            width=400,
            border_radius=16,
        ),
        elevation=4,
    )

    return ft.Container(
        content=ft.Column(
            [card],
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.alignment.center,
        expand=True,
        bgcolor=BG_COLOR,
    )
