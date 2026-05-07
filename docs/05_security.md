# 5. Методы защиты данных

## 5.1 Обзор уровней защиты

Система реализует защиту данных на **четырёх уровнях**:

```
┌─────────────────────────────────────────┐
│  1. Транспортный уровень (HTTPS/TLS)    │  ← Nginx reverse proxy
├─────────────────────────────────────────┤
│  2. Уровень приложения (JWT + RBAC)     │  ← FastAPI middleware
├─────────────────────────────────────────┤
│  3. Уровень БД (GRANT/REVOKE)           │  ← Роли PostgreSQL
├─────────────────────────────────────────┤
│  4. Уровень строк (RLS)                 │  ← Row Level Security
└─────────────────────────────────────────┘
```

## 5.2 Аутентификация

### Хранение паролей

Пароли хранятся в виде **bcrypt-хэшей** с cost factor 12:

```python
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())
```

Bcrypt обеспечивает:
- Устойчивость к атакам по радужным таблицам (встроенная соль).
- Адаптивную вычислительную сложность (cost factor).
- Фиксированную длину хэша (60 символов).

### JWT-токены

Авторизация реализована через **JSON Web Tokens (JWT)** со схемой HS256:

```python
import jwt
from datetime import datetime, timedelta

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=24)
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
```

Структура payload:
```json
{
  "sub": "42",
  "email": "user@example.com",
  "role": "guest",
  "exp": 1717200000
}
```

Время жизни токена: **24 часа**. После истечения клиент должен повторно авторизоваться.

## 5.3 Авторизация (RBAC)

### Уровень приложения

Каждый API-эндпоинт защищён зависимостью FastAPI:

```python
from fastapi import Depends, HTTPException

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    user = await get_user_by_id(payload["sub"])
    if not user["is_active"]:
        raise HTTPException(403, "Учётная запись заблокирована")
    return user

def require_role(*roles):
    async def checker(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "Недостаточно прав")
        return user
    return checker
```

Матрица доступа:

| Ресурс | guest | manager | admin |
|--------|:-----:|:-------:|:-----:|
| Регистрация / вход | + | + | + |
| Просмотр номеров | + | + | + |
| Создание бронирования | + | + | + |
| Мои бронирования | + | + | + |
| Все бронирования | — | + | + |
| Смена статуса бронирования | — | + | + |
| Управление пользователями | — | — | + |
| Аудит-лог | — | — | + |
| Отчёты | — | + | + |

### Уровень БД (GRANT/REVOKE)

```sql
-- Гость: только чтение каталога и запись бронирований
GRANT SELECT ON rooms, room_categories, amenities, services TO hotel_guest;
GRANT SELECT, INSERT, UPDATE ON bookings TO hotel_guest;
GRANT SELECT, INSERT, UPDATE ON guest_profiles TO hotel_guest;

-- Менеджер: дополнительно управление бронированиями
GRANT SELECT, UPDATE ON bookings TO hotel_manager;
GRANT SELECT, INSERT ON payments TO hotel_manager;
GRANT SELECT ON audit_log TO hotel_manager;

-- Администратор: полный доступ
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hotel_admin;
```

## 5.4 Row Level Security (RLS)

RLS обеспечивает изоляцию данных на уровне строк:

```sql
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;

-- Гость видит только свои бронирования
CREATE POLICY bookings_guest_policy ON bookings
    FOR ALL TO hotel_guest
    USING (user_id = current_setting('app.current_user_id')::INTEGER);

-- Менеджер видит все бронирования
CREATE POLICY bookings_manager_policy ON bookings
    FOR ALL TO hotel_manager
    USING (TRUE);

-- Аналогично для guest_profiles
ALTER TABLE guest_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY profiles_owner_policy ON guest_profiles
    FOR ALL TO hotel_guest
    USING (user_id = current_setting('app.current_user_id')::INTEGER);
```

## 5.5 Защита от SQL-инъекций

Все запросы к БД выполняются через **параметризованные запросы asyncpg**:

```python
# Безопасно — параметры передаются отдельно
row = await conn.fetchrow(
    "SELECT * FROM users WHERE email = $1",
    email
)

# Никогда не используется конкатенация строк:
# cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")  # ОПАСНО!
```

Asyncpg использует протокол PostgreSQL Extended Query, который передаёт параметры в бинарном формате, полностью исключая SQL-инъекции.

## 5.6 Аудит (Audit Log)

Все изменения в таблице `bookings` автоматически записываются в `audit_log` через триггер:

```sql
CREATE OR REPLACE FUNCTION fn_audit_log() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, record_id, action, new_data, changed_by)
        VALUES (TG_TABLE_NAME, NEW.id, 'INSERT', row_to_json(NEW)::JSONB, current_user);
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, record_id, action, old_data, new_data, changed_by)
        VALUES (TG_TABLE_NAME, NEW.id, 'UPDATE',
                row_to_json(OLD)::JSONB, row_to_json(NEW)::JSONB, current_user);
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, record_id, action, old_data, changed_by)
        VALUES (TG_TABLE_NAME, OLD.id, 'DELETE', row_to_json(OLD)::JSONB, current_user);
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;
```

Хранимые данные:
- `table_name` — имя таблицы
- `record_id` — ID записи
- `action` — тип операции (INSERT / UPDATE / DELETE)
- `old_data` / `new_data` — полные снимки записи в формате JSONB
- `changed_by` — пользователь PostgreSQL
- `changed_at` — метка времени

## 5.7 CORS

Настройка CORS (Cross-Origin Resource Sharing) в FastAPI:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

На продакшене `CORS_ORIGINS` ограничен адресом клиентского приложения.

## 5.8 Валидация входных данных

Все входные данные проходят двойную валидацию:

1. **На уровне приложения** — Pydantic v2 модели с аннотациями типов:
```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
```

2. **На уровне БД** — домены и CHECK-ограничения:
```sql
CREATE DOMAIN email_domain AS VARCHAR(255)
    CHECK (VALUE ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');
```

## 5.9 Резюме методов защиты

| Угроза | Метод защиты |
|--------|-------------|
| Перехват трафика | HTTPS/TLS (nginx) |
| Подбор пароля | bcrypt с cost factor 12 |
| Кража сессии | JWT с коротким временем жизни |
| Несанкционированный доступ | RBAC + JWT |
| Просмотр чужих данных | Row Level Security |
| Превышение привилегий | GRANT/REVOKE на уровне ролей БД |
| SQL-инъекции | Параметризованные запросы (asyncpg) |
| Неотслеживаемые изменения | Аудит-лог (триггер) |
| Некорректные данные | Pydantic + домены PostgreSQL |
| CSRF/XSS | CORS-политика, отсутствие cookie-авторизации |
