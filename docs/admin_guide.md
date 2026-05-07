# Руководство администратора

Документ для администраторов системы (специалистов, отвечающих за развёртывание, обслуживание и
безопасность сервера).

---

## 1. Архитектура развёртывания

```
┌───────────────────────────────────┐
│  Клиент (Flet — desktop / web)    │  ← на машине пользователя
└────────────────┬──────────────────┘
                 │ HTTPS/HTTP (REST)
                 ▼
┌───────────────────────────────────┐
│  Nginx (порт 80) reverse proxy    │
└────────────────┬──────────────────┘
                 │ proxy_pass 127.0.0.1:8000
                 ▼
┌───────────────────────────────────┐
│  systemd unit: hotel-api.service  │
│  uvicorn (FastAPI), workers=2     │
└────────────────┬──────────────────┘
                 │ asyncpg (UDS)
                 ▼
┌───────────────────────────────────┐
│  PostgreSQL 16 (DB hotel_db)      │
│  user: hotel_app                  │
└───────────────────────────────────┘
```

---

## 2. Серверная инсталляция

### 2.1 Размещение

| Что                        | Где                                              |
|----------------------------|--------------------------------------------------|
| Репозиторий с кодом        | `/opt/hotel/hotel-management-system/`           |
| Виртуальное окружение Python| `/opt/hotel/hotel-management-system/server/.venv/` |
| Переменные окружения        | `/opt/hotel/hotel-management-system/server/.env`  |
| systemd unit                | `/etc/systemd/system/hotel-api.service`           |
| Nginx site                  | `/etc/nginx/sites-available/hotel-api`            |
| Логи API                    | `journalctl -u hotel-api -f`                      |
| Логи Nginx                  | `/var/log/nginx/{access,error}.log`               |

### 2.2 Управление сервисом

```bash
# статус
systemctl status hotel-api

# перезапуск (после деплоя кода)
systemctl restart hotel-api

# журнал в реальном времени
journalctl -u hotel-api -f

# сервис включён в автозапуск
systemctl is-enabled hotel-api
```

### 2.3 Деплой нового кода

```bash
cd /opt/hotel/hotel-management-system
git fetch origin
git checkout devin/1778122922-database-foundation   # или main после мержа
git pull
cd server
.venv/bin/uv pip install -e .   # если изменились зависимости
systemctl restart hotel-api
```

### 2.4 Обновление БД

Скрипты идемпотентны и могут выполняться повторно, но содержат `DROP IF EXISTS` для пересоздания
функций/процедур.

```bash
cd /opt/hotel/hotel-management-system/pg_scripts
sudo -u postgres ./reset.sh         # сброс и накат всех 10 SQL-файлов
```

⚠️ `reset.sh` сначала **сбрасывает базу полностью**. Используйте только в dev/тестовом контуре.

---

## 3. Учётные записи и роли в БД

В PostgreSQL созданы три SQL-роли (см. `pg_scripts/10_security.sql`):

| Роль | Привилегии |
|------|------------|
| `hotel_guest` | SELECT по каталогу + INSERT/SELECT/UPDATE по своим бронированиям через RLS |
| `hotel_manager` | + SELECT по аудиту, выручке, всем бронированиям |
| `hotel_admin` | владелец схемы — полный доступ |

В коде backend используется единственный технический пользователь `hotel_app` (DBA-уровня). В каждой
сессии устанавливаются переменные:

- `app.user_id` — текущий пользователь;
- `app.actor_id` — для журнала аудита (используется триггерами).

Это даёт работоспособность RLS-политик и аудит-триггеров без передачи разных credentials в backend.

---

## 4. Резервное копирование

### 4.1 Логический бэкап (рекомендуется ежесуточно)

```bash
PGPASSWORD=AppHotelStrong_pass_2026 pg_dump -h localhost -U hotel_app -d hotel_db -Fc \
    -f /var/backups/hotel_$(date +%F).dump
```

### 4.2 Восстановление

```bash
pg_restore -h localhost -U hotel_app -d hotel_db_new -1 /var/backups/hotel_2026-05-07.dump
```

### 4.3 PITR (точка во времени)

PostgreSQL должен быть настроен на архивирование WAL (`archive_mode=on`). Подробности — в документации
PostgreSQL и `docs/security.md`.

---

## 5. Управление пользователями (приложение)

Через UI клиента: **«Администрирование» → «Пользователи»**.

Через API:

```bash
# список
curl -H "Authorization: Bearer <admin_token>" http://77.221.151.85/users

# смена роли
curl -X PATCH -H "Authorization: Bearer <admin_token>" \
     -H "Content-Type: application/json" \
     -d '{"role_code":"manager"}' \
     http://77.221.151.85/users/3

# деактивация
curl -X PATCH -H "Authorization: Bearer <admin_token>" \
     -H "Content-Type: application/json" \
     -d '{"is_active":false}' \
     http://77.221.151.85/users/3
```

---

## 6. Журнал аудита

Триггеры `trg_audit_bookings`, `trg_audit_users`, `trg_audit_rooms` автоматически фиксируют все
INSERT/UPDATE/DELETE. Для расследования:

```sql
-- последние 50 операций
SELECT * FROM audit_log ORDER BY happened_at DESC LIMIT 50;

-- операции конкретного пользователя
SELECT * FROM audit_log WHERE actor_id = 5 ORDER BY happened_at DESC;

-- удаления номеров за месяц
SELECT * FROM audit_log
 WHERE table_name = 'rooms' AND action = 'DELETE'
   AND happened_at >= now() - interval '30 days';
```

---

## 7. Мониторинг и метрики

- `GET /health` — проверка живости сервиса (DB pool checked).
- `journalctl -u hotel-api --since "1 hour ago"` — логи запросов и ошибок.
- `pg_stat_activity` — текущие сессии БД.
- `pg_stat_statements` — топ медленных запросов (требует расширения).

---

## 8. Восстановление аварии

| Сценарий | Действия |
|----------|----------|
| Сервис не запускается | `journalctl -u hotel-api -n 100` → найти ошибку → проверить `.env`, наличие venv, доступность БД |
| БД недоступна | `systemctl status postgresql` → `pg_isready -h localhost -U hotel_app -d hotel_db` |
| Порт 80 занят | `ss -tlnp \| grep :80` → конфликтующая служба |
| Неконсистентные данные | Восстановление из бэкапа: `pg_restore -d hotel_db_restored backup.dump` |

---

## 9. Чек-лист первичной установки на новом сервере

```bash
# 1) PostgreSQL
apt install -y postgresql-16
sudo -u postgres createuser --pwprompt hotel_app
sudo -u postgres createdb -O hotel_app hotel_db

# 2) Python 3.13 (через uv)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.13

# 3) Код
git clone https://github.com/imooporos/hotel-management-system.git /opt/hotel/hotel-management-system

# 4) Применение скриптов БД
cd /opt/hotel/hotel-management-system/pg_scripts && sudo -u postgres ./reset.sh

# 5) Backend venv
cd ../server
uv venv .venv
uv pip install --python .venv/bin/python -e .

# 6) .env с DATABASE_URL и JWT_SECRET (chmod 600)

# 7) systemd unit + nginx (см. /etc/systemd/system/hotel-api.service и /etc/nginx/sites-available/hotel-api)

# 8) Запуск
systemctl daemon-reload
systemctl enable --now hotel-api
nginx -t && systemctl reload nginx
```
