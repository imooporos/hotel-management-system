#!/usr/bin/env bash
# Полностью пересобирает БД проекта.
# Использование:
#   PGPASSWORD=... ./reset.sh [db_name] [db_user] [db_host] [db_port]

set -euo pipefail

DB="${1:-hotel_db}"
USR="${2:-hotel_app}"
HOST="${3:-localhost}"
PORT="${4:-5432}"

cd "$(dirname "$0")"

PSQL=(psql -h "$HOST" -p "$PORT" -U "$USR" -d "$DB" -v ON_ERROR_STOP=1 -X --quiet)

echo "Применяю SQL-скрипты к $USR@$HOST:$PORT/$DB ..."
for f in 01_domains_types.sql 02_tables.sql 03_indexes.sql 04_views.sql \
         05_functions.sql 06_procedures.sql 07_triggers.sql 08_seed_data.sql; do
    echo "  ▶ $f"
    "${PSQL[@]}" -f "$f"
done

echo "Готово. Применяю security/RLS под суперпользователем (опционально, нужны права)..."
"${PSQL[@]}" -f 10_security.sql || \
    echo "  ! 10_security.sql не применён (нужны привилегии superuser)."

echo
echo "База готова. Тестовые учётки:"
echo "  admin@hotel.local      / Admin_2026!"
echo "  manager@hotel.local    / Manager_2026!"
echo "  ivanov@example.com     / Guest_2026!"
