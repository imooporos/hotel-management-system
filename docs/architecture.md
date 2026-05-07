# Архитектура системы

## 1. Высокоуровневая схема

```
   Пользователь
        │
        ▼
┌──────────────────┐         ┌────────────────────┐
│  Flet-клиент     │ ───►    │   Nginx (80)       │
│  (Python, GUI)   │ JWT/REST│   reverse proxy    │
└──────────────────┘         └─────────┬──────────┘
                                       │
                                       ▼
                             ┌────────────────────┐
                             │  FastAPI + uvicorn │
                             │  systemd: hotel-api│
                             └─────────┬──────────┘
                                       │ asyncpg pool
                                       ▼
                             ┌────────────────────┐
                             │   PostgreSQL 16    │
                             │   (RLS + триггеры) │
                             └────────────────────┘
```

## 2. Слои приложения

```
client/                        — Flet (Python) cross-platform UI
├── hotel_client/api.py        — httpx wrapper, JWT, обработка ошибок
├── hotel_client/state.py      — глобальное состояние (user, theme)
├── hotel_client/theme.py      — дизайн-токены (палитра, типографика)
├── hotel_client/components/   — кнопки, инпуты, карточки, навигация
└── hotel_client/views/        — экраны: auth, home, booking, profile, admin

server/                        — FastAPI backend
├── app/main.py                — сборка приложения, lifecycle pool
├── app/core/
│   ├── config.py              — настройки из .env
│   ├── db.py                  — asyncpg pool, RLS context
│   ├── security.py            — bcrypt, JWT, RBAC
│   └── errors.py              — единая обработка исключений
├── app/routers/               — auth, rooms, bookings, services, users, reports, admin
├── app/schemas/               — Pydantic DTO
└── app/services/pdf.py        — ReportLab генерация PDF

pg_scripts/                    — все DDL и DML для БД (10 файлов)
├── 01_domains_types.sql       — домены и ENUM
├── 02_tables.sql              — 11 таблиц + EXCLUDE
├── 03_indexes.sql             — B-tree, GiST, функциональные
├── 04_views.sql               — 4 представления
├── 05_functions.sql           — фн. fn_room_is_free, fn_calculate_..., fn_occupancy_rate
├── 06_procedures.sql          — sp_register_user, sp_create/update/cancel_booking, sp_get_user_bookings
├── 07_triggers.sql            — 5 триггеров (updated_at, no_overlap, room_status, аудит)
├── 08_seed_data.sql           — 5 пользователей, 50 номеров, 6 услуг, 5 броней
├── 09_queries_pool.sql        — 12 типов запросов из пула
└── 10_security.sql            — RLS, роли БД

tests/                         — pytest
├── unit/                      — 2 юнит-теста (security)
└── integration/               — 5 тест-кейсов (auth, booking, overlap, RBAC, PDF)

docs/                          — документация
├── user_guide.md
├── admin_guide.md
├── security.md
└── architecture.md (этот файл)
```

## 3. Потоки данных

### 3.1 Бронирование

```
┌──────────┐     POST /bookings/calculate     ┌────────────┐
│  Клиент  │ ────────────────────────────────►│  FastAPI   │
└──────────┘                                  └─────┬──────┘
     │                                              │
     │                                              ▼
     │                                       SELECT fn_room_is_free
     │                                       SELECT fn_calculate_booking_total
     │                                              │
     │ ◄─── { total_price, nights, is_room_free } ──┘
     │
     │     POST /bookings (room_id, dates, services)
     │  ────────────────────────────────►│
     │                                   ▼
     │                            SET LOCAL app.user_id
     │                            SELECT * FROM fn_create_booking(...)
     │                                  │
     │                                  ▼
     │                            CALL sp_create_booking(...)
     │                            ↳ trg_no_overlap_booking
     │                            ↳ trg_audit_bookings
     │                            ↳ trg_update_room_status
     │                                  │
     │ ◄────── { booking_id, total_price, ... } ─────┘
```

### 3.2 Аутентификация

```
1) POST /auth/register
        ▼
   Pydantic валидация (email, password ≥ 8, phone format)
        ▼
   bcrypt.hashpw(password, rounds=12)
        ▼
   CALL sp_register_user(...)
        ▼
   Возврат JWT (HS256, exp=12h)

2) Authorization: Bearer <jwt>
        ▼
   decode_token(token)
        ▼
   SELECT u.user_id, ..., r.code AS role FROM users u JOIN roles r
        ▼
   inject CurrentUser в обработчик
```

## 4. Технологический стек

| Слой | Технология |
|------|------------|
| СУБД | PostgreSQL 16 |
| Backend | Python 3.13, FastAPI, uvicorn, asyncpg |
| Авторизация | bcrypt, PyJWT |
| Документы | ReportLab (PDF) |
| Клиент | Python 3.11+, Flet, httpx |
| Тесты | pytest, pytest-asyncio, httpx |
| Деплой | systemd, Nginx, Linux (Ubuntu 24.04) |
| CI | (не настроено в рамках КП) |

## 5. Решения по безопасности

См. отдельный документ — `security.md`.
