"""
config.py - ИСПРАВЛЕННАЯ конфигурация для бота
Использует правильные КЛЮЧИ переменных окружения, а не значения!
"""

import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()


class Config:
    """Конфигурация приложения"""
    
    # Telegram настройки - ИСПРАВЛЕНО: используем КЛЮЧИ, а не значения!
    TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
    
    # Supabase настройки - ИСПРАВЛЕНО: используем КЛЮЧИ!
    SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    SUPABASE_KEY = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
    
    # Flask настройки
    FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Encryption key (если используется)
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
    
    # Настройки бота
    ADMIN_IDS = [7746862973]  # ID администратора
    SUPPORT_CONTACT = "@banana_pwr"
    ENABLED_COMMANDS = ['start', 'status', 'trade', 'stop']
    
    @classmethod
    def validate(cls):
        """Проверка наличия необходимых переменных окружения"""
        required_vars = {
            'BOT_TOKEN': cls.TELEGRAM_TOKEN,
            'NEXT_PUBLIC_SUPABASE_URL': cls.SUPABASE_URL,
            'NEXT_PUBLIC_SUPABASE_ANON_KEY': cls.SUPABASE_KEY
        }
        
        missing = [key for key, value in required_vars.items() if not value]
        
        if missing:
            raise ValueError(
                f"❌ Отсутствуют обязательные переменные окружения: {', '.join(missing)}\n"
                f"Проверьте файл .env или настройки BotHost.ru"
            )
        
        return True


# Глобальный экземпляр конфигурации
config = Config()