# Backend (FastAPI)

REST API для информационной системы управления гостиницей.

## Возможности

- Регистрация и логин (OAuth2 password flow → JWT)
- Bcrypt-хэширование паролей (cost factor 12)
- Ролевая модель: `guest` / `manager` / `admin`
- Полное использование объектов БД: процедуры `sp_register_user`, `sp_create_booking`, `sp_update_booking_status`, `sp_cancel_booking`; функции `fn_room_is_free`, `fn_calculate_booking_total`, `fn_occupancy_rate`; представления `v_room_availability`, `v_guest_bookings`, `v_revenue_by_category`, `v_active_bookings`
- Глобальная обработка исключений: `asyncpg.PostgresError` → понятный JSON
- Генерация PDF бланка заказа (ReportLab)
- Авто-документация Swagger / ReDoc

## Запуск (локально)

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # отредактируйте DATABASE_URL и JWT_SECRET
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

После запуска:

- API: <http://localhost:8000>
- Swagger: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

## Структура

```
app/
├── main.py                 точка входа FastAPI, lifespan, middleware, exception handlers
├── core/
│   ├── config.py           pydantic-settings: чтение переменных окружения
│   ├── db.py               пул asyncpg, контекст app.user_id, app.actor_id
│   ├── security.py         bcrypt, JWT, dependency require_role(...)
│   └── errors.py           кастомные исключения и единые ответы об ошибках
├── routers/
│   ├── auth.py             /auth/register, /auth/login, /auth/me
│   ├── rooms.py            /rooms (каталог + удобства), /rooms/{id}/availability
│   ├── bookings.py         /bookings (CRUD), /bookings/{id}/receipt.pdf
│   ├── services.py         /services (CRUD для admin)
│   ├── users.py            /users (admin: управление пользователями)
│   └── reports.py          /reports/occupancy, /reports/revenue
├── schemas/                Pydantic-схемы запросов/ответов
└── services/
    ├── pdf.py              генерация PDF-квитанций и отчётов
    └── reports.py          бизнес-логика отчётов
```

## Эндпоинты (основные)

| Метод | Путь                              | Роль          | Описание                                 |
|-------|-----------------------------------|---------------|------------------------------------------|
| POST  | `/auth/register`                  | публичный     | Регистрация (роль guest)                 |
| POST  | `/auth/login`                     | публичный     | Получение JWT                            |
| GET   | `/auth/me`                        | любая         | Информация о текущем пользователе        |
| GET   | `/rooms`                          | любая         | Каталог номеров (фильтры, доступность)   |
| GET   | `/rooms/{id}`                     | любая         | Детали номера                            |
| GET   | `/rooms/{id}/availability`        | любая         | Проверка свободы по датам                |
| POST  | `/rooms`                          | admin         | Создание номера                          |
| PATCH | `/rooms/{id}`                     | admin         | Обновление номера                        |
| GET   | `/services`                       | любая         | Список услуг                             |
| POST  | `/services`                       | admin         | Создание услуги                          |
| GET   | `/bookings`                       | manager/admin | Все бронирования                         |
| GET   | `/bookings/me`                    | guest         | Свои бронирования                        |
| POST  | `/bookings`                       | guest+        | Создать бронирование                     |
| PATCH | `/bookings/{id}/status`           | manager/admin | Сменить статус бронирования              |
| DELETE| `/bookings/{id}`                  | guest+ (свой) | Отменить бронирование                    |
| GET   | `/bookings/{id}/receipt.pdf`      | guest+ (свой) | Распечатать бланк заказа                 |
| GET   | `/users`                          | admin         | Список пользователей                     |
| PATCH | `/users/{id}`                     | admin         | Изменить роль / активность               |
| GET   | `/reports/occupancy`              | manager/admin | Загрузка фонда (JSON или PDF)            |
| GET   | `/reports/revenue`                | manager/admin | Выручка по категориям (JSON или PDF)     |
| GET   | `/admin/audit`                    | admin         | Журнал аудита                            |

## Тесты

```bash
cd server
pytest -v
```

Тесты используют тестовую БД (см. `tests/conftest.py` — переменная `TEST_DATABASE_URL`).
