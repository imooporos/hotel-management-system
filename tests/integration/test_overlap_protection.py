"""Тест-кейс 3: триггер не даёт создать бронь, пересекающуюся по датам."""

from __future__ import annotations

import secrets
from datetime import date, timedelta

import httpx


def test_overlap_rejected(http: httpx.Client, fresh_guest):
    headers = {"Authorization": f"Bearer {fresh_guest['token']}"}

    # выберем свободный на нужный период номер.
    # Берём случайный смещённый период в будущем, чтобы тесты были независимы между запусками.
    offset = 90 + secrets.randbelow(120)
    base = date.today() + timedelta(days=offset)
    rooms = http.get(
        "/rooms",
        params={
            "free_from": base.isoformat(),
            "free_to": (base + timedelta(days=5)).isoformat(),
        },
    ).json()
    assert rooms, "Должен быть хотя бы один свободный номер на тестовый диапазон"
    room = rooms[0]
    room_id = room["room_id"]

    # 1) создаём первую бронь
    resp = http.post(
        "/bookings",
        headers=headers,
        json={
            "room_id": room_id,
            "check_in": base.isoformat(),
            "check_out": (base + timedelta(days=4)).isoformat(),
            "guests_count": 1,
            "service_ids": [],
        },
    )
    assert resp.status_code == 201, resp.text
    booking_id_1 = resp.json()["booking_id"]

    # 2) пересекающаяся бронь должна быть отклонена
    resp = http.post(
        "/bookings",
        headers=headers,
        json={
            "room_id": room_id,
            "check_in": (base + timedelta(days=1)).isoformat(),
            "check_out": (base + timedelta(days=5)).isoformat(),
            "guests_count": 1,
            "service_ids": [],
        },
    )
    assert resp.status_code == 409, resp.text
    payload = resp.json()
    assert payload["code"] in ("overlap", "conflict", "exclusion")
    # Сообщение должно намекать на пересечение / занятость
    msg = (payload.get("message") or "").lower()
    assert any(w in msg for w in ("занят", "забронир", "перес", "конфликт", "overlap"))

    # 3) cleanup — отменим первую
    http.delete(f"/bookings/{booking_id_1}", headers=headers)
