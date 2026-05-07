# Методы защиты данных

В рамках курсового проекта «Технология разработки и защиты баз данных» в системе реализован
многоуровневый комплекс мер защиты — от валидации входных данных до RLS на уровне СУБД и аудита.

---

## 1. Аутентификация и авторизация

### 1.1 Хеширование паролей — bcrypt

**Реализация:** `server/app/core/security.py`

```python
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
```

- алгоритм: **bcrypt** с автоматической солью;
- стоимость **rounds = 12** (≈250 ms на современном CPU — компромисс между безопасностью и UX);
- проверка через `bcrypt.checkpw()` — постоянное по времени сравнение, защита от **timing-атак**;
- хранится в `users.password_hash` (длина 60 символов).

### 1.2 JWT-токены (HS256)

- симметричный секрет `JWT_SECRET` из `.env` (никогда не коммитится; `.env` имеет `chmod 600`);
- `jwt_expire_minutes = 720` (12 часов);
- payload содержит `sub` (user_id), `role`, `iat`, `exp`;
- любая ошибка декодирования (`InvalidTokenError`, `ExpiredSignatureError`) ⇒ `AuthError 401`;
- секрет генерируется при первоначальном развёртывании командой `python -c "import secrets; print(secrets.token_urlsafe(64))"`.

### 1.3 RBAC (Role-Based Access Control)

Три роли (см. таблицу `roles`): `guest`, `manager`, `admin`.

В backend защита через FastAPI dependency:

```python
@router.get("/admin/audit", dependencies=[Depends(require_role("admin"))])
```

Дополнительно — RLS-политики в БД (см. ниже), которые работают, даже если backend ошибётся.

---

## 2. Защита данных на уровне СУБД

### 2.1 Domains и CHECK-ограничения

`pg_scripts/01_domains_types.sql`:

```sql
CREATE DOMAIN email_domain AS varchar(255)
       CHECK (VALUE ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

CREATE DOMAIN phone_domain AS varchar(32)
       CHECK (VALUE IS NULL OR VALUE ~ '^\+?[0-9 \-\(\)]{10,32}$');

CREATE DOMAIN positive_money AS numeric(12, 2)
       CHECK (VALUE >= 0);
```

- email-формат проверяется ДО вставки (защита от мусора и SQL-инъекций);
- цены не могут быть отрицательными (нарушение целостности → CheckViolationError → 422);
- эти ограничения «нельзя обойти» — валидация выполняется самой PostgreSQL.

### 2.2 ENUM-типы

Статусы номеров и бронирований не могут принимать произвольные значения:

```sql
CREATE TYPE booking_status AS ENUM ('pending', 'confirmed', 'checked_in', 'checked_out', 'cancelled');
```

Это защищает от опечаток и логических багов.

### 2.3 EXCLUDE constraint и триггер для бронирований

`pg_scripts/02_tables.sql` + `07_triggers.sql`:

- столбец `stay_period tsrange GENERATED ALWAYS AS (tsrange(check_in, check_out, '[)')) STORED`;
- индекс GiST по `stay_period`;
- триггер `trg_no_overlap_booking` блокирует пересечения для одного номера среди нон-cancelled бронирований:

```sql
IF v_conflict IS NOT NULL THEN
    RAISE EXCEPTION 'Номер уже забронирован на эти даты (конфликт с бронью %).', v_conflict
        USING ERRCODE = 'P0001';
END IF;
```

В обработчике ошибок backend это сообщение распознаётся и возвращает HTTP 409 Conflict с кодом `overlap`.

### 2.4 Foreign keys + ON DELETE поведение

Все связи защищены FK. Удаление пользователя/категории каскадно либо запрещено в зависимости от
семантики (например, нельзя удалить категорию, к которой привязаны номера).

---

## 3. Row-Level Security (RLS)

`pg_scripts/10_security.sql` — для таблицы `bookings`:

```sql
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;

CREATE POLICY p_bookings_owner ON bookings
    FOR ALL TO PUBLIC
    USING ( user_id::text = current_setting('app.user_id', TRUE) );

CREATE POLICY p_bookings_staff ON bookings
    FOR ALL TO hotel_manager, hotel_admin
    USING ( TRUE );
```

В backend перед каждым запросом устанавливаются переменные сессии:

```python
async with acquire_for_user(user.user_id) as conn:
    # выполняется SET LOCAL app.user_id, app.actor_id
    rows = await conn.fetch(...)
```

Эффект:

