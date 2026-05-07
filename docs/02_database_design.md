# 2. Проектирование базы данных

## 2.1 Концептуальная модель данных

### Сущности предметной области

| Сущность | Описание |
|----------|----------|
| **Пользователь** (users) | Учётная запись с ролью (guest / manager / admin) |
| **Профиль гостя** (guest_profiles) | Расширенные данные: паспорт, дата рождения |
| **Категория номера** (room_categories) | Тип номера: стандарт, комфорт, люкс, президентский |
| **Номер** (rooms) | Физический номер в гостинице |
| **Удобства** (amenities) | Список удобств: Wi-Fi, мини-бар, кондиционер и т.д. |
| **Бронирование** (bookings) | Заявка на проживание с датами |
| **Услуга** (services) | Дополнительная услуга: трансфер, завтрак и т.д. |
| **Оплата** (payments) | Фиксация факта оплаты |
| **Аудит-лог** (audit_log) | Журнал изменений в системе |

### Связи между сущностями

```
users 1──1 guest_profiles        (у каждого гостя один профиль)
users 1──* bookings              (гость создаёт бронирования)
rooms *──1 room_categories       (номер принадлежит категории)
rooms *──* amenities             (через room_amenities)
bookings *──1 rooms              (бронирование на конкретный номер)
bookings *──* services           (через booking_services)
bookings 1──* payments           (к бронированию привязаны платежи)
```

## 2.2 Реляционная модель

### Таблица `users`

| Столбец | Тип | Ограничения |
|---------|-----|-------------|
| id | SERIAL | PRIMARY KEY |
| email | email_domain | UNIQUE, NOT NULL |
| password_hash | VARCHAR(255) | NOT NULL |
| first_name | VARCHAR(100) | NOT NULL |
| last_name | VARCHAR(100) | NOT NULL |
| patronymic | VARCHAR(100) | |
| phone | phone_domain | |
| role | user_role | DEFAULT 'guest' |
| is_active | BOOLEAN | DEFAULT TRUE |
| created_at | TIMESTAMPTZ | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() |

### Таблица `guest_profiles`

| Столбец | Тип | Ограничения |
|---------|-----|-------------|
| id | SERIAL | PRIMARY KEY |
| user_id | INTEGER | FK → users(id), UNIQUE |
| passport_series | VARCHAR(10) | |
| passport_number | VARCHAR(20) | |
| birth_date | DATE | |
| notes | TEXT | |

### Таблица `room_categories`

| Столбец | Тип | Ограничения |
|---------|-----|-------------|
| id | SERIAL | PRIMARY KEY |
| name | VARCHAR(100) | UNIQUE, NOT NULL |
| description | TEXT | |
| base_price | price_domain | NOT NULL |

### Таблица `rooms`

| Столбец | Тип | Ограничения |
|---------|-----|-------------|
| id | SERIAL | PRIMARY KEY |
| room_number | VARCHAR(10) | UNIQUE, NOT NULL |
| category_id | INTEGER | FK → room_categories(id) |
| floor | SMALLINT | NOT NULL |
| capacity | SMALLINT | NOT NULL, DEFAULT 2 |
| status | room_status | DEFAULT 'available' |
| description | TEXT | |

### Таблица `amenities`

| Столбец | Тип | Ограничения |
|---------|-----|-------------|
| id | SERIAL | PRIMARY KEY |
| name | VARCHAR(100) | UNIQUE, NOT NULL |
| description | TEXT | |

### Таблица `room_amenities`

| Столбец | Тип | Ограничения |
|---------|-----|-------------|
| room_id | INTEGER | FK → rooms(id), PK |
| amenity_id | INTEGER | FK → amenities(id), PK |

### Таблица `bookings`

| Столбец | Тип | Ограничения |
|---------|-----|-------------|
| id | SERIAL | PRIMARY KEY |
| user_id | INTEGER | FK → users(id) |
| room_id | INTEGER | FK → rooms(id) |
| check_in | DATE | NOT NULL |
| check_out | DATE | NOT NULL, CHECK > check_in |
| guests_count | SMALLINT | NOT NULL, DEFAULT 1 |
| status | booking_status | DEFAULT 'pending' |
| total_amount | price_domain | |
| notes | TEXT | |
| created_at | TIMESTAMPTZ | DEFAULT NOW() |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() |

### Таблица `services`

| Столбец | Тип | Ограничения |
|---------|-----|-------------|
| id | SERIAL | PRIMARY KEY |
| name | VARCHAR(200) | UNIQUE, NOT NULL |
| description | TEXT | |
| price | price_domain | NOT NULL |
| is_active | BOOLEAN | DEFAULT TRUE |

### Таблица `booking_services`

| Столбец | Тип | Ограничения |
|---------|-----|-------------|
| id | SERIAL | PRIMARY KEY |
| booking_id | INTEGER | FK → bookings(id) |
| service_id | INTEGER | FK → services(id) |
| quantity | SMALLINT | DEFAULT 1 |
| price_at_booking | price_domain | NOT NULL |

