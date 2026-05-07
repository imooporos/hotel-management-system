# Тесты

Тестовая часть курсового проекта:

| Тип            | Файл                                            | Что проверяет |
|----------------|-------------------------------------------------|----------------|
| **юнит-1**     | `tests/unit/test_security.py::test_password_hash_and_verify` | bcrypt-хеширование пароля и `verify_password()` |
| **юнит-2**     | `tests/unit/test_security.py::test_jwt_round_trip`           | Создание и разбор JWT-токена |
| тест-кейс 1    | `tests/integration/test_auth_flow.py`           | Регистрация → вход → /auth/me |
| тест-кейс 2    | `tests/integration/test_booking_flow.py`        | Расчёт, создание, отмена бронирования |
| тест-кейс 3    | `tests/integration/test_overlap_protection.py`  | Триггер защиты от пересекающихся бронирований |
| тест-кейс 4    | `tests/integration/test_rbac.py`                | Гость не имеет доступа к отчётам и админ-эндпоинтам |
| тест-кейс 5    | `tests/integration/test_pdf.py`                 | Скачивание PDF-бланка заказа и отчётов |

## Запуск

```bash
cd server
. .venv/bin/activate
pip install -e .[dev]                # либо pip install pytest pytest-asyncio httpx
pytest -q ../tests
```

По умолчанию интеграционные тесты обращаются к рабочему серверу
`http://77.221.151.85`. URL можно переопределить переменной окружения
`HOTEL_API_URL`.

```bash
HOTEL_API_URL=http://localhost:8000 pytest -q ../tests
```
