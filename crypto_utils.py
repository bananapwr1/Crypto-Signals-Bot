"""
crypto_utils.py - Криптографические утилиты
Версия: 1.0
Дата: 2025-12-09

Обеспечивает:
- Шифрование/дешифрование SSID для Pocket Option
- Генерация ключей
- Безопасное хранение паролей
"""

import os
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# Получаем ключ шифрования из переменной окружения
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')


def generate_key(password: str = None, salt: bytes = None) -> bytes:
    """
    Генерирует ключ шифрования из пароля
    
    Args:
        password: Пароль для генерации ключа (если None, используется ENCRYPTION_KEY из env)
        salt: Соль для KDF (если None, используется фиксированная соль)
    
    Returns:
        bytes: Ключ шифрования (32 байта)
    """
    if password is None:
        password = ENCRYPTION_KEY or 'default-encryption-key-change-me'
    
    if salt is None:
        # Фиксированная соль (в продакшене лучше хранить отдельно)
        salt = b'pocket-option-ssid-salt-v1'
    
    # Используем PBKDF2 для генерации ключа
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def get_cipher() -> Optional[Fernet]:
    """
    Получить объект Fernet для шифрования/дешифрования
    
    Returns:
        Fernet: Объект шифрования или None при ошибке
    """
    try:
        key = generate_key()
        return Fernet(key)
    except Exception as e:
        logger.error(f"❌ Ошибка создания cipher: {e}")
        return None


def encrypt_ssid(ssid: str) -> Optional[str]:
    """
    Шифрует SSID для безопасного хранения в БД
    
    Args:
        ssid: SSID в открытом виде
    
    Returns:
        str: Зашифрованный SSID (base64) или None при ошибке
    """
    if not ssid:
        return None
    
    try:
        cipher = get_cipher()
        if not cipher:
            logger.error("❌ Не удалось получить cipher для шифрования")
            return None
        
        encrypted = cipher.encrypt(ssid.encode())
        encrypted_base64 = base64.urlsafe_b64encode(encrypted).decode()
        
        logger.info(f"✅ SSID успешно зашифрован (длина: {len(encrypted_base64)})")
        return encrypted_base64
    
    except Exception as e:
        logger.error(f"❌ Ошибка шифрования SSID: {e}")
        return None


def decrypt_ssid(encrypted_ssid: str) -> Optional[str]:
    """
    Дешифрует SSID из БД
    
    Args:
        encrypted_ssid: Зашифрованный SSID (base64)
    
    Returns:
        str: SSID в открытом виде или None при ошибке
    """
    if not encrypted_ssid:
        return None
    
    try:
        cipher = get_cipher()
        if not cipher:
            logger.error("❌ Не удалось получить cipher для дешифрования")
            return None
        
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_ssid.encode())
        decrypted = cipher.decrypt(encrypted_bytes).decode()
        
        logger.info(f"✅ SSID успешно дешифрован (длина: {len(decrypted)})")
        return decrypted
    
    except Exception as e:
        logger.error(f"❌ Ошибка дешифрования SSID: {e}")
        return None


def validate_ssid(ssid: str) -> bool:
    """
    Валидирует формат SSID
    
    Args:
        ssid: SSID для проверки
    
    Returns:
        bool: True если SSID валиден
    """
    if not ssid or not isinstance(ssid, str):
        return False
    
    # SSID должен быть достаточно длинным (обычно 32+ символов)
    if len(ssid) < 20:
        logger.warning(f"⚠️ SSID слишком короткий: {len(ssid)} символов")
        return False
    
    # SSID не должен содержать пробелы
    if ' ' in ssid:
        logger.warning("⚠️ SSID содержит пробелы")
        return False
    
    return True


# ========================================
# ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ
# ========================================

def hash_password(password: str) -> str:
    """
    Хэширует пароль для безопасного хранения
    (опционально, если нужно хранить пароли пользователей)
    
    Args:
        password: Пароль в открытом виде
    
    Returns:
        str: Хэш пароля (bcrypt)
    """
    import bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()


def verify_password(password: str, hashed: str) -> bool:
    """
    Проверяет пароль по хэшу
    
    Args:
        password: Пароль в открытом виде
        hashed: Хэш пароля
    
    Returns:
        bool: True если пароль верный
    """
    import bcrypt
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ========================================
# ТЕСТИРОВАНИЕ
# ========================================

def test_crypto_utils():
    """Тестирует функции шифрования"""
    logger.info("🧪 Тестирование crypto_utils...")
    
    # Тест шифрования SSID
    test_ssid = "42ba6c51b138c4907298829c6d1c7e09a4f5e3d8"
    
    logger.info(f"📝 Исходный SSID: {test_ssid}")
    
    # Шифруем
    encrypted = encrypt_ssid(test_ssid)
    logger.info(f"🔒 Зашифрованный: {encrypted}")
    
    # Дешифруем
    decrypted = decrypt_ssid(encrypted)
    logger.info(f"🔓 Дешифрованный: {decrypted}")
    
    # Проверяем
    if decrypted == test_ssid:
        logger.info("✅ Тест пройден: шифрование/дешифрование работает корректно")
        return True
    else:
        logger.error("❌ Тест провален: SSID не совпадают")
        return False


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_crypto_utils()
