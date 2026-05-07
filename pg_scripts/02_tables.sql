-- ============================================================================
--  02_tables.sql
--  DDL основных таблиц информационной системы гостиницы.
-- ============================================================================

\echo '>>> applying 02_tables.sql'

-- Полная очистка всего предметного слоя (идемпотентность скрипта)
DROP TABLE IF EXISTS audit_log         CASCADE;
DROP TABLE IF EXISTS payments          CASCADE;
DROP TABLE IF EXISTS booking_services  CASCADE;
DROP TABLE IF EXISTS bookings          CASCADE;
DROP TABLE IF EXISTS room_amenities    CASCADE;
DROP TABLE IF EXISTS amenities         CASCADE;
DROP TABLE IF EXISTS services          CASCADE;
DROP TABLE IF EXISTS rooms             CASCADE;
DROP TABLE IF EXISTS room_categories   CASCADE;
DROP TABLE IF EXISTS guest_profiles    CASCADE;
DROP TABLE IF EXISTS users             CASCADE;
DROP TABLE IF EXISTS roles             CASCADE;

-- ---------------------------------------------------------------------------
--  roles — справочник ролей пользователей системы
-- ---------------------------------------------------------------------------
CREATE TABLE roles (
    role_id        smallserial PRIMARY KEY,
    code           varchar(32)  NOT NULL UNIQUE,
    title          varchar(64)  NOT NULL,
    description    text,
    CONSTRAINT roles_code_check CHECK (code IN ('guest', 'manager', 'admin'))
);

COMMENT ON TABLE  roles               IS 'Справочник ролей. Применяется в RBAC.';
COMMENT ON COLUMN roles.code          IS 'Машинный код роли (guest|manager|admin).';
COMMENT ON COLUMN roles.title         IS 'Человекочитаемое название роли.';

-- ---------------------------------------------------------------------------
--  users — учётные записи всех пользователей
-- ---------------------------------------------------------------------------
CREATE TABLE users (
    user_id        bigserial PRIMARY KEY,
    email          email_domain NOT NULL UNIQUE,
    password_hash  varchar(255) NOT NULL,
    full_name      varchar(128) NOT NULL,
    phone          phone_domain,
    role_id        smallint     NOT NULL REFERENCES roles(role_id),
    is_active      boolean      NOT NULL DEFAULT TRUE,
    created_at     timestamptz  NOT NULL DEFAULT now(),
    updated_at     timestamptz  NOT NULL DEFAULT now(),
    last_login_at  timestamptz,
    CONSTRAINT users_full_name_not_blank CHECK (length(btrim(full_name)) >= 2)
);

COMMENT ON TABLE  users               IS 'Учётные записи. Пароль хранится как bcrypt-хэш.';
COMMENT ON COLUMN users.password_hash IS 'Хэш пароля bcrypt ($2b$...). Никогда не записывается в plain.';

-- ---------------------------------------------------------------------------
--  guest_profiles — расширенный профиль гостя
--  Хранит данные документа удостоверения личности; связь 1:1 с users.
-- ---------------------------------------------------------------------------
CREATE TABLE guest_profiles (
    user_id           bigint PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    passport_series   varchar(12),
    passport_number   varchar(20),
    passport_issued   varchar(255),
    birth_date        date,
    address           text,
    citizenship       varchar(64) DEFAULT 'РФ',
    notes             text,
    CONSTRAINT guest_profiles_birth_check CHECK (birth_date IS NULL OR birth_date < CURRENT_DATE),
    CONSTRAINT guest_profiles_passport_unique UNIQUE (passport_series, passport_number)
);

COMMENT ON TABLE guest_profiles IS 'Паспортные данные и контакты гостя (1:1 с users).';

-- ---------------------------------------------------------------------------
--  room_categories — категории номеров
-- ---------------------------------------------------------------------------
CREATE TABLE room_categories (
    category_id      smallserial PRIMARY KEY,
    code             varchar(32)   NOT NULL UNIQUE,
    title            varchar(64)   NOT NULL,
    description      text,
    base_price       positive_money NOT NULL,
    capacity         smallint      NOT NULL CHECK (capacity BETWEEN 1 AND 6),
    photo_url        varchar(512)
);

COMMENT ON TABLE  room_categories          IS 'Справочник категорий номеров (стандарт, люкс…).';
COMMENT ON COLUMN room_categories.base_price IS 'Базовая цена за сутки. Может корректироваться надбавками номера.';

-- ---------------------------------------------------------------------------
--  rooms — фактические номера гостиницы
-- ---------------------------------------------------------------------------
CREATE TABLE rooms (
    room_id        bigserial PRIMARY KEY,
    room_number    varchar(16)    NOT NULL UNIQUE,
    floor          smallint       NOT NULL CHECK (floor BETWEEN -1 AND 50),
    category_id    smallint       NOT NULL REFERENCES room_categories(category_id),
    price_modifier numeric(5, 2)  NOT NULL DEFAULT 0,   -- надбавка/скидка к base_price
    status         room_status    NOT NULL DEFAULT 'available',
    description    text,
    is_active      boolean        NOT NULL DEFAULT TRUE,
    created_at     timestamptz    NOT NULL DEFAULT now()
);

COMMENT ON TABLE rooms IS 'Гостиничный номерной фонд.';

