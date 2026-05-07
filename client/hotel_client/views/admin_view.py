"""Админ-панель: управление бронированиями, пользователями, отчёты."""

import flet as ft
from hotel_client.theme import (
    PRIMARY, ERROR, SUCCESS, BG_COLOR, TEXT_SECONDARY,
    SECONDARY, status_chip, page_title,
)


def admin_view(page: ft.Page, api):
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=200,
        expand=True,
        tabs=[
            ft.Tab(text="Бронирования", icon=ft.Icons.BOOK_ONLINE),
            ft.Tab(text="Пользователи", icon=ft.Icons.PEOPLE),
            ft.Tab(text="Отчёты", icon=ft.Icons.BAR_CHART),
            ft.Tab(text="Аудит", icon=ft.Icons.HISTORY),
        ],
    )

    bookings_col = ft.Column(spacing=8)
    users_col = ft.Column(spacing=8)
    report_col = ft.Column(spacing=8)
    audit_col = ft.Column(spacing=6)
    loading = ft.ProgressRing(visible=False, width=24, height=24)

    # ── Бронирования ──────────────────────────────────────────────────────

    async def load_bookings(e=None):
        loading.visible = True
        bookings_col.controls.clear()
        page.update()

        try:
            bookings = await api.get_all_bookings()
            for b in bookings:
                status_actions = ft.Row(spacing=4)
                current_status = b["status"]

                if current_status == "pending":
                    status_actions.controls.append(ft.TextButton(
                        "Подтвердить", style=ft.ButtonStyle(color=SUCCESS),
                        on_click=lambda _, bid=b["id"]: page.run_task(
                            lambda: change_status(bid, "confirmed")),
                    ))
                if current_status == "confirmed":
                    status_actions.controls.append(ft.TextButton(
                        "Заселить", style=ft.ButtonStyle(color=PRIMARY),
                        on_click=lambda _, bid=b["id"]: page.run_task(
                            lambda: change_status(bid, "checked_in")),
                    ))
                if current_status == "checked_in":
                    status_actions.controls.append(ft.TextButton(
                        "Выселить", style=ft.ButtonStyle(color=SECONDARY),
                        on_click=lambda _, bid=b["id"]: page.run_task(
                            lambda: change_status(bid, "checked_out")),
                    ))
                if current_status not in ("cancelled", "checked_out"):
                    status_actions.controls.append(ft.TextButton(
                        "Отменить", style=ft.ButtonStyle(color=ERROR),
                        on_click=lambda _, bid=b["id"]: page.run_task(
                            lambda: change_status(bid, "cancelled")),
                    ))

                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"#{b['id']}", size=15, weight=ft.FontWeight.BOLD),
                                ft.Text(f"{b.get('guest_name', '—')} ({b.get('guest_email', '')})",
                                        size=13, color=TEXT_SECONDARY),
                                status_chip(current_status),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),
                            ft.Row([
                                ft.Text(f"Ном. {b.get('room_number', '—')}", size=13),
                                ft.Text(f"{b['check_in_date']} → {b['check_out_date']}", size=13,
                                        color=TEXT_SECONDARY),
                                ft.Text(f"{b['total_amount']:.0f} ₽", size=14,
                                        weight=ft.FontWeight.W_600, color=SECONDARY),
                            ], spacing=12, wrap=True),
                            status_actions,
                        ], spacing=4),
                        padding=12,
                        border_radius=10,
                    ),
                    elevation=1,
                )
                bookings_col.controls.append(card)
        except Exception as ex:
            bookings_col.controls.append(ft.Text(f"Ошибка: {ex}", color=ERROR))
        finally:
            loading.visible = False
            page.update()

    async def change_status(booking_id: int, status: str):
        try:
            await api.update_booking_status(booking_id, status)
            page.open(ft.SnackBar(content=ft.Text(f"Статус бронирования #{booking_id} обновлён"),
                                   bgcolor=SUCCESS))
            await load_bookings()
        except Exception as ex:
            page.open(ft.SnackBar(content=ft.Text(f"Ошибка: {ex}"), bgcolor=ERROR))
            page.update()

    # ── Пользователи ──────────────────────────────────────────────────────

    async def load_users(e=None):
        loading.visible = True
        users_col.controls.clear()
        page.update()

        try:
            users = await api.get_users()
            for u in users:
                role_map = {"admin": "Админ", "manager": "Менеджер", "guest": "Гость"}
                role_dd = ft.Dropdown(
                    value=u["role"], width=140, border_radius=8,
                    options=[
                        ft.dropdown.Option("guest", "Гость"),
                        ft.dropdown.Option("manager", "Менеджер"),
                        ft.dropdown.Option("admin", "Админ"),
                    ],
                    on_change=lambda e, uid=u["id"]: page.run_task(
                        lambda: set_role(uid, e.control.value)),
                )

                block_btn = ft.IconButton(
                    icon=ft.Icons.BLOCK if u["is_active"] else ft.Icons.CHECK_CIRCLE,
                    icon_color=ERROR if u["is_active"] else SUCCESS,
                    tooltip="Заблокировать" if u["is_active"] else "Разблокировать",
                    on_click=lambda _, uid=u["id"], active=u["is_active"]: page.run_task(
                        lambda: toggle_block(uid, not active)),
                )

                name = f"{u.get('last_name', '') or ''} {u.get('first_name', '') or ''}".strip() or "—"
                status_icon = ft.Icon(
                    ft.Icons.CHECK_CIRCLE if u["is_active"] else ft.Icons.CANCEL,
                    color=SUCCESS if u["is_active"] else ERROR,
                    size=16,
                )

                card = ft.Container(
                    content=ft.Row([
                        status_icon,
                        ft.Column([
                            ft.Text(name, size=14, weight=ft.FontWeight.W_600),
                            ft.Text(u["email"], size=12, color=TEXT_SECONDARY),
                        ], spacing=2, expand=True),
                        role_dd,
                        block_btn,
                    ], spacing=8, alignment=ft.MainAxisAlignment.START),
                    padding=10,
                    border=ft.border.all(1, "#e0e0e0"),
                    border_radius=10,
                )
                users_col.controls.append(card)
        except Exception as ex:
            users_col.controls.append(ft.Text(f"Ошибка: {ex}", color=ERROR))
        finally:
            loading.visible = False
            page.update()

    async def set_role(user_id: int, role: str):
        try:
            await api.update_user_role(user_id, role)
            page.open(ft.SnackBar(content=ft.Text("Роль обновлена"), bgcolor=SUCCESS))
        except Exception as ex:
            page.open(ft.SnackBar(content=ft.Text(f"Ошибка: {ex}"), bgcolor=ERROR))
            page.update()

    async def toggle_block(user_id: int, is_active: bool):
        try:
            await api.block_user(user_id, is_active)
            action = "разблокирован" if is_active else "заблокирован"
            page.open(ft.SnackBar(content=ft.Text(f"Пользователь {action}"), bgcolor=SUCCESS))
            await load_users()
        except Exception as ex:
            page.open(ft.SnackBar(content=ft.Text(f"Ошибка: {ex}"), bgcolor=ERROR))
            page.update()

    # ── Отчёты ────────────────────────────────────────────────────────────

    async def load_reports(e=None):
        loading.visible = True
        report_col.controls.clear()
        page.update()

        try:
            revenue = await api.get_revenue_report()
            report_col.controls.append(
                ft.Text("Выручка по категориям", size=16, weight=ft.FontWeight.BOLD, color=PRIMARY),
            )

            if revenue:
                header = ft.Row([
                    ft.Text("Категория", size=13, weight=ft.FontWeight.BOLD, expand=True),
                    ft.Text("Брониров.", size=13, weight=ft.FontWeight.BOLD, width=80),
                    ft.Text("Выручка", size=13, weight=ft.FontWeight.BOLD, width=100),
                    ft.Text("Ср. выручка", size=13, weight=ft.FontWeight.BOLD, width=100),
                ])
                report_col.controls.append(header)
                report_col.controls.append(ft.Divider())

                for r in revenue:
                    report_col.controls.append(ft.Row([
                        ft.Text(r["category_name"], size=13, expand=True),
                        ft.Text(str(r["total_bookings"]), size=13, width=80),
                        ft.Text(f"{r['total_revenue']:.0f} ₽", size=13, width=100),
                        ft.Text(f"{r['avg_revenue_per_booking']:.0f} ₽", size=13, width=100),
                    ]))
            else:
                report_col.controls.append(ft.Text("Нет данных", color=TEXT_SECONDARY))
        except Exception as ex:
            report_col.controls.append(ft.Text(f"Ошибка: {ex}", color=ERROR))
        finally:
            loading.visible = False
            page.update()

    # ── Аудит ─────────────────────────────────────────────────────────────

    async def load_audit(e=None):
        loading.visible = True
        audit_col.controls.clear()
        page.update()

        try:
            logs = await api.get_audit_log(limit=30)
            if not logs:
                audit_col.controls.append(ft.Text("Журнал пуст", color=TEXT_SECONDARY))
            else:
                for entry in logs:
                    action_color = {"INSERT": SUCCESS, "UPDATE": PRIMARY, "DELETE": ERROR}
                    audit_col.controls.append(ft.Container(
                        content=ft.Row([
                            ft.Text(entry["action"], size=12,
                                    weight=ft.FontWeight.BOLD,
                                    color=action_color.get(entry["action"], TEXT_SECONDARY),
                                    width=60),
                            ft.Text(entry["table_name"], size=12, color=TEXT_SECONDARY, width=100),
                            ft.Text(f"ID: {entry['record_id']}", size=12, width=60),
                            ft.Text(entry["changed_at"][:19], size=11, color=TEXT_SECONDARY),
                        ], spacing=8),
                        padding=6,
                        border=ft.border.all(1, "#eeeeee"),
                        border_radius=6,
                    ))
        except Exception as ex:
            audit_col.controls.append(ft.Text(f"Ошибка: {ex}", color=ERROR))
        finally:
            loading.visible = False
            page.update()

    # ── Переключение вкладок ──────────────────────────────────────────────

    async def on_tab_change(e):
        idx = tabs.selected_index
        if idx == 0:
            await load_bookings()
        elif idx == 1:
            await load_users()
        elif idx == 2:
            await load_reports()
        elif idx == 3:
            await load_audit()

    tabs.on_change = on_tab_change
    page.run_task(load_bookings)

    tab_contents = [bookings_col, users_col, report_col, audit_col]

    content_container = ft.Container(expand=True)

    def build_view():
        idx = tabs.selected_index or 0
        return ft.Column([
            page_title("Панель управления"),
            tabs,
            ft.Row([loading], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(content=tab_contents[idx], expand=True),
        ], expand=True, scroll=ft.ScrollMode.AUTO)

    return ft.Container(
        content=ft.Column([
            page_title("Панель управления"),
            tabs,
            ft.Row([
                ft.IconButton(icon=ft.Icons.REFRESH, tooltip="Обновить",
                              on_click=lambda _: page.run_task(
                                  lambda: on_tab_change(None))),
            ], alignment=ft.MainAxisAlignment.END),
            ft.Row([loading], alignment=ft.MainAxisAlignment.CENTER),
            bookings_col,
            users_col,
            report_col,
            audit_col,
        ], expand=True, scroll=ft.ScrollMode.AUTO),
        padding=20,
        expand=True,
        bgcolor=BG_COLOR,
    )
