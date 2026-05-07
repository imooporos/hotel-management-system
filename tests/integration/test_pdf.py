"""Тест-кейс 5: формирование PDF-документов."""

from __future__ import annotations

import secrets
from datetime import date, timedelta

import httpx


PDF_HEADER = b"%PDF-"


def test_booking_receipt_pdf(http: httpx.Client, fresh_guest):
    headers = {"Authorization": f"Bearer {fresh_guest['token']}"}

    # создаём свежую бронь на случайный период в будущем
    offset = 300 + secrets.randbelow(60)
    base = date.today() + timedelta(days=offset)
    rooms = http.get(
        "/rooms",
        params={"free_from": base.isoformat(), "free_to": (base + timedelta(days=2)).isoformat()},
    ).json()
    assert rooms
    room = rooms[0]

    booking = http.post(
        "/bookings",
        headers=headers,
        json={
            "room_id": room["room_id"],
            "check_in": base.isoformat(),
            "check_out": (base + timedelta(days=2)).isoformat(),
            "guests_count": 1,
            "service_ids": [],
        },
    )
    assert booking.status_code == 201, booking.text
    booking_id = booking.json()["booking_id"]

    resp = http.get(f"/bookings/{booking_id}/receipt.pdf", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("application/pdf")
    assert resp.content[:5] == PDF_HEADER
    assert len(resp.content) > 1000  # настоящий PDF, не пустышка

    http.delete(f"/bookings/{booking_id}", headers=headers)


def test_revenue_pdf(http: httpx.Client, manager_token: str):
    resp = http.get("/reports/revenue.pdf", headers={"Authorization": f"Bearer {manager_token}"})
    assert resp.status_code == 200
    assert resp.content[:5] == PDF_HEADER


def test_occupancy_pdf(http: httpx.Client, manager_token: str):
    resp = http.get(
        "/reports/occupancy.pdf",
        params={"from": "2026-01-01", "to": "2026-12-31"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    assert resp.content[:5] == PDF_HEADER
