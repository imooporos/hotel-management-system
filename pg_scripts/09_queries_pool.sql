-- =============================================================================
-- 09_queries_pool.sql
-- 12 типов SQL-запросов из пула требований курсового проекта
-- Каждый запрос пронумерован и снабжён комментарием
-- =============================================================================

-- ──────────────────────────────────────────────────────────────────────────────
-- 1. Простые запросы с условием (операторы сравнения, AND, OR, LIKE, SIMILAR TO, BETWEEN, IN)
-- ──────────────────────────────────────────────────────────────────────────────

-- 1a. Свободные номера на этажах 1–3 с ценой от 3000 до 9000
SELECT r.room_number, rc.name AS category, rc.base_price, r.floor
FROM rooms r
JOIN room_categories rc ON rc.id = r.category_id
WHERE r.status = 'available'
  AND r.floor BETWEEN 1 AND 3
  AND rc.base_price BETWEEN 3000 AND 9000
ORDER BY rc.base_price;

-- 1b. Гости, чья фамилия начинается на «И» или «П»
SELECT gp.first_name, gp.last_name, u.email
FROM guest_profiles gp
JOIN users u ON u.id = gp.user_id
WHERE gp.last_name LIKE 'И%' OR gp.last_name LIKE 'П%';

-- 1c. Услуги дешевле 2000 или связанные с трансфером
SELECT name, price
FROM services
WHERE price < 2000 OR name SIMILAR TO '%(Т|т)рансфер%'
ORDER BY price;

-- 1d. Бронирования в определённых статусах
SELECT id, guest_id, room_id, status, total_amount
FROM bookings
WHERE status IN ('confirmed', 'checked_in')
  AND total_amount > 10000;

-- ──────────────────────────────────────────────────────────────────────────────
-- 2. Подзапросы скалярные (после WHERE, SELECT, HAVING)
-- ──────────────────────────────────────────────────────────────────────────────

-- 2a. Номера, цена которых выше средней по всем категориям
SELECT r.room_number, rc.name, rc.base_price
FROM rooms r
JOIN room_categories rc ON rc.id = r.category_id
WHERE rc.base_price > (SELECT AVG(base_price) FROM room_categories);

-- 2b. Имя гостя и количество его бронирований в SELECT
SELECT
    gp.first_name || ' ' || gp.last_name AS guest,
    (SELECT COUNT(*) FROM bookings b WHERE b.guest_id = u.id) AS bookings_count
FROM users u
JOIN guest_profiles gp ON gp.user_id = u.id
WHERE u.role = 'guest';

-- ──────────────────────────────────────────────────────────────────────────────
-- 3. Подзапросы табличные (после FROM, WHERE, HAVING)
-- ──────────────────────────────────────────────────────────────────────────────

-- Топ-3 самых дорогих бронирования с информацией о госте
SELECT t.guest_name, t.room_number, t.total_amount
FROM (
    SELECT
        gp.first_name || ' ' || gp.last_name AS guest_name,
        r.room_number,
        b.total_amount,
        ROW_NUMBER() OVER (ORDER BY b.total_amount DESC) AS rn
    FROM bookings b
    JOIN users u ON u.id = b.guest_id
    JOIN guest_profiles gp ON gp.user_id = u.id
    JOIN rooms r ON r.id = b.room_id
    WHERE b.status != 'cancelled'
) t
WHERE t.rn <= 3;

-- ──────────────────────────────────────────────────────────────────────────────
-- 4. Подзапросы с кванторами (EXISTS, ALL)
-- ──────────────────────────────────────────────────────────────────────────────

-- 4a. Гости, у которых есть хотя бы одно подтверждённое бронирование (EXISTS)
SELECT gp.first_name, gp.last_name, u.email
FROM users u
JOIN guest_profiles gp ON gp.user_id = u.id
WHERE EXISTS (
    SELECT 1 FROM bookings b
    WHERE b.guest_id = u.id AND b.status = 'confirmed'
);

-- 4b. Категория с ценой выше всех стандартных (ALL)
SELECT rc.name, rc.base_price
FROM room_categories rc
WHERE rc.base_price > ALL (
    SELECT rc2.base_price FROM room_categories rc2 WHERE rc2.name = 'Стандарт'
);

