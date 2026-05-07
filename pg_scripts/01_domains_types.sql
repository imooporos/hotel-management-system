-- =============================================================================
-- 01_domains_types.sql
-- Пользовательские домены и перечислимые типы (ENUM) для базы данных гостиницы
-- =============================================================================

-- Домен для email: строка до 255 символов, формат проверяется через CHECK
CREATE DOMAIN email_domain AS VARCHAR(255)
    CHECK (VALUE ~* '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$');

COMMENT ON DOMAIN email_domain IS 'Домен для хранения email-адресов с валидацией формата';

-- Домен для телефона: международный формат +7XXXXXXXXXX или аналогичный
CREATE DOMAIN phone_domain AS VARCHAR(20)
    CHECK (VALUE ~* '^\+?[0-9]{10,15}$');

COMMENT ON DOMAIN phone_domain IS 'Домен для хранения телефонных номеров в международном формате';

-- Домен для денежных сумм: строго положительное число
CREATE DOMAIN positive_money AS NUMERIC(12, 2)
    CHECK (VALUE > 0);

COMMENT ON DOMAIN positive_money IS 'Домен для хранения денежных сумм (только положительные значения)';

-- Перечислимый тип: статус номера
CREATE TYPE room_status AS ENUM (
    'available',    -- свободен
    'occupied',     -- занят
    'cleaning',     -- уборка
    'maintenance'   -- на ремонте
);

COMMENT ON TYPE room_status IS 'Статус гостиничного номера';

-- Перечислимый тип: статус бронирования
CREATE TYPE booking_status AS ENUM (
    'pending',      -- ожидает подтверждения
    'confirmed',    -- подтверждено
    'checked_in',   -- гость заселён
    'checked_out',  -- гость выехал
    'cancelled'     -- отменено
);

COMMENT ON TYPE booking_status IS 'Статус бронирования гостиничного номера';

-- Перечислимый тип: способ оплаты
CREATE TYPE payment_method AS ENUM (
    'cash',         -- наличные
    'card',         -- банковская карта
    'transfer'      -- безналичный перевод
);

COMMENT ON TYPE payment_method IS 'Способ оплаты';
