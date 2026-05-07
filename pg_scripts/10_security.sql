-- =============================================================================
-- 10_security.sql
-- Роли PostgreSQL, GRANT/REVOKE, Row Level Security (RLS)
-- Методы защиты данных на уровне СУБД
-- =============================================================================

-- ─── Роли базы данных ────────────────────────────────────────────────────────

-- Роль для гостевого доступа (минимальные привилегии)
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hotel_guest') THEN
        CREATE ROLE hotel_guest NOLOGIN;
    END IF;
END $$;

-- Роль для менеджеров
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hotel_manager') THEN
        CREATE ROLE hotel_manager NOLOGIN;
    END IF;
END $$;

-- Роль для администраторов
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hotel_admin') THEN
        CREATE ROLE hotel_admin NOLOGIN;
    END IF;
END $$;

-- ─── GRANT для hotel_guest ───────────────────────────────────────────────────

GRANT SELECT ON rooms, room_categories, amenities, room_amenities, services TO hotel_guest;
GRANT SELECT, INSERT ON bookings, booking_services TO hotel_guest;
GRANT SELECT ON v_room_availability TO hotel_guest;
GRANT SELECT, UPDATE (first_name, last_name, patronymic, phone, passport_series, passport_number, birth_date)
    ON guest_profiles TO hotel_guest;
GRANT USAGE ON SEQUENCE bookings_id_seq, booking_services_id_seq TO hotel_guest;

-- ─── GRANT для hotel_manager ─────────────────────────────────────────────────

GRANT hotel_guest TO hotel_manager;
GRANT SELECT, UPDATE ON bookings TO hotel_manager;
GRANT SELECT ON users, guest_profiles, payments, audit_log TO hotel_manager;
GRANT SELECT ON v_guest_bookings, v_active_bookings, v_revenue_by_category TO hotel_manager;
GRANT UPDATE (status) ON rooms TO hotel_manager;
GRANT INSERT ON payments TO hotel_manager;
GRANT USAGE ON SEQUENCE payments_id_seq TO hotel_manager;

-- ─── GRANT для hotel_admin ───────────────────────────────────────────────────

GRANT hotel_manager TO hotel_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hotel_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO hotel_admin;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO hotel_admin;
GRANT EXECUTE ON ALL PROCEDURES IN SCHEMA public TO hotel_admin;

-- ─── Row Level Security (RLS) для таблицы bookings ──────────────────────────

ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;

-- Политика: гость видит только свои бронирования
CREATE POLICY bookings_guest_policy ON bookings
    FOR SELECT
    TO hotel_guest
    USING (guest_id = (current_setting('app.current_user_id', TRUE))::INTEGER);

-- Политика: гость может создавать только свои бронирования
CREATE POLICY bookings_guest_insert_policy ON bookings
    FOR INSERT
    TO hotel_guest
    WITH CHECK (guest_id = (current_setting('app.current_user_id', TRUE))::INTEGER);

-- Политика: менеджер и админ видят все бронирования
CREATE POLICY bookings_staff_policy ON bookings
    FOR ALL
    TO hotel_manager, hotel_admin
    USING (TRUE)
    WITH CHECK (TRUE);

-- ─── RLS для таблицы guest_profiles ──────────────────────────────────────────

ALTER TABLE guest_profiles ENABLE ROW LEVEL SECURITY;

-- Гость видит и редактирует только свой профиль
CREATE POLICY profiles_guest_policy ON guest_profiles
    FOR ALL
    TO hotel_guest
    USING (user_id = (current_setting('app.current_user_id', TRUE))::INTEGER)
    WITH CHECK (user_id = (current_setting('app.current_user_id', TRUE))::INTEGER);

-- Менеджер и админ видят все профили
CREATE POLICY profiles_staff_policy ON guest_profiles
    FOR ALL
    TO hotel_manager, hotel_admin
    USING (TRUE)
    WITH CHECK (TRUE);

-- ─── Комментарии ─────────────────────────────────────────────────────────────

COMMENT ON POLICY bookings_guest_policy ON bookings IS
'RLS: гость видит только свои бронирования (guest_id = current_user_id)';

COMMENT ON POLICY bookings_staff_policy ON bookings IS
'RLS: персонал (менеджер/админ) имеет полный доступ к бронированиям';

COMMENT ON POLICY profiles_guest_policy ON guest_profiles IS
'RLS: гость может просматривать и редактировать только свой профиль';
