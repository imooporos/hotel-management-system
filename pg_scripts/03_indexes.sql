-- =============================================================================
-- 03_indexes.sql
-- Индексы для оптимизации запросов
-- B-tree для FK и частых фильтров, GiST для диапазонов дат бронирований
-- =============================================================================

-- Индексы для таблицы users
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_role ON users (role);
CREATE INDEX idx_users_active ON users (is_active) WHERE is_active = TRUE;

-- Индексы для таблицы guest_profiles
CREATE INDEX idx_guest_profiles_user_id ON guest_profiles (user_id);
CREATE INDEX idx_guest_profiles_last_name ON guest_profiles (last_name);

-- Индексы для таблицы rooms
CREATE INDEX idx_rooms_category_id ON rooms (category_id);
CREATE INDEX idx_rooms_status ON rooms (status);
CREATE INDEX idx_rooms_floor ON rooms (floor);

-- Индексы для таблицы bookings
CREATE INDEX idx_bookings_guest_id ON bookings (guest_id);
CREATE INDEX idx_bookings_room_id ON bookings (room_id);
CREATE INDEX idx_bookings_status ON bookings (status);
CREATE INDEX idx_bookings_dates ON bookings (check_in_date, check_out_date);

-- GiST-индекс для быстрой проверки пересечения диапазонов дат бронирований
-- Используется триггером trg_no_overlap_booking и функцией fn_room_is_free
CREATE INDEX idx_bookings_daterange ON bookings
    USING GIST (
        daterange(check_in_date, check_out_date, '[)')
    );

-- Индексы для таблицы payments
CREATE INDEX idx_payments_booking_id ON payments (booking_id);
CREATE INDEX idx_payments_paid_at ON payments (paid_at);

-- Индексы для таблицы audit_log
CREATE INDEX idx_audit_log_table ON audit_log (table_name);
CREATE INDEX idx_audit_log_changed_at ON audit_log (changed_at);
CREATE INDEX idx_audit_log_action ON audit_log (action);
