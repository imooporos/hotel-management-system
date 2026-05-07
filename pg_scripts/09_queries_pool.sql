-- ============================================================================
--  09_queries_pool.sql
--  Демонстрация 12 типов запросов из пула задания.
--  Скрипт безопасен для повторного запуска (только SELECT).
--  Каждый запрос предварён комментарием с номером и кратким описанием.
-- ============================================================================

\echo '>>> applying 09_queries_pool.sql (read-only demo)'

-- 1. Простые запросы с условием: операторы сравнения, AND/OR, LIKE/ILIKE,
--    SIMILAR TO, BETWEEN, IN
SELECT room_id, room_number, floor, status
  FROM rooms
 WHERE floor BETWEEN 2 AND 4
   AND status IN ('available', 'cleaning')
   AND room_number ILIKE '2%'
 ORDER BY room_number;

-- 2. Скалярный подзапрос — после WHERE / SELECT / HAVING
SELECT b.booking_id, b.total_price,
       (SELECT AVG(total_price)
          FROM bookings
         WHERE status NOT IN ('cancelled')) AS avg_total
  FROM bookings b
 WHERE b.total_price > (SELECT AVG(total_price)
                          FROM bookings
                         WHERE status NOT IN ('cancelled'))
 ORDER BY b.total_price DESC;

-- 3. Табличные подзапросы — после FROM / WHERE / HAVING
SELECT cat.title, stats.avg_price, stats.rooms_n
  FROM room_categories cat
  JOIN (
        SELECT rc.category_id,
               AVG(rc.base_price + r.price_modifier) AS avg_price,
               COUNT(*)                              AS rooms_n
          FROM rooms r
          JOIN room_categories rc ON rc.category_id = r.category_id
         GROUP BY rc.category_id
       ) stats ON stats.category_id = cat.category_id
 ORDER BY stats.avg_price DESC;

-- 4. Подзапросы с кванторами EXISTS / ALL
--    EXISTS: пользователи, у которых есть хотя бы одно подтверждённое бронирование
SELECT u.user_id, u.full_name
  FROM users u
 WHERE EXISTS (
       SELECT 1 FROM bookings b
        WHERE b.user_id = u.user_id
          AND b.status IN ('confirmed', 'checked_in', 'checked_out')
       );

--    ALL: номер, цена которого больше или равна всем остальным
SELECT room_id, room_number, (rc.base_price + r.price_modifier) AS price_per_night
  FROM rooms r
  JOIN room_categories rc ON rc.category_id = r.category_id
 WHERE (rc.base_price + r.price_modifier) >= ALL (
        SELECT (rc2.base_price + r2.price_modifier)
          FROM rooms r2
          JOIN room_categories rc2 ON rc2.category_id = r2.category_id
       )
 LIMIT 1;

-- 5. Множественные операции — UNION, INTERSECT, EXCEPT
--    Все «занятые» номера (UNION) — заселены сейчас или зарезервированы
(
 SELECT room_id FROM rooms WHERE status = 'occupied'
)
UNION
(
 SELECT room_id FROM rooms WHERE status = 'reserved'
);

--    INTERSECT: гости, у которых были и активные, и отменённые брони
(SELECT user_id FROM bookings WHERE status IN ('confirmed', 'checked_in', 'checked_out'))
INTERSECT
(SELECT user_id FROM bookings WHERE status = 'cancelled');

--    EXCEPT: номера, которые НИКОГДА не бронировались
(SELECT room_id FROM rooms)
EXCEPT
(SELECT room_id FROM bookings);

-- 6. Запрос с CTE (WITH)
WITH category_rev AS (
    SELECT rc.category_id, rc.title,
           SUM(b.total_price) FILTER (WHERE b.status <> 'cancelled') AS revenue
      FROM room_categories rc
      JOIN rooms     r ON r.category_id = rc.category_id
      LEFT JOIN bookings  b ON b.room_id = r.room_id
     GROUP BY rc.category_id, rc.title
)
SELECT title, revenue
  FROM category_rev
 WHERE revenue IS NOT NULL
 ORDER BY revenue DESC;

-- 7. Агрегатные функции, GROUP BY, HAVING
SELECT u.user_id, u.full_name,
       COUNT(b.booking_id)             AS bookings_total,
       SUM(b.total_price)              AS revenue_total,
       AVG(b.check_out - b.check_in)   AS avg_nights
  FROM users u
  JOIN bookings b ON b.user_id = u.user_id
 GROUP BY u.user_id, u.full_name
