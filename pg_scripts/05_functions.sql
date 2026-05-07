-- =============================================================================
-- 05_functions.sql
-- Скалярные и табличные функции PostgreSQL
-- =============================================================================

-- 1. Проверка свободен ли номер на заданный период
CREATE OR REPLACE FUNCTION fn_room_is_free(
    p_room_id INTEGER,
    p_check_in DATE,
    p_check_out DATE,
    p_exclude_booking_id INTEGER DEFAULT NULL
) RETURNS BOOLEAN
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN NOT EXISTS (
        SELECT 1
        FROM bookings b
        WHERE b.room_id = p_room_id
          AND b.status NOT IN ('cancelled', 'checked_out')
          AND daterange(b.check_in_date, b.check_out_date, '[)') &&
              daterange(p_check_in, p_check_out, '[)')
          AND (p_exclude_booking_id IS NULL OR b.id != p_exclude_booking_id)
    );
END;
$$;

COMMENT ON FUNCTION fn_room_is_free IS
'Проверяет, свободен ли номер на заданный диапазон дат. Использует GiST-индекс по daterange.
Параметр p_exclude_booking_id позволяет исключить текущее бронирование при редактировании.';

-- 2. Расчёт итоговой стоимости бронирования
CREATE OR REPLACE FUNCTION fn_calculate_booking_total(
    p_booking_id INTEGER
) RETURNS NUMERIC(12, 2)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_room_price   NUMERIC(12, 2);
    v_nights       INTEGER;
    v_services     NUMERIC(12, 2);
    v_total        NUMERIC(12, 2);
BEGIN
    SELECT rc.base_price, (b.check_out_date - b.check_in_date)
    INTO v_room_price, v_nights
    FROM bookings b
    JOIN rooms r ON r.id = b.room_id
    JOIN room_categories rc ON rc.id = r.category_id
    WHERE b.id = p_booking_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Бронирование с id=% не найдено', p_booking_id;
    END IF;

    SELECT COALESCE(SUM(bs.quantity * bs.price_at_booking), 0)
    INTO v_services
    FROM booking_services bs
    WHERE bs.booking_id = p_booking_id;

    v_total := v_room_price * v_nights + v_services;
    RETURN v_total;
END;
$$;

COMMENT ON FUNCTION fn_calculate_booking_total IS
'Рассчитывает итоговую стоимость бронирования: цена номера × количество ночей + доп. услуги';

-- 3. Коэффициент загрузки номерного фонда за период
CREATE OR REPLACE FUNCTION fn_occupancy_rate(
    p_start_date DATE,
    p_end_date DATE,
    p_category_id INTEGER DEFAULT NULL
) RETURNS NUMERIC(5, 2)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_total_room_days  INTEGER;
    v_booked_days      INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_total_room_days
    FROM rooms r
    CROSS JOIN generate_series(p_start_date, p_end_date - 1, '1 day'::INTERVAL) d(dt)
    WHERE r.is_active = TRUE
      AND (p_category_id IS NULL OR r.category_id = p_category_id);

    IF v_total_room_days = 0 THEN
        RETURN 0;
    END IF;

    SELECT COUNT(*)
    INTO v_booked_days
    FROM rooms r
    CROSS JOIN generate_series(p_start_date, p_end_date - 1, '1 day'::INTERVAL) d(dt)
    WHERE r.is_active = TRUE
      AND (p_category_id IS NULL OR r.category_id = p_category_id)
      AND EXISTS (
          SELECT 1 FROM bookings b
          WHERE b.room_id = r.id
            AND b.status IN ('confirmed', 'checked_in', 'checked_out')
            AND d.dt::DATE >= b.check_in_date
            AND d.dt::DATE < b.check_out_date
      );

    RETURN ROUND(v_booked_days * 100.0 / v_total_room_days, 2);
END;
$$;

COMMENT ON FUNCTION fn_occupancy_rate IS
'Рассчитывает процент загрузки номерного фонда за указанный период.
Опциональный параметр p_category_id позволяет фильтровать по категории номеров.';
