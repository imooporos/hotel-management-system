# 3. Создание объектов базы данных

Все SQL-скрипты расположены в каталоге `pg_scripts/` и выполняются последовательно скриптом `reset.sh`.

## 3.1 Домены (01_domains_types.sql)

### email_domain
```sql
CREATE DOMAIN email_domain AS VARCHAR(255)
    CHECK (VALUE ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');
```
**Назначение**: валидация формата электронной почты на уровне БД. Используется в таблице `users` (столбец `email`).

### phone_domain
```sql
CREATE DOMAIN phone_domain AS VARCHAR(20)
    CHECK (VALUE IS NULL OR VALUE ~* '^\+?\d{10,15}$');
```
**Назначение**: валидация формата номера телефона. Разрешает международный формат (+7XXXXXXXXXX). Используется в таблице `users` (столбец `phone`).

### price_domain
```sql
CREATE DOMAIN price_domain AS NUMERIC(12, 2)
    CHECK (VALUE >= 0);
```
**Назначение**: денежные суммы не могут быть отрицательными. Используется в таблицах `room_categories`, `services`, `bookings`, `booking_services`, `payments`.

## 3.2 ENUM-типы (01_domains_types.sql)

### user_role
```sql
CREATE TYPE user_role AS ENUM ('guest', 'manager', 'admin');
```
**Назначение**: ограничение допустимых ролей пользователей. Применяется при регистрации (по умолчанию `guest`) и при смене ролей администратором.

### room_status
```sql
CREATE TYPE room_status AS ENUM ('available', 'occupied', 'maintenance', 'cleaning');
```
**Назначение**: статус номера. Влияет на фильтрацию при бронировании и отображение в каталоге.

### booking_status
```sql
CREATE TYPE booking_status AS ENUM ('pending', 'confirmed', 'checked_in', 'checked_out', 'cancelled');
```
**Назначение**: жизненный цикл бронирования. Переходы между статусами контролируются триггером `trg_booking_status_change`.

## 3.3 Таблицы (02_tables.sql)

Всего **11 таблиц**:

| Таблица | Описание | Ключевые ограничения |
|---------|----------|---------------------|
| `users` | Учётные записи | PK, UNIQUE email, домены email_domain и phone_domain |
| `guest_profiles` | Паспортные данные | FK → users, UNIQUE user_id |
| `room_categories` | Категории номеров | PK, UNIQUE name, price_domain |
| `rooms` | Номера гостиницы | FK → room_categories, UNIQUE room_number |
| `amenities` | Удобства | PK, UNIQUE name |
| `room_amenities` | Связь номер↔удобство | Составной PK (room_id, amenity_id) |
| `bookings` | Бронирования | FK → users, FK → rooms, CHECK check_out > check_in |
| `booking_services` | Услуги в бронировании | FK → bookings, FK → services |
| `services` | Каталог услуг | PK, UNIQUE name, price_domain |
| `payments` | Платежи | FK → bookings, price_domain |
| `audit_log` | Аудит-лог | JSONB для old_data/new_data |

## 3.4 Индексы (03_indexes.sql)

Всего **12 индексов**:

```sql
-- B-tree индексы для ускорения поиска
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_role ON users (role);
CREATE INDEX idx_rooms_category ON rooms (category_id);
CREATE INDEX idx_rooms_status ON rooms (status);
CREATE INDEX idx_bookings_user ON bookings (user_id);
CREATE INDEX idx_bookings_room ON bookings (room_id);
CREATE INDEX idx_bookings_status ON bookings (status);
CREATE INDEX idx_bookings_dates ON bookings (check_in, check_out);
CREATE INDEX idx_booking_services_booking ON booking_services (booking_id);
CREATE INDEX idx_payments_booking ON payments (booking_id);
CREATE INDEX idx_audit_table ON audit_log (table_name);
CREATE INDEX idx_audit_changed_at ON audit_log (changed_at);
```

