import os
import logging
import pandas as pd
import numpy as np
import yfinance as yf
import asyncio
import sqlite3
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.patheffects as pe
import io
import time
import random
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import warnings
import uuid
from yookassa import Configuration, Payment
from webhook_system import webhook_system
from crypto_utils import encrypt_ssid, decrypt_ssid
warnings.filterwarnings('ignore')

load_dotenv()
matplotlib.use('Agg')

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
SUPPORT_CONTACT = "@banana_pwr"

# Московский часовой пояс (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))

# Реферальная ссылка Pocket Option
POCKET_OPTION_REF_LINK = "https://pocket-friends.com/r/ugauihalod"

# Промокод для новых пользователей
PROMO_CODE = "FRIENDUGAUIHALOD"

# Команды бота по умолчанию (для сброса настроек)
DEFAULT_BOT_COMMANDS = [
    ("start", "🏠 Главное меню"),
    ("plans", "💎 Тарифы и подписки"),
    ("bank", "💰 Управление банком"),
    ("autotrade", "🤖 Автоторговля (VIP)"),
    ("settings", "⚙️ Настройки"),
    ("short", "⚡ SHORT сигнал (1-5 мин)"),
    ("long", "🔵 LONG сигнал (1-4 часа)"),
    ("my_longs", "📋 Мои LONG позиции"),
    ("my_stats", "📊 Моя статистика"),
    ("help", "❓ Помощь и инструкции"),
]

# Система тарифов
SUBSCRIPTION_PLANS = {
    'short': {
        '1m': 4990,
        '6m': 26946,
        '12m': 47904,
        'name': 'SHORT',
        'description': 'Быстрые сигналы (1-5 мин) с мартингейлом',
        'emoji': '⚡️'
    },
    'long': {
        '1m': 4990,
        '6m': 26946,
        '12m': 47904,
        'name': 'LONG',
        'description': 'Длинные сигналы (1-4 часа) с процентной ставкой',
        'emoji': '🔵'
    },
    'vip': {
        '1m': 9990,
        '6m': 53946,
        '12m': 95904,
        'name': 'VIP',
        'description': 'Все сигналы SHORT + LONG + приоритет + гибкие настройки стратегий и статистика',
        'emoji': '💎'
    }
}

# Акция для новых пользователей
NEW_USER_PROMO = {
    'price': 1490,
    'duration_days': 30,
    'plan': 'short',
    'discount_percent': 70
}

PAYOUT_PERCENT = 92

