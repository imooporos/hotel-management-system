-- =============================================================================
-- 06_procedures.sql
-- Хранимые процедуры для CRUD-операций и бизнес-логики
-- =============================================================================

-- 1. Регистрация нового пользователя (INSERT)
CREATE OR REPLACE PROCEDURE sp_register_user(
    p_email       VARCHAR,
    p_password_hash VARCHAR,
    p_first_name  VARCHAR,
    p_last_name   VARCHAR,
    p_phone       VARCHAR DEFAULT NULL,
    p_role        VARCHAR DEFAULT 'guest',
    INOUT p_user_id INTEGER DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO users (email, password_hash, role)
    VALUES (p_email, p_password_hash, p_role)
    RETURNING id INTO p_user_id;

    INSERT INTO guest_profiles (user_id, first_name, last_name, phone)
    VALUES (p_user_id, p_first_name, p_last_name, p_phone);
END;
$$;

COMMENT ON PROCEDURE sp_register_user IS
'Регистрация нового пользователя: создаёт запись в users и guest_profiles в одной транзакции';

-- 2. Создание бронирования (INSERT + расчёт)
CREATE OR REPLACE PROCEDURE sp_create_booking(
    p_guest_id    INTEGER,
    p_room_id     INTEGER,
    p_check_in    DATE,
    p_check_out   DATE,
    p_guests_count INTEGER DEFAULT 1,
    p_notes       TEXT DEFAULT NULL,
    INOUT p_booking_id INTEGER DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_room_price NUMERIC(12, 2);
    v_nights     INTEGER;
BEGIN
    IF NOT fn_room_is_free(p_room_id, p_check_in, p_check_out) THEN
        RAISE EXCEPTION 'Номер занят на выбранные даты (% — %)', p_check_in, p_check_out;
    END IF;

    SELECT rc.base_price
    INTO v_room_price
    FROM rooms r
    JOIN room_categories rc ON rc.id = r.category_id
    WHERE r.id = p_room_id;

    v_nights := p_check_out - p_check_in;

    INSERT INTO bookings (guest_id, room_id, check_in_date, check_out_date, guests_count, total_amount, notes)
    VALUES (p_guest_id, p_room_id, p_check_in, p_check_out, p_guests_count, v_room_price * v_nights, p_notes)
    RETURNING id INTO p_booking_id;
END;
$$;

COMMENT ON PROCEDURE sp_create_booking IS
'Создание бронирования с проверкой доступности номера и расчётом стоимости';

-- 3. Обновление статуса бронирования (UPDATE)
CREATE OR REPLACE PROCEDURE sp_update_booking_status(
    p_booking_id  INTEGER,
    p_new_status  VARCHAR,
    p_changed_by  VARCHAR DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_current_status booking_status;
BEGIN
    SELECT status INTO v_current_status
    FROM bookings WHERE id = p_booking_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Бронирование с id=% не найдено', p_booking_id;
    END IF;

    -- Проверяем допустимые переходы статусов
    IF v_current_status = 'cancelled' THEN
        RAISE EXCEPTION 'Невозможно изменить статус отменённого бронирования';
    END IF;

    IF v_current_status = 'checked_out' AND p_new_status != 'cancelled' THEN
        RAISE EXCEPTION 'Гость уже выехал, допустима только отмена';
    END IF;

    UPDATE bookings
    SET status = p_new_status::booking_status,
        updated_at = NOW()
    WHERE id = p_booking_id;
END;
$$;

COMMENT ON PROCEDURE sp_update_booking_status IS
'Обновление статуса бронирования с проверкой допустимости перехода';

-- 4. Отмена бронирования (UPDATE + бизнес-логика)
CREATE OR REPLACE PROCEDURE sp_cancel_booking(
    p_booking_id INTEGER,
    p_changed_by VARCHAR DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_status booking_status;
BEGIN
    SELECT status INTO v_status
    FROM bookings WHERE id = p_booking_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Бронирование с id=% не найдено', p_booking_id;
    END IF;

    IF v_status IN ('checked_out', 'cancelled') THEN
        RAISE EXCEPTION 'Невозможно отменить бронирование в статусе %', v_status;
    END IF;

    UPDATE bookings
    SET status = 'cancelled',
        updated_at = NOW()
    WHERE id = p_booking_id;
END;
$$;

COMMENT ON PROCEDURE sp_cancel_booking IS
'Отмена бронирования с проверкой текущего статуса';

-- 5. Получение бронирований пользователя (SELECT — обёртка для удобства)
CREATE OR REPLACE FUNCTION sp_get_user_bookings(
    p_user_id INTEGER,
    p_status  VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    booking_id     INTEGER,
    room_number    VARCHAR,
    category_name  VARCHAR,
    check_in_date  DATE,
    check_out_date DATE,
    nights         INTEGER,
    status         booking_status,
    total_amount   NUMERIC,
    guests_count   INTEGER,
    booked_at      TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        b.id,
        r.room_number,
        rc.name,
        b.check_in_date,
        b.check_out_date,
        (b.check_out_date - b.check_in_date),
        b.status,
        b.total_amount,
        b.guests_count,
        b.created_at
    FROM bookings b
    JOIN rooms r ON r.id = b.room_id
    JOIN room_categories rc ON rc.id = r.category_id
    WHERE b.guest_id = p_user_id
      AND (p_status IS NULL OR b.status = p_status::booking_status)
    ORDER BY b.created_at DESC;
END;
$$;

COMMENT ON FUNCTION sp_get_user_bookings IS
'Возвращает список бронирований пользователя с возможностью фильтрации по статусу';
