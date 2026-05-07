# Hotel Management System — Server

REST API сервер на базе FastAPI для системы управления гостиницей.

## Технологии

- **FastAPI** — асинхронный веб-фреймворк
- **asyncpg** — асинхронный драйвер PostgreSQL
- **Pydantic v2** — валидация данных
- **PyJWT** — JWT-аутентификация (HS256)
- **bcrypt** — хэширование паролей (cost factor 12)
- **ReportLab** — генерация PDF-документов
- **pytest** — тестирование

## Структура

```
server/
├── app/
│   ├── __init__.py
│   ├── main.py              # Точка входа FastAPI
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py         # Конфигурация (env vars)
│   │   ├── database.py       # Пул соединений asyncpg
│   │   └── security.py       # JWT, bcrypt, RBAC
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py           # POST /auth/register, /auth/login
│   │   ├── users.py          # GET/PUT /users/me, GET /users
│   │   ├── rooms.py          # GET /rooms, /rooms/{id}
│   │   ├── bookings.py       # CRUD бронирований + PDF
│   │   ├── services.py       # GET /services
│   │   └── reports.py        # GET /reports/revenue, /reports/audit
│   ├── schemas/
│   │   └── __init__.py       # Pydantic-модели
│   └── services/
│       └── pdf_generator.py  # Генерация PDF (ReportLab)
├── tests/
│   ├── conftest.py           # Фикстуры pytest
│   └── test_api.py           # Юнит-тесты
└── pyproject.toml            # Зависимости проекта
```

## Установка и запуск

```bash
# Создать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# Установить зависимости
pip install -e .

# Настроить переменные окружения
export DATABASE_URL="postgresql://hotel_app:hotel_secure_pwd_2025@localhost:5432/hotel_db"
export JWT_SECRET="your-secret-key-change-in-production"
export CORS_ORIGINS="*"

# Запустить сервер
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API-эндпоинты

| Метод | Путь | Описание | Доступ |
|-------|------|----------|--------|
| POST | /auth/register | Регистрация | Все |
| POST | /auth/login | Вход | Все |
| GET | /users/me | Профиль | Авторизованные |
| PUT | /users/me | Обновить профиль | Авторизованные |
| GET | /users | Список пользователей | admin |
| PUT | /users/{id}/role | Сменить роль | admin |
| PUT | /users/{id}/block | Блокировать | admin |
| GET | /rooms | Каталог номеров | Все |
| GET | /rooms/{id} | Детали номера | Все |
| POST | /bookings | Создать бронирование | Авторизованные |
| GET | /bookings | Мои бронирования | Авторизованные |
| GET | /bookings/all | Все бронирования | manager, admin |
| PUT | /bookings/{id}/status | Сменить статус | manager, admin |
| PUT | /bookings/{id}/cancel | Отменить | Владелец, manager, admin |
| GET | /bookings/{id}/pdf | Скачать PDF | Владелец, manager, admin |
| GET | /services | Список услуг | Все |
| GET | /reports/revenue | Отчёт по выручке | manager, admin |
| GET | /reports/audit | Аудит-лог | admin |
| GET | /health | Статус сервера | Все |

## Тестирование

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Развёрнутый сервер

Сервер развёрнут и доступен по адресу: `http://77.221.151.85:8000`

- Документация Swagger: http://77.221.151.85:8000/docs
- Документация ReDoc: http://77.221.151.85:8000/redoc
- Health check: http://77.221.151.85:8000/health
