"""Экран профиля пользователя."""

import flet as ft
from hotel_client.theme import PRIMARY, ERROR, SUCCESS, BG_COLOR, TEXT_SECONDARY


def profile_view(page: ft.Page, api):
    first_name = ft.TextField(label="Имя", border_radius=10, width=300)
    last_name = ft.TextField(label="Фамилия", border_radius=10, width=300)
    patronymic = ft.TextField(label="Отчество", border_radius=10, width=300)
    phone = ft.TextField(label="Телефон", border_radius=10, width=300)
    passport_s = ft.TextField(label="Серия паспорта (4 цифры)", border_radius=10, width=200)
    passport_n = ft.TextField(label="Номер паспорта (6 цифр)", border_radius=10, width=200)
    birth_date = ft.TextField(label="Дата рождения (ГГГГ-ММ-ДД)", border_radius=10, width=300)

    email_display = ft.Text("", size=14, color=TEXT_SECONDARY)
    role_display = ft.Text("", size=14, color=TEXT_SECONDARY)
    msg_text = ft.Text("", size=13, visible=False)
    loading = ft.ProgressRing(visible=False, width=20, height=20)

    async def load_profile():
        try:
            p = await api.get_profile()
            first_name.value = p.get("first_name", "")
            last_name.value = p.get("last_name", "")
            patronymic.value = p.get("patronymic", "") or ""
            phone.value = p.get("phone", "") or ""
            passport_s.value = p.get("passport_series", "") or ""
            passport_n.value = p.get("passport_number", "") or ""
            birth_date.value = p.get("birth_date", "") or ""
            email_display.value = f"Email: {p.get('email', '—')}"
            role_map = {"admin": "Администратор", "manager": "Менеджер", "guest": "Гость"}
            role_display.value = f"Роль: {role_map.get(p.get('role', ''), p.get('role', ''))}"
            page.update()
        except Exception as ex:
            msg_text.value = f"Ошибка загрузки профиля: {ex}"
            msg_text.color = ERROR
            msg_text.visible = True
            page.update()

    async def save_profile(e):
        loading.visible = True
        msg_text.visible = False
        page.update()

        data = {}
        if first_name.value.strip():
            data["first_name"] = first_name.value.strip()
        if last_name.value.strip():
            data["last_name"] = last_name.value.strip()
        if patronymic.value.strip():
            data["patronymic"] = patronymic.value.strip()
        if phone.value.strip():
            data["phone"] = phone.value.strip()
        if passport_s.value.strip():
            data["passport_series"] = passport_s.value.strip()
        if passport_n.value.strip():
            data["passport_number"] = passport_n.value.strip()
        if birth_date.value.strip():
            data["birth_date"] = birth_date.value.strip()

        try:
            await api.update_profile(data)
            msg_text.value = "Профиль сохранён"
            msg_text.color = SUCCESS
            msg_text.visible = True
        except Exception as ex:
            msg_text.value = f"Ошибка: {ex}"
            msg_text.color = ERROR
            msg_text.visible = True
        finally:
            loading.visible = False
            page.update()

    page.run_task(load_profile)

    save_btn = ft.ElevatedButton(
        text="Сохранить",
        icon=ft.Icons.SAVE,
        bgcolor=PRIMARY,
        color="#ffffff",
        width=200, height=44,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        on_click=save_profile,
    )

    return ft.Container(
        content=ft.Column([
            ft.Text("Личный кабинет", size=24, weight=ft.FontWeight.BOLD, color=PRIMARY),
            ft.Divider(height=6, color="transparent"),
            email_display,
            role_display,
            ft.Divider(height=10, color="transparent"),
            ft.Row([last_name, first_name], wrap=True, spacing=10),
            patronymic,
            phone,
            ft.Row([passport_s, passport_n], wrap=True, spacing=10),
            birth_date,
            msg_text,
            ft.Row([loading], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(height=6, color="transparent"),
            save_btn,
        ], scroll=ft.ScrollMode.AUTO, expand=True),
        padding=20,
        expand=True,
        bgcolor=BG_COLOR,
    )
