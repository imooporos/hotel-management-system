# Полное руководство по проекту «HotelMS»

## Информационная система управления гостиницей

Курсовой проект по дисциплине «Технология разработки и защиты баз данных»

---

## Содержание

1. [Обзор проекта](#1-обзор-проекта)
2. [Архитектура системы](#2-архитектура-системы)
3. [Стек технологий](#3-стек-технологий)
4. [Структура репозитория](#4-структура-репозитория)
5. [База данных PostgreSQL](#5-база-данных-postgresql)
6. [Серверная часть (FastAPI)](#6-серверная-часть-fastapi)
7. [Десктоп-клиент (Flet)](#7-десктоп-клиент-flet)
8. [Веб-клиент (SPA)](#8-веб-клиент-spa)
9. [Безопасность](#9-безопасность)
10. [Развёртывание](#10-развёртывание)
11. [Тестирование](#11-тестирование)
12. [Руководство по дальнейшему развитию](#12-руководство-по-дальнейшему-развитию)
13. [Часто задаваемые вопросы](#13-часто-задаваемые-вопросы)

---

## 1. Обзор проекта

### 1.1 Назначение

HotelMS — клиент-серверная информационная система для управления гостиницей. Система позволяет гостям бронировать номера, менеджерам — управлять бронированиями и заселением, администраторам — контролировать всю деятельность гостиницы.

### 1.2 Функциональные возможности

#### Для гостя (роль `guest`)
- Регистрация личного кабинета (имя, фамилия, email, телефон, паспортные данные)
- Вход по email и паролю
- Просмотр и редактирование профиля
- Просмотр каталога номеров с фильтрами (категория, вместимость, этаж, статус)
- Создание бронирования с выбором дат, количества гостей и дополнительных услуг
- Просмотр истории своих бронирований
- Скачивание PDF-бланка заказа
- Отмена бронирования (до заселения)

#### Для менеджера (роль `manager`)
- Все возможности гостя
- Просмотр всех бронирований гостиницы
- Подтверждение бронирований (pending → confirmed)
- Регистрация заезда (confirmed → checked_in)
- Регистрация выезда (checked_in → checked_out)
- Отмена бронирований
- Просмотр отчётов по доходам и загруженности

#### Для администратора (роль `admin`)
- Все возможности менеджера
- Управление пользователями (просмотр, смена ролей, блокировка/разблокировка)
- Просмотр журнала аудита (все операции INSERT/UPDATE/DELETE с данными)
- Полный доступ ко всем данным системы

### 1.3 Клиенты

Система имеет **два клиента**, подключённых к одному серверу:

| Клиент | Технология | Назначение |
|--------|------------|------------|
| Десктоп | Python + Flet | Нативное приложение для Windows/macOS/Linux |
| Веб | HTML + CSS + JavaScript | Работа через браузер без установки |

Оба клиента обращаются к одному и тому же REST API.

---

## 2. Архитектура системы

### 2.1 Общая схема

```
┌────────────────────────────────┐    ┌────────────────────────────────┐
│   Десктоп-клиент (Flet)        │    │   Веб-клиент (HTML/CSS/JS)     │
│   - Python 3.13                │    │   - Vanilla JavaScript SPA     │
│   - Кроссплатформенный         │    │   - Адаптивный дизайн          │
│   - httpx (async HTTP)         │    │   - fetch API                  │
└──────────────┬─────────────────┘    └──────────────┬─────────────────┘
               │                                      │
               │  HTTP/JSON (REST API)                 │
               └──────────────┬────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI (Python 3.13)                          │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Маршрутизаторы (Routers)                  │   │
│  │   auth.py │ users.py │ rooms.py │ bookings.py │ reports.py  │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│  ┌──────────────────────────┴───────────────────────────────────┐   │
│  │                    Ядро (Core)                                │   │
│  │   config.py │ security.py │ database.py │ exceptions.py      │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│  ┌──────────────────────────┴───────────────────────────────────┐   │
│  │                    Pydantic-схемы (Schemas)                   │   │
│  │   auth │ users │ rooms │ bookings │ services │ reports       │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Сервисы (Services)                         │   │
│  │   pdf_generator.py — генерация PDF-бланков заказов            │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ asyncpg (пул подключений)
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        PostgreSQL 16                                │
│                                                                     │
│  11 таблиц │ 3 домена │ 3 ENUM │ 18 индексов │ 4 представления     │
│  3 функции │ 5 процедур │ 4 триггера │ 4 RLS-политики              │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Потоки данных

```
Пользователь → [Клиент] → HTTP-запрос с JWT → [FastAPI] → SQL-запрос → [PostgreSQL]
                                                              │
Пользователь ← [Клиент] ← HTTP-ответ JSON  ← [FastAPI] ← Результат ←─┘
```

**Авторизация**: клиент отправляет email/пароль → сервер проверяет bcrypt-хэш → возвращает JWT-токен → клиент сохраняет токен и отправляет его в заголовке `Authorization: Bearer <token>` при каждом запросе.

### 2.3 Модель данных (ER)

```
users ─────────── guest_profiles
  │
  │ (guest_id)
  ▼
bookings ──────── booking_services ──── services
  │
  │ (room_id)
  ▼
rooms ─────────── room_amenities ────── amenities
  │
  │ (category_id)
  ▼
room_categories

payments ──────── bookings (через booking_id)

audit_log ─────── (автоматически через триггеры)
```

---

## 3. Стек технологий

### 3.1 Подробная таблица

| Компонент | Технология | Версия | Назначение |
|-----------|------------|--------|------------|
| СУБД | PostgreSQL | 16 | Хранение данных, бизнес-логика на уровне БД |
| Backend | Python | 3.13+ | Язык серверной части |
| Framework | FastAPI | 0.115+ | REST API, Swagger-документация |
| ORM/Driver | asyncpg | 0.30+ | Асинхронный PostgreSQL-драйвер |
| Валидация | Pydantic | 2.x | Валидация входных/выходных данных |
| Аутентификация | PyJWT | 2.x | JSON Web Tokens (HS256) |
| Хэширование | bcrypt (passlib) | — | Хэширование паролей (cost factor 12) |
| PDF | ReportLab | 4.x | Генерация PDF-бланков заказов |
| Десктоп-клиент | Flet | 0.27+ | Кроссплатформенный GUI (Flutter) |
| HTTP-клиент | httpx | 0.28+ | Асинхронные HTTP-запросы из десктопа |
| Веб-клиент | Vanilla JS | ES2020 | SPA без фреймворков |
| Шрифты | Google Fonts (Inter) | — | Современная типографика |
| Иконки | Font Awesome | 6.5 | Векторные иконки |
| Тесты | pytest + httpx | — | Юнит- и интеграционные тесты |
| Деплой | systemd + uvicorn | — | Автоматический перезапуск |

### 3.2 Почему выбраны эти технологии

- **PostgreSQL 16** — самая важная часть проекта. Используются все возможности: домены, ENUM, представления, функции, процедуры, триггеры, RLS, индексы.
- **FastAPI** — автоматическая генерация Swagger-документации, нативная поддержка async/await, валидация через Pydantic.
- **asyncpg** — в 3-5 раз быстрее psycopg2 на async-нагрузке, нативный PostgreSQL-протокол.
- **Flet** — единый Python-код для Windows/macOS/Linux/Web/Mobile.
- **Vanilla JS** — демонстрирует понимание основ фронтенда без абстракций фреймворков.

---

## 4. Структура репозитория

```
hotel-management-system/
│
├── pg_scripts/                     SQL-скрипты базы данных
│   ├── 01_domains_types.sql        Пользовательские домены и ENUM-типы
│   ├── 02_tables.sql               DDL всех таблиц с ограничениями
│   ├── 03_indexes.sql              18 индексов (B-tree, GiST)
│   ├── 04_views.sql                4 представления для отчётов
│   ├── 05_functions.sql            3 функции (проверка свободности, расчёт суммы, загруженность)
│   ├── 06_procedures.sql           5 хранимых процедур (CRUD + выборка)
│   ├── 07_triggers.sql             4 триггера (пересечение дат, аудит, статус номера, обновление суммы)
│   ├── 08_seed_data.sql            Тестовые данные (категории, номера, услуги, пользователи)
│   ├── 09_queries_pool.sql         12 типов SQL-запросов из требований курсовой
│   ├── 10_security.sql             Роли БД, GRANT/REVOKE, RLS-политики
│   └── reset.sh                    Скрипт полной пересборки БД
│
├── server/                          Серверная часть (FastAPI)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  Точка входа, middleware, lifespan
│   │   ├── core/
│   │   │   ├── config.py            Настройки из ENV
│   │   │   ├── database.py          Пул asyncpg
│   │   │   ├── security.py          JWT + bcrypt + RBAC
│   │   │   └── exceptions.py        Глобальные обработчики ошибок
│   │   ├── routers/
│   │   │   ├── auth.py              Регистрация и авторизация
│   │   │   ├── users.py             Пользователи и профили
│   │   │   ├── rooms.py             Каталог номеров
│   │   │   ├── bookings.py          Бронирования (CRUD)
│   │   │   ├── services.py          Дополнительные услуги
│   │   │   └── reports.py           Отчёты и аудит
│   │   ├── schemas/                 Pydantic v2 схемы
│   │   └── services/
│   │       └── pdf_generator.py     Генерация PDF ReportLab
│   ├── tests/
│   │   ├── conftest.py              Фикстуры pytest
│   │   └── test_api.py              Тесты API
│   ├── pyproject.toml               Зависимости и метаданные
│   └── README.md
│
├── client/                          Десктоп-клиент (Flet)
│   ├── hotel_client/
│   │   ├── main.py                  Точка входа, навигация
│   │   ├── api_client.py            HTTP-клиент httpx
│   │   ├── theme.py                 Цвета и стили
│   │   ├── views/                   7 экранов
│   │   │   ├── login_view.py
│   │   │   ├── register_view.py
│   │   │   ├── rooms_view.py
│   │   │   ├── booking_view.py
│   │   │   ├── profile_view.py
│   │   │   ├── my_bookings_view.py
│   │   │   └── admin_view.py
│   │   └── components/
│   ├── pyproject.toml
│   └── README.md
│
├── web/                             Веб-клиент (SPA)
│   ├── index.html                   Главная страница
│   ├── css/style.css                Стили (600+ строк, CSS-переменные, адаптив)
│   ├── js/api.js                    HTTP-клиент HotelAPI (класс, 20+ методов)
│   ├── js/app.js                    Логика SPA (840 строк, навигация, формы)
│   └── README.md
│
├── docs/                            Документация курсового проекта
│   ├── 01_problem_statement.md      Постановка задачи
│   ├── 02_database_design.md        Проектирование БД
│   ├── 03_db_objects.md             Объекты БД (подробно)
│   ├── 04_application_design.md     Проектирование приложения
│   ├── 05_security.md               Методы защиты данных
│   ├── 06_user_guide.md             Руководство пользователя
│   ├── 07_admin_guide.md            Руководство администратора
│   ├── 08_test_cases.md             Тест-кейсы
│   ├── api_reference.md             Справочник API
│   └── PROJECT_GUIDE.md             Данное руководство
│
└── README.md                        Главный README проекта
```

---

## 5. База данных PostgreSQL

### 5.1 Домены

Домены — пользовательские типы данных с ограничениями. Файл: `pg_scripts/01_domains_types.sql`

```sql
-- Валидация email через регулярное выражение
CREATE DOMAIN email_domain AS VARCHAR(255)
    CHECK (VALUE ~ '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$');

-- Валидация телефона (формат +7XXXXXXXXXX)
CREATE DOMAIN phone_domain AS VARCHAR(20)
    CHECK (VALUE ~ '^\+?[0-9]{10,15}$');

-- Положительная денежная сумма
CREATE DOMAIN positive_money AS NUMERIC(12,2)
    CHECK (VALUE >= 0);
```

**Применение в приложении**: при INSERT/UPDATE PostgreSQL автоматически проверяет формат email, телефона и денежных сумм — даже если клиент отправит невалидные данные, БД их отклонит.

### 5.2 ENUM-типы

```sql
CREATE TYPE user_role AS ENUM ('guest', 'manager', 'admin');
CREATE TYPE room_status AS ENUM ('available', 'occupied', 'maintenance', 'cleaning');
CREATE TYPE booking_status AS ENUM ('pending', 'confirmed', 'checked_in', 'checked_out', 'cancelled');
```

**Зачем ENUM вместо VARCHAR**: экономия места (1-2 байта vs строка), защита от опечаток, автодокументирование допустимых значений.

### 5.3 Таблицы (11 штук)

| Таблица | Назначение | Ключевые поля |
|---------|------------|---------------|
| `users` | Учётные записи | email (email_domain), password_hash, role (user_role) |
| `guest_profiles` | Профили гостей | first_name, last_name, phone (phone_domain), passport |
| `room_categories` | Категории номеров | name, base_price (positive_money), capacity |
| `rooms` | Номера гостиницы | room_number, floor, status (room_status), category_id |
| `amenities` | Удобства | name, icon |
| `room_amenities` | Связь номер↔удобство | room_id, amenity_id (M:N) |
| `services` | Дополнительные услуги | name, price (positive_money), description |
| `bookings` | Бронирования | guest_id, room_id, check_in/out_date, status (booking_status) |
| `booking_services` | Услуги в бронировании | booking_id, service_id, quantity, price_at_booking |
| `payments` | Платежи | booking_id, amount, payment_method, paid_at |
| `audit_log` | Журнал аудита | table_name, record_id, action, old_data (JSONB), new_data (JSONB) |

### 5.4 Индексы (18 штук)

Файл: `pg_scripts/03_indexes.sql`

```sql
-- B-tree индексы на FK и часто используемые поля
CREATE INDEX idx_rooms_category ON rooms(category_id);
CREATE INDEX idx_rooms_status ON rooms(status);
CREATE INDEX idx_rooms_floor ON rooms(floor);
CREATE INDEX idx_bookings_guest ON bookings(guest_id);
CREATE INDEX idx_bookings_room ON bookings(room_id);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_bookings_dates ON bookings(check_in_date, check_out_date);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- GiST индекс для проверки пересечения диапазонов дат
CREATE INDEX idx_bookings_daterange ON bookings
    USING gist (daterange(check_in_date, check_out_date, '[]'));

-- и другие...
```

**Почему GiST**: оператор `&&` (пересечение диапазонов) не может использовать B-tree, поэтому для триггера проверки пересечения дат необходим GiST-индекс.

### 5.5 Представления (4 штуки)

Файл: `pg_scripts/04_views.sql`

| Представление | Назначение | Используется в |
|---------------|------------|----------------|
| `v_room_availability` | Номера с информацией о категории, удобствах и текущем статусе | GET /rooms |
| `v_guest_bookings` | Бронирования с именем гостя, номером комнаты и категорией | GET /bookings, Админ-панель |
| `v_revenue_by_category` | Доход по категориям номеров (агрегация) | GET /reports/revenue |
| `v_active_bookings` | Только активные бронирования (не отменённые) | Дашборд менеджера |

### 5.6 Функции (3 штуки)

Файл: `pg_scripts/05_functions.sql`

```sql
-- Проверяет, свободен ли номер на указанные даты
fn_room_is_free(p_room_id INT, p_check_in DATE, p_check_out DATE, p_exclude_booking INT DEFAULT NULL)
    RETURNS BOOLEAN

-- Рассчитывает итоговую сумму бронирования (ночи * цена + услуги)
fn_calculate_booking_total(p_booking_id INT)
    RETURNS NUMERIC(12,2)

-- Возвращает процент загруженности номерного фонда
fn_occupancy_rate(p_start DATE, p_end DATE)
    RETURNS NUMERIC(5,2)
```

### 5.7 Процедуры (5 штук)

Файл: `pg_scripts/06_procedures.sql`

```sql
-- Создаёт бронирование с проверкой свободности номера
sp_create_booking(p_guest_id, p_room_id, p_check_in, p_check_out, p_guests_count, p_notes)

-- Обновляет статус бронирования с валидацией переходов
sp_update_booking_status(p_booking_id, p_new_status)

-- Отменяет бронирование (только pending/confirmed)
sp_cancel_booking(p_booking_id)

-- Регистрирует нового пользователя (хэш пароля + профиль)
sp_register_user(p_email, p_password_hash, p_first_name, p_last_name, p_phone)

-- Получает бронирования конкретного гостя
sp_get_user_bookings(p_user_id)
```

### 5.8 Триггеры (4 штуки)

Файл: `pg_scripts/07_triggers.sql`

| Триггер | Таблица | Событие | Назначение |
|---------|---------|---------|------------|
| `trg_no_overlap_booking` | bookings | BEFORE INSERT/UPDATE | Запрещает пересечение дат бронирований для одного номера |
| `trg_audit_bookings` | bookings | AFTER INSERT/UPDATE/DELETE | Записывает все изменения в audit_log (JSONB) |
| `trg_update_room_status` | bookings | AFTER UPDATE | При заселении ставит номер в occupied, при выезде — в cleaning |
| `trg_recalc_total` | booking_services | AFTER INSERT/UPDATE/DELETE | Пересчитывает total_amount при изменении услуг |

### 5.9 RLS-политики

Файл: `pg_scripts/10_security.sql`

```sql
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;

-- Гость видит только свои бронирования
CREATE POLICY bookings_guest_policy ON bookings
    FOR SELECT USING (guest_id = current_setting('app.current_user_id')::INT);

-- Менеджер и администратор видят все бронирования
CREATE POLICY bookings_staff_policy ON bookings
    FOR ALL USING (current_setting('app.current_role') IN ('manager', 'admin'));
```

### 5.10 Пул SQL-запросов (12 типов)

Файл: `pg_scripts/09_queries_pool.sql` — содержит примеры всех 12 типов запросов из задания:

1. Простые запросы с условием (WHERE, LIKE, BETWEEN, IN)
2. Скалярные подзапросы (после WHERE, SELECT, HAVING)
3. Табличные подзапросы (после FROM, WHERE)
4. Подзапросы с кванторами (EXISTS, ALL)
5. Множественные операции (UNION, INTERSECT, EXCEPT)
6. Вынесенные подзапросы (WITH / CTE)
7. Агрегатные функции с GROUP BY и HAVING
8. Многотабличные запросы (JOIN)
9. Функции для строк, дат, преобразований
10. Рекурсивные подзапросы (WITH RECURSIVE)
11. Сводные таблицы (CROSSTAB через tablefunc)
12. Оконные функции (ROW_NUMBER, RANK, SUM OVER)

---

## 6. Серверная часть (FastAPI)

### 6.1 Конфигурация

Файл: `server/app/core/config.py`

Настройки загружаются из переменных окружения:

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `DATABASE_URL` | — | Строка подключения PostgreSQL |
| `JWT_SECRET` | — | Секретный ключ для подписи JWT |
| `JWT_ALGORITHM` | HS256 | Алгоритм подписи |
| `JWT_EXPIRE_MINUTES` | 480 | Время жизни токена (8 часов) |
| `CORS_ORIGINS` | * | Разрешённые источники CORS |
| `APP_TITLE` | HotelMS API | Название в Swagger |
| `APP_VERSION` | 1.0.0 | Версия API |
| `WEB_DIR` | ../web | Путь к каталогу веб-клиента |

### 6.2 Аутентификация

Файл: `server/app/core/security.py`

```
1. Клиент отправляет POST /api/auth/login { email, password }
2. Сервер ищет пользователя по email
3. Проверяет bcrypt-хэш пароля (passlib CryptContext, cost factor 12)
4. Если совпал — генерирует JWT:
   {
     "sub": user_id,
     "email": email,
     "role": "admin|manager|guest",
     "exp": timestamp + 8h
   }
5. Клиент сохраняет токен (localStorage / переменная)
6. Все последующие запросы содержат заголовок:
   Authorization: Bearer <token>
7. FastAPI-зависимость get_current_user() декодирует токен
8. require_role("admin") проверяет роль и блокирует если нет доступа
```

### 6.3 API-эндпоинты (полный список)

| Метод | Путь | Минимальная роль | Описание |
|-------|------|-----------------|----------|
| POST | /api/auth/register | — | Регистрация нового пользователя |
| POST | /api/auth/login | — | Вход, получение JWT |
| GET | /api/users/me | any | Текущий профиль |
| PUT | /api/users/me | any | Обновление профиля |
| PUT | /api/users/me/password | any | Смена пароля |
| GET | /api/users | admin | Список всех пользователей |
| PUT | /api/users/{id}/role | admin | Смена роли пользователя |
| PUT | /api/users/{id}/block | admin | Блокировка/разблокировка |
| GET | /api/rooms | any | Каталог номеров (с фильтрами) |
| GET | /api/rooms/{id} | any | Детали номера |
| GET | /api/rooms/categories | any | Список категорий |
| GET | /api/rooms/{id}/amenities | any | Удобства номера |
| POST | /api/bookings | guest+ | Создание бронирования |
| GET | /api/bookings | guest+ | Мои бронирования |
| GET | /api/bookings/all | manager+ | Все бронирования |
| GET | /api/bookings/{id} | guest+ | Детали бронирования |
| PUT | /api/bookings/{id}/status | manager+ | Смена статуса |
| PUT | /api/bookings/{id}/cancel | guest+ | Отмена бронирования |
| POST | /api/bookings/{id}/services | guest+ | Добавление услуги |
| GET | /api/bookings/{id}/pdf | guest+ | Скачать PDF-бланк |
| GET | /api/services | any | Список услуг |
| GET | /api/services/all | admin | Полный список услуг |
| GET | /api/reports/revenue | manager+ | Отчёт по доходам |
| GET | /api/reports/occupancy | manager+ | Загруженность |
| GET | /api/reports/audit | admin | Журнал аудита |

### 6.4 Обработка ошибок

Три уровня обработки:

```python
# 1. Бизнес-ошибки
class AppException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
# → { "detail": "Номер занят на указанные даты" }

# 2. Ошибки PostgreSQL
asyncpg.PostgresError
# → { "detail": "Ошибка базы данных: ..." }

# 3. Непредвиденные ошибки
Exception
# → { "detail": "Внутренняя ошибка сервера" }
```

### 6.5 PDF-генерация

Файл: `server/app/services/pdf_generator.py`

PDF-бланк содержит:
- Логотип и название «Гранд Отель»
- Данные гостя (ФИО, email, телефон)
- Информация о номере (номер, категория, этаж)
- Даты проживания и количество ночей
- Список дополнительных услуг с ценами
- Итоговая сумма
- Дата формирования документа

---

## 7. Десктоп-клиент (Flet)

### 7.1 Запуск

```bash
cd client
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
HOTEL_API_URL=http://77.221.151.85:8000 python -m hotel_client.main
```

### 7.2 Экраны

| Экран | Файл | Описание |
|-------|------|----------|
| Вход | login_view.py | Поля email + пароль, ссылка на регистрацию |
| Регистрация | register_view.py | Полная форма с валидацией |
| Каталог | rooms_view.py | Карточки номеров с фильтрами |
| Бронирование | booking_view.py | Выбор дат, гостей, услуг |
| Профиль | profile_view.py | Редактирование данных |
| Мои бронирования | my_bookings_view.py | История с PDF |
| Админ-панель | admin_view.py | 4 вкладки |

### 7.3 Навигация

- `NavigationRail` в левой части экрана
- Пункты меню зависят от роли пользователя
- При выходе из системы все данные очищаются

---

## 8. Веб-клиент (SPA)

### 8.1 Архитектура SPA

Весь интерфейс — одна HTML-страница. Навигация реализована через JavaScript-функцию `navigate()`, которая заменяет содержимое контейнера `<main id="app">`:

```javascript
function navigate(page) {
    switch(page) {
        case 'login':    renderLogin(); break;
        case 'register': renderRegister(); break;
        case 'rooms':    renderRooms(); break;
        case 'bookings': renderMyBookings(); break;
        case 'profile':  renderProfile(); break;
        case 'admin':    renderAdmin(); break;
    }
    renderNav();
}
```

### 8.2 API-клиент (api.js)

Класс `HotelAPI`:
- Хранит JWT-токен и данные пользователя в `localStorage`
- Все методы возвращают `Promise`
- При ответе 401 автоматически выполняет `logout()`
- `API_BASE` определяется как `window.location.origin + '/api'`

### 8.3 Стили (style.css)

- **CSS-переменные** для централизованного управления цветами
- **Адаптивная вёрстка** — breakpoint 768px для мобильных
- **Компоненты**: navbar, карточки, таблицы, формы, модальные окна, тосты, бейджи

### 8.4 Дизайн

| Параметр | Значение |
|----------|----------|
| Основной цвет | #1565C0 (синий) |
| Акцентный цвет | #FF8F00 (янтарный) |
| Фон | #F5F5F5 |
| Шрифт | Inter (Google Fonts) |
| Иконки | Font Awesome 6.5 (CDN) |
| Радиус скругления | 12px |
| Анимации | CSS transitions 0.2s ease |

---

## 9. Безопасность

### 9.1 Три уровня защиты

```
Уровень 1: Приложение (FastAPI)
├── JWT-токен в заголовке Authorization
├── Зависимость require_role() проверяет роль
├── Bcrypt-хэширование паролей (cost factor 12)
└── CORS-политика ограничивает источники

Уровень 2: База данных (PostgreSQL — GRANT/REVOKE)
├── Роль hotel_guest — SELECT на rooms, свои bookings
├── Роль hotel_manager — + UPDATE bookings, INSERT payments
├── Роль hotel_admin — ALL PRIVILEGES
└── Приложение подключается под hotel_app

Уровень 3: Строки (Row Level Security)
├── bookings_guest_policy — гость видит только свои
├── bookings_staff_policy — менеджер/админ видят все
└── Реализовано через current_setting('app.current_user_id')
```

### 9.2 Защита от атак

| Атака | Защита |
|-------|--------|
| SQL Injection | Параметризованные запросы asyncpg ($1, $2) |
| XSS | Данные экранируются при вставке в DOM |
| CSRF | JWT в заголовке (не cookie) |
| Brute Force | Можно добавить rate limiting (см. раздел улучшений) |
| Data Leak | Пароли хранятся как bcrypt-хэши, секреты в ENV |

---

## 10. Развёртывание

### 10.1 Текущий деплой

Сервер развёрнут на **77.221.151.85** (Debian 12):

```
http://77.221.151.85:8000        ← Веб-приложение (браузер)
http://77.221.151.85:8000/api    ← REST API
http://77.221.151.85:8000/docs   ← Swagger-документация
http://77.221.151.85:8000/health ← Проверка здоровья
```

### 10.2 Как развернуть на новом сервере

#### Шаг 1: Установить PostgreSQL 16

```bash
sudo apt update && sudo apt install -y postgresql-16 postgresql-16-contrib
sudo systemctl enable --now postgresql
```

#### Шаг 2: Создать БД и пользователя

```bash
sudo -u postgres psql -c "CREATE USER hotel_app WITH PASSWORD 'ваш_пароль';"
sudo -u postgres psql -c "CREATE DATABASE hotel_db OWNER hotel_app;"
```

#### Шаг 3: Выполнить SQL-скрипты

```bash
cd pg_scripts
chmod +x reset.sh
PGPASSWORD=ваш_пароль ./reset.sh hotel_db hotel_app
```

#### Шаг 4: Установить Python и зависимости

```bash
sudo apt install -y python3 python3-venv python3-pip
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

#### Шаг 5: Настроить переменные окружения

```bash
export DATABASE_URL="postgresql://hotel_app:ваш_пароль@localhost:5432/hotel_db"
export JWT_SECRET="ваш-секретный-ключ-для-jwt"
export CORS_ORIGINS="*"
export WEB_DIR="/путь/к/web"
```

#### Шаг 6: Запустить сервер

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Шаг 7: Настроить systemd (для автозапуска)

```ini
# /etc/systemd/system/hotelms.service
[Unit]
Description=HotelMS API
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/путь/к/server
Environment=DATABASE_URL=postgresql://hotel_app:пароль@localhost:5432/hotel_db
Environment=JWT_SECRET=ваш-секрет
Environment=WEB_DIR=/путь/к/web
ExecStart=/путь/к/server/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hotelms
```

#### Шаг 8: Настроить nginx (опционально, для HTTPS)

```nginx
server {
    listen 80;
    server_name ваш-домен.ru;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 11. Тестирование

### 11.1 Запуск тестов

```bash
cd server
source .venv/bin/activate
pytest tests/ -v
```

### 11.2 Тестовые аккаунты

| Email | Пароль | Роль |
|-------|--------|------|
| admin@hotel.local | Admin123! | Администратор |
| manager@hotel.local | Manager123! | Менеджер |
| ivanov@example.com | Guest123! | Гость |
| petrova@example.com | Guest123! | Гость |
| sidorov@example.com | Guest123! | Гость |

### 11.3 Ручное тестирование через curl

```bash
# Авторизация
TOKEN=$(curl -s http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@hotel.local","password":"Admin123!"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# Получить список номеров
curl -s http://localhost:8000/api/rooms -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Создать бронирование
curl -s -X POST http://localhost:8000/api/bookings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"room_id":1,"check_in_date":"2026-06-01","check_out_date":"2026-06-05","guests_count":2}' \
  | python3 -m json.tool

# Скачать PDF
curl -s http://localhost:8000/api/bookings/1/pdf \
  -H "Authorization: Bearer $TOKEN" -o booking.pdf
```

---

## 12. Руководство по дальнейшему развитию

### 12.1 Приоритетные улучшения

#### 1. Добавить Refresh-токены

Сейчас JWT истекает через 8 часов, и пользователю нужно заново вводить логин/пароль.

**Что сделать**:
```python
# В security.py добавить:
def create_refresh_token(user_id: int) -> str:
    payload = {"sub": user_id, "type": "refresh", "exp": datetime.utcnow() + timedelta(days=30)}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

# Новый эндпоинт:
@router.post("/auth/refresh")
async def refresh_token(refresh: str):
    # Проверить refresh-токен → выдать новый access-токен
```

**Файлы для изменения**: `server/app/core/security.py`, `server/app/routers/auth.py`, `web/js/api.js`

#### 2. Добавить Rate Limiting

Защита от brute force атак на эндпоинт авторизации.

**Что сделать**:
```bash
pip install slowapi
```
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    ...
```

**Файлы для изменения**: `server/app/main.py`, `server/app/routers/auth.py`

#### 3. Добавить загрузку фотографий номеров

Сейчас карточки номеров используют иконку вместо фото.

**Что сделать**:
1. Создать эндпоинт `POST /api/rooms/{id}/photo` (multipart/form-data)
2. Сохранять файлы в `server/uploads/rooms/`
3. Отдавать через `GET /api/rooms/{id}/photo`
4. В веб-клиенте заменить иконку на `<img>`

**Файлы для изменения**: `server/app/routers/rooms.py`, `web/js/app.js`, `web/css/style.css`

#### 4. Добавить уведомления по email

Отправка email при создании/подтверждении/отмене бронирования.

**Что сделать**:
```bash
pip install aiosmtplib email-validator
```
```python
# server/app/services/email_service.py
async def send_booking_confirmation(email: str, booking: dict):
    msg = MIMEText(f"Ваше бронирование #{booking['id']} подтверждено!")
    msg['Subject'] = 'Подтверждение бронирования — Гранд Отель'
    ...
```

**Файлы**: новый `server/app/services/email_service.py`, изменить `server/app/routers/bookings.py`

#### 5. Пагинация на фронтенде

При большом количестве номеров/бронирований/записей аудита нужна постраничная навигация.

**Что сделать**:
1. На бэкенде: добавить параметры `?page=1&per_page=20` и возвращать `{"items": [...], "total": 100, "pages": 5}`
2. На фронтенде: добавить кнопки «Назад / Вперёд» под таблицами

**Файлы**: `server/app/routers/*.py`, `web/js/app.js`

#### 6. Поиск номеров по датам

Фильтрация номеров по свободным датам (используя функцию `fn_room_is_free`).

**Что сделать**:
1. Добавить параметры `?check_in=2026-06-01&check_out=2026-06-05` к `GET /api/rooms`
2. Фильтровать через `WHERE fn_room_is_free(r.id, $check_in, $check_out)`
3. Добавить поля дат в фильтры на фронтенде

**Файлы**: `server/app/routers/rooms.py`, `web/js/app.js`

### 12.2 Средний приоритет

#### 7. Дашборд менеджера/администратора

Добавить на главную страницу админ-панели виджеты:
- Сегодня заезды / выезды
- Загруженность номерного фонда (%)
- Доход за текущий месяц
- Последние бронирования

#### 8. Добавить оплату

Интеграция с платёжной системой (YooKassa/Stripe):
- Эндпоинт `POST /api/payments/{booking_id}`
- Webhook для подтверждения оплаты
- Статус бронирования: pending → paid → confirmed

#### 9. Мультиязычность (i18n)

Поддержка русского и английского языков:
- JSON-файлы с переводами
- Переключатель языка в навигации

#### 10. Тёмная тема

CSS-переменные уже позволяют легко добавить тёмную тему:
```css
[data-theme="dark"] {
    --bg: #121212;
    --surface: #1E1E1E;
    --text: #E0E0E0;
    --border: #333333;
}
```

### 12.3 Долгосрочные улучшения

#### 11. Docker-контейнеризация

```dockerfile
# Dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY server/ .
RUN pip install -e .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: hotel_db
      POSTGRES_USER: hotel_app
      POSTGRES_PASSWORD: secret
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./pg_scripts:/docker-entrypoint-initdb.d
  api:
    build: ./server
    depends_on: [db]
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql://hotel_app:secret@db:5432/hotel_db
volumes:
  pgdata:
```

#### 12. CI/CD (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.13' }
      - run: pip install -e server/
      - run: pytest server/tests/ -v
```

#### 13. Миграции БД (Alembic)

Вместо ручных SQL-скриптов использовать автоматические миграции:
```bash
pip install alembic
alembic init migrations
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

#### 14. WebSocket-уведомления

Реальтайм-уведомления при изменении статуса бронирования:
```python
from fastapi import WebSocket

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message: {data}")
```

#### 15. Мобильное приложение

Flet поддерживает компиляцию в нативные iOS/Android приложения:
```bash
flet build apk   # Android APK
flet build ipa   # iOS
```

---

## 13. Часто задаваемые вопросы

### Как сбросить БД к начальному состоянию?

```bash
cd pg_scripts
PGPASSWORD=пароль ./reset.sh hotel_db hotel_app
```

### Как добавить нового администратора?

```sql
-- Через SQL:
UPDATE users SET role = 'admin' WHERE email = 'new_admin@example.com';

-- Или через API (от имени существующего админа):
curl -X PUT http://localhost:8000/api/users/6/role \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

### Как добавить новую категорию номеров?

```sql
INSERT INTO room_categories (name, description, base_price, capacity)
VALUES ('Апартаменты', 'Просторные апартаменты с кухней', 15000.00, 4);
```

### Как добавить новый номер?

```sql
INSERT INTO rooms (room_number, floor, category_id, status, description)
VALUES ('501', 5, (SELECT id FROM room_categories WHERE name = 'Апартаменты'), 'available', 'Апартаменты с видом на город');
```

### Как добавить новую услугу?

```sql
INSERT INTO services (name, description, price)
VALUES ('Массаж', 'Расслабляющий массаж 60 минут', 5000.00);
```

### Как посмотреть логи сервера?

```bash
# Если запущен через systemd:
journalctl -u hotelms -f

# Если запущен вручную:
tail -f /root/server.log
```

### Как обновить код на сервере?

```bash
cd /путь/к/проекту
git pull origin main
cd server && pip install -e .
sudo systemctl restart hotelms
```

### Как посмотреть Swagger-документацию?

Откройте в браузере: http://77.221.151.85:8000/docs

Там можно тестировать все API-эндпоинты: нажмите «Authorize», введите JWT-токен (полученный через /api/auth/login) и выполняйте запросы.

### Как изменить порт сервера?

```bash
uvicorn app.main:app --host 0.0.0.0 --port 3000
```

### Как подключиться к БД напрямую?

```bash
psql -h localhost -U hotel_app -d hotel_db
# Пароль: hotel_secure_pwd_2025
```

---

*Документ создан: май 2026*
*Версия проекта: 1.0.0*
*Автор: imooporos*
