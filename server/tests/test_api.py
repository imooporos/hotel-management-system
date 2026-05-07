"""
Тест-кейсы и юнит-тесты для Hotel Management API.

5 тест-кейсов:
  1. Регистрация пользователя
  2. Аутентификация пользователя
  3. Получение списка номеров
  4. Получение списка услуг
  5. Получение профиля

2 юнит-теста:
  1. Хеширование пароля
  2. Создание/проверка JWT-токена
"""

import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_token


# ═══════════════════════════════════════════════════════════════════════════════
# Юнит-тесты
# ═══════════════════════════════════════════════════════════════════════════════

class TestPasswordHashing:
    """Юнит-тест 1: Хеширование и верификация паролей."""

    def test_hash_and_verify(self):
        password = "Str0ng_P@ssw0rd!"
        hashed = hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False

    def test_different_hashes_for_same_password(self):
        password = "TestPassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTToken:
    """Юнит-тест 2: Создание и декодирование JWT-токенов."""

    def test_create_and_decode_token(self):
        payload = {"sub": "42", "email": "test@example.com", "role": "guest"}
        token = create_access_token(payload)

        decoded = decode_token(token)
        assert decoded["sub"] == "42"
        assert decoded["email"] == "test@example.com"
        assert decoded["role"] == "guest"
        assert "exp" in decoded

    def test_invalid_token_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid.token.value")
        assert exc_info.value.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Тест-кейсы (интеграционные, требуют БД)
# ═══════════════════════════════════════════════════════════════════════════════

# Тест-кейс 1: Регистрация нового пользователя
# Предусловие: БД запущена и доступна
# Шаги: POST /api/auth/register с валидными данными
# Ожидаемый результат: 201, возврат токена и данных пользователя

# Тест-кейс 2: Аутентификация существующего пользователя
# Предусловие: Пользователь зарегистрирован в системе
# Шаги: POST /api/auth/login с email и паролем
# Ожидаемый результат: 200, возврат JWT-токена

# Тест-кейс 3: Получение каталога номеров
# Предусловие: В БД есть номера с категориями
# Шаги: GET /api/rooms/ без авторизации
# Ожидаемый результат: 200, массив номеров с полями id, room_number, category_name

# Тест-кейс 4: Получение списка услуг
# Предусловие: В БД есть активные услуги
# Шаги: GET /api/services/
# Ожидаемый результат: 200, массив услуг с полями id, name, price

# Тест-кейс 5: Получение профиля авторизованного пользователя
# Предусловие: Пользователь авторизован (имеет JWT-токен)
# Шаги: GET /api/users/me с заголовком Authorization: Bearer <token>
# Ожидаемый результат: 200, данные профиля