-- ──────────────────────────────────────────────────────────────────────────────
-- 5. Запросы с множественными операциями (UNION, INTERSECT, EXCEPT)
-- ──────────────────────────────────────────────────────────────────────────────

-- Все активные пользователи (гости с бронированиями UNION менеджеры)
SELECT u.email, u.role, 'Имеет бронирования' AS info
FROM users u
WHERE u.role = 'guest' AND EXISTS (SELECT 1 FROM bookings b WHERE b.guest_id = u.id)
UNION
SELECT u.email, u.role, 'Сотрудник' AS info
FROM users u
WHERE u.role IN ('manager', 'admin')
ORDER BY role, email;

-- Гости, забронировавшие и «Стандарт», и «Комфорт» (INTERSECT)
SELECT b.guest_id
FROM bookings b JOIN rooms r ON r.id = b.room_id JOIN room_categories rc ON rc.id = r.category_id
WHERE rc.name = 'Стандарт'
INTERSECT
SELECT b.guest_id
FROM bookings b JOIN rooms r ON r.id = b.room_id JOIN room_categories rc ON rc.id = r.category_id
WHERE rc.name = 'Комфорт';

-- Номера, которые никогда не бронировались (EXCEPT)
SELECT r.id FROM rooms r
EXCEPT
SELECT DISTINCT b.room_id FROM bookings b;

-- ──────────────────────────────────────────────────────────────────────────────
-- 6. Вынесенные подзапросы WITH (CTE)
-- ──────────────────────────────────────────────────────────────────────────────

WITH booking_stats AS (
    SELECT
        guest_id,
        COUNT(*) AS cnt,
        SUM(total_amount) AS total_spent
    FROM bookings
    WHERE status != 'cancelled'
    GROUP BY guest_id
)
SELECT
    gp.first_name || ' ' || gp.last_name AS guest,
    bs.cnt AS bookings_count,
    bs.total_spent
FROM booking_stats bs
JOIN guest_profiles gp ON gp.user_id = bs.guest_id
ORDER BY bs.total_spent DESC;

-- ──────────────────────────────────────────────────────────────────────────────
-- 7. Запросы с агрегатными функциями, GROUP BY, HAVING
-- ──────────────────────────────────────────────────────────────────────────────

-- Категории, в которых суммарная выручка превышает 20000
SELECT
    rc.name AS category,
    COUNT(b.id) AS bookings_count,
    SUM(b.total_amount) AS total_revenue,
    AVG(b.total_amount) AS avg_revenue,
    MIN(b.total_amount) AS min_booking,
    MAX(b.total_amount) AS max_booking
FROM bookings b
JOIN rooms r ON r.id = b.room_id
JOIN room_categories rc ON rc.id = r.category_id
WHERE b.status != 'cancelled'
GROUP BY rc.name
HAVING SUM(b.total_amount) > 20000
ORDER BY total_revenue DESC;

-- ──────────────────────────────────────────────────────────────────────────────
-- 8. Многотабличные запросы (JOIN нескольких таблиц)
-- ──────────────────────────────────────────────────────────────────────────────

-- Полная информация о бронировании: гость, номер, категория, услуги, платежи
SELECT
    b.id AS booking_id,
    gp.first_name || ' ' || gp.last_name AS guest,
    u.email,
    r.room_number,
    rc.name AS category,
    b.check_in_date,
    b.check_out_date,
    b.status,
    b.total_amount,
    COALESCE(STRING_AGG(DISTINCT s.name, ', '), 'Нет') AS services,
    COALESCE(SUM(DISTINCT p.amount), 0) AS paid_total
FROM bookings b
JOIN users u ON u.id = b.guest_id
JOIN guest_profiles gp ON gp.user_id = u.id
JOIN rooms r ON r.id = b.room_id
JOIN room_categories rc ON rc.id = r.category_id
LEFT JOIN booking_services bs ON bs.booking_id = b.id
LEFT JOIN services s ON s.id = bs.service_id
LEFT JOIN payments p ON p.booking_id = b.id
GROUP BY b.id, gp.first_name, gp.last_name, u.email, r.room_number, rc.name
ORDER BY b.created_at DESC;

-- ──────────────────────────────────────────────────────────────────────────────
-- 9. Запросы с функциями для строк, дат, преобразования
-- ──────────────────────────────────────────────────────────────────────────────

