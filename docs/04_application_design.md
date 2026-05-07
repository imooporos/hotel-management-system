# 4. Проектирование и создание приложения

## 4.1 Архитектура системы

Система построена по архитектуре **клиент-сервер** с чётким разделением на три слоя:

```
┌─────────────────────────────────────────────────────┐
│                  Клиент (Flet)                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐ │
│  │  Login   │ │  Rooms  │ │ Profile │ │   Admin   │ │
│  │  View    │ │  View   │ │  View   │ │   Panel   │ │
│  └────┬─────┘ └────┬────┘ └────┬────┘ └─────┬─────┘ │
│       └────────────┴──────────┴─────────────┘       │
│                    ApiClient                         │
│                (httpx, async)                        │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP/JSON (REST API)
┌──────────────────────┴──────────────────────────────┐
│                  Сервер (FastAPI)                     │
│  ┌──────────────────────────────────────────────┐    │
│  │              Routers (API Layer)              │    │
│  │  auth │ users │ rooms │ bookings │ reports    │    │
│  └──────────────────┬───────────────────────────┘    │
│  ┌──────────────────┴───────────────────────────┐    │
│  │            Core / Services Layer              │    │
│  │  security │ database │ config │ pdf_generator │    │
│  └──────────────────┬───────────────────────────┘    │
│  ┌──────────────────┴───────────────────────────┐    │
│  │             Schemas (Pydantic v2)             │    │
│  │  UserCreate │ BookingCreate │ RoomResponse    │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────┘
                       │ asyncpg (пул подключений)
┌──────────────────────┴──────────────────────────────┐
│                 PostgreSQL 16                        │
│  Таблицы │ Представления │ Функции │ Триггеры │ RLS │
└─────────────────────────────────────────────────────┘
```

## 4.2 Серверная часть (FastAPI)

### Структура каталогов

```
server/
├── app/
│   ├── __init__.py
│   ├── main.py              # Точка входа, lifespan, middleware
│   ├── core/
│   │   ├── config.py        # Настройки из переменных окружения
│   │   ├── database.py      # Пул подключений asyncpg
│   │   ├── security.py      # JWT, bcrypt, зависимости авторизации
│   │   └── exceptions.py    # Глобальные обработчики ошибок
│   ├── routers/
│   │   ├── auth.py          # POST /auth/register, /auth/login
│   │   ├── users.py         # GET/PUT /users/me, GET /users (admin)
│   │   ├── rooms.py         # GET /rooms, GET /rooms/{id}
│   │   ├── bookings.py      # CRUD бронирований
│   │   ├── services.py      # GET /services
│   │   └── reports.py       # GET /reports/revenue, /reports/audit
│   ├── schemas/
│   │   ├── auth.py          # LoginRequest, TokenResponse
│   │   ├── users.py         # UserCreate, UserResponse, UserUpdate
│   │   ├── rooms.py         # RoomResponse, RoomFilter
│   │   ├── bookings.py      # BookingCreate, BookingResponse
│   │   ├── services.py      # ServiceResponse
│   │   └── reports.py       # RevenueReport, AuditEntry
│   └── services/
│       └── pdf_generator.py # Генерация PDF-бланка заказа
├── tests/
│   ├── conftest.py          # Фикстуры pytest
│   └── test_api.py          # Юнит-тесты и тест-кейсы
└── pyproject.toml
```

### Ключевые паттерны

1. **Lifespan** — пул подключений asyncpg создаётся при старте и закрывается при остановке.
2. **Dependency Injection** — `get_current_user()` извлекает JWT из заголовка, `require_role()` проверяет роль.
3. **Pydantic v2** — валидация входных данных с автоматической генерацией JSON Schema.
4. **Глобальные обработчики исключений** — AppException, asyncpg.PostgresError, Exception.

### API-эндпоинты

| Метод | Путь | Роль | Описание |
|-------|------|------|----------|
| POST | /auth/register | — | Регистрация |
| POST | /auth/login | — | Авторизация, получение JWT |
| GET | /users/me | any | Профиль текущего пользователя |
| PUT | /users/me | any | Обновление профиля |
| GET | /users | admin | Список пользователей |
| PUT | /users/{id}/role | admin | Смена роли |
| PUT | /users/{id}/block | admin | Блокировка пользователя |
| GET | /rooms | any | Каталог номеров с фильтрами |
| GET | /rooms/{id} | any | Детали номера |
| POST | /bookings | guest+ | Создание бронирования |
| GET | /bookings | guest+ | Мои бронирования |
| GET | /bookings/all | manager+ | Все бронирования |
| PUT | /bookings/{id}/status | manager+ | Смена статуса |
| PUT | /bookings/{id}/cancel | guest+ | Отмена бронирования |
| GET | /bookings/{id}/pdf | guest+ | Скачать PDF бланк |
| GET | /services | any | Список услуг |
| GET | /reports/revenue | manager+ | Отчёт по выручке |
| GET | /reports/audit | admin | Аудит-лог |

## 4.3 Клиентская часть (Flet)

### Структура каталогов

```
client/
├── hotel_client/
│   ├── __init__.py
│   ├── main.py              # Точка входа, навигация
│   ├── api_client.py        # HTTP-клиент (httpx)
│   ├── theme.py             # Тема, цвета, стили
│   ├── views/
│   │   ├── login_view.py    # Экран входа
│   │   ├── register_view.py # Экран регистрации
│   │   ├── rooms_view.py    # Каталог номеров
│   │   ├── booking_view.py  # Форма бронирования
│   │   ├── profile_view.py  # Личный кабинет
│   │   ├── my_bookings_view.py  # История бронирований
│   │   └── admin_view.py    # Панель администратора
│   └── components/
│       └── __init__.py      # Переиспользуемые компоненты
└── pyproject.toml
```

### Описание экранов

| Экран | Файл | Функционал |
|-------|------|-----------|
| Вход | login_view.py | Email + пароль, ссылка на регистрацию |
| Регистрация | register_view.py | ФИО, email, телефон, пароль с валидацией |
| Каталог номеров | rooms_view.py | Фильтрация по категории/вместимости, карточки номеров |
| Бронирование | booking_view.py | Даты, количество гостей, выбор услуг, итоговая сумма |
| Профиль | profile_view.py | Редактирование ФИО, телефона, паспортных данных |
| Мои бронирования | my_bookings_view.py | Список бронирований со статусами, отмена, PDF |
| Админ-панель | admin_view.py | 4 вкладки: бронирования, пользователи, отчёты, аудит |

### Навигация

Навигация реализована через `NavigationRail` с динамическим набором пунктов:
- Гость: Номера, Бронирования, Профиль
- Менеджер/Админ: + Управление

## 4.4 Обработка ошибок

### Серверная сторона

```python
# Пользовательские исключения
class AppException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

# Глобальные обработчики
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(asyncpg.PostgresError, asyncpg_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
```

### Клиентская сторона

Все вызовы API обёрнуты в try/except с отображением SnackBar:
```python
try:
    result = await api.create_booking(...)
    page.snack_bar = ft.SnackBar(ft.Text("Бронирование создано!"))
except Exception as e:
    page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка: {e}"))
```

## 4.5 Генерация PDF

Для формирования бланка заказа используется библиотека **ReportLab**:

```python
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
```

PDF-документ содержит:
- Заголовок «Гранд Отель — Бланк заказа»
- Данные гостя (ФИО, email, телефон)
- Информация о номере (номер, категория, этаж)
- Даты проживания
- Список дополнительных услуг с ценами
- Итоговая сумма
- Дата формирования документа
