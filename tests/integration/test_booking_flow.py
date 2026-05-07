"""Тест-кейс 2: расчёт → создание → отмена бронирования."""

from __future__ import annotations

import secrets
from datetime import date, timedelta

import httpx


def test_calculate_create_cancel(http: httpx.Client, fresh_guest):
    token = fresh_guest["token"]
    headers = {"Authorization": f"Bearer {token}"}

    offset = 200 + secrets.randbelow(60)
    check_in = date.today() + timedelta(days=offset)
    check_out = check_in + timedelta(days=3)
    rooms = http.get(
        "/rooms",
        params={"free_from": check_in.isoformat(), "free_to": check_out.isoformat()},
    ).json()
    assert rooms, "Должен быть хотя бы один свободный номер на тестовый диапазон"
    room = rooms[0]

    # 1) расчёт стоимости
    resp = http.post(
        "/bookings/calculate",
        headers=headers,
        json={
            "room_id": room["room_id"],
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "service_ids": [],
        },
    )
    assert resp.status_code == 200, resp.text
    calc = resp.json()
    assert calc["nights"] == 3
    assert float(calc["total_price"]) > 0
    assert calc["is_room_free"] is True

    # 2) создание брони
    resp = http.post(
        "/bookings",
        headers=headers,
        json={
            "room_id": room["room_id"],
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests_count": 1,
            "service_ids": [],
            "notes": "Автотест",
        },
    )
    assert resp.status_code == 201, resp.text
    booking = resp.json()
    assert booking["status"] == "pending"
    assert booking["nights"] == 3
    booking_id = booking["booking_id"]

    # 3) видна в /bookings/me
    resp = http.get("/bookings/me", headers=headers)
    assert resp.status_code == 200
    assert any(b["booking_id"] == booking_id for b in resp.json())

    # 4) отмена
    resp = http.delete(f"/bookings/{booking_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "cancelled"
