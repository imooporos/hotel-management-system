# SQL-скрипты для базы данных гостиницы

В этой папке собраны все DDL/DML скрипты, необходимые для воспроизведения схемы БД с нуля. Каждый скрипт — самостоятельный, нумерация определяет порядок применения.

## Порядок применения

| #  | Скрипт                       | Что создаёт                                           |
|----|------------------------------|-------------------------------------------------------|
| 01 | `01_domains_types.sql`       | Домены `email_domain`, `phone_domain`, `positive_money`; ENUM `room_status`, `booking_status` |
| 02 | `02_tables.sql`              | DDL для 11 таблиц + ограничения CHECK / UNIQUE / FK   |
| 03 | `03_indexes.sql`             | B-tree-индексы по внешним ключам; GiST-индекс по `tsrange` дат бронирований; функциональный индекс по `LOWER(email)` |
| 04 | `04_views.sql`               | 4 представления: `v_room_availability`, `v_guest_bookings`, `v_revenue_by_category`, `v_active_bookings` |
| 05 | `05_functions.sql`           | Функции `fn_room_is_free`, `fn_calculate_booking_total`, `fn_occupancy_rate` |
| 06 | `06_procedures.sql`          | Процедуры `sp_register_user`, `sp_create_booking`, `sp_update_booking_status`, `sp_cancel_booking`, `sp_get_user_bookings` |
| 07 | `07_triggers.sql`            | Триггеры `trg_no_overlap_booking` (бизнес-правило непересечения броней), `trg_audit_bookings` (аудит изменений), `trg_update_room_status` (синхронизация статуса номера) |
| 08 | `08_seed_data.sql`           | Тестовые данные: роли, пользователи, категории, номера, услуги, бронирования, платежи |
| 09 | `09_queries_pool.sql`        | 12 типов SQL-запросов из пула задания (для демонстрации) |
| 10 | `10_security.sql`            | Роли БД (`hotel_guest`, `hotel_manager`, `hotel_admin`), GRANT/REVOKE, Row Level Security |

## Быстрая пересборка

```bash
PGPASSWORD=AppHotelStrong_pass_2026 \
  psql -h localhost -U hotel_app -d hotel_db \
  -v ON_ERROR_STOP=1 \
  -f 01_domains_types.sql \
  -f 02_tables.sql \
  -f 03_indexes.sql \
  -f 04_views.sql \
  -f 05_functions.sql \
  -f 06_procedures.sql \
  -f 07_triggers.sql \
  -f 08_seed_data.sql
```

или с помощью обёртки:

```bash
./reset.sh hotel_db hotel_app
```

## Применение объектов в приложении

| Объект БД                       | Где используется в приложении                                  |
|---------------------------------|---------------------------------------------------------------|
| `email_domain`, `phone_domain`  | Регистрация пользователя и обновление профиля                 |
| ENUM `room_status`              | Сетка состояний номера в админ-панели                         |
| ENUM `booking_status`           | Воркфлоу бронирования (pending → confirmed → checked_in → …)  |
| `v_room_availability`           | Витрина доступных номеров на главном экране клиента           |
| `v_guest_bookings`              | Личный кабинет гостя — «Мои бронирования»                     |
| `v_revenue_by_category`         | Отчёт «Выручка по категориям» (PDF) для администратора        |
| `v_active_bookings`             | Дашборд менеджера: текущие заезды/выезды                      |
| `fn_room_is_free`               | Проверка перед оформлением бронирования (server: bookings.py) |
| `fn_calculate_booking_total`    | Калькулятор стоимости в форме бронирования                    |
| `fn_occupancy_rate`             | Отчёт «Загрузка номерного фонда»                              |
| `sp_register_user`              | Endpoint `POST /auth/register`                                |
| `sp_create_booking`             | Endpoint `POST /bookings`                                     |
| `sp_update_booking_status`      | Endpoint `PATCH /bookings/{id}/status`                        |
| `sp_cancel_booking`             | Endpoint `DELETE /bookings/{id}`                              |
| `sp_get_user_bookings`          | Endpoint `GET /bookings/me`                                   |
| `trg_no_overlap_booking`        | Гарантирует невозможность забронировать номер на пересекающиеся даты — поднимает понятную ошибку, которую перехватывает API |
| `trg_audit_bookings`            | Эндпоинт `GET /admin/audit` отдаёт записи аудита             |
| `trg_update_room_status`        | Автоматически синхронизирует `rooms.status` при смене статуса бронирования |
| RLS на `bookings`               | Принудительное разграничение «гость видит только свои брони» |
