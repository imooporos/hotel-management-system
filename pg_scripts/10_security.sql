-- ============================================================================
--  10_security.sql
--  Безопасность БД: роли PostgreSQL, GRANT/REVOKE, RLS, политики.
-- ============================================================================

\echo '>>> applying 10_security.sql'

-- ---------------------------------------------------------------------------
--  Роли PostgreSQL для разных групп пользователей
--  Приложение продолжает подключаться под hotel_app, но сервер при необходимости
--  может выполнить SET ROLE для запросов от имени конкретной группы.
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hotel_guest') THEN
        CREATE ROLE hotel_guest;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hotel_manager') THEN
        CREATE ROLE hotel_manager;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hotel_admin') THEN
        CREATE ROLE hotel_admin;
    END IF;
END $$;

-- ---------------------------------------------------------------------------
--  hotel_guest — только базовые операции с собственными бронями и профилем
-- ---------------------------------------------------------------------------
GRANT USAGE ON SCHEMA public TO hotel_guest;
GRANT SELECT          ON room_categories, rooms, amenities, room_amenities,
                         services, v_room_availability TO hotel_guest;
GRANT SELECT, UPDATE  ON users, guest_profiles TO hotel_guest;
GRANT SELECT, INSERT  ON bookings, booking_services TO hotel_guest;
GRANT SELECT          ON v_guest_bookings TO hotel_guest;
GRANT EXECUTE ON FUNCTION fn_room_is_free(bigint, date, date)        TO hotel_guest;
GRANT EXECUTE ON FUNCTION fn_calculate_booking_total(bigint, date, date, integer[]) TO hotel_guest;

-- ---------------------------------------------------------------------------
--  hotel_manager — всё, что guest, плюс смена статуса бронирования
-- ---------------------------------------------------------------------------
GRANT hotel_guest TO hotel_manager;
GRANT SELECT, UPDATE ON bookings TO hotel_manager;
GRANT SELECT, INSERT ON payments TO hotel_manager;
GRANT SELECT         ON v_active_bookings, v_revenue_by_category TO hotel_manager;
GRANT EXECUTE ON FUNCTION fn_occupancy_rate(date, date)               TO hotel_manager;
GRANT EXECUTE ON PROCEDURE sp_update_booking_status(bigint, booking_status, bigint) TO hotel_manager;
GRANT EXECUTE ON PROCEDURE sp_cancel_booking(bigint, bigint)                        TO hotel_manager;
GRANT EXECUTE ON FUNCTION  sp_get_user_bookings(bigint)                             TO hotel_manager;

-- ---------------------------------------------------------------------------
--  hotel_admin — всё, что manager, плюс CRUD номеров/услуг и пользователи
-- ---------------------------------------------------------------------------
GRANT hotel_manager TO hotel_admin;
GRANT INSERT, UPDATE, DELETE ON rooms, room_categories, amenities, room_amenities,
                                services TO hotel_admin;
GRANT SELECT, UPDATE, DELETE ON users TO hotel_admin;
GRANT SELECT                 ON audit_log TO hotel_admin;

-- ---------------------------------------------------------------------------
--  Row Level Security: гость видит только свои бронирования.
--  Включается в таблице, дальше — политика для каждой группы.
-- ---------------------------------------------------------------------------
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings FORCE  ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_bookings_owner ON bookings;
CREATE POLICY p_bookings_owner ON bookings
    FOR ALL
    TO hotel_guest
    USING (user_id = NULLIF(current_setting('app.user_id', true), '')::bigint)
    WITH CHECK (user_id = NULLIF(current_setting('app.user_id', true), '')::bigint);

DROP POLICY IF EXISTS p_bookings_staff ON bookings;
CREATE POLICY p_bookings_staff ON bookings
    FOR ALL
    TO hotel_manager, hotel_admin
    USING (true)
    WITH CHECK (true);

-- ---------------------------------------------------------------------------
--  Дать hotel_app (нашему пользователю приложения) права всех групп.
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hotel_app') THEN
        EXECUTE 'GRANT hotel_admin TO hotel_app';
    END IF;
END $$;

\echo '<<< 10_security.sql ok'
