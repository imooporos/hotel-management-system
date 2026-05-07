-- ============================================================================
--  05_functions.sql
--  Скалярные и табличные функции.
-- ============================================================================

\echo '>>> applying 05_functions.sql'

DROP FUNCTION IF EXISTS fn_room_is_free(bigint, date, date)         CASCADE;
DROP FUNCTION IF EXISTS fn_calculate_booking_total(bigint, date, date, integer[]) CASCADE;
DROP FUNCTION IF EXISTS fn_occupancy_rate(date, date)               CASCADE;

-- ---------------------------------------------------------------------------
--  fn_room_is_free
--  Возвращает TRUE, если в указанные даты в номере нет активной брони.
--  Применяется приложением перед оформлением бронирования.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_room_is_free(
    p_room_id   bigint,
    p_check_in  date,
    p_check_out date
)
RETURNS boolean
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_overlap_count integer;
BEGIN
    IF p_check_out <= p_check_in THEN
        RAISE EXCEPTION 'Дата выезда должна быть позже даты заезда' USING ERRCODE = '22023';
    END IF;

    SELECT COUNT(*)
      INTO v_overlap_count
      FROM bookings
     WHERE room_id = p_room_id
       AND status NOT IN ('cancelled')
       AND stay_period && daterange(p_check_in, p_check_out, '[)');

    RETURN v_overlap_count = 0;
END;
$$;

COMMENT ON FUNCTION fn_room_is_free(bigint, date, date) IS
    'Проверяет, свободен ли номер в указанный диапазон дат (полуоткрытый).';

-- ---------------------------------------------------------------------------
--  fn_calculate_booking_total
--  Вычисляет полную стоимость бронирования: проживание + услуги.
--  p_service_ids — необязательный массив id допуслуг (по умолчанию NULL).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_calculate_booking_total(
    p_room_id     bigint,
    p_check_in    date,
    p_check_out   date,
    p_service_ids integer[] DEFAULT NULL
)
RETURNS positive_money
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_nights         integer;
    v_price_per_night positive_money;
    v_room_total     positive_money;
    v_services_total positive_money := 0;
BEGIN
    v_nights := p_check_out - p_check_in;
    IF v_nights <= 0 THEN
        RAISE EXCEPTION 'Период проживания должен быть положительным' USING ERRCODE = '22023';
    END IF;

    SELECT (rc.base_price + r.price_modifier)::positive_money
      INTO v_price_per_night
      FROM rooms r
      JOIN room_categories rc ON rc.category_id = r.category_id
     WHERE r.room_id = p_room_id;

    IF v_price_per_night IS NULL THEN
        RAISE EXCEPTION 'Номер с id % не найден', p_room_id USING ERRCODE = 'NOROW';
    END IF;

    v_room_total := (v_price_per_night * v_nights)::positive_money;

    IF p_service_ids IS NOT NULL AND array_length(p_service_ids, 1) > 0 THEN
        SELECT COALESCE(SUM(price), 0)::positive_money
          INTO v_services_total
          FROM services
         WHERE service_id = ANY (p_service_ids)
           AND is_active;
    END IF;

    RETURN (v_room_total + v_services_total)::positive_money;
END;
$$;

COMMENT ON FUNCTION fn_calculate_booking_total(bigint, date, date, integer[]) IS
    'Считает стоимость бронирования с учётом ночёвок и допуслуг.';

-- ---------------------------------------------------------------------------
--  fn_occupancy_rate
--  Возвращает коэффициент загрузки номерного фонда за период (0..1).
--  Применяется в отчёте «Загрузка номерного фонда» (admin).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_occupancy_rate(
    p_date_from date,
    p_date_to   date
)
RETURNS numeric(5, 4)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_total_room_nights numeric;
    v_used_room_nights  numeric;
    v_period_days       integer;
BEGIN
    IF p_date_to <= p_date_from THEN
        RAISE EXCEPTION 'Период должен быть положительным' USING ERRCODE = '22023';
    END IF;

    v_period_days := p_date_to - p_date_from;

    SELECT COUNT(*) * v_period_days
      INTO v_total_room_nights
      FROM rooms
     WHERE is_active;

    IF v_total_room_nights IS NULL OR v_total_room_nights = 0 THEN
        RETURN 0::numeric(5, 4);
    END IF;

    SELECT COALESCE(SUM(
              -- ночёвок в пересечении периода брони и запрашиваемого периода
              GREATEST(0,
                  LEAST(b.check_out, p_date_to) - GREATEST(b.check_in, p_date_from)
              )
           ), 0)
      INTO v_used_room_nights
      FROM bookings b
     WHERE b.status IN ('confirmed', 'checked_in', 'checked_out')
       AND b.check_in  <  p_date_to
       AND b.check_out >  p_date_from;

    RETURN ROUND((v_used_room_nights / v_total_room_nights)::numeric, 4);
END;
$$;

COMMENT ON FUNCTION fn_occupancy_rate(date, date) IS
    'Доля занятых ночёвок к общему числу ночёвок в период.';

\echo '<<< 05_functions.sql ok'