-- ---------------------------------------------------------------------------
--  amenities — справочник удобств
-- ---------------------------------------------------------------------------
CREATE TABLE amenities (
    amenity_id   serial PRIMARY KEY,
    code         varchar(32) NOT NULL UNIQUE,
    title        varchar(64) NOT NULL,
    icon         varchar(32)
);

COMMENT ON TABLE amenities IS 'Удобства в номере: wifi, кондиционер, мини-бар…';

-- ---------------------------------------------------------------------------
--  room_amenities — связка комнат и удобств (M:M)
-- ---------------------------------------------------------------------------
CREATE TABLE room_amenities (
    room_id     bigint  NOT NULL REFERENCES rooms(room_id)         ON DELETE CASCADE,
    amenity_id  integer NOT NULL REFERENCES amenities(amenity_id)  ON DELETE CASCADE,
    PRIMARY KEY (room_id, amenity_id)
);

COMMENT ON TABLE room_amenities IS 'Какие удобства имеются в каждом конкретном номере.';

-- ---------------------------------------------------------------------------
--  services — дополнительные услуги (трансфер, завтрак, сауна и т.д.)
-- ---------------------------------------------------------------------------
CREATE TABLE services (
    service_id   serial PRIMARY KEY,
    code         varchar(32)    NOT NULL UNIQUE,
    title        varchar(96)    NOT NULL,
    description  text,
    price        positive_money NOT NULL,
    is_active    boolean        NOT NULL DEFAULT TRUE
);

COMMENT ON TABLE services IS 'Каталог дополнительных платных услуг.';

-- ---------------------------------------------------------------------------
--  bookings — бронирования
--  Используется генерируемое поле stay_period::tsrange для проверки пересечений.
-- ---------------------------------------------------------------------------
CREATE TABLE bookings (
    booking_id   bigserial PRIMARY KEY,
    user_id      bigint         NOT NULL REFERENCES users(user_id),
    room_id      bigint         NOT NULL REFERENCES rooms(room_id),
    check_in     date           NOT NULL,
    check_out    date           NOT NULL,
    guests_count smallint       NOT NULL DEFAULT 1 CHECK (guests_count BETWEEN 1 AND 6),
    status       booking_status NOT NULL DEFAULT 'pending',
    total_price  positive_money NOT NULL DEFAULT 0,
    notes        text,
    created_at   timestamptz    NOT NULL DEFAULT now(),
    updated_at   timestamptz    NOT NULL DEFAULT now(),

    -- Дата выезда строго позже даты заезда
    CONSTRAINT bookings_dates_check CHECK (check_out > check_in),

    -- Период проживания, индексированный далее GiST для проверки overlap'ов
    stay_period  daterange GENERATED ALWAYS AS
                 (daterange(check_in, check_out, '[)')) STORED
);

COMMENT ON TABLE  bookings              IS 'Бронирования номеров пользователями.';
COMMENT ON COLUMN bookings.stay_period  IS 'Полуоткрытый период [check_in, check_out). Используется для EXCLUDE.';

-- Запрет пересечений активных броней одного и того же номера.
-- Реализован через EXCLUDE c GiST: статус cancelled из проверки исключаем
-- частичным индексом → используем CONSTRAINT TRIGGER (см. 07_triggers.sql).
ALTER TABLE bookings
    ADD CONSTRAINT bookings_room_period_excl
    EXCLUDE USING gist (
        room_id WITH =,
        stay_period WITH &&
    )
    WHERE (status NOT IN ('cancelled'));

-- ---------------------------------------------------------------------------
--  booking_services — связь брони с дополнительными услугами (M:M, с количеством)
-- ---------------------------------------------------------------------------
CREATE TABLE booking_services (
    booking_id  bigint  NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
    service_id  integer NOT NULL REFERENCES services(service_id),
    quantity    smallint NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price  positive_money NOT NULL,    -- фиксируем цену на момент брони
    PRIMARY KEY (booking_id, service_id)
);

COMMENT ON TABLE booking_services IS 'Услуги, добавленные к конкретному бронированию.';

-- ---------------------------------------------------------------------------
--  payments — платежи
-- ---------------------------------------------------------------------------
CREATE TABLE payments (
    payment_id    bigserial PRIMARY KEY,
    booking_id    bigint         NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
    amount        positive_money NOT NULL CHECK (amount > 0),
    method        payment_method NOT NULL DEFAULT 'card',
    paid_at       timestamptz    NOT NULL DEFAULT now(),
    transaction_ref varchar(64)
);

COMMENT ON TABLE payments IS 'Платежи по бронированиям. Может быть несколько (предоплата + остаток).';

-- ---------------------------------------------------------------------------
--  audit_log — журнал аудита (заполняется триггером)
-- ---------------------------------------------------------------------------
CREATE TABLE audit_log (
    log_id       bigserial PRIMARY KEY,
    table_name   varchar(64)  NOT NULL,
    row_pk       text         NOT NULL,
    action       audit_action NOT NULL,
    actor_id     bigint REFERENCES users(user_id),
    actor_name   varchar(128),
    old_data     jsonb,
    new_data     jsonb,
    happened_at  timestamptz  NOT NULL DEFAULT now()
);

COMMENT ON TABLE audit_log IS 'Журнал изменений критичных таблиц. Заполняется триггером trg_audit_*.';

\echo '<<< 02_tables.sql ok'