- **гость физически не сможет получить чужие бронирования**, даже при ошибке в backend (например, забыли проверить `user_id`);
- менеджеру/админу политика разрешает видеть всё.

---

## 4. Аудит изменений

`pg_scripts/07_triggers.sql` — триггеры `trg_audit_bookings`, `trg_audit_users`, `trg_audit_rooms`.

Каждый INSERT / UPDATE / DELETE в этих таблицах автоматически создаёт запись в `audit_log`:

| Поле | Содержимое |
|------|------------|
| `table_name` | имя таблицы |
| `row_pk` | PK затронутой строки |
| `action` | ENUM: INSERT / UPDATE / DELETE |
| `actor_id` | ID пользователя из `current_setting('app.actor_id')` |
| `actor_name` | ФИО актора |
| `happened_at` | timestamptz |
| `old_data`, `new_data` | row_to_json до и после |

API `/admin/audit` (только для `admin`) даёт удобный доступ к журналу с фильтрацией по таблице.

Это базис для расследования инцидентов: «кто и когда изменил роль пользователя X», «когда удалили
номер 305», «кто отменил бронь Y».

---

## 5. Транспортная безопасность

- Backend слушает только `127.0.0.1:8000` — снаружи доступ исключительно через Nginx;
- Nginx настроен с заголовками `X-Real-IP`, `X-Forwarded-For`;
- В production-конфигурации рекомендуется добавить TLS (Let's Encrypt) и редирект 80→443. На текущем
  тестовом стенде используется HTTP, чтобы избежать необходимости в DNS-имени для сертификата.

---

## 6. Защита от классических атак

| Атака | Защита |
|-------|--------|
| **SQL-инъекция** | Параметризованные запросы asyncpg (`$1`, `$2`...); никогда не используется конкатенация строк |
| **Brute-force паролей** | bcrypt с rounds=12 + ограничение на длину и формат пароля; рекомендация — добавить fail2ban на уровне Nginx |
| **Подделка JWT** | HS256 с длинным секретом; токен с инвалидной подписью отбрасывается |
| **Перехват токена** | Включить HTTPS на production; срок жизни токена ограничен 12 часами |
| **CSRF** | API stateless (Bearer JWT), без cookie-сессий, поэтому CSRF не применима |
| **XSS** | Клиент Flet рендерит контент через виджеты (не innerHTML); валидация на уровне доменов БД |
| **Mass Assignment** | Pydantic-схемы строго перечисляют разрешённые поля; неизвестные поля игнорируются |
| **Privilege escalation** | RLS + RBAC на двух уровнях (backend + БД); даже если в коде ошибка, БД не отдаст чужие данные |

---

## 7. Защита учётных данных в репозитории

- Файл `server/.env` указан в `.gitignore`. В репозитории только `.env.example` с placeholder-значениями;
- Пароли БД заданы в зашифрованном виде только на сервере;
- GitHub-токен пользователя был использован разово для пушей; рекомендуется ротировать после защиты КП.

---

## 8. Журнал ошибок (audit trail в логах)

В `core/errors.py` заведена единая обработка исключений:

- `PostgresError` без специфики → 500 + `database_error` (детали в логах, не в ответе);
- `Exception` любой → 500 + `internal_error` + полный stacktrace в `journalctl`;
- бизнес-ошибки и нарушения CHECK/EXCLUDE → 4xx с понятным сообщением для пользователя.

Это разделение «что показывать пользователю» vs «что писать в лог» — важно для не утечки деталей
системы.

---

## 9. Контроль доступа в файловой системе

```bash
chmod 600 /opt/hotel/hotel-management-system/server/.env
chown root:root /etc/systemd/system/hotel-api.service
```

---

## 10. Чек-лист соответствия требованиям задания

- [x] Триггеры (5 шт.) — `pg_scripts/07_triggers.sql`
- [x] Представления (≥3, всего 4) — `pg_scripts/04_views.sql`
- [x] Хранимые процедуры (5: insert/update/delete/select/state-machine) — `pg_scripts/06_procedures.sql`
- [x] Хранимые функции (3 + обёртка) — `pg_scripts/05_functions.sql`
- [x] Собственные доменные типы и ограничения — `pg_scripts/01_domains_types.sql`
- [x] 12 типов запросов из пула — `pg_scripts/09_queries_pool.sql`
- [x] **Методы защиты данных:**
  - bcrypt + JWT + RBAC (на уровне приложения),
  - CHECK / DOMAIN / EXCLUDE (на уровне СУБД),
  - RLS-политики (на уровне строк),
  - триггеры аудита (полный audit trail).
