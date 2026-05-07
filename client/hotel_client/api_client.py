"""HTTP-клиент для взаимодействия с Hotel Management API."""

import httpx
from typing import Optional


class ApiClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.user_role: Optional[str] = None
        self.user_email: Optional[str] = None

    @property
    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    # ── Аутентификация ────────────────────────────────────────────────────

    async def register(self, email: str, password: str, first_name: str,
                       last_name: str, patronymic: str = "", phone: str = "") -> dict:
        payload = {
            "email": email, "password": password,
            "first_name": first_name, "last_name": last_name,
        }
        if patronymic:
            payload["patronymic"] = patronymic
        if phone:
            payload["phone"] = phone

        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(self._url("/api/auth/register"), json=payload)
            r.raise_for_status()
            data = r.json()
            self.token = data["access_token"]
            self.user_id = data["user_id"]
            self.user_role = data["role"]
            self.user_email = data["email"]
            return data

    async def login(self, email: str, password: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(self._url("/api/auth/login"),
                             json={"email": email, "password": password})
            r.raise_for_status()
            data = r.json()
            self.token = data["access_token"]
            self.user_id = data["user_id"]
            self.user_role = data["role"]
            self.user_email = data["email"]
            return data

    def logout(self):
        self.token = None
        self.user_id = None
        self.user_role = None
        self.user_email = None

    # ── Профиль ───────────────────────────────────────────────────────────

    async def get_profile(self) -> dict:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(self._url("/api/users/me"), headers=self._headers)
            r.raise_for_status()
            return r.json()

    async def update_profile(self, data: dict) -> dict:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.put(self._url("/api/users/me"), json=data, headers=self._headers)
            r.raise_for_status()
            return r.json()

    # ── Номера ────────────────────────────────────────────────────────────

    async def get_rooms(self, **params) -> list:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(self._url("/api/rooms/"), headers=self._headers, params=params)
            r.raise_for_status()
            return r.json()

    async def get_room(self, room_id: int) -> dict:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(self._url(f"/api/rooms/{room_id}"), headers=self._headers)
            r.raise_for_status()
            return r.json()

    async def get_categories(self) -> list:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(self._url("/api/rooms/categories"), headers=self._headers)
            r.raise_for_status()
            return r.json()

    # ── Бронирования ──────────────────────────────────────────────────────

    async def create_booking(self, room_id: int, check_in: str, check_out: str,
                             guests_count: int = 1, notes: str = "",
                             service_ids: list | None = None) -> dict:
        payload = {
            "room_id": room_id,
            "check_in_date": check_in,
            "check_out_date": check_out,
            "guests_count": guests_count,
            "notes": notes,
            "service_ids": service_ids or [],
        }
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(self._url("/api/bookings/"), json=payload, headers=self._headers)
            r.raise_for_status()
            return r.json()

    async def get_my_bookings(self, status: str = "") -> list:
        params = {}
        if status:
            params["status"] = status
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(self._url("/api/bookings/my"), headers=self._headers, params=params)
            r.raise_for_status()
            return r.json()

    async def get_all_bookings(self, status: str = "") -> list:
        params = {}
        if status:
            params["status"] = status
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(self._url("/api/bookings/all"), headers=self._headers, params=params)
            r.raise_for_status()
            return r.json()

    async def cancel_booking(self, booking_id: int) -> dict:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(self._url(f"/api/bookings/{booking_id}/cancel"), headers=self._headers)
            r.raise_for_status()
            return r.json()

    async def update_booking_status(self, booking_id: int, status: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.put(self._url(f"/api/bookings/{booking_id}/status"),
                            json={"status": status}, headers=self._headers)
            r.raise_for_status()
            return r.json()

    # ── Услуги ────────────────────────────────────────────────────────────

    async def get_services(self) -> list:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(self._url("/api/services/"), headers=self._headers)
            r.raise_for_status()
            return r.json()

    # ── Пользователи (админ) ─────────────────────────────────────────────

    async def get_users(self) -> list:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(self._url("/api/users/"), headers=self._headers)
            r.raise_for_status()
            return r.json()

    async def update_user_role(self, user_id: int, role: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.put(self._url(f"/api/users/{user_id}/role"),
                            json={"role": role}, headers=self._headers)
            r.raise_for_status()
            return r.json()

    async def block_user(self, user_id: int, is_active: bool) -> dict:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.put(self._url(f"/api/users/{user_id}/block"),
                            json={"is_active": is_active}, headers=self._headers)
            r.raise_for_status()
            return r.json()

    # ── Отчёты ────────────────────────────────────────────────────────────

    async def get_revenue_report(self) -> list:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(self._url("/api/reports/revenue"), headers=self._headers)
            r.raise_for_status()
            return r.json()

    async def get_audit_log(self, limit: int = 50) -> list:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(self._url("/api/reports/audit"),
                            headers=self._headers, params={"limit": limit})
            r.raise_for_status()
            return r.json()

    async def download_booking_pdf(self, booking_id: int) -> bytes:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(self._url(f"/api/reports/booking/{booking_id}/pdf"),
                            headers=self._headers)
            r.raise_for_status()
            return r.content