### Таблица `payments`

| Столбец | Тип | Ограничения |
|---------|-----|-------------|
| id | SERIAL | PRIMARY KEY |
| booking_id | INTEGER | FK → bookings(id) |
| amount | price_domain | NOT NULL |
| payment_method | VARCHAR(50) | NOT NULL |
| paid_at | TIMESTAMPTZ | DEFAULT NOW() |

### Таблица `audit_log`

| Столбец | Тип | Ограничения |
|---------|-----|-------------|
| id | BIGSERIAL | PRIMARY KEY |
| table_name | VARCHAR(100) | NOT NULL |
| record_id | INTEGER | NOT NULL |
| action | VARCHAR(10) | NOT NULL |
| old_data | JSONB | |
| new_data | JSONB | |
| changed_by | TEXT | |
| changed_at | TIMESTAMPTZ | DEFAULT NOW() |

## 2.3 Нормализация

База данных приведена к **третьей нормальной форме (3НФ)**:

1. **1НФ**: Все атрибуты атомарны, нет повторяющихся групп.
2. **2НФ**: Все неключевые атрибуты зависят от полного ключа (устранены частичные зависимости).
3. **3НФ**: Нет транзитивных зависимостей — например, `base_price` вынесена в `room_categories`, а не хранится в `rooms`.

## 2.4 Пользовательские типы и домены

### Домены

```sql
-- Email: строка до 255 символов, проверка формата через регулярное выражение
CREATE DOMAIN email_domain AS VARCHAR(255)
    CHECK (VALUE ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

-- Телефон: формат +7XXXXXXXXXX или пустое значение
CREATE DOMAIN phone_domain AS VARCHAR(20)
    CHECK (VALUE IS NULL OR VALUE ~* '^\+?\d{10,15}$');

-- Цена: числовое значение >= 0
CREATE DOMAIN price_domain AS NUMERIC(12, 2)
    CHECK (VALUE >= 0);
```

### ENUM-типы

```sql
CREATE TYPE user_role AS ENUM ('guest', 'manager', 'admin');
CREATE TYPE room_status AS ENUM ('available', 'occupied', 'maintenance', 'cleaning');
CREATE TYPE booking_status AS ENUM ('pending', 'confirmed', 'checked_in', 'checked_out', 'cancelled');
```

## 2.5 Схема данных

```
┌──────────────┐     ┌───────────────────┐     ┌──────────────────┐
│   users      │     │  guest_profiles   │     │ room_categories  │
│──────────────│     │───────────────────│     │──────────────────│
│ id (PK)      │←─┐  │ id (PK)           │     │ id (PK)          │
│ email        │  │  │ user_id (FK→users)│     │ name             │
│ password_hash│  │  │ passport_series   │     │ description      │
│ first_name   │  │  │ passport_number   │     │ base_price       │
│ last_name    │  │  │ birth_date        │     └────────┬─────────┘
│ role         │  │  └───────────────────┘              │
│ is_active    │  │                                     │
└──────┬───────┘  │  ┌──────────────────┐               │
       │          │  │     rooms        │               │
       │          │  │──────────────────│               │
       │          │  │ id (PK)          │←──────────────┘
       │          │  │ room_number      │
       │          │  │ category_id (FK) │     ┌──────────────────┐
       │          │  │ floor            │     │   amenities      │
       │          │  │ capacity         │     │──────────────────│
       │          │  │ status           │     │ id (PK)          │
       │          │  └────────┬─────────┘     │ name             │
       │          │           │               └────────┬─────────┘
       │          │           │                        │
       │          │  ┌────────┴─────────┐     ┌────────┴─────────┐
       │          │  │    bookings      │     │  room_amenities  │
       │          │  │──────────────────│     │──────────────────│
       │          └─►│ user_id (FK)     │     │ room_id (FK)     │
       │             │ room_id (FK)     │     │ amenity_id (FK)  │
       │             │ check_in         │     └──────────────────┘
       │             │ check_out        │
       │             │ status           │     ┌──────────────────┐
       │             │ total_amount     │     │    services      │
       │             └────────┬─────────┘     │──────────────────│
       │                      │               │ id (PK)          │
       │             ┌────────┴─────────┐     │ name             │
       │             │ booking_services │     │ price            │
       │             │──────────────────│     └────────┬─────────┘
       │             │ booking_id (FK)  │              │
       │             │ service_id (FK)──│──────────────┘
       │             │ quantity         │
       │             │ price_at_booking │
       │             └──────────────────┘
       │
       │             ┌──────────────────┐
       │             │    payments      │
       │             │──────────────────│
       │             │ booking_id (FK)  │
       │             │ amount           │
       │             │ payment_method   │
       │             └──────────────────┘
```
