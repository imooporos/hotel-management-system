-- ============================================================================
--  04_views.sql
--  Представления (views) для витрин данных и отчётов.
-- ============================================================================

\echo '>>> applying 04_views.sql'

DROP VIEW IF EXISTS v_room_availability    CASCADE;
DROP VIEW IF EXISTS v_guest_bookings       CASCADE;
DROP VIEW IF EXISTS v_revenue_by_category  CASCADE;
DROP VIEW IF EXISTS v_active_bookings      CASCADE;

-- ---------------------------------------------------------------------------
--  v_room_availability
--  Полная карточка номера для каталога: цена, удобства, текущий статус.
-- ---------------------------------------------------------------------------
CREATE VIEW v_room_availability AS
SELECT
    r.room_id,
    r.room_number,
    r.floor,
    rc.category_id,
    rc.code              AS category_code,
    rc.title             AS category_title,
    rc.capacity,
    (rc.base_price + r.price_modifier)::positive_money AS price_per_night,
    r.status,
    r.description,
    r.is_active,
    COALESCE(
        (
            SELECT array_agg(a.code ORDER BY a.code)
            FROM   room_amenities ra
            JOIN   amenities a ON a.amenity_id = ra.amenity_id
            WHERE  ra.room_id = r.room_id
        ),
        ARRAY[]::text[]
    )                    AS amenities
FROM rooms r
JOIN room_categories rc ON rc.category_id = r.category_id;

COMMENT ON VIEW v_room_availability IS
    'Карточки номеров с актуальной ценой и списком удобств. Используется в каталоге клиента.';

-- ---------------------------------------------------------------------------
--  v_guest_bookings
--  Список бронирований с человеко-читаемой информацией.
--  Используется в личном кабинете и на дашборде менеджера.
-- ---------------------------------------------------------------------------
CREATE VIEW v_guest_bookings AS
SELECT
    b.booking_id,
    b.user_id,
    u.full_name             AS guest_name,
    u.email                 AS guest_email,
    u.phone                 AS guest_phone,
    r.room_number,
    rc.title                AS category_title,
    b.check_in,
    b.check_out,
    (b.check_out - b.check_in)        AS nights,
    b.guests_count,
    b.status,
    b.total_price,
    b.created_at,
    COALESCE(p.paid_total, 0)::positive_money AS paid_total,
    GREATEST(b.total_price - COALESCE(p.paid_total, 0), 0)::positive_money AS amount_due
FROM bookings b
JOIN users           u  ON u.user_id      = b.user_id
JOIN rooms           r  ON r.room_id      = b.room_id
JOIN room_categories rc ON rc.category_id = r.category_id
LEFT JOIN (
    SELECT booking_id, SUM(amount) AS paid_total
    FROM   payments
    GROUP  BY booking_id
) p ON p.booking_id = b.booking_id;

COMMENT ON VIEW v_guest_bookings IS
    'Бронирования с фактической оплатой и долгом. Гость видит свои строки (RLS), менеджер/админ — все.';

-- ---------------------------------------------------------------------------
--  v_revenue_by_category
--  Агрегированная выручка по категориям номеров.
--  Применяется в отчёте «Выручка по категориям».
-- ---------------------------------------------------------------------------
CREATE VIEW v_revenue_by_category AS
SELECT
    rc.category_id,
    rc.code      AS category_code,
    rc.title     AS category_title,
    COUNT(DISTINCT b.booking_id) FILTER (WHERE b.status IN ('confirmed','checked_in','checked_out'))
                 AS bookings_count,
    COALESCE(SUM(b.total_price)
             FILTER (WHERE b.status IN ('confirmed','checked_in','checked_out')), 0)::positive_money
                 AS revenue_total,
    COALESCE(SUM(p.amount), 0)::positive_money
                 AS revenue_paid
FROM room_categories rc
LEFT JOIN rooms     r ON r.category_id = rc.category_id
LEFT JOIN bookings  b ON b.room_id     = r.room_id
LEFT JOIN payments  p ON p.booking_id  = b.booking_id
GROUP BY rc.category_id, rc.code, rc.title;

COMMENT ON VIEW v_revenue_by_category IS
    'Сводный отчёт по выручке для администратора.';

-- ---------------------------------------------------------------------------
--  v_active_bookings
--  Брони, по которым гость сейчас должен заселиться или уже заселён.
-- ---------------------------------------------------------------------------
CREATE VIEW v_active_bookings AS
SELECT
    b.booking_id,
    u.full_name AS guest_name,
    u.phone     AS guest_phone,
    r.room_number,
    rc.title    AS category_title,
    b.check_in,
    b.check_out,
    b.status,
    b.total_price
FROM bookings b
JOIN users           u  ON u.user_id      = b.user_id
JOIN rooms           r  ON r.room_id      = b.room_id
JOIN room_categories rc ON rc.category_id = r.category_id
WHERE  b.status IN ('confirmed', 'checked_in')
   AND b.check_out >= CURRENT_DATE;

COMMENT ON VIEW v_active_bookings IS
    'Действующие бронирования (для рабочей панели менеджера ресепшена).';

\echo '<<< 04_views.sql ok'
