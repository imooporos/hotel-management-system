-- =============================================================================
-- 02_tables.sql
-- DDL таблиц базы данных гостиницы с ограничениями целостности
-- =============================================================================

-- Таблица пользователей системы
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    email           email_domain NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL DEFAULT 'guest'
                        CHECK (role IN ('guest', 'manager', 'admin')),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE users IS 'Пользователи системы с аутентификационными данными';
COMMENT ON COLUMN users.role IS 'Роль пользователя: guest, manager, admin';
COMMENT ON COLUMN users.is_active IS 'Флаг активности: заблокированные пользователи не могут войти';

-- Профили гостей (расширенная информация)
CREATE TABLE guest_profiles (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    patronymic      VARCHAR(100),
    phone           phone_domain,
    passport_series VARCHAR(4),
    passport_number VARCHAR(6),
    birth_date      DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_passport_format CHECK (
        (passport_series IS NULL AND passport_number IS NULL) OR
        (passport_series ~ '^\d{4}$' AND passport_number ~ '^\d{6}$')
    )
);

COMMENT ON TABLE guest_profiles IS 'Профили гостей с паспортными данными и контактной информацией';
COMMENT ON COLUMN guest_profiles.passport_series IS 'Серия паспорта (4 цифры)';
COMMENT ON COLUMN guest_profiles.passport_number IS 'Номер паспорта (6 цифр)';

-- Категории номеров
CREATE TABLE room_categories (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    description     TEXT,
    base_price      positive_money NOT NULL,
    capacity        INTEGER NOT NULL CHECK (capacity BETWEEN 1 AND 10),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE room_categories IS 'Категории гостиничных номеров (стандарт, люкс, сюит и т.д.)';

-- Номера гостиницы
CREATE TABLE rooms (
    id              SERIAL PRIMARY KEY,
    room_number     VARCHAR(10) NOT NULL UNIQUE,
    category_id     INTEGER NOT NULL REFERENCES room_categories(id) ON DELETE RESTRICT,
    floor           INTEGER NOT NULL CHECK (floor BETWEEN 1 AND 50),
    status          room_status NOT NULL DEFAULT 'available',
    description     TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE rooms IS 'Гостиничные номера с привязкой к категориям';
COMMENT ON COLUMN rooms.room_number IS 'Уникальный номер комнаты (например, 101, 205A)';

-- Удобства номеров
CREATE TABLE amenities (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    icon            VARCHAR(50),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE amenities IS 'Справочник удобств номеров (Wi-Fi, кондиционер, мини-бар и т.д.)';

-- Связь номеров и удобств (many-to-many)
CREATE TABLE room_amenities (
    room_id         INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    amenity_id      INTEGER NOT NULL REFERENCES amenities(id) ON DELETE CASCADE,
    PRIMARY KEY (room_id, amenity_id)
);

COMMENT ON TABLE room_amenities IS 'Связующая таблица: какие удобства есть в каждом номере';

-- Дополнительные услуги
CREATE TABLE services (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    price           positive_money NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE services IS 'Каталог дополнительных услуг гостиницы';

-- Бронирования
CREATE TABLE bookings (
    id              SERIAL PRIMARY KEY,
    guest_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    room_id         INTEGER NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
    check_in_date   DATE NOT NULL,
    check_out_date  DATE NOT NULL,
    status          booking_status NOT NULL DEFAULT 'pending',
    guests_count    INTEGER NOT NULL DEFAULT 1 CHECK (guests_count >= 1),
    total_amount    NUMERIC(12, 2) NOT NULL DEFAULT 0,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_dates CHECK (check_out_date > check_in_date),
    CONSTRAINT chk_duration CHECK (check_out_date - check_in_date <= 365)
);

COMMENT ON TABLE bookings IS 'Бронирования гостиничных номеров';
COMMENT ON COLUMN bookings.check_in_date IS 'Дата заезда';
COMMENT ON COLUMN bookings.check_out_date IS 'Дата выезда';

-- Услуги, подключённые к бронированию
CREATE TABLE booking_services (
    id              SERIAL PRIMARY KEY,
    booking_id      INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    service_id      INTEGER NOT NULL REFERENCES services(id) ON DELETE RESTRICT,
    quantity        INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 1),
    price_at_booking positive_money NOT NULL,
    UNIQUE (booking_id, service_id)
);

COMMENT ON TABLE booking_services IS 'Дополнительные услуги, подключённые к конкретному бронированию';

-- Платежи
CREATE TABLE payments (
    id              SERIAL PRIMARY KEY,
    booking_id      INTEGER NOT NULL REFERENCES bookings(id) ON DELETE RESTRICT,
    amount          positive_money NOT NULL,
    method          payment_method NOT NULL DEFAULT 'card',
    paid_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    description     VARCHAR(500)
);

COMMENT ON TABLE payments IS 'Платежи по бронированиям';

-- Журнал аудита
CREATE TABLE audit_log (
    id              SERIAL PRIMARY KEY,
    table_name      VARCHAR(100) NOT NULL,
    record_id       INTEGER NOT NULL,
    action          VARCHAR(10) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_data        JSONB,
    new_data        JSONB,
    changed_by      VARCHAR(100),
    changed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE audit_log IS 'Журнал аудита изменений в таблицах БД';
