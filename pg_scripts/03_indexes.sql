-- ============================================================================
--  03_indexes.sql
--  Индексы для оптимизации частых запросов.
-- ============================================================================

\echo '>>> applying 03_indexes.sql'

-- ---------------------------------------------------------------------------
--  users — поиск по email регистронезависимо
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_users_email_lower
    ON users (lower(email));

CREATE INDEX IF NOT EXISTS ix_users_role_id
    ON users (role_id);

-- ---------------------------------------------------------------------------
--  rooms — фильтрация по статусу/категории
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_rooms_category    ON rooms (category_id);
CREATE INDEX IF NOT EXISTS ix_rooms_status      ON rooms (status);
CREATE INDEX IF NOT EXISTS ix_rooms_active      ON rooms (is_active) WHERE is_active;

-- ---------------------------------------------------------------------------
--  bookings — поиск по гостю / номеру / диапазону дат
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_bookings_user     ON bookings (user_id);
CREATE INDEX IF NOT EXISTS ix_bookings_room     ON bookings (room_id);
CREATE INDEX IF NOT EXISTS ix_bookings_status   ON bookings (status);
CREATE INDEX IF NOT EXISTS ix_bookings_check_in ON bookings (check_in);

-- GiST по diapason'у даёт быстрый поиск пересечений в EXCLUDE-ограничении
-- и в функции fn_room_is_free.
CREATE INDEX IF NOT EXISTS ix_bookings_period_gist
    ON bookings USING gist (stay_period);

-- ---------------------------------------------------------------------------
--  payments — поиск платежей по бронированию
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_payments_booking  ON payments (booking_id);
CREATE INDEX IF NOT EXISTS ix_payments_paid_at  ON payments (paid_at DESC);

-- ---------------------------------------------------------------------------
--  audit_log — поиск по таблице и времени
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_audit_table_time
    ON audit_log (table_name, happened_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_actor       ON audit_log (actor_id);

\echo '<<< 03_indexes.sql ok'