**GiST-индекс** для проверки пересечений дат (exclusion constraint):
```sql
-- Используется совместно с расширением btree_gist
CREATE EXTENSION IF NOT EXISTS btree_gist;
```

**Обоснование выбора типов индексов**:
- **B-tree**: стандартный тип для колонок с операциями сравнения (=, <, >, BETWEEN).
- **GiST**: необходим для exclusion constraint на диапазонах дат (`daterange`), обеспечивает проверку пересечений за O(log n).

## 3.5 Представления (04_views.sql)

### v_room_catalog
```sql
CREATE OR REPLACE VIEW v_room_catalog AS
SELECT r.id, r.room_number, rc.name AS category, rc.base_price,
       r.floor, r.capacity, r.status, r.description,
       COALESCE(string_agg(a.name, ', ' ORDER BY a.name), '') AS amenities
FROM rooms r
JOIN room_categories rc ON rc.id = r.category_id
LEFT JOIN room_amenities ra ON ra.room_id = r.id
LEFT JOIN amenities a ON a.id = ra.amenity_id
GROUP BY r.id, r.room_number, rc.name, rc.base_price, r.floor, r.capacity, r.status, r.description;
```
**Применение в приложении**: роутер `GET /api/rooms` использует это представление для формирования каталога номеров с агрегированным списком удобств.

### v_booking_details
**Применение**: роутер `GET /api/bookings` — детальная информация о бронировании с данными гостя и номера.

### v_revenue_by_category
**Применение**: роутер `GET /api/reports/revenue` — отчёт о выручке по категориям номеров.

### v_guest_statistics
**Применение**: роутер `GET /api/reports/statistics` — статистика по гостям (количество бронирований, общая сумма).

## 3.6 Функции (05_functions.sql)

### fn_room_is_free(p_room_id, p_check_in, p_check_out)
```sql
CREATE OR REPLACE FUNCTION fn_room_is_free(
    p_room_id INTEGER,
    p_check_in DATE,
    p_check_out DATE
) RETURNS BOOLEAN
```
**Назначение**: проверяет, свободен ли номер на указанные даты. Учитывает только бронирования в статусах `pending`, `confirmed`, `checked_in`.
**Применение**: вызывается при создании бронирования (`POST /api/bookings`), а также в процедуре `sp_create_booking`.

### fn_calculate_booking_total(p_booking_id)
```sql
CREATE OR REPLACE FUNCTION fn_calculate_booking_total(p_booking_id INTEGER)
RETURNS NUMERIC(12,2)
```
**Назначение**: рассчитывает итоговую стоимость бронирования = (цена_номера × кол-во_ночей) + сумма_дополнительных_услуг.
**Применение**: вызывается при обновлении бронирования и в отчётах.

### fn_occupancy_rate(p_date_from, p_date_to)
```sql
CREATE OR REPLACE FUNCTION fn_occupancy_rate(
    p_date_from DATE, p_date_to DATE
) RETURNS NUMERIC(5,2)
```
**Назначение**: рассчитывает процент загрузки гостиницы за период.
**Применение**: роутер `GET /api/reports/occupancy`.

## 3.7 Хранимые процедуры (06_procedures.sql)

### sp_create_booking
**Назначение**: создание бронирования с проверкой свободности номера и расчётом стоимости.
**Операции**: INSERT (bookings), вызов fn_room_is_free, fn_calculate_booking_total.

### sp_update_booking_status
**Назначение**: смена статуса бронирования с валидацией допустимых переходов.
**Операции**: UPDATE (bookings), проверка бизнес-правил.

### sp_register_guest
**Назначение**: регистрация нового пользователя с созданием профиля гостя.
**Операции**: INSERT (users), INSERT (guest_profiles).

### sp_add_booking_service
**Назначение**: добавление дополнительной услуги к бронированию с фиксацией цены.
**Операции**: INSERT (booking_services), UPDATE total_amount.