SELECT
    UPPER(gp.last_name) AS last_name_upper,
    INITCAP(gp.first_name) AS first_name_cap,
    LENGTH(u.email) AS email_length,
    CONCAT_WS(' ', gp.last_name, gp.first_name, gp.patronymic) AS full_name,
    TO_CHAR(gp.birth_date, 'DD.MM.YYYY') AS birth_formatted,
    AGE(CURRENT_DATE, gp.birth_date) AS age,
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, gp.birth_date))::INTEGER AS age_years,
    TO_CHAR(u.created_at, 'DD Mon YYYY HH24:MI') AS registered_at
FROM guest_profiles gp
JOIN users u ON u.id = gp.user_id
ORDER BY gp.last_name;

-- ──────────────────────────────────────────────────────────────────────────────
-- 10. Рекурсивные подзапросы (WITH RECURSIVE)
-- ──────────────────────────────────────────────────────────────────────────────

-- Генерация календаря загрузки на ближайшие 30 дней
WITH RECURSIVE calendar AS (
    SELECT CURRENT_DATE AS dt
    UNION ALL
    SELECT dt + 1 FROM calendar WHERE dt < CURRENT_DATE + 29
)
SELECT
    c.dt AS date,
    (SELECT COUNT(*) FROM rooms WHERE is_active = TRUE) AS total_rooms,
    (
        SELECT COUNT(DISTINCT b.room_id)
        FROM bookings b
        WHERE b.status IN ('confirmed', 'checked_in')
          AND c.dt >= b.check_in_date
          AND c.dt < b.check_out_date
    ) AS occupied_rooms,
    ROUND(
        (SELECT COUNT(DISTINCT b.room_id)
         FROM bookings b
         WHERE b.status IN ('confirmed', 'checked_in')
           AND c.dt >= b.check_in_date AND c.dt < b.check_out_date
        ) * 100.0 /
        NULLIF((SELECT COUNT(*) FROM rooms WHERE is_active = TRUE), 0), 1
    ) AS occupancy_pct
FROM calendar c
ORDER BY c.dt;

-- ──────────────────────────────────────────────────────────────────────────────
-- 11. Запросы на построение сводных таблиц (перекрёстные запросы, CROSSTAB)
-- ──────────────────────────────────────────────────────────────────────────────

-- Количество бронирований по категориям и статусам (динамическая сводная)
SELECT
    rc.name AS category,
    COUNT(*) FILTER (WHERE b.status = 'pending')    AS pending,
    COUNT(*) FILTER (WHERE b.status = 'confirmed')  AS confirmed,
    COUNT(*) FILTER (WHERE b.status = 'checked_in') AS checked_in,
    COUNT(*) FILTER (WHERE b.status = 'checked_out') AS checked_out,
    COUNT(*) FILTER (WHERE b.status = 'cancelled')  AS cancelled,
    COUNT(*) AS total
FROM bookings b
JOIN rooms r ON r.id = b.room_id
JOIN room_categories rc ON rc.id = r.category_id
GROUP BY rc.name
ORDER BY rc.name;

-- ──────────────────────────────────────────────────────────────────────────────
-- 12. Запросы с применением оконных функций
-- ──────────────────────────────────────────────────────────────────────────────

-- Ранжирование гостей по суммарной стоимости бронирований + накопительный итог
SELECT
    gp.first_name || ' ' || gp.last_name AS guest,
    b.id AS booking_id,
    b.total_amount,
    SUM(b.total_amount) OVER (
        PARTITION BY b.guest_id ORDER BY b.created_at
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_total,
    RANK() OVER (ORDER BY b.total_amount DESC) AS amount_rank,
    DENSE_RANK() OVER (ORDER BY b.total_amount DESC) AS amount_dense_rank,
    NTILE(3) OVER (ORDER BY b.total_amount DESC) AS tercile,
    LAG(b.total_amount) OVER (PARTITION BY b.guest_id ORDER BY b.created_at) AS prev_amount,
    LEAD(b.total_amount) OVER (PARTITION BY b.guest_id ORDER BY b.created_at) AS next_amount
FROM bookings b
JOIN guest_profiles gp ON gp.user_id = b.guest_id
WHERE b.status != 'cancelled'
ORDER BY guest, b.created_at;
