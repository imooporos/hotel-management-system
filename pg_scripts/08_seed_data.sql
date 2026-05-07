-- ============================================================================
--  08_seed_data.sql
--  Тестовые данные для разработки и демонстрации.
--  Пароли хэшированы bcrypt:
--    Admin_2026!     → admin@hotel.local
--    Manager_2026!   → manager@hotel.local
--    Guest_2026!     → ivanov@example.com / petrova@example.com / sidorov@example.com
-- ============================================================================

\echo '>>> applying 08_seed_data.sql'

-- ---------------------------------------------------------------------------
--  Очистка
-- ---------------------------------------------------------------------------
TRUNCATE TABLE audit_log, payments, booking_services, bookings,
               room_amenities, amenities, services,
               rooms, room_categories,
               guest_profiles, users, roles
       RESTART IDENTITY CASCADE;

-- ---------------------------------------------------------------------------
--  Роли
-- ---------------------------------------------------------------------------
INSERT INTO roles (code, title, description) VALUES
    ('guest',   'Гость',          'Может бронировать номера и редактировать свой профиль'),
    ('manager', 'Менеджер',       'Подтверждает бронирования и управляет заездами'),
    ('admin',   'Администратор',  'Полный доступ к системе, включая управление пользователями');

-- ---------------------------------------------------------------------------
--  Пользователи (bcrypt-хэши совпадают с паролями выше)
-- ---------------------------------------------------------------------------
-- Сгенерированы python -c "import bcrypt; print(bcrypt.hashpw(b'...', bcrypt.gensalt(12)).decode())"
INSERT INTO users (email, password_hash, full_name, phone, role_id) VALUES
    ('admin@hotel.local',
     '$2b$12$LbnVkzgKi5Qfs/mxD7ZVDuM4Kf6WLuIdwF6C/XtdYrkrl7A1.KFQC',
     'Администратор Системы',
     '+79990000000',
     (SELECT role_id FROM roles WHERE code = 'admin')),
    ('manager@hotel.local',
     '$2b$12$a6dL3kI7EiH3zqNEHfobRuVpe2N4as2HCjBcFG7ua8c4c77Td5Uem',
     'Иван Менеджеров',
     '+79990000001',
     (SELECT role_id FROM roles WHERE code = 'manager')),
    ('ivanov@example.com',
     '$2b$12$dNTgqMTF6euZ19kvfq1iA.lVCPsJNhCuQHOPi0USey8X2EEReKnGm',
     'Иванов Иван Иванович',
     '+79111111111',
     (SELECT role_id FROM roles WHERE code = 'guest')),
    ('petrova@example.com',
     '$2b$12$dNTgqMTF6euZ19kvfq1iA.lVCPsJNhCuQHOPi0USey8X2EEReKnGm',
     'Петрова Анна Сергеевна',
     '+79222222222',
     (SELECT role_id FROM roles WHERE code = 'guest')),
    ('sidorov@example.com',
     '$2b$12$dNTgqMTF6euZ19kvfq1iA.lVCPsJNhCuQHOPi0USey8X2EEReKnGm',
     'Сидоров Пётр Алексеевич',
     '+79333333333',
     (SELECT role_id FROM roles WHERE code = 'guest'));

-- профили гостей (только для роли guest)
INSERT INTO guest_profiles (user_id, passport_series, passport_number, passport_issued, birth_date, address)
SELECT u.user_id,
       (4000 + u.user_id)::text,
       (100000 + u.user_id * 17)::text,
       'УФМС России по г. Великий Новгород',
       (DATE '1990-01-01' + (u.user_id * 200) * INTERVAL '1 day')::date,
       'г. Великий Новгород, ул. Учебная, д. ' || u.user_id::text
  FROM users u
  JOIN roles r ON r.role_id = u.role_id
 WHERE r.code = 'guest';

-- ---------------------------------------------------------------------------
--  Категории номеров
-- ---------------------------------------------------------------------------
INSERT INTO room_categories (code, title, description, base_price, capacity) VALUES
    ('standard',     'Стандарт',         'Уютный номер с одной двуспальной кроватью',                      3500.00, 2),
    ('comfort',      'Комфорт',          'Просторный номер с улучшенной отделкой',                          5000.00, 2),
    ('junior_suite', 'Полулюкс',         'Двухкомнатный номер с гостиной зоной',                            7500.00, 3),
    ('suite',        'Люкс',             'Большой номер с отдельной гостиной и панорамным видом',          12000.00, 4),
    ('family',       'Семейный',         'Просторный номер с двумя комнатами для семьи с детьми',           9000.00, 4);

-- ---------------------------------------------------------------------------
--  Удобства
-- ---------------------------------------------------------------------------
INSERT INTO amenities (code, title, icon) VALUES
    ('wifi',          'Wi-Fi',                'wifi'),
    ('air_cond',      'Кондиционер',          'ac_unit'),
    ('mini_bar',      'Мини-бар',             'liquor'),
    ('safe',          'Сейф',                 'lock'),
    ('tv',            'Телевизор',            'tv'),
    ('balcony',       'Балкон',               'deck'),
    ('bath_tub',      'Ванна',                'bathtub'),
    ('coffee_maker',  'Кофемашина',           'coffee'),
    ('view_river',    'Вид на реку',          'water'),
    ('soundproof',    'Звукоизоляция',        'volume_off');

