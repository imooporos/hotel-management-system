-- ============================================================================
--  06_procedures.sql
--  Хранимые процедуры: регистрация пользователя, бронирование,
--  смена статуса, отмена, выборка броней.
-- ============================================================================

\echo '>>> applying 06_procedures.sql'

DROP PROCEDURE IF EXISTS sp_register_user(varchar, varchar, varchar, varchar, varchar) CASCADE;
DROP PROCEDURE IF EXISTS sp_create_booking(bigint, bigint, date, date, smallint, integer[], OUT bigint, OUT positive_money) CASCADE;
DROP PROCEDURE IF EXISTS sp_update_booking_status(bigint, booking_status, bigint) CASCADE;
DROP PROCEDURE IF EXISTS sp_cancel_booking(bigint, bigint) CASCADE;
DROP FUNCTION  IF EXISTS sp_get_user_bookings(bigint) CASCADE;

-- ---------------------------------------------------------------------------
--  sp_register_user
--  Регистрирует нового пользователя с ролью «guest» и опциональным профилем.
--  password_hash должен быть уже посчитан приложением (bcrypt).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_register_user(
    p_email         varchar,
    p_password_hash varchar,
    p_full_name     varchar,
    p_phone         varchar,
    p_role_code     varchar DEFAULT 'guest'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_role_id  smallint;
    v_user_id  bigint;
BEGIN
    SELECT role_id INTO v_role_id FROM roles WHERE code = p_role_code;
    IF v_role_id IS NULL THEN
        RAISE EXCEPTION 'Неизвестная роль: %', p_role_code USING ERRCODE = '23514';
    END IF;

    INSERT INTO users (email, password_hash, full_name, phone, role_id)
    VALUES (p_email, p_password_hash, p_full_name, NULLIF(p_phone, ''), v_role_id)
    RETURNING user_id INTO v_user_id;

    -- guest_profile создаётся «пустой», поля можно заполнить позже
    IF p_role_code = 'guest' THEN
        INSERT INTO guest_profiles (user_id) VALUES (v_user_id);
    END IF;
END;
$$;

COMMENT ON PROCEDURE sp_register_user(varchar, varchar, varchar, varchar, varchar) IS
    'Регистрирует пользователя. password_hash принимает bcrypt-хэш, плейн-пароль не передаётся.';

-- ---------------------------------------------------------------------------
--  sp_create_booking
--  Создаёт бронирование, проверяет свободу номера, фиксирует цены услуг,
--  возвращает booking_id и итоговую сумму.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_create_booking(
    p_user_id      bigint,
    p_room_id      bigint,
    p_check_in     date,
    p_check_out    date,
    p_guests_count smallint,
    p_service_ids  integer[],
    OUT  out_booking_id  bigint,
    OUT  out_total_price positive_money
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total positive_money;
    v_room_capacity smallint;
BEGIN
    IF NOT fn_room_is_free(p_room_id, p_check_in, p_check_out) THEN
        RAISE EXCEPTION 'Номер занят на указанные даты' USING ERRCODE = 'P0001';
    END IF;

    SELECT rc.capacity INTO v_room_capacity
      FROM rooms r
      JOIN room_categories rc ON rc.category_id = r.category_id
     WHERE r.room_id = p_room_id;

    IF p_guests_count > v_room_capacity THEN
        RAISE EXCEPTION 'В номере не более % гостей', v_room_capacity USING ERRCODE = '23514';
    END IF;

    v_total := fn_calculate_booking_total(p_room_id, p_check_in, p_check_out, p_service_ids);

    INSERT INTO bookings (user_id, room_id, check_in, check_out, guests_count, total_price)
    VALUES (p_user_id, p_room_id, p_check_in, p_check_out, p_guests_count, v_total)
    RETURNING booking_id INTO out_booking_id;

    IF p_service_ids IS NOT NULL THEN
        INSERT INTO booking_services (booking_id, service_id, quantity, unit_price)
        SELECT out_booking_id, s.service_id, 1, s.price
          FROM services s
         WHERE s.service_id = ANY (p_service_ids)
           AND s.is_active;
    END IF;

    out_total_price := v_total;
END;
$$;

COMMENT ON PROCEDURE sp_create_booking(bigint, bigint, date, date, smallint, integer[], OUT bigint, OUT positive_money) IS
    'Создаёт бронирование с допуслугами. Возвращает booking_id и итоговую цену.';

-- ---------------------------------------------------------------------------
--  sp_update_booking_status
--  Меняет статус бронирования с проверкой допустимых переходов.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_update_booking_status(
    p_booking_id bigint,
    p_new_status booking_status,
    p_actor_id   bigint DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_current booking_status;
BEGIN
    SELECT status INTO v_current FROM bookings WHERE booking_id = p_booking_id FOR UPDATE;
    IF v_current IS NULL THEN
        RAISE EXCEPTION 'Бронирование % не найдено', p_booking_id USING ERRCODE = 'NOROW';
    END IF;

    -- допустимые переходы
    IF NOT (
            (v_current = 'pending'    AND p_new_status IN ('confirmed', 'cancelled'))
         OR (v_current = 'confirmed'  AND p_new_status IN ('checked_in', 'cancelled'))
         OR (v_current = 'checked_in' AND p_new_status = 'checked_out')
         OR (v_current = p_new_status)  -- идемпотентность
    ) THEN
        RAISE EXCEPTION 'Недопустимый переход статуса: % -> %', v_current, p_new_status
              USING ERRCODE = '23514';
    END IF;

    UPDATE bookings
       SET status     = p_new_status,
           updated_at = now()
     WHERE booking_id = p_booking_id;

    -- метка «кто менял» уйдёт в audit_log через триггер; но если хотим
    -- сохранить actor отдельно — можно записать через PERFORM set_config().
    PERFORM set_config('app.actor_id',
                       COALESCE(p_actor_id::text, ''),
                       true);
END;
$$;

COMMENT ON PROCEDURE sp_update_booking_status(bigint, booking_status, bigint) IS
    'Меняет статус брони с проверкой допустимых переходов.';

-- ---------------------------------------------------------------------------
--  sp_cancel_booking
--  Отдельная процедура для отмены — удобнее проверять права на стороне API.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_cancel_booking(
    p_booking_id bigint,
    p_actor_id   bigint
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM set_config('app.actor_id', p_actor_id::text, true);
    CALL sp_update_booking_status(p_booking_id, 'cancelled'::booking_status, p_actor_id);
END;
$$;

COMMENT ON PROCEDURE sp_cancel_booking(bigint, bigint) IS
    'Помечает бронирование как cancelled.';

-- ---------------------------------------------------------------------------
--  sp_get_user_bookings — табличная функция, удобна для FastAPI.
--  Возвращает строки v_guest_bookings, отфильтрованные по user_id.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION sp_get_user_bookings(p_user_id bigint)
RETURNS TABLE (
    booking_id     bigint,
    room_number    varchar,
    category_title varchar,
    check_in       date,
    check_out      date,
    nights         integer,
    guests_count   smallint,
    status         booking_status,
    total_price    positive_money,
    paid_total     positive_money,
    amount_due     positive_money
)
LANGUAGE sql
STABLE
AS $$
    SELECT booking_id, room_number, category_title, check_in, check_out,
           nights, guests_count, status, total_price, paid_total, amount_due
      FROM v_guest_bookings
     WHERE user_id = p_user_id
     ORDER BY check_in DESC;
$$;

COMMENT ON FUNCTION sp_get_user_bookings(bigint) IS
    'Возвращает бронирования конкретного пользователя.';

\echo '<<< 06_procedures.sql ok'
