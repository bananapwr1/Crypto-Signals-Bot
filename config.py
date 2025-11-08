# config.py - ИСПРАВЛЕННАЯ версия
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Основные ключи - ИСПРАВЛЕНО: используем названия переменных, а не значения!
    TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')  # было: os.getenv('8218904195:AAGinuQn0eGe8qYm-P5EOPwVq3awPyJ5fD8')
    SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')  # было: os.getenv('https://qdilspmiaoxrnotarjnq.supabase.co')
    SUPABASE_KEY = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')  # было: os.getenv('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...')
    
    # Дополнительные настройки
    ADMIN_IDS = [7746862973]  # ваш Telegram ID
    SUPPORT_CONTACT = "@banana_pwr"
    
    # Настройки кеширования
    CACHE_TTL = {
        'signals': 300,
        'market_data': 60,
        'user_data': 3600
    }