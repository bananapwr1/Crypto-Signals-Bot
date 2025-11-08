# config.py - минимальная но достаточная конфигурация
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Основные ключи
    TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
    SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    SUPABASE_KEY = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
    DATABASE_URL = os.getenv('DATABASE_URL')

    # Настройки бота
    ADMIN_IDS = [7746862973]  # Замените на ваш Telegram ID
    ENABLED_COMMANDS = ['start', 'status', 'profile', 'signals']

    # Настройки кеширования
    CACHE_TTL = {
        'signals': 300,      # 5 минут
        'market_data': 60,   # 1 минута
        'user_data': 3600    # 1 час
    }

    # Торговые настройки
    TRADING = {
        'default_symbols': ['BTC/USDT', 'ETH/USDT', 'ADA/USDT'],
        'timeframes': ['1h', '4h', '1d'],
        'min_signal_strength': 0.6
    }