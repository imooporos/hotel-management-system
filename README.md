# Информационная система управления гостиницей

Курсовой проект по дисциплине **«Технология разработки и защиты баз данных»**.

Клиент-серверное приложение для управления гостиницей с акцентом на проектирование и использование объектов реляционной базы данных PostgreSQL: пользовательских доменов, типов, представлений, функций, процедур и триггеров.

---

## Содержание

- [Стек технологий](#стек-технологий)
- [Архитектура](#архитектура)
- [Структура репозитория](#структура-репозитория)
- [Функционал](#функционал)
- [Группы пользователей](#группы-пользователей-и-разграничение-прав)
- [Объекты базы данных](#объекты-базы-данных)
- [Запуск проекта](#запуск-проекта)
- [Развёрнутый сервер](#развёрнутый-сервер)
- [Документация](#документация)

---

## Стек технологий

| Слой         | Технология                                                                 |
|--------------|----------------------------------------------------------------------------|
| СУБД         | **PostgreSQL 16** (домены, ENUM, представления, функции, процедуры, триггеры) |
| Backend      | Python 3.13, **FastAPI**, asyncpg, Pydantic v2, PyJWT, bcrypt              |
| Клиент       | Python 3.13, **Flet** (кроссплатформенный — Desktop / Web / iOS / Android) |
| Аутентификация| OAuth2 Password flow + JWT (HS256), bcrypt-хэширование паролей           |
| Транспорт    | HTTP/JSON REST API, TLS терминируется на Nginx                             |
| Отчёты       | ReportLab → PDF (распечатка бланка заказа, отчёт по бронированиям)         |
| Тесты        | pytest, httpx (5 тест-кейсов + 2 юнит-теста)                               |
| Деплой       | Debian 12, systemd, nginx (reverse proxy)                                  |

## Архитектура

```
┌──────────────────────────────────┐
│  Клиент Flet (Desktop / Mobile)  │
│  - Личный кабинет                │
│  - Каталог номеров               │
│  - Бронирование, печать заказа   │
│  - Админ-панель                  │
└──────────────┬───────────────────┘
               │ HTTPS / JSON
               ▼
┌──────────────────────────────────┐
│  Nginx (reverse proxy, TLS)      │
└──────────────┬───────────────────┘
               │ http://127.0.0.1:8000
               ▼
┌──────────────────────────────────┐
│  FastAPI (Python 3.13)           │
│  - JWT auth, RBAC                │
│  - Bcrypt-пароли                 │
│  - Валидация Pydantic            │
│  - Глобальные обработчики ошибок │
└──────────────┬───────────────────┘
               │ asyncpg
               ▼
┌──────────────────────────────────┐
│  PostgreSQL 16                   │
│  - Домены / ENUM                 │
│  - Триггеры на бронирования      │
│  - Представления для отчётов     │
│  - Хранимые процедуры / функции  │
│  - Аудит-лог (trigger)           │
└──────────────────────────────────┘
```

## Структура репозитория

```
.
├── pg_scripts/              SQL-скрипты для воспроизведения БД
│   ├── 01_domains_types.sql Домены, ENUM, пользовательские типы
│   ├── 02_tables.sql        DDL таблиц + ограничения целостности
│   ├── 03_indexes.sql       Индексы (B-tree, GiST для диапазонов дат)
│   ├── 04_views.sql         Представления для отчётов и витрин
│   ├── 05_functions.sql     Скалярные и табличные функции
│   ├── 06_procedures.sql    Хранимые процедуры (insert/update/delete/select)
│   ├── 07_triggers.sql      Триггеры (бизнес-логика, аудит, целостность)
│   ├── 08_seed_data.sql     Тестовые данные
│   ├── 09_queries_pool.sql  12 типов SQL-запросов из требований
│   ├── 10_security.sql      Роли БД, GRANT/REVOKE, RLS
│   └── reset.sh             Полная пересборка БД
│
├── server/                  Backend FastAPI
│   ├── app/
│   │   ├── main.py          Точка входа FastAPI
│   │   ├── core/            Настройки, безопасность, БД, исключения
│   │   ├── routers/         API-эндпоинты
│   │   ├── schemas/         Pydantic-схемы запроса/ответа
│   │   └── services/        Бизнес-логика, генерация PDF
│   ├── tests/               pytest: интеграционные и юнит-тесты
│   ├── pyproject.toml
│   └── README.md
│
├── client/                  Клиентское приложение Flet
│   ├── hotel_client/
│   │   ├── main.py          Точка входа клиента
│   │   ├── api.py           HTTP-клиент к серверу
│   │   ├── theme.py         Тема, токены дизайна
│   │   ├── views/           Экраны (login, rooms, profile, admin, …)
│   │   └── components/      Переиспользуемые UI-компоненты
│   ├── pyproject.toml
│   └── README.md
│
├── docs/                    Документация курсового проекта
│   ├── 01_problem_statement.md
│   ├── 02_database_design.md
│   ├── 03_db_objects.md
│   ├── 04_application_design.md
│   ├── 05_security.md
│   ├── 06_user_guide.md
│   ├── 07_admin_guide.md
│   ├── 08_test_cases.md
│   ├── api_reference.md
│   └── screenshots/
│
└── .github/workflows/       CI: линт, тесты
```

## Функционал

### Для гостя (роль `guest`)
- Регистрация личного кабинета (имя, email, телефон, паспортные данные)
- Вход по email + пароль (bcrypt + JWT)
- Просмотр и редактирование профиля
- Просмотр каталога номеров с фильтрами (категория, цена, вместимость, даты)
- Создание бронирования (с автоматической проверкой свободных дат через триггер)
- Подключение дополнительных услуг к бронированию
- Печать бланка заказа (PDF)
- История своих бронирований

### Для менеджера (роль `manager`)
- Все возможности гостя
- Подтверждение бронирований
- Регистрация заезда / выезда (check-in / check-out)
- Изменение статуса номера (свободен / занят / уборка / на ремонте)
- Просмотр актуальных бронирований всех гостей
- Формирование отчётов: загрузка номерного фонда, выручка по категориям

### Для администратора (роль `admin`)
- Все возможности менеджера
- CRUD номеров и категорий
- Управление дополнительными услугами (CRUD)
- Управление пользователями (просмотр, смена ролей, блокировка)
- Просмотр аудит-лога

## Группы пользователей и разграничение прав

Разграничение прав реализовано на трёх уровнях:

1. **На уровне приложения** — JWT-токен содержит `role`, FastAPI-зависимость `require_role(...)` блокирует запросы без нужной роли (см. `server/app/core/security.py`).
2. **На уровне БД** — отдельные роли PostgreSQL (`hotel_guest`, `hotel_manager`, `hotel_admin`), GRANT на нужные таблицы/представления/процедуры. Само приложение подключается под единым пользователем `hotel_app`, но при необходимости может использовать `SET ROLE`.
3. **На уровне строк (RLS)** — Row Level Security включён для таблицы `bookings`: гость видит только свои бронирования (см. `pg_scripts/10_security.sql`).

## Объекты базы данных

| Тип объекта      | Кол-во | Краткое описание |
|------------------|:------:|------------------|
| Таблицы          | 11     | users, roles, guest_profiles, room_categories, rooms, amenities, room_amenities, services, bookings, booking_services, payments, audit_log |
| Домены           | 3      | `email_domain`, `phone_domain`, `positive_money` |
| ENUM-типы        | 2      | `room_status`, `booking_status` |
| Индексы          | 12     | B-tree по FK, GiST по `tsrange` (даты бронирований) |
| Представления    | 4      | `v_room_availability`, `v_guest_bookings`, `v_revenue_by_category`, `v_active_bookings` |
| Функции          | 3      | `fn_room_is_free`, `fn_calculate_booking_total`, `fn_occupancy_rate` |
| Процедуры        | 5      | `sp_create_booking`, `sp_update_booking_status`, `sp_cancel_booking`, `sp_register_user`, `sp_get_user_bookings` |
| Триггеры         | 3      | `trg_no_overlap_booking`, `trg_audit_bookings`, `trg_update_room_status` |
| RLS-политики     | 2      | владелец видит свои бронирования, админ видит всё |

Подробное описание — в [docs/03_db_objects.md](docs/03_db_objects.md).

## Запуск проекта

### Требования
- PostgreSQL 16+
- Python 3.13+
- pip / venv

### 1. Развёртывание базы данных

```bash
cd pg_scripts
psql -U postgres -c "CREATE USER hotel_app WITH PASSWORD 'AppHotelStrong_pass_2026';"
psql -U postgres -c "CREATE DATABASE hotel_db OWNER hotel_app;"
PGPASSWORD=AppHotelStrong_pass_2026 ./reset.sh hotel_db hotel_app
```

### 2. Backend

```bash
cd server
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env   # затем отредактировать DATABASE_URL и JWT_SECRET
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API будет доступен по адресу `http://localhost:8000`, документация Swagger — `http://localhost:8000/docs`.

### 3. Клиент

```bash
cd client
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e .
HOTEL_API_URL=http://localhost:8000 python -m hotel_client.main
```

## Развёрнутый сервер

Тестовый сервер курсового проекта развёрнут на:

- **Хост**: `77.221.151.85`
- **API**: `http://77.221.151.85/api` (за reverse proxy nginx)
- **Документация Swagger**: `http://77.221.151.85/api/docs`

Тестовые учётные записи (см. `pg_scripts/08_seed_data.sql`):

| Роль    | Email                   | Пароль          |
|---------|-------------------------|-----------------|
| admin   | admin@hotel.local       | Admin_2026!     |
| manager | manager@hotel.local     | Manager_2026!   |
| guest   | ivanov@example.com      | Guest_2026!     |

## Документация

Полная пояснительная записка курсового проекта — в каталоге [docs/](docs/):

1. [Постановка задачи](docs/01_problem_statement.md)
2. [Проектирование БД](docs/02_database_design.md)
3. [Объекты БД](docs/03_db_objects.md)
4. [Проектирование приложения](docs/04_application_design.md)
5. [Методы защиты данных](docs/05_security.md)
6. [Руководство пользователя](docs/06_user_guide.md)
7. [Руководство администратора](docs/07_admin_guide.md)
8. [Тест-кейсы](docs/08_test_cases.md)
9. [API Reference](docs/api_reference.md)

## Лицензия

Учебный проект. Все права принадлежат автору.
