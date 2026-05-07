-- ============================================================================
--  07_triggers.sql
--  Триггеры: бизнес-логика бронирования, аудит изменений, синхронизация
--  статуса номера, автообновление updated_at.
-- ============================================================================

\echo '>>> applying 07_triggers.sql'

-- ---------------------------------------------------------------------------
--  trg_set_updated_at — универсальный триггер обновления updated_at
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_trg_set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_users_updated_at    ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION fn_trg_set_updated_at();

DROP TRIGGER IF EXISTS trg_bookings_updated_at ON bookings;
CREATE TRIGGER trg_bookings_updated_at
    BEFORE UPDATE ON bookings
    FOR EACH ROW EXECUTE FUNCTION fn_trg_set_updated_at();

-- ---------------------------------------------------------------------------
--  trg_no_overlap_booking
--  Дополнительный страховочный триггер: дублирует EXCLUDE-ограничение,
--  но даёт человеко-понятное сообщение об ошибке. Срабатывает при
--  INSERT и UPDATE дат/статуса.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_trg_no_overlap_booking()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_conflict bigint;
BEGIN
    IF NEW.status = 'cancelled' THEN
        RETURN NEW;
    END IF;

    SELECT booking_id
      INTO v_conflict
      FROM bookings
     WHERE room_id = NEW.room_id
       AND booking_id <> COALESCE(NEW.booking_id, -1)
       AND status NOT IN ('cancelled')
       AND stay_period && daterange(NEW.check_in, NEW.check_out, '[)')
     LIMIT 1;

    IF v_conflict IS NOT NULL THEN
        RAISE EXCEPTION
              'Номер уже забронирован на эти даты (конфликт с бронью %).', v_conflict
            USING ERRCODE = 'P0001';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_no_overlap_booking ON bookings;
CREATE TRIGGER trg_no_overlap_booking
    BEFORE INSERT OR UPDATE OF check_in, check_out, room_id, status
    ON bookings
    FOR EACH ROW
    EXECUTE FUNCTION fn_trg_no_overlap_booking();

-- ---------------------------------------------------------------------------
--  trg_update_room_status
--  Автоматически синхронизирует rooms.status при смене статуса бронирования.
--   - confirmed  → reserved
--   - checked_in → occupied
--   - checked_out| cancelled → cleaning (если других активных броней нет → available)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_trg_update_room_status()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_other_active integer;
BEGIN
    IF (TG_OP = 'INSERT' AND NEW.status IN ('confirmed', 'checked_in'))
       OR (TG_OP = 'UPDATE' AND NEW.status IS DISTINCT FROM OLD.status) THEN

        IF NEW.status = 'confirmed' THEN
            UPDATE rooms SET status = 'reserved'  WHERE room_id = NEW.room_id;
        ELSIF NEW.status = 'checked_in' THEN
            UPDATE rooms SET status = 'occupied'  WHERE room_id = NEW.room_id;
        ELSIF NEW.status IN ('checked_out', 'cancelled') THEN
            -- проверяем, остались ли активные брони у номера
            SELECT COUNT(*)
              INTO v_other_active
              FROM bookings b
             WHERE b.room_id = NEW.room_id
               AND b.booking_id <> NEW.booking_id
               AND b.status IN ('confirmed', 'checked_in')
               AND b.check_out >= CURRENT_DATE;

            IF v_other_active = 0 THEN
                UPDATE rooms
                   SET status = CASE WHEN NEW.status = 'checked_out'
                                     THEN 'cleaning'::room_status
                                     ELSE 'available'::room_status
                                END
                 WHERE room_id = NEW.room_id;
            END IF;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_update_room_status ON bookings;
CREATE TRIGGER trg_update_room_status
    AFTER INSERT OR UPDATE OF status ON bookings
    FOR EACH ROW
    EXECUTE FUNCTION fn_trg_update_room_status();

-- ---------------------------------------------------------------------------
--  trg_audit_bookings
--  Универсальный аудит изменений критичных таблиц.
--  Используется для bookings, users, rooms.
--  actor_id берётся из настройки сессии app.actor_id (которую устанавливает API).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_trg_audit()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_actor_id   bigint;
    v_actor_name varchar(128);
    v_pk         text;
BEGIN
    BEGIN
        v_actor_id := NULLIF(current_setting('app.actor_id', true), '')::bigint;
    EXCEPTION WHEN others THEN
        v_actor_id := NULL;
    END;

    IF v_actor_id IS NOT NULL THEN
        SELECT full_name INTO v_actor_name FROM users WHERE user_id = v_actor_id;
    END IF;

    -- определяем PK строки в зависимости от таблицы
    IF TG_TABLE_NAME = 'bookings' THEN
        v_pk := COALESCE(NEW.booking_id, OLD.booking_id)::text;
    ELSIF TG_TABLE_NAME = 'users' THEN
        v_pk := COALESCE(NEW.user_id, OLD.user_id)::text;
    ELSIF TG_TABLE_NAME = 'rooms' THEN
        v_pk := COALESCE(NEW.room_id, OLD.room_id)::text;
    ELSE
        v_pk := '';
    END IF;

    INSERT INTO audit_log (table_name, row_pk, action, actor_id, actor_name, old_data, new_data)
    VALUES (
        TG_TABLE_NAME,
        v_pk,
        TG_OP::audit_action,
        v_actor_id,
        v_actor_name,
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) ELSE NULL END,
        CASE WHEN TG_OP IN ('UPDATE', 'INSERT') THEN to_jsonb(NEW) ELSE NULL END
    );

    RETURN COALESCE(NEW, OLD);
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_bookings ON bookings;
CREATE TRIGGER trg_audit_bookings
    AFTER INSERT OR UPDATE OR DELETE ON bookings
    FOR EACH ROW EXECUTE FUNCTION fn_trg_audit();

DROP TRIGGER IF EXISTS trg_audit_users ON users;
CREATE TRIGGER trg_audit_users
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION fn_trg_audit();

DROP TRIGGER IF EXISTS trg_audit_rooms ON rooms;
CREATE TRIGGER trg_audit_rooms
    AFTER INSERT OR UPDATE OR DELETE ON rooms
    FOR EACH ROW EXECUTE FUNCTION fn_trg_audit();

\echo '<<< 07_triggers.sql ok'
