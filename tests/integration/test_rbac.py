"""Тест-кейс 4: RBAC — гость не имеет доступа к admin/manager эндпоинтам."""

from __future__ import annotations

import httpx


def test_guest_cannot_access_admin_endpoints(http: httpx.Client, guest_token: str):
    g = {"Authorization": f"Bearer {guest_token}"}

    # отчёты — только для manager/admin
    assert http.get("/reports/revenue", headers=g).status_code == 403
    assert http.get("/reports/occupancy?from=2026-01-01&to=2026-12-31", headers=g).status_code == 403

    # управление пользователями — только admin
    assert http.get("/users", headers=g).status_code == 403

    # журнал аудита — только admin
    assert http.get("/admin/audit", headers=g).status_code == 403

    # /bookings (просмотр всех) — только manager/admin
    assert http.get("/bookings", headers=g).status_code == 403


def test_manager_has_access(http: httpx.Client, manager_token: str):
    h = {"Authorization": f"Bearer {manager_token}"}
    assert http.get("/reports/revenue", headers=h).status_code == 200
    assert http.get("/bookings", headers=h).status_code == 200
    # но не админские
    assert http.get("/users", headers=h).status_code == 403
    assert http.get("/admin/audit", headers=h).status_code == 403


def test_anonymous_blocked(http: httpx.Client):
    assert http.get("/auth/me").status_code == 401
    assert http.get("/bookings/me").status_code == 401
