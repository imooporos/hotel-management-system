# API Reference

Базовый URL: `http://77.221.151.85:8000`

Авторизация: Bearer Token (JWT) в заголовке `Authorization`.

## Аутентификация

### POST /auth/register

Регистрация нового пользователя.

**Тело запроса:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "Иван",
  "last_name": "Иванов",
  "middle_name": "Иванович",
  "phone": "+79001234567"
}
```

**Ответ 201:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user_id": 1,
  "role": "guest"
}
```

**Ошибки:**
- `409 Conflict` — email уже зарегистрирован
- `422 Unprocessable Entity` — невалидные данные

### POST /auth/login

Авторизация пользователя.

**Тело запроса:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Ответ 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user_id": 1,
  "role": "guest"
}
```

**Ошибки:**
- `401 Unauthorized` — неверный email или пароль
- `403 Forbidden` — аккаунт заблокирован

## Пользователи

### GET /users/me

Получить профиль текущего пользователя.

**Заголовки:** `Authorization: Bearer <token>`

**Ответ 200:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "Иван",
  "last_name": "Иванов",
  "middle_name": "Иванович",
  "phone": "+79001234567",
  "role": "guest",
  "is_active": true,
  "created_at": "2025-05-01T12:00:00",
  "passport_series": "1234",
  "passport_number": "567890",
  "birth_date": "1990-01-15"
}
```

### PUT /users/me

Обновить профиль.

**Тело запроса:**
```json
{
  "first_name": "Иван",
  "last_name": "Иванов",
  "phone": "+79001234567",
  "passport_series": "1234",
  "passport_number": "567890",
  "birth_date": "1990-01-15"
}
```

**Ответ 200:** обновлённый профиль пользователя.

### GET /users

Список всех пользователей (только admin).

**Ответ 200:**
```json
[
  {
    "id": 1,
    "email": "admin@hotel.local",
    "first_name": "Администратор",
    "last_name": "Системный",
    "role": "admin",
    "is_active": true,
    "created_at": "2025-01-01T00:00:00"
  }
]
```

### PUT /users/{user_id}/role

Изменить роль пользователя (только admin).

**Тело запроса:**
```json
{
  "role": "manager"
}
```

### PUT /users/{user_id}/block

Заблокировать / разблокировать пользователя (только admin).

## Номера

### GET /rooms

Каталог номеров с фильтрацией.

**Параметры запроса:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| category | string | Фильтр по категории |
| min_capacity | int | Минимальная вместимость |
| status | string | Статус номера |
| min_price | float | Минимальная цена |
| max_price | float | Максимальная цена |

**Ответ 200:**
```json
[
  {
    "id": 1,
    "room_number": "101",
    "category": "Стандарт",
    "base_price": 3500.00,
    "floor": 1,
    "capacity": 2,
    "status": "available",
    "description": "Уютный номер с видом на парк",
    "amenities": "Wi-Fi, Кондиционер, Телевизор"
  }
]
```

### GET /rooms/{room_id}

Детальная информация о номере.

## Бронирования

### POST /bookings

Создать бронирование.

**Тело запроса:**
```json
{
  "room_id": 1,
  "check_in": "2025-06-01",
  "check_out": "2025-06-05",
  "guests_count": 2,
  "notes": "Поздний заезд",
  "service_ids": [1, 3]
}
```

**Ответ 201:**
```json
{
  "id": 1,
  "room_id": 1,
  "user_id": 1,
  "check_in": "2025-06-01",
  "check_out": "2025-06-05",
  "guests_count": 2,
  "status": "pending",
  "total_amount": 15500.00,
  "notes": "Поздний заезд",
  "created_at": "2025-05-01T12:00:00"
}
```

**Ошибки:**
- `400 Bad Request` — номер занят, некорректные даты, превышение вместимости
- `401 Unauthorized` — не авторизован

### GET /bookings

Бронирования текущего пользователя.

### GET /bookings/all

Все бронирования (manager, admin).

### PUT /bookings/{booking_id}/status

Изменить статус бронирования (manager, admin).

**Тело запроса:**
```json
{
  "status": "confirmed"
}
```

### PUT /bookings/{booking_id}/cancel

Отменить бронирование (владелец или manager/admin).

### GET /bookings/{booking_id}/pdf

Скачать PDF-бланк заказа.

**Ответ:** файл `application/pdf`.

## Услуги

### GET /services

Список дополнительных услуг.

**Ответ 200:**
```json
[
  {
    "id": 1,
    "name": "Завтрак",
    "description": "Шведский стол, 7:00-10:00",
    "price": 800.00,
    "is_active": true
  }
]
```

## Отчёты

### GET /reports/revenue

Отчёт по выручке (manager, admin).

**Ответ 200:**
```json
{
  "categories": [
    {
      "category": "Люкс",
      "bookings_count": 15,
      "total_revenue": 450000.00,
      "avg_booking": 30000.00
    }
  ],
  "total_revenue": 1250000.00
}
```

### GET /reports/audit

Аудит-лог (только admin).

**Параметры:** `limit` (int), `offset` (int).

**Ответ 200:**
```json
[
  {
    "id": 1,
    "table_name": "bookings",
    "record_id": 5,
    "action": "UPDATE",
    "old_data": {"status": "pending"},
    "new_data": {"status": "confirmed"},
    "changed_by": "hotel_app",
    "changed_at": "2025-05-01T14:30:00"
  }
]
```

## Системные

### GET /health

Проверка работоспособности сервера.

**Ответ 200:**
```json
{
  "status": "ok",
  "database": "connected"
}
```

## Коды ошибок

| Код | Описание |
|-----|----------|
| 400 | Некорректный запрос (невалидные данные) |
| 401 | Не авторизован (отсутствует или невалидный токен) |
| 403 | Доступ запрещён (недостаточно прав) |
| 404 | Ресурс не найден |
| 409 | Конфликт (дублирование данных) |
| 422 | Ошибка валидации (Pydantic) |
| 500 | Внутренняя ошибка сервера |
