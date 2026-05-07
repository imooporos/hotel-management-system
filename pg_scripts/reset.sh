#!/usr/bin/env bash
# =============================================================================
# reset.sh — Полная пересборка базы данных гостиницы
# Использование: ./reset.sh [db_name] [db_user]
# По умолчанию: db_name=hotel_db, db_user=hotel_app
# =============================================================================

set -euo pipefail

DB_NAME="${1:-hotel_db}"
DB_USER="${2:-hotel_app}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "═══════════════════════════════════════════════════════════"
echo " Пересборка базы данных: $DB_NAME"
echo " Пользователь: $DB_USER"
echo "═══════════════════════════════════════════════════════════"

PSQL_CMD="psql -U $DB_USER -d $DB_NAME -v ON_ERROR_STOP=1"

echo ""
echo "▸ Очистка: удаление всех объектов..."
$PSQL_CMD -c "
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO $DB_USER;
GRANT ALL ON SCHEMA public TO public;
"

echo "▸ [1/10] Домены и типы..."
$PSQL_CMD -f "$SCRIPT_DIR/01_domains_types.sql"

echo "▸ [2/10] Таблицы..."
$PSQL_CMD -f "$SCRIPT_DIR/02_tables.sql"

echo "▸ [3/10] Индексы..."
$PSQL_CMD -f "$SCRIPT_DIR/03_indexes.sql"

echo "▸ [4/10] Представления..."
$PSQL_CMD -f "$SCRIPT_DIR/04_views.sql"

echo "▸ [5/10] Функции..."
$PSQL_CMD -f "$SCRIPT_DIR/05_functions.sql"

echo "▸ [6/10] Хранимые процедуры..."
$PSQL_CMD -f "$SCRIPT_DIR/06_procedures.sql"

echo "▸ [7/10] Триггеры..."
$PSQL_CMD -f "$SCRIPT_DIR/07_triggers.sql"

echo "▸ [8/10] Тестовые данные..."
$PSQL_CMD -f "$SCRIPT_DIR/08_seed_data.sql"

echo "▸ [9/10] Безопасность (роли, GRANT, RLS)..."
$PSQL_CMD -f "$SCRIPT_DIR/10_security.sql"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo " ✔ База данных $DB_NAME успешно пересобрана!"
echo "═══════════════════════════════════════════════════════════"