# Система мультиязычности
TRANSLATIONS = {
    'ru': {
        'choose_language': '🌍 Выберите язык / Choose language:',
        'language_selected': '✅ Язык установлен: Русский',
        'choose_currency': '💱 Выберите валюту для отображения цен:',
        'currency_selected': '✅ Валюта установлена',
        'welcome': '👋 Добро пожаловать в бот торговых сигналов!',
        'welcome_desc': 'Выберите тариф для начала работы:',
        'short_plan': '⚡️ SHORT',
        'short_desc': 'Быстрые сигналы (1-5 мин)\nМартингейл x3 стратегия',
        'long_plan': '🔵 LONG',
        'long_desc': 'Длинные сигналы (1-4 часа)\n2.5% процентная ставка',
        'vip_plan': '💎 VIP',
        'vip_desc': 'Все сигналы + 5 ежедневных рассылок',
        'free_plan': '🆓 FREE',
        'free_desc': 'LONG сигналы (10 рассылок/день)',
        'buy_subscription': 'Купить подписку',
        'my_stats': 'Моя статистика',
        'my_longs': 'Мои лонги',
        'help': 'Помощь',
        'settings': 'Настройки',
        'short_signal': 'Короткий сигнал',
        'long_signal': 'Длинный сигнал',
        'get_signal': '🎯 Получить сигнал',
        'back': '◀️ Назад',
        'call': '🟢 CALL',
        'put': '🔴 PUT',
        'price': 'Цена',
        'subscription': 'Подписка',
        'expires': 'Истекает',
        'balance': 'Баланс',
        'win_rate': 'Доходность сигналов',
        'profit': 'Прибыль',
        'month': 'месяц',
        'months': 'месяцев',
    },
    'en': {
        'choose_language': '🌍 Choose language:',
        'language_selected': '✅ Language set: English',
        'choose_currency': '💱 Choose currency for price display:',
        'currency_selected': '✅ Currency set',
        'welcome': '👋 Welcome to Trading Signals Bot!',
        'welcome_desc': 'Choose a plan to get started:',
        'short_plan': '⚡️ SHORT',
        'short_desc': 'Fast signals (1-5 min)\nMartingale x3 strategy',
        'long_plan': '🔵 LONG',
        'long_desc': 'Long signals (1-4 hours)\n2.5% percentage rate',
        'vip_plan': '💎 VIP',
        'vip_desc': 'All signals + 5 daily broadcasts',
        'free_plan': '🆓 FREE',
        'free_desc': 'LONG signals (10 broadcasts/day)',
        'buy_subscription': 'Buy Subscription',
        'my_stats': 'My Statistics',
        'my_longs': 'My Longs',
        'help': 'Help',
        'settings': 'Settings',
        'short_signal': 'Short Signal',
        'long_signal': 'Long Signal',
        'get_signal': '🎯 Get Signal',
        'back': '◀️ Back',
        'call': '🟢 CALL',
        'put': '🔴 PUT',
        'price': 'Price',
        'subscription': 'Subscription',
        'expires': 'Expires',
        'balance': 'Balance',
        'win_rate': 'Signal Profitability',
        'profit': 'Profit',
        'month': 'month',
        'months': 'months',
    },
    'es': {
        'choose_language': '🌍 Elige idioma:',
        'language_selected': '✅ Idioma establecido: Español',
        'choose_currency': '💱 Elige la moneda para mostrar precios:',
        'currency_selected': '✅ Moneda establecida',
        'welcome': '👋 ¡Bienvenido al Bot de Señales de Trading!',
        'welcome_desc': 'Elige un plan para comenzar:',
        'short_plan': '⚡️ CORTO',
        'short_desc': 'Señales rápidas (1-5 min)\nEstrategia Martingala x3',
        'long_plan': '🔵 LARGO',
        'long_desc': 'Señales largas (1-4 horas)\nTasa porcentual del 2.5%',
        'vip_plan': '💎 VIP',
        'vip_desc': 'Todas las señales + 5 transmisiones diarias',
        'free_plan': '🆓 GRATIS',
        'free_desc': 'Señales LONG (10 transmisiones/día)',
        'buy_subscription': 'Comprar Suscripción',
        'my_stats': 'Mis Estadísticas',
        'my_longs': 'Mis Largos',
        'help': 'Ayuda',
        'settings': 'Configuración',
        'short_signal': 'Señal Corta',
        'long_signal': 'Señal Larga',
        'get_signal': '🎯 Obtener Señal',
        'back': '◀️ Atrás',
        'call': '🟢 CALL',
        'put': '🔴 PUT',
        'price': 'Precio',
        'subscription': 'Suscripción',
        'expires': 'Expira',
        'balance': 'Saldo',
        'win_rate': 'Rentabilidad de Señales',
        'profit': 'Ganancia',
        'month': 'mes',
        'months': 'meses',
    },
    'pt': {
        'choose_language': '🌍 Escolha o idioma:',
        'language_selected': '✅ Idioma definido: Português',
        'choose_currency': '💱 Escolha a moeda para exibição de preços:',
        'currency_selected': '✅ Moeda definida',
        'welcome': '👋 Bem-vindo ao Bot de Sinais de Trading!',
        'welcome_desc': 'Escolha um plano para começar:',
        'short_plan': '⚡️ CURTO',
        'short_desc': 'Sinais rápidos (1-5 min)\nEstratégia Martingale x3',
        'long_plan': '🔵 LONGO',
        'long_desc': 'Sinais longos (1-4 horas)\nTaxa percentual de 2.5%',
        'vip_plan': '💎 VIP',
        'vip_desc': 'Todos os sinais + 5 transmissões diárias',
        'free_plan': '🆓 GRÁTIS',
        'free_desc': 'Sinais LONG (10 transmissões/dia)',
        'buy_subscription': 'Comprar Assinatura',
        'my_stats': 'Minhas Estatísticas',
        'my_longs': 'Meus Longos',
        'help': 'Ajuda',
        'settings': 'Configurações',
        'short_signal': 'Sinal Curto',
        'long_signal': 'Sinal Longo',
        'get_signal': '🎯 Obter Sinal',
        'back': '◀️ Voltar',
        'call': '🟢 CALL',
        'put': '🔴 PUT',
        'price': 'Preço',
        'subscription': 'Assinatura',
        'expires': 'Expira',
        'balance': 'Saldo',
        'win_rate': 'Rentabilidade de Sinais',
        'profit': 'Lucro',
        'month': 'mês',
        'months': 'meses',
    }
}

