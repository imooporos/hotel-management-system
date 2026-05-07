-- =============================================================================
-- 04_views.sql
-- Представления (Views) для отчётов и витрин данных
-- =============================================================================

-- 1. Доступность номеров на текущую дату
CREATE OR REPLACE VIEW v_room_availability AS
SELECT
    r.id AS room_id,
    r.room_number,
    rc.name AS category_name,
    rc.base_price,
    rc.capacity,
    r.floor,
    r.status,
    r.description AS room_description,
    CASE
        WHEN r.status != 'available' THEN FALSE
        WHEN EXISTS (
            SELECT 1 FROM bookings b
            WHERE b.room_id = r.id
              AND b.status IN ('confirmed', 'checked_in')
              AND b.check_in_date <= CURRENT_DATE
              AND b.check_out_date > CURRENT_DATE
        ) THEN FALSE
        ELSE TRUE
    END AS is_free_today,
    (
        SELECT STRING_AGG(a.name, ', ' ORDER BY a.name)
        FROM room_amenities ra
        JOIN amenities a ON a.id = ra.amenity_id
        WHERE ra.room_id = r.id
    ) AS amenities_list
FROM rooms r
JOIN room_categories rc ON rc.id = r.category_id
WHERE r.is_active = TRUE
ORDER BY r.room_number;

COMMENT ON VIEW v_room_availability IS 'Каталог номеров с информацией о доступности на сегодня и списком удобств';

-- 2. Бронирования с информацией о госте и номере
CREATE OR REPLACE VIEW v_guest_bookings AS
SELECT
    b.id AS booking_id,
    b.guest_id,
    gp.first_name || ' ' || gp.last_name AS guest_name,
    u.email AS guest_email,
    gp.phone AS guest_phone,
    r.room_number,
    rc.name AS category_name,
    b.check_in_date,
    b.check_out_date,
    (b.check_out_date - b.check_in_date) AS nights,
    b.guests_count,
    b.status,
    b.total_amount,
    b.notes,
    b.created_at AS booked_at,
    (
        SELECT COALESCE(SUM(bs.quantity * bs.price_at_booking), 0)
        FROM booking_services bs
        WHERE bs.booking_id = b.id
    ) AS services_total,
    (
        SELECT STRING_AGG(s.name || ' x' || bs.quantity, ', ')
        FROM booking_services bs
        JOIN services s ON s.id = bs.service_id
        WHERE bs.booking_id = b.id
    ) AS services_list
FROM bookings b
JOIN users u ON u.id = b.guest_id
LEFT JOIN guest_profiles gp ON gp.user_id = b.guest_id
JOIN rooms r ON r.id = b.room_id
JOIN room_categories rc ON rc.id = r.category_id
ORDER BY b.created_at DESC;

COMMENT ON VIEW v_guest_bookings IS 'Развёрнутая информация о бронированиях с данными гостя и номера';

-- 3. Выручка по категориям номеров за последние 12 месяцев
CREATE OR REPLACE VIEW v_revenue_by_category AS
SELECT
    rc.id AS category_id,
    rc.name AS category_name,
    COUNT(b.id) AS total_bookings,
    COALESCE(SUM(b.total_amount), 0) AS total_revenue,
    COALESCE(AVG(b.total_amount), 0) AS avg_revenue_per_booking,
    COALESCE(AVG(b.check_out_date - b.check_in_date), 0) AS avg_nights
FROM room_categories rc
LEFT JOIN rooms r ON r.category_id = rc.id
LEFT JOIN bookings b ON b.room_id = r.id
    AND b.status IN ('confirmed', 'checked_in', 'checked_out')
    AND b.created_at >= NOW() - INTERVAL '12 months'
GROUP BY rc.id, rc.name
ORDER BY total_revenue DESC;

COMMENT ON VIEW v_revenue_by_category IS 'Аналитика выручки по категориям номеров за последние 12 месяцев';

-- 4. Активные бронирования (текущие и предстоящие)
CREATE OR REPLACE VIEW v_active_bookings AS
SELECT
    b.id AS booking_id,
    b.guest_id,
    gp.first_name || ' ' || gp.last_name AS guest_name,
    u.email AS guest_email,
    r.room_number,
    rc.name AS category_name,
    b.check_in_date,
    b.check_out_date,
    b.status,
    b.guests_count,
    b.total_amount,
    CASE
        WHEN b.status = 'checked_in' THEN 'Гость в номере'
        WHEN b.status = 'confirmed' AND b.check_in_date <= CURRENT_DATE THEN 'Ожидает заезда'
        WHEN b.status = 'confirmed' THEN 'Предстоящее'
        WHEN b.status = 'pending' THEN 'Ожидает подтверждения'
        ELSE b.status::TEXT
    END AS status_display
FROM bookings b
JOIN users u ON u.id = b.guest_id
LEFT JOIN guest_profiles gp ON gp.user_id = b.guest_id
JOIN rooms r ON r.id = b.room_id
JOIN room_categories rc ON rc.id = r.category_id
WHERE b.status IN ('pending', 'confirmed', 'checked_in')
ORDER BY b.check_in_date;

COMMENT ON VIEW v_active_bookings IS 'Активные бронирования: текущие, подтверждённые и ожидающие';