### sp_generate_monthly_report
**Назначение**: формирование месячного отчёта по загрузке и выручке.
**Операции**: SELECT с агрегацией, использование представления v_revenue_by_category.

## 3.8 Триггеры (07_triggers.sql)

### trg_booking_status_change
```sql
CREATE TRIGGER trg_booking_status_change
    BEFORE UPDATE OF status ON bookings
    FOR EACH ROW
    EXECUTE FUNCTION fn_validate_status_transition();
```
**Назначение**: контролирует допустимые переходы между статусами бронирования. Например, нельзя перевести `cancelled` обратно в `confirmed`.

### trg_audit_bookings
```sql
CREATE TRIGGER trg_audit_bookings
    AFTER INSERT OR UPDATE OR DELETE ON bookings
    FOR EACH ROW
    EXECUTE FUNCTION fn_audit_log();
```
**Назначение**: записывает все изменения в таблице `bookings` в `audit_log` (old_data / new_data в формате JSONB).

### trg_update_timestamp
```sql
CREATE TRIGGER trg_update_timestamp
    BEFORE UPDATE ON bookings
    FOR EACH ROW
    EXECUTE FUNCTION fn_set_updated_at();
```
**Назначение**: автоматически обновляет столбец `updated_at` при любом изменении записи.

### trg_check_room_capacity
```sql
CREATE TRIGGER trg_check_room_capacity
    BEFORE INSERT OR UPDATE ON bookings
    FOR EACH ROW
    EXECUTE FUNCTION fn_check_capacity();
```
**Назначение**: проверяет, что количество гостей (`guests_count`) не превышает вместимость номера (`rooms.capacity`).

## 3.9 Пул SQL-запросов (09_queries_pool.sql)

Файл содержит **12 типов запросов** согласно требованиям курсового проекта:

| № | Тип запроса | Пример из проекта |
|---|------------|-------------------|
| 1 | Простые с условием (LIKE, BETWEEN, IN) | Поиск номеров по диапазону цен |
| 2 | Скалярные подзапросы | Средняя цена в категории в SELECT |
| 3 | Табличные подзапросы | Номера с бронированиями в FROM |
| 4 | Подзапросы с кванторами (EXISTS, ALL) | Номера без бронирований |
| 5 | Множественные операции (UNION, INTERSECT, EXCEPT) | Объединение активных и завершённых |
| 6 | Вынесенные подзапросы (WITH / CTE) | Статистика загрузки по месяцам |
| 7 | Агрегатные функции (GROUP BY, HAVING) | Выручка по категориям |
| 8 | Многотабличные запросы (JOIN) | Детали бронирования с гостем и номером |
| 9 | Строковые/датовые функции | Форматирование дат, конкатенация ФИО |
| 10 | Рекурсивные (WITH RECURSIVE) | Иерархия категорий номеров |
| 11 | Сводные таблицы (CROSSTAB) | Загрузка по месяцам и категориям |
| 12 | Оконные функции (OVER, PARTITION BY) | Ранжирование номеров по популярности |

## 3.10 Безопасность (10_security.sql)

### Роли PostgreSQL

```sql
CREATE ROLE hotel_guest;
CREATE ROLE hotel_manager;
CREATE ROLE hotel_admin;
```

### GRANT/REVOKE

- `hotel_guest`: SELECT на rooms, room_categories, amenities, services; INSERT на bookings; SELECT/UPDATE на собственный профиль.
- `hotel_manager`: всё от guest + UPDATE bookings, SELECT/INSERT payments, SELECT audit_log.
- `hotel_admin`: FULL на все таблицы.

### Row Level Security (RLS)

```sql
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;

CREATE POLICY bookings_guest_policy ON bookings
    FOR ALL TO hotel_guest
    USING (user_id = current_setting('app.current_user_id')::INTEGER);

CREATE POLICY bookings_manager_policy ON bookings
    FOR ALL TO hotel_manager
    USING (TRUE);
```

**Назначение**: гость видит только свои бронирования, менеджер и администратор видят все.