# Курсы валют для конвертации (примерные, можно получать через API)
CURRENCY_RATES = {
    'RUB': 1.0,
    'USD': 0.011,
}

CURRENCY_SYMBOLS = {
    'RUB': '₽',
    'USD': '$',
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ЮКасса настройки
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

# Конфигурация ЮКассы
if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
    try:
        Configuration.configure(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
        logger.info("✅ YooKassa configured successfully")
    except Exception as e:
        logger.error(f"❌ YooKassa configuration failed: {e}")
else:
    logger.warning("⚠️ YooKassa credentials not found - payment will use manual mode")

class CryptoSignalsBot:
    def __init__(self):
        # АКТУАЛЬНЫЕ АКТИВЫ POCKET OPTION (синхронизировано с MARKET_ASSETS)
        # Инициализация отложена - вызывается initialize_assets() после определения MARKET_ASSETS
        self.assets = {}
        
        self.timeframes = {
            "1M": "1m", "3M": "3m", "5M": "5m", "15M": "15m", 
            "30M": "30m", "1H": "1h", "4H": "4h", 
            "1D": "1d", "1W": "1wk"
        }
        
        self.setup_database()
        
    def setup_database(self):
        self.conn = sqlite3.connect('crypto_signals_bot.db', check_same_thread=False)
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_date DATETIME,
                subscription_end DATETIME,
                is_premium BOOLEAN DEFAULT 0,
                free_trials_used INTEGER DEFAULT 0,
                signals_used INTEGER DEFAULT 0,
                last_signal_date DATETIME,
                initial_balance REAL DEFAULT NULL,
                current_balance REAL DEFAULT NULL
            )
        ''')
        
        try:
            cursor.execute('SELECT initial_balance FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN initial_balance REAL DEFAULT NULL')
            cursor.execute('ALTER TABLE users ADD COLUMN current_balance REAL DEFAULT NULL')
            logger.info("✅ Added balance columns to users table")
        
        try:
            cursor.execute('SELECT short_base_stake FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN short_base_stake REAL DEFAULT 100')
            cursor.execute('ALTER TABLE users ADD COLUMN current_martingale_level INTEGER DEFAULT 0')
            cursor.execute('ALTER TABLE users ADD COLUMN consecutive_losses INTEGER DEFAULT 0')
            cursor.execute('ALTER TABLE users ADD COLUMN currency TEXT DEFAULT "RUB"')
            logger.info("✅ Added martingale and currency columns to users table")
        
        try:
            cursor.execute('SELECT martingale_type FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN martingale_type INTEGER DEFAULT 3')
            cursor.execute('ALTER TABLE users ADD COLUMN long_percentage REAL DEFAULT 2.5')
            logger.info("✅ Added strategy selection columns to users table")
        
        try:
            cursor.execute('SELECT subscription_type FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN subscription_type TEXT DEFAULT NULL')
            cursor.execute('ALTER TABLE users ADD COLUMN referral_code TEXT DEFAULT NULL')
            cursor.execute('ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT NULL')
            cursor.execute('ALTER TABLE users ADD COLUMN new_user_discount_used BOOLEAN DEFAULT 0')
            cursor.execute('ALTER TABLE users ADD COLUMN referral_earnings REAL DEFAULT 0')
            cursor.execute('ALTER TABLE users ADD COLUMN pocket_option_registered BOOLEAN DEFAULT 0')
            cursor.execute('ALTER TABLE users ADD COLUMN pocket_option_login TEXT DEFAULT NULL')
            logger.info("✅ Added subscription and referral columns to users table")
        
        try:
            cursor.execute('SELECT pocket_option_login FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN pocket_option_login TEXT DEFAULT NULL')
            logger.info("✅ Added pocket_option_login column to users table")
        
        try:
            cursor.execute('SELECT last_upgrade_offer FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN last_upgrade_offer TEXT DEFAULT NULL')
            logger.info("✅ Added last_upgrade_offer column to users table")
        
        try:
            cursor.execute('SELECT language FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN language TEXT DEFAULT "ru"')
            logger.info("✅ Added language column to users table")
        
        try:
            cursor.execute('SELECT free_short_signals_today FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN free_short_signals_today INTEGER DEFAULT 0')
            cursor.execute('ALTER TABLE users ADD COLUMN free_short_signals_date TEXT DEFAULT NULL')
            logger.info("✅ Added FREE short signals limit columns to users table")
        
        try:
            cursor.execute('SELECT free_long_signals_today FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN free_long_signals_today INTEGER DEFAULT 0')
            cursor.execute('ALTER TABLE users ADD COLUMN free_long_signals_date TEXT DEFAULT NULL')
            logger.info("✅ Added FREE long signals limit columns to users table")
        
        try:
            cursor.execute('SELECT banned FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN banned BOOLEAN DEFAULT 0')
            logger.info("✅ Added banned column to users table")
        
        try:
            cursor.execute('SELECT trading_strategy FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN trading_strategy TEXT DEFAULT NULL')
            logger.info("✅ Added trading_strategy column to users table")
        
        try:
            cursor.execute('SELECT martingale_multiplier FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN martingale_multiplier INTEGER DEFAULT 3')
            logger.info("✅ Added martingale_multiplier column to users table")
        
        try:
            cursor.execute('SELECT martingale_base_stake FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN martingale_base_stake REAL DEFAULT NULL')
            logger.info("✅ Added martingale_base_stake column to users table")
        
        try:
            cursor.execute('SELECT percentage_value FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN percentage_value REAL DEFAULT 2.5')
            logger.info("✅ Added percentage_value column to users table")
        
        try:
            cursor.execute('SELECT auto_trading_enabled FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN auto_trading_enabled BOOLEAN DEFAULT 0')
            cursor.execute('ALTER TABLE users ADD COLUMN pocket_option_email TEXT DEFAULT NULL')
            cursor.execute('ALTER TABLE users ADD COLUMN auto_trading_mode TEXT DEFAULT "demo"')
            logger.info("✅ Added auto_trading columns to users table")
        
        try:
            cursor.execute('SELECT dalembert_base_stake FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN dalembert_base_stake REAL DEFAULT 100')
            cursor.execute('ALTER TABLE users ADD COLUMN dalembert_unit REAL DEFAULT 50')
            cursor.execute('ALTER TABLE users ADD COLUMN current_dalembert_level INTEGER DEFAULT 0')
            logger.info("✅ Added D'Alembert strategy columns to users table")
        
        try:
            cursor.execute('SELECT auto_trading_strategy FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN auto_trading_strategy TEXT DEFAULT "percentage"')
            logger.info("✅ Added auto_trading_strategy column to users table")
        
        try:
            cursor.execute('SELECT pocket_option_ssid FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN pocket_option_ssid TEXT DEFAULT NULL')
            cursor.execute('ALTER TABLE users ADD COLUMN pocket_option_connected BOOLEAN DEFAULT 0')
            logger.info("✅ Added Pocket Option SSID columns to users table")
        
        try:
            cursor.execute('SELECT ssid_automation_purchased FROM users LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE users ADD COLUMN ssid_automation_purchased BOOLEAN DEFAULT 0')
            cursor.execute('ALTER TABLE users ADD COLUMN ssid_automation_purchase_date DATETIME DEFAULT NULL')
            logger.info("✅ Added SSID Automation purchase columns to users table")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                asset TEXT,
                timeframe TEXT,
                signal_type TEXT,
                confidence REAL,
                entry_price REAL,
                result TEXT,
                profit_loss REAL,
                stake_amount REAL,
                signal_date DATETIME,
                close_date DATETIME,
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        try:
            cursor.execute('SELECT expiration_time FROM signal_history LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE signal_history ADD COLUMN expiration_time TEXT')
            logger.info("✅ Added expiration_time column to signal_history table")
        
        try:
            cursor.execute('SELECT signal_tier FROM signal_history LIMIT 1')
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE signal_history ADD COLUMN signal_tier TEXT DEFAULT "vip"')
            logger.info("✅ Added signal_tier column to signal_history table")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signal_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                total_signals INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                adaptive_weight REAL DEFAULT 1.0,
                last_updated TEXT NOT NULL,
                UNIQUE(asset, timeframe)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                timeframe_type T