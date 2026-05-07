-- =============================================================================
-- 07_triggers.sql
-- Триггеры для обеспечения бизнес-логики и аудита
-- =============================================================================

-- 1. Триггер проверки пересечения дат бронирований
CREATE OR REPLACE FUNCTION trg_fn_no_overlap_booking()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.status IN ('cancelled', 'checked_out') THEN
        RETURN NEW;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM bookings b
        WHERE b.room_id = NEW.room_id
          AND b.id != COALESCE(NEW.id, 0)
          AND b.status NOT IN ('cancelled', 'checked_out')
          AND daterange(b.check_in_date, b.check_out_date, '[)') &&
              daterange(NEW.check_in_date, NEW.check_out_date, '[)')
    ) THEN
        RAISE EXCEPTION 'Номер % занят на период % — %. Выберите другие даты.',
            (SELECT room_number FROM rooms WHERE id = NEW.room_id),
            NEW.check_in_date, NEW.check_out_date;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_no_overlap_booking
    BEFORE INSERT OR UPDATE ON bookings
    FOR EACH ROW
    EXECUTE FUNCTION trg_fn_no_overlap_booking();

COMMENT ON FUNCTION trg_fn_no_overlap_booking IS
'Не допускает пересечение дат бронирований для одного номера. Использует GiST-индекс.';

-- 2. Триггер аудита изменений бронирований
CREATE OR REPLACE FUNCTION trg_fn_audit_bookings()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, record_id, action, new_data, changed_by)
        VALUES ('bookings', NEW.id, 'INSERT', to_jsonb(NEW), current_user);
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, record_id, action, old_data, new_data, changed_by)
        VALUES ('bookings', NEW.id, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), current_user);
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, record_id, action, old_data, changed_by)
        VALUES ('bookings', OLD.id, 'DELETE', to_jsonb(OLD), current_user);
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE TRIGGER trg_audit_bookings
    AFTER INSERT OR UPDATE OR DELETE ON bookings
    FOR EACH ROW
    EXECUTE FUNCTION trg_fn_audit_bookings();

COMMENT ON FUNCTION trg_fn_audit_bookings IS
'Записывает все изменения таблицы bookings в audit_log: INSERT, UPDATE, DELETE.
Сохраняет старые и новые данные в формате JSONB для полной трассировки.';

-- 3. Триггер автоматического обновления статуса номера
CREATE OR REPLACE FUNCTION trg_fn_update_room_status()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.status = 'checked_in' AND (OLD.status IS NULL OR OLD.status != 'checked_in') THEN
        UPDATE rooms SET status = 'occupied', updated_at = NOW()
        WHERE id = NEW.room_id;
    ELSIF NEW.status = 'checked_out' AND (OLD.status IS NULL OR OLD.status != 'checked_out') THEN
        UPDATE rooms SET status = 'cleaning', updated_at = NOW()
        WHERE id = NEW.room_id;
    ELSIF NEW.status = 'cancelled' AND OLD.status = 'checked_in' THEN
        UPDATE rooms SET status = 'available', updated_at = NOW()
        WHERE id = NEW.room_id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_update_room_status
    AFTER UPDATE ON bookings
    FOR EACH ROW
    EXECUTE FUNCTION trg_fn_update_room_status();

COMMENT ON FUNCTION trg_fn_update_room_status IS
'Автоматически обновляет статус номера при изменении статуса бронирования:
- checked_in  → номер «occupied»
- checked_out → номер «cleaning»
- отмена при заселении → номер «available»';

-- 4. Триггер автоматического обновления updated_at
CREATE OR REPLACE FUNCTION trg_fn_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION trg_fn_set_updated_at();

CREATE TRIGGER trg_guest_profiles_updated_at
    BEFORE UPDATE ON guest_profiles
    FOR EACH ROW
    EXECUTE FUNCTION trg_fn_set_updated_at();

CREATE TRIGGER trg_rooms_updated_at
    BEFORE UPDATE ON rooms
    FOR EACH ROW
    EXECUTE FUNCTION trg_fn_set_updated_at();

COMMENT ON FUNCTION trg_fn_set_updated_at IS
'Автоматически устанавливает поле updated_at при обновлении записи';
