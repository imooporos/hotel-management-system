"""Тонкий HTTP-клиент к FastAPI бэкенду."""

from __future__ import annotations

import os
from datetime import date
from typing import Any

import httpx


DEFAULT_TIMEOUT = 30.0


class ApiError(RuntimeError):
    """Общая ошибка API."""

    def __init__(self, message: str, *, status_code: int = 0, code: str = "api_error", details: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details

    def __str__(self) -> str:  # noqa: D401
        return self.message


class ApiClient:
    """
    Обёртка httpx с авторизацией Bearer JWT и единообразной обработкой ошибок.
    Используется в синхронном виде (Flet event handlers).
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.environ.get("HOTEL_API_URL", "http://77.221.151.85")).rstrip("/")
        self._token: str | None = None
        self._client = httpx.Client(timeout=DEFAULT_TIMEOUT)

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    @property
    def token(self) -> str | None:
        return self._token

    @token.setter
    def token(self, value: str | None) -> None:
        self._token = value

    @property
    def is_authenticated(self) -> bool:
        return bool(self._token)

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if extra:
            headers.update(extra)
        return headers

    def _handle(self, resp: httpx.Response) -> Any:
        if resp.is_success:
            ctype = resp.headers.get("content-type", "")
            if "application/json" in ctype:
                return resp.json()
            return resp.content
        # Try to parse error JSON
        try:
            data = resp.json()
            message = data.get("message") or data.get("detail") or "Ошибка запроса"
            code = data.get("code", "api_error")
            details = data.get("details")
        except Exception:  # noqa: BLE001
            message = resp.text or f"HTTP {resp.status_code}"
            code = "http_error"
            details = None
        raise ApiError(message, status_code=resp.status_code, code=code, details=details)

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        try:
            resp = self._client.request(method, url, headers=self._headers(kwargs.pop("headers", None)), **kwargs)
        except httpx.HTTPError as exc:
            raise ApiError(f"Сетевая ошибка: {exc}", code="network") from exc
        return self._handle(resp)

    # ------------------------------------------------------------------
    # Auth endpoints
    # ------------------------------------------------------------------

    def login(self, email: str, password: str) -> dict:
        data = self._request("POST", "/auth/login-json", json={"email": email, "password": password})
        self._token = data["access_token"]
        return data

    def register(self, email: str, password: str, full_name: str, phone: str | None = None) -> dict:
        body = {"email": email, "password": password, "full_name": full_name}
        if phone:
            body["phone"] = phone
        data = self._request("POST", "/auth/register", json=body)
        self._token = data["access_token"]
        return data

    def logout(self) -> None:
        self._token = None

    def me(self) -> dict:
        return self._request("GET", "/auth/me")

    def update_profile(self, **fields) -> dict:
        return self._request("PATCH", "/auth/me", json={k: v for k, v in fields.items() if v is not None})

    # ------------------------------------------------------------------
    # Catalog
    # ------------------------------------------------------------------

    def list_categories(self) -> list[dict]:
        return self._request("GET", "/categories")

    def list_rooms(
        self,
        *,
        category_id: int | None = None,
        capacity_min: int | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        free_from: date | None = None,
        free_to: date | None = None,
    ) -> list[dict]:
        params: dict[str, Any] = {}
        if category_id is not None:
            params["category_id"] = category_id
        if capacity_min is not None:
            params["capacity_min"] = capacity_min
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price
        if free_from:
            params["free_from"] = free_from.isoformat()
        if free_to:
            params["free_to"] = free_to.isoformat()
        return self._request("GET", "/rooms", params=params)

    def get_room(self, room_id: int) -> dict:
        return self._request("GET", f"/rooms/{room_id}")

    def list_services(self) -> list[dict]:
        return self._request("GET", "/services")

    # ------------------------------------------------------------------
    # Bookings
    # ------------------------------------------------------------------

    def my_bookings(self) -> list[dict]:
        return self._request("GET", "/bookings/me")

    def all_bookings(self) -> list[dict]:
        return self._request("GET", "/bookings")

    def calculate_booking(
        self, room_id: int, check_in: date, check_out: date, service_ids: list[int]
    ) -> dict:
        return self._request(
            "POST",
            "/bookings/calculate",
            json={
                "room_id": room_id,
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "service_ids": service_ids,
            },
        )

    def create_booking(
        self,
        *,
        room_id: int,
        check_in: date,
        check_out: date,
        guests_count: int,
        service_ids: list[int],
        notes: str | None = None,
    ) -> dict:
        return self._request(
            "POST",
            "/bookings",
            json={
                "room_id": room_id,
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "guests_count": guests_count,
                "service_ids": service_ids,
                "notes": notes,
            },
        )

    def cancel_booking(self, booking_id: int) -> dict:
        return self._request("DELETE", f"/bookings/{booking_id}")

    def update_booking_status(self, booking_id: int, status_value: str) -> dict:
        return self._request(
            "PATCH", f"/bookings/{booking_id}/status", json={"status": status_value}
        )

    def receipt_pdf(self, booking_id: int) -> bytes:
        url = f"{self.base_url}/bookings/{booking_id}/receipt.pdf"
        resp = self._client.get(url, headers=self._headers())
        if not resp.is_success:
            raise ApiError(f"Не удалось скачать PDF: HTTP {resp.status_code}")
        return resp.content

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------

    def list_users(self) -> list[dict]:
        return self._request("GET", "/users")

    def update_user(self, user_id: int, *, role_code: str | None = None, is_active: bool | None = None) -> dict:
        body: dict = {}
        if role_code is not None:
            body["role_code"] = role_code
        if is_active is not None:
            body["is_active"] = is_active
        return self._request("PATCH", f"/users/{user_id}", json=body)

    def revenue_report(self) -> list[dict]:
        return self._request("GET", "/reports/revenue")

    def occupancy_report(self, period_start: date, period_end: date) -> dict:
        return self._request(
            "GET", "/reports/occupancy",
            params={"from": period_start.isoformat(), "to": period_end.isoformat()},
        )

    def revenue_pdf(self) -> bytes:
        url = f"{self.base_url}/reports/revenue.pdf"
        resp = self._client.get(url, headers=self._headers())
        if not resp.is_success:
            raise ApiError(f"Не удалось скачать PDF: HTTP {resp.status_code}")
        return resp.content

    def occupancy_pdf(self, period_start: date, period_end: date) -> bytes:
        url = f"{self.base_url}/reports/occupancy.pdf"
        resp = self._client.get(
            url,
            headers=self._headers(),
            params={"from": period_start.isoformat(), "to": period_end.isoformat()},
        )
        if not resp.is_success:
            raise ApiError(f"Не удалось скачать PDF: HTTP {resp.status_code}")
        return resp.content

    def audit_log(self, *, table_name: str | None = None, limit: int = 50) -> list[dict]:
        params: dict[str, Any] = {"limit": limit}
        if table_name:
            params["table_name"] = table_name
        return self._request("GET", "/admin/audit", params=params)

    def create_room(
        self,
        *,
        room_number: str,
        floor: int,
        category_id: int,
        price_modifier: float = 0,
        description: str | None = None,
    ) -> dict:
        return self._request(
            "POST",
            "/rooms",
            json={
                "room_number": room_number,
                "floor": floor,
                "category_id": category_id,
                "price_modifier": price_modifier,
                "description": description,
            },
        )

    def update_room(self, room_id: int, **fields) -> dict:
        return self._request("PATCH", f"/rooms/{room_id}", json={k: v for k, v in fields.items() if v is not None})

    def create_service(self, *, code: str, title: str, price: float, description: str | None = None) -> dict:
        return self._request(
            "POST",
            "/services",
            json={"code": code, "title": title, "price": price, "description": description},
        )