-- ---------------------------------------------------------------------------
--  Номера (50 шт, 5 этажей × 10 номеров; категория зависит от этажа)
-- ---------------------------------------------------------------------------
INSERT INTO rooms (room_number, floor, category_id, price_modifier, status, description, is_active)
SELECT
    LPAD((floor * 100 + n)::text, 3, '0')                              AS room_number,
    floor                                                              AS floor,
    CASE
        WHEN floor = 1 THEN (SELECT category_id FROM room_categories WHERE code = 'standard')
        WHEN floor = 2 THEN (SELECT category_id FROM room_categories WHERE code = 'comfort')
        WHEN floor = 3 THEN (SELECT category_id FROM room_categories WHERE code = 'junior_suite')
        WHEN floor = 4 THEN (SELECT category_id FROM room_categories WHERE code = 'family')
        WHEN floor = 5 THEN (SELECT category_id FROM room_categories WHERE code = 'suite')
    END                                                                AS category_id,
    CASE WHEN n % 7 = 0 THEN 500.00 ELSE 0 END                         AS price_modifier,
    'available'::room_status,
    'Уютный номер ' || LPAD((floor * 100 + n)::text, 3, '0'),
    TRUE
  FROM generate_series(1, 5)  AS floor
  CROSS JOIN generate_series(1, 10) AS n;

-- удобства: каждый номер получает 4–6 случайных удобств
INSERT INTO room_amenities (room_id, amenity_id)
SELECT r.room_id, a.amenity_id
  FROM rooms r
  CROSS JOIN LATERAL (
        SELECT amenity_id
          FROM amenities
         ORDER BY (r.room_id * amenity_id) % 7
         LIMIT (4 + (r.room_id % 3))
  ) a
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
--  Услуги
-- ---------------------------------------------------------------------------
INSERT INTO services (code, title, description, price) VALUES
    ('breakfast', 'Завтрак "шведский стол"', 'Завтрак в ресторане отеля',                      650.00),
    ('transfer',  'Трансфер от/до вокзала',  'Поездка на легковом автомобиле',                1200.00),
    ('sauna',     'Сауна',                   'Час в сауне с бассейном',                       1800.00),
    ('parking',   'Охраняемая парковка',     'Сутки на охраняемой стоянке',                    400.00),
    ('laundry',   'Услуги прачечной',        'Стирка и сушка одного комплекта одежды',         500.00),
    ('late_checkout', 'Поздний выезд',        'Выезд после 14:00 без доплаты за лишние сутки', 1000.00);

-- ---------------------------------------------------------------------------
--  Бронирования + платежи (используем процедуру и прямой INSERT)
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    v_guest_id1 bigint := (SELECT user_id FROM users WHERE email = 'ivanov@example.com');
    v_guest_id2 bigint := (SELECT user_id FROM users WHERE email = 'petrova@example.com');
    v_guest_id3 bigint := (SELECT user_id FROM users WHERE email = 'sidorov@example.com');
    v_room_id1  bigint := (SELECT room_id FROM rooms WHERE room_number = '101');
    v_room_id2  bigint := (SELECT room_id FROM rooms WHERE room_number = '203');
    v_room_id3  bigint := (SELECT room_id FROM rooms WHERE room_number = '305');
    v_room_id4  bigint := (SELECT room_id FROM rooms WHERE room_number = '402');
    v_room_id5  bigint := (SELECT room_id FROM rooms WHERE room_number = '501');
    v_book_id   bigint;
    v_total     positive_money;
    v_breakfast_id integer := (SELECT service_id FROM services WHERE code = 'breakfast');
    v_transfer_id  integer := (SELECT service_id FROM services WHERE code = 'transfer');
BEGIN
    -- 1: прошлое подтверждённое и заселённое выезжающее
    CALL sp_create_booking(v_guest_id1, v_room_id1,
                          (CURRENT_DATE - 5)::date, (CURRENT_DATE - 2)::date,
                          2::smallint, ARRAY[v_breakfast_id]::integer[], v_book_id, v_total);
    CALL sp_update_booking_status(v_book_id, 'confirmed', NULL);
    CALL sp_update_booking_status(v_book_id, 'checked_in', NULL);
    CALL sp_update_booking_status(v_book_id, 'checked_out', NULL);
    INSERT INTO payments (booking_id, amount, method) VALUES (v_book_id, v_total, 'card');

    -- 2: текущая активная (заселён сейчас)
    CALL sp_create_booking(v_guest_id2, v_room_id2,
                          (CURRENT_DATE - 1)::date, (CURRENT_DATE + 3)::date,
                          1::smallint, ARRAY[v_breakfast_id, v_transfer_id]::integer[], v_book_id, v_total);
    CALL sp_update_booking_status(v_book_id, 'confirmed', NULL);
    CALL sp_update_booking_status(v_book_id, 'checked_in', NULL);
    INSERT INTO payments (booking_id, amount, method) VALUES (v_book_id, v_total/2, 'card');

    -- 3: будущая подтверждённая
    CALL sp_create_booking(v_guest_id3, v_room_id3,
                          (CURRENT_DATE + 7)::date, (CURRENT_DATE + 10)::date,
                          3::smallint, ARRAY[v_breakfast_id]::integer[], v_book_id, v_total);
    CALL sp_update_booking_status(v_book_id, 'confirmed', NULL);

    -- 4: ожидает подтверждения (новая)
    CALL sp_create_booking(v_guest_id1, v_room_id4,
                          (CURRENT_DATE + 15)::date, (CURRENT_DATE + 18)::date,
                          4::smallint, NULL, v_book_id, v_total);

    -- 5: отменённая
    CALL sp_create_booking(v_guest_id2, v_room_id5,
                          (CURRENT_DATE + 30)::date, (CURRENT_DATE + 33)::date,
                          2::smallint, NULL, v_book_id, v_total);
    CALL sp_update_booking_status(v_book_id, 'cancelled', NULL);
END $$;

\echo '<<< 08_seed_data.sql ok'