HAVING SUM(b.total_price) > 0
 ORDER BY revenue_total DESC;

-- 8. Многотабличный запрос (4+ таблицы)
SELECT b.booking_id,
       u.full_name           AS guest,
       r.room_number,
       rc.title              AS category,
       b.check_in, b.check_out, b.total_price,
       string_agg(s.title, ', ' ORDER BY s.title) AS services
  FROM bookings           b
  JOIN users              u  ON u.user_id      = b.user_id
  JOIN rooms              r  ON r.room_id      = b.room_id
  JOIN room_categories    rc ON rc.category_id = r.category_id
  LEFT JOIN booking_services bs ON bs.booking_id = b.booking_id
  LEFT JOIN services         s  ON s.service_id  = bs.service_id
 GROUP BY b.booking_id, u.full_name, r.room_number, rc.title;

-- 9. Функции работы со строками, датами, преобразования
SELECT u.user_id,
       upper(u.full_name)                                 AS name_upper,
       to_char(b.created_at, 'DD.MM.YYYY HH24:MI')        AS created_at_fmt,
       length(u.full_name)                                AS name_len,
       extract(year from b.check_in)::int                 AS year_in,
       (b.check_out - b.check_in)                         AS nights,
       split_part(u.email, '@', 2)                        AS email_domain
  FROM users u
  JOIN bookings b ON b.user_id = u.user_id
 ORDER BY b.created_at DESC;

-- 10. Рекурсивный подзапрос (демонстрация на категориях, которые могут иметь parent_id)
--     Здесь демонстрируем «номер по соседству» через generate_series + соединение.
WITH RECURSIVE neighbour_chain(start_room, current_room, depth) AS (
    SELECT room_id, room_id, 0
      FROM rooms
     WHERE room_number = '101'
    UNION ALL
    SELECT nc.start_room, r.room_id, nc.depth + 1
      FROM neighbour_chain nc
      JOIN rooms r ON r.floor = (SELECT floor FROM rooms WHERE room_id = nc.current_room)
                 AND r.room_id <> nc.current_room
                 AND r.room_id  > nc.current_room
     WHERE nc.depth < 3
)
SELECT * FROM neighbour_chain;

-- 11. Перекрёстный (сводный) запрос. PostgreSQL: tablefunc.crosstab требует расширения,
--     поэтому используем эквивалент через FILTER + SUM по столбцам.
SELECT extract(year from check_in)::int AS year_in,
       SUM(total_price) FILTER (WHERE extract(month from check_in) = 1)  AS jan,
       SUM(total_price) FILTER (WHERE extract(month from check_in) = 2)  AS feb,
       SUM(total_price) FILTER (WHERE extract(month from check_in) = 3)  AS mar,
       SUM(total_price) FILTER (WHERE extract(month from check_in) = 4)  AS apr,
       SUM(total_price) FILTER (WHERE extract(month from check_in) = 5)  AS may,
       SUM(total_price) FILTER (WHERE extract(month from check_in) = 6)  AS jun,
       SUM(total_price) FILTER (WHERE extract(month from check_in) = 7)  AS jul,
       SUM(total_price) FILTER (WHERE extract(month from check_in) = 8)  AS aug,
       SUM(total_price) FILTER (WHERE extract(month from check_in) = 9)  AS sep,
       SUM(total_price) FILTER (WHERE extract(month from check_in) = 10) AS oct,
       SUM(total_price) FILTER (WHERE extract(month from check_in) = 11) AS nov,
       SUM(total_price) FILTER (WHERE extract(month from check_in) = 12) AS dec
  FROM bookings
 WHERE status <> 'cancelled'
 GROUP BY 1
 ORDER BY 1;

-- 12. Оконные функции — рейтинг гостей по выручке, скользящая сумма
SELECT u.full_name,
       b.booking_id,
       b.total_price,
       SUM(b.total_price) OVER (PARTITION BY u.user_id ORDER BY b.created_at)
                                                AS running_total,
       RANK() OVER (ORDER BY b.total_price DESC)
                                                AS rank_by_price,
       LAG(b.total_price)  OVER (PARTITION BY u.user_id ORDER BY b.created_at)
                                                AS prev_booking_price
  FROM bookings b
  JOIN users u ON u.user_id = b.user_id
 WHERE b.status <> 'cancelled'
 ORDER BY u.full_name, b.created_at;

\echo '<<< 09_queries_pool.sql ok'
