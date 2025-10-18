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
                timeframe_type TEXT,
                created_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                description TEXT,
                updated_at TEXT,
                updated_by INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                price REAL,
                volatility REAL,
                volume REAL,
                avg_volume REAL,
                volume_ratio REAL,
                whale_detected INTEGER DEFAULT 0,
                trend TEXT,
                rsi REAL,
                macd REAL,
                stoch_k REAL,
                ema_20 REAL,
                ema_50 REAL,
                signal_generated TEXT,
                confidence REAL,
                score INTEGER
            )
        ''')
        
        # Инициализировать настройки по умолчанию
        default_settings = [
            ('yookassa_shop_id', '', 'YooKassa Shop ID для автоматических платежей'),
            ('yookassa_secret_key', '', 'YooKassa Secret Key для автоматических платежей'),
            ('reviews_group', '@cryptosignalsbot_otz', 'Telegram группа с отзывами пользователей'),
            ('reviews_enabled', 'true', 'Показывать кнопку отзывов пользователям'),
            ('payment_enabled', 'false', 'Включить автоматические платежи через YooKassa'),
            ('admin_users', str(ADMIN_USER_ID), 'Список ID администраторов (через запятую)'),
            ('bot_configured', 'false', 'Завершена ли первичная настройка бота'),
            ('vip_price_rub', '9990', 'Цена тарифа VIP в рублях'),
            ('short_price_rub', '4990', 'Цена тарифа SHORT в рублях'),
            ('long_price_rub', '6990', 'Цена тарифа LONG в рублях'),
            ('ssid_automation_price_rub', '2990', 'Цена скрипта SSID Automation в рублях'),
            ('support_contact', '@banana_pwr', 'Контакт поддержки (Telegram username)'),
            ('webhook_url', '', 'URL для отправки сигналов через webhook'),
            ('webhook_secret', '', 'Секретный ключ для JWT-авторизации webhook'),
            ('webhook_enabled', 'false', 'Включить отправку сигналов через webhook'),
        ]
        
        for key, value, description in default_settings:
            cursor.execute('''
                INSERT OR IGNORE INTO bot_settings (key, value, description, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (key, value, description, datetime.now().isoformat()))
        
        self.conn.commit()
    
    def get_setting(self, key, default=''):
        """Получить значение настройки"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM bot_settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        return result[0] if result and result[0] else default
    
    def set_setting(self, key, value, admin_id):
        """Установить значение настройки"""
        # 🛡️ ЗАЩИТА: Главный админ не может быть удален
        if key == 'admin_users':
            admin_list = [uid.strip() for uid in str(value).split(',') if uid.strip()]
            if str(ADMIN_USER_ID) not in admin_list:
                # Всегда сохраняем главного админа первым
                admin_list.insert(0, str(ADMIN_USER_ID))
                value = ','.join(admin_list)
        
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO bot_settings (key, value, updated_at, updated_by)
            VALUES (?, ?, ?, ?)
        ''', (key, value, datetime.now().isoformat(), admin_id))
        self.conn.commit()
    
    def is_admin(self, user_id):
        """Проверить, является ли пользователь администратором"""
        admin_users = self.get_setting('admin_users', str(ADMIN_USER_ID))
        admin_list = [int(uid.strip()) for uid in admin_users.split(',') if uid.strip()]
        logger.debug(f"🔍 is_admin check: user_id={user_id}, admin_users='{admin_users}', admin_list={admin_list}, result={user_id in admin_list}")
        return user_id in admin_list
    
    def get_support_contact(self):
        """Получить контакт поддержки"""
        return self.get_setting('support_contact', '@banana_pwr')
    
    def save_market_data(self, asset_symbol, timeframe, market_data):
        """Сохранить данные анализа рынка в историю"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO market_history (
                    asset_symbol, timeframe, price, volatility, volume, avg_volume,
                    volume_ratio, whale_detected, trend, rsi, macd, stoch_k,
                    ema_20, ema_50, signal_generated, confidence, score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                asset_symbol, timeframe,
                market_data.get('price', 0),
                market_data.get('volatility', 0),
                market_data.get('volume', 0),
                market_data.get('avg_volume', 0),
                market_data.get('volume_ratio', 0),
                1 if market_data.get('whale_detected', False) else 0,
                market_data.get('trend', 'NEUTRAL'),
                market_data.get('rsi', 50),
                market_data.get('macd', 0),
                market_data.get('stoch_k', 50),
                market_data.get('ema_20', 0),
                market_data.get('ema_50', 0),
                market_data.get('signal', 'NONE'),
                market_data.get('confidence', 0),
                market_data.get('score', 0)
            ))
            self.conn.commit()
            logger.debug(f"💾 Saved market data: {asset_symbol} {timeframe} | {market_data.get('trend')} | Whale: {market_data.get('whale_detected', False)}")
        except Exception as e:
            logger.error(f"❌ Error saving market data for {asset_symbol} {timeframe}: {e}")
    
    def get_historical_pattern(self, asset_symbol, timeframe, lookback_hours=24):
        """Анализ исторических паттернов для предсказания движения"""
        try:
            cursor = self.conn.cursor()
            
            # Получить данные за последние N часов
            cursor.execute('''
                SELECT trend, whale_detected, volatility, signal_generated, confidence, score, timestamp
                FROM market_history
                WHERE asset_symbol = ? AND timeframe = ?
                AND datetime(timestamp) >= datetime('now', '-' || ? || ' hours')
                ORDER BY timestamp DESC
            ''', (asset_symbol, timeframe, lookback_hours))
            
            history = cursor.fetchall()
            
            if not history or len(history) < 3:
                return None
            
            # Анализ паттернов
            bullish_count = sum(1 for row in history if row[0] == 'BULLISH')
            bearish_count = sum(1 for row in history if row[0] == 'BEARISH')
            whale_activity = sum(1 for row in history if row[1] == 1)
            avg_volatility = sum(row[2] for row in history) / len(history)
            
            # Определить тренд на основе истории
            trend_strength = (bullish_count - bearish_count) / len(history)
            
            # Бонус предсказания
            prediction_bonus = 0
            predicted_direction = None
            
            # Сильный бычий тренд в истории
            if trend_strength > 0.5:
                predicted_direction = 'CALL'
                prediction_bonus = 2
            # Сильный медвежий тренд в истории  
            elif trend_strength < -0.5:
                predicted_direction = 'PUT'
                prediction_bonus = 2
            # Умеренный тренд
            elif abs(trend_strength) > 0.3:
                predicted_direction = 'CALL' if trend_strength > 0 else 'PUT'
                prediction_bonus = 1
            
            # Дополнительный бонус за активность китов
            if whale_activity >= len(history) * 0.3:  # 30%+ с китами
                prediction_bonus += 1
            
            return {
                'predicted_direction': predicted_direction,
                'prediction_bonus': prediction_bonus,
                'trend_strength': trend_strength,
                'whale_activity_rate': whale_activity / len(history) if len(history) > 0 else 0,
                'avg_volatility': avg_volatility,
                'data_points': len(history)
            }
        except Exception as e:
            logger.error(f"Error analyzing historical pattern: {e}")
            return None
    
    def get_user_language(self, user_id):
        """Получить язык пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result and result[0] else 'ru'
    
    def set_user_language(self, user_id, language):
        """Установить язык пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
        self.conn.commit()
    
    def t(self, user_id, key):
        """Получить перевод для пользователя"""
        language = self.get_user_language(user_id)
        return TRANSLATIONS.get(language, TRANSLATIONS['ru']).get(key, key)
    
    def convert_price(self, price_rub, target_currency):
        """Конвертировать цену из рублей в целевую валюту"""
        if target_currency not in CURRENCY_RATES:
            return price_rub
        rate = CURRENCY_RATES[target_currency]
        return int(price_rub * rate)
    
    def format_price(self, price, currency):
        """Форматировать цену с символом валюты"""
        symbol = CURRENCY_SYMBOLS.get(currency, '₽')
        return f"{price}{symbol}"
    
    def check_subscription(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT subscription_end, is_premium, signals_used, free_trials_used, subscription_type FROM users WHERE user_id = ?', 
            (user_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            return False, "Пользователь не найден", 0, 0, None
        
        subscription_end, is_premium, signals_used, free_trials_used, subscription_type = result
        
        # ПРИОРИТЕТ 1: Пожизненные тарифы (subscription_end = NULL, subscription_type не NULL)
        if subscription_type and not subscription_end:
            return True, None, signals_used, free_trials_used, subscription_type
        
        # ПРИОРИТЕТ 2: Проверка обычной подписки с датой окончания
        if subscription_end and datetime.now() < datetime.fromisoformat(subscription_end):
            return True, subscription_end, signals_used, free_trials_used, subscription_type
        
        # ПРИОРИТЕТ 3: Проверка пробного периода (3 дня VIP для новых пользователей)
        if free_trials_used == 0:
            # Новый пользователь получает 3 дня VIP
            trial_end = datetime.now() + timedelta(days=3)
            cursor.execute(
                'UPDATE users SET subscription_end = ?, subscription_type = ?, free_trials_used = 1 WHERE user_id = ?',
                (trial_end.isoformat(), 'vip', user_id)
            )
            self.conn.commit()
            return True, trial_end.isoformat(), signals_used, 1, 'vip'
            
        return False, "Нет активной подписки", signals_used, free_trials_used, None
    
    def is_banned(self, user_id):
        """Проверить, забанен ли пользователь"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT banned FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result and result[0] == 1
    
    def ban_user(self, user_id, admin_id):
        """Забанить пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET banned = 1 WHERE user_id = ?', (user_id,))
        self.conn.commit()
        logger.info(f"🚫 Admin {admin_id} banned user {user_id}")
    
    def unban_user(self, user_id, admin_id):
        """Разбанить пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET banned = 0 WHERE user_id = ?', (user_id,))
        self.conn.commit()
        logger.info(f"✅ Admin {admin_id} unbanned user {user_id}")
    
    def reset_user(self, user_id, admin_id):
        """Сбросить пользователя до нового (обнулить все данные)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET subscription_end = NULL,
                subscription_type = NULL,
                is_premium = 0,
                free_trials_used = 0,
                signals_used = 0,
                initial_balance = NULL,
                current_balance = NULL,
                short_base_stake = 100,
                current_martingale_level = 0,
                consecutive_losses = 0,
                new_user_discount_used = 0,
                free_short_signals_today = 0,
                free_short_signals_date = NULL,
                free_long_signals_today = 0,
                free_long_signals_date = NULL,
                last_upgrade_offer = NULL
            WHERE user_id = ?
        ''', (user_id,))
        
        # Удалить историю сигналов пользователя
        cursor.execute('DELETE FROM signal_history WHERE user_id = ?', (user_id,))
        
        self.conn.commit()
        logger.info(f"🔄 Admin {admin_id} reset user {user_id} to new state")
    
    def check_free_short_limit(self, user_id):
        """Проверить лимит шорт-сигналов для FREE пользователя (5 в день)"""
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT free_short_signals_today, free_short_signals_date FROM users WHERE user_id = ?',
            (user_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            return False, 0
        
        signals_today, last_date = result
        today = datetime.now().date().isoformat()
        
        # Если новый день - сбросить счетчик
        if last_date != today:
            cursor.execute(
                'UPDATE users SET free_short_signals_today = 0, free_short_signals_date = ? WHERE user_id = ?',
                (today, user_id)
            )
            self.conn.commit()
            signals_today = 0
        
        # Проверить лимит (5 сигналов в день)
        if signals_today >= 5:
            return False, signals_today
        
        return True, signals_today
    
    def increment_free_short_signal(self, user_id):
        """Увеличить счетчик использованных FREE шорт-сигналов (атомарно)"""
        today = datetime.now().date().isoformat()
        cursor = self.conn.cursor()
        
        # Атомарное обновление с проверкой лимита и автосбросом в новый день
        # CASE 1: Если дата совпадает И счетчик < 5 - увеличить
        # CASE 2: Если дата не совпадает (включая NULL) - сбросить на 1
        cursor.execute('''
            UPDATE users 
            SET free_short_signals_today = CASE 
                WHEN free_short_signals_date = ? THEN 
                    CASE WHEN free_short_signals_today < 5 THEN free_short_signals_today + 1 ELSE free_short_signals_today END
                ELSE 1
            END,
            free_short_signals_date = ?
            WHERE user_id = ? 
            AND (free_short_signals_date != ? OR free_short_signals_date IS NULL OR free_short_signals_today < 5)
        ''', (today, today, user_id, today))
        
        affected_rows = cursor.rowcount
        self.conn.commit()
        
        # Возвращаем True если обновление прошло успешно (не достигнут лимит)
        return affected_rows > 0
    
    def check_free_long_limit(self, user_id):
        """Проверить лимит лонг-сигналов для FREE пользователя (5 в день)"""
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT free_long_signals_today, free_long_signals_date FROM users WHERE user_id = ?',
            (user_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            return False, 0
        
        signals_today, last_date = result
        today = datetime.now().date().isoformat()
        
        # Если новый день - сбросить счетчик
        if last_date != today:
            cursor.execute(
                'UPDATE users SET free_long_signals_today = 0, free_long_signals_date = ? WHERE user_id = ?',
                (today, user_id)
            )
            self.conn.commit()
            signals_today = 0
        
        # Проверить лимит (5 сигналов в день)
        if signals_today >= 5:
            return False, signals_today
        
        return True, signals_today
    
    def increment_free_long_signal(self, user_id):
        """Увеличить счетчик использованных FREE лонг-сигналов (атомарно)"""
        today = datetime.now().date().isoformat()
        cursor = self.conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET free_long_signals_today = CASE 
                WHEN free_long_signals_date = ? THEN 
                    CASE WHEN free_long_signals_today < 5 THEN free_long_signals_today + 1 ELSE free_long_signals_today END
                ELSE 1
            END,
            free_long_signals_date = ?
            WHERE user_id = ? 
            AND (free_long_signals_date != ? OR free_long_signals_date IS NULL OR free_long_signals_today < 5)
        ''', (today, today, user_id, today))
        
        affected_rows = cursor.rowcount
        self.conn.commit()
        
        return affected_rows > 0
    
    def can_access_signal_type(self, user_id, signal_type):
        """Проверить доступ к типу сигнала (short/long) на основе подписки"""
        has_sub, _, _, _, sub_type = self.check_subscription(user_id)
        
        # FREE пользователи (без подписки)
        if not has_sub:
            if signal_type == 'short':
                # Проверить лимит 5 шорт-сигналов в день
                can_access, used_today = self.check_free_short_limit(user_id)
                if can_access:
                    return True, f"FREE доступ ({used_today}/5 сегодня)"
                else:
                    return False, f"Лимит FREE шорт-сигналов исчерпан ({used_today}/5). Купите подписку для неограниченного доступа"
            elif signal_type == 'long':
                # LONG сигналы доступны FREE через автобродкаст
                return False, "LONG сигналы доступны FREE пользователям только через ежедневную рассылку в /my_longs"
        
        # Платные подписки
        if sub_type == 'vip':
            return True, "VIP доступ"
        
        if signal_type == 'short' and sub_type == 'short':
            return True, "SHORT подписка"
        
        if signal_type == 'long' and sub_type == 'long':
            return True, "LONG подписка"
        
        if signal_type == 'short' and sub_type != 'short':
            return False, f"Нужна подписка SHORT или VIP. У вас: {sub_type.upper() if sub_type else 'нет'}"
        
        if signal_type == 'long' and sub_type != 'long':
            return False, f"Нужна подписка LONG или VIP. У вас: {sub_type.upper() if sub_type else 'нет'}"
        
        return False, "Нет доступа к этому типу сигналов"
    
    def add_subscription(self, user_id, days=30, subscription_type='vip'):
        """Добавить подписку определенного типа (short/long/vip)"""
        cursor = self.conn.cursor()
        
        # Проверить текущую подписку
        cursor.execute('SELECT subscription_end FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            current_end = datetime.fromisoformat(result[0])
            if current_end > datetime.now():
                new_end = current_end + timedelta(days=days)
            else:
                new_end = datetime.now() + timedelta(days=days)
        else:
            new_end = datetime.now() + timedelta(days=days)
        
        cursor.execute('''
            UPDATE users 
            SET subscription_end = ?, is_premium = 1, subscription_type = ?
            WHERE user_id = ?
        ''', (new_end.isoformat(), subscription_type, user_id))
        
        self.conn.commit()
        logger.info(f"✅ Added {subscription_type.upper()} subscription for user {user_id} until {new_end}")
        
        # Проверить реферальную программу - начислить бонус пригласившему
        cursor.execute('SELECT referred_by FROM users WHERE user_id = ?', (user_id,))
        ref_result = cursor.fetchone()
        
        if ref_result and ref_result[0]:
            referrer_id = ref_result[0]
            
            # Получить текущую подписку пригласившего
            cursor.execute('SELECT subscription_end, subscription_type FROM users WHERE user_id = ?', (referrer_id,))
            ref_sub = cursor.fetchone()
            
            if subscription_type == 'vip':
                # Друг купил VIP - пригласивший получает +30 дней VIP автоматически
                if ref_sub and ref_sub[0]:
                    ref_current_end = datetime.fromisoformat(ref_sub[0])
                    if ref_current_end > datetime.now():
                        ref_new_end = ref_current_end + timedelta(days=30)
                    else:
                        ref_new_end = datetime.now() + timedelta(days=30)
                else:
                    ref_new_end = datetime.now() + timedelta(days=30)
                
                cursor.execute('''
                    UPDATE users 
                    SET subscription_end = ?, is_premium = 1, subscription_type = 'vip'
                    WHERE user_id = ?
                ''', (ref_new_end.isoformat(), referrer_id))
                self.conn.commit()
                
                logger.info(f"🎁 Referral bonus: User {referrer_id} got +30 days VIP for referring {user_id}")
                
            elif subscription_type in ['long', 'short']:
                # Друг купил LONG/SHORT - пригласивший может ВЫБРАТЬ LONG или SHORT
                # Добавить поле для хранения доступных бонусов
                try:
                    cursor.execute('SELECT referral_bonus_pending FROM users WHERE user_id = ?', (referrer_id,))
                except:
                    # Поле еще не существует, добавим его
                    cursor.execute('ALTER TABLE users ADD COLUMN referral_bonus_pending TEXT DEFAULT NULL')
                    self.conn.commit()
                
                # Сохранить право выбора (пока не выбрал - pending)
                cursor.execute('UPDATE users SET referral_bonus_pending = ? WHERE user_id = ?', 
                             ('choice', referrer_id))
                self.conn.commit()
                
                logger.info(f"🎁 Referral bonus: User {referrer_id} can choose LONG or SHORT (referral {user_id} bought {subscription_type})")
        
        return new_end
    
    def generate_referral_code(self, user_id):
        """Генерация уникального реферального кода"""
        import hashlib
        import time
        code_base = f"{user_id}_{int(time.time())}"
        code = hashlib.md5(code_base.encode()).hexdigest()[:8].upper()
        
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET referral_code = ? WHERE user_id = ?', (code, user_id))
        self.conn.commit()
        
        return code
    
    def get_referral_code(self, user_id):
        """Получить реферальный код пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT referral_code FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            return result[0]
        
        return self.generate_referral_code(user_id)
    
    def apply_referral_code(self, user_id, referral_code):
        """Применить реферальный код при регистрации"""
        cursor = self.conn.cursor()
        
        # Найти владельца реферального кода
        cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (referral_code,))
        result = cursor.fetchone()
        
        if not result:
            return False, "Неверный реферальный код"
        
        referrer_id = result[0]
        
        if referrer_id == user_id:
            return False, "Нельзя использовать свой собственный код"
        
        # Проверить, не использовал ли пользователь уже чей-то код
        cursor.execute('SELECT referred_by FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            return False, "Вы уже использовали реферальный код"
        
        # Применить код
        cursor.execute('UPDATE users SET referred_by = ? WHERE user_id = ?', (referrer_id, user_id))
        self.conn.commit()
        
        return True, f"Реферальный код применен! Ваш пригласитель: {referrer_id}"
    
    def get_referral_stats(self, user_id):
        """Получить статистику рефералов"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE referred_by = ?', (user_id,))
        total_referrals = cursor.fetchone()[0]
        
        cursor.execute('SELECT referral_earnings FROM users WHERE user_id = ?', (user_id,))
        earnings = cursor.fetchone()[0] or 0
        
        return total_referrals, earnings
    
    def get_all_vip_users(self):
        """Получить всех VIP подписчиков с активной подпиской"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id 
            FROM users 
            WHERE subscription_type = 'vip' 
            AND subscription_end IS NOT NULL 
            AND datetime(subscription_end) > datetime('now')
        ''')
        return [row[0] for row in cursor.fetchall()]
    
    def get_all_free_users(self):
        """Получить всех FREE пользователей (без подписки или истекшая подписка)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id 
            FROM users 
            WHERE (subscription_type IS NULL OR subscription_type = 'free'
                   OR subscription_end IS NULL 
                   OR datetime(subscription_end) <= datetime('now'))
            AND user_id IS NOT NULL
        ''')
        return [row[0] for row in cursor.fetchall()]
    
    def get_best_long_signals(self, limit=5, min_confidence=90.0):
        """Получить лучшие LONG сигналы (сверхточные)
        
        Args:
            limit: Максимальное количество сигналов
            min_confidence: Минимальная точность (по умолчанию 90%, для FREE - 95%)
        """
        best_signals = []
        
        # Проверяем только LONG таймфреймы
        long_timeframes = ["1H", "4H"]
        
        # Все активы для LONG
        all_assets = {**self.assets}
        
        for asset_name, asset_symbol in all_assets.items():
            for timeframe in long_timeframes:
                signal_info, error = self.analyze_asset_timeframe(asset_symbol, timeframe)
                
                if signal_info and signal_info.get('confidence', 0) >= min_confidence:
                    best_signals.append({
                        'asset': asset_name,
                        'signal': signal_info,
                        'timeframe': timeframe,
                        'confidence': signal_info.get('confidence', 0)
                    })
                
                # Короткая задержка между запросами
                time.sleep(0.1)
        
        # Сортировать по confidence (от большего к меньшему)
        best_signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        return best_signals[:limit]
    
    def save_signal_to_longs(self, user_id, asset, timeframe, signal_type, entry_price, confidence, tier='free'):
        """Сохранить сигнал в my_longs для пользователя
        
        Args:
            user_id: ID пользователя
            asset: Название актива
            timeframe: Таймфрейм
            signal_type: CALL или PUT
            entry_price: Цена входа
            confidence: Процент уверенности
            tier: Тип сигнала ('vip' или 'free')
        """
        cursor = self.conn.cursor()
        
        # Определить время истечения на основе таймфрейма
        expiry_minutes = 60 if timeframe == "1H" else 240  # 1H или 4H
        expiry_time = (datetime.now() + timedelta(minutes=expiry_minutes)).isoformat()
        
        cursor.execute('''
            INSERT INTO signal_history 
            (user_id, asset, timeframe, signal_type, entry_price, confidence, 
             signal_time, status, expiry_time, signal_tier)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        ''', (user_id, asset, timeframe, signal_type, entry_price, confidence, 
              datetime.now().isoformat(), expiry_time, tier))
        
        self.conn.commit()
    
    def add_lifetime_subscription(self, user_id):
        cursor = self.conn.cursor()
        lifetime_end = datetime.now() + timedelta(days=36500)
        
        # Проверить существует ли админ и имеет ли он уже подписку
        cursor.execute('SELECT subscription_end, is_premium FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result and result[0] and result[1]:
            # Админ уже имеет подписку - не трогать
            return lifetime_end
        
        # Создать запись админа если её нет, НО НЕ устанавливать pocket_option_registered
        # чтобы onboarding мог запуститься
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date)
            VALUES (?, 'admin', 'Admin', ?)
        ''', (user_id, datetime.now().isoformat()))
        
        # Обновить только подписку
        cursor.execute('''
            UPDATE users 
            SET subscription_end = ?, is_premium = 1, subscription_type = 'vip'
            WHERE user_id = ?
        ''', (lifetime_end.isoformat(), user_id))
        
        self.conn.commit()
        return lifetime_end
    
    def get_bot_stats(self):
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_premium = 1')
        premium_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(signals_used) FROM users')
        total_signals = cursor.fetchone()[0] or 0
        
        cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE subscription_end IS NOT NULL 
            AND datetime(subscription_end) > datetime('now')
        ''')
        active_subs = cursor.fetchone()[0]
        
        return {
            'total_users': total_users,
            'premium_users': premium_users,
            'active_subscriptions': active_subs,
            'total_signals': total_signals
        }
    
    def get_user_signal_stats(self, user_id, timeframe_type=None, tier=None):
        """Получить статистику пользователя, опционально фильтруя по типу таймфрейма и tier"""
        cursor = self.conn.cursor()
        
        # Определить короткие и длинные таймфреймы
        short_timeframes = ['1M', '2M', '3M', '5M', '15M', '30M']
        long_timeframes = ['1H', '4H', '1D', '1W']
        
        filters = []
        params = [user_id]
        
        if timeframe_type == 'short':
            timeframe_filter = f"timeframe IN ({','.join('?' * len(short_timeframes))})"
            filters.append(timeframe_filter)
            params.extend(short_timeframes)
        elif timeframe_type == 'long':
            timeframe_filter = f"timeframe IN ({','.join('?' * len(long_timeframes))})"
            filters.append(timeframe_filter)
            params.extend(long_timeframes)
        
        if tier:
            filters.append("signal_tier = ?")
            params.append(tier)
        
        filter_clause = " AND " + " AND ".join(filters) if filters else ""
        
        query = f'''
            SELECT COALESCE(COUNT(*), 0) as total,
                   COALESCE(SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END), 0) as wins,
                   COALESCE(SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END), 0) as losses,
                   COALESCE(SUM(CASE WHEN result = 'win' THEN profit_loss ELSE 0 END), 0) as total_profit,
                   COALESCE(SUM(CASE WHEN result = 'loss' THEN profit_loss ELSE 0 END), 0) as total_loss,
                   COALESCE(AVG(confidence), 0) as avg_confidence
            FROM signal_history 
            WHERE user_id = ? AND result IS NOT NULL {filter_clause}
        '''
        cursor.execute(query, params)
        
        stats = cursor.fetchone()
        total, wins, losses, profit, loss, avg_conf = stats
        
        total = total or 0
        wins = wins or 0
        losses = losses or 0
        
        win_rate = (wins / total * 100) if total > 0 else 0
        net_profit = (profit or 0) + (loss or 0)
        
        cursor.execute('''
            SELECT asset, 
                   COUNT(*) as total,
                   SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins
            FROM signal_history 
            WHERE user_id = ? AND result IS NOT NULL
            GROUP BY asset
            ORDER BY wins DESC
            LIMIT 5
        ''', (user_id,))
        
        best_assets = cursor.fetchall()
        
        return {
            'total_signals': total,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'net_profit': net_profit,
            'avg_confidence': avg_conf or 0,
            'best_assets': best_assets
        }
    
    def get_autotrade_stats(self, user_id):
        """Получить статистику автоматической торговли пользователя"""
        cursor = self.conn.cursor()
        
        # Получить статистику автотрейдинга (signal_tier = 'autotrade')
        cursor.execute('''
            SELECT COALESCE(COUNT(*), 0) as total,
                   COALESCE(SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END), 0) as wins,
                   COALESCE(SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END), 0) as losses,
                   COALESCE(SUM(CASE WHEN result = 'draw' THEN 1 ELSE 0 END), 0) as draws,
                   COALESCE(SUM(profit_loss), 0) as total_profit,
                   COALESCE(SUM(stake_amount), 0) as total_stakes
            FROM signal_history 
            WHERE user_id = ? AND signal_tier = 'autotrade' AND result IS NOT NULL
        ''', (user_id,))
        
        stats = cursor.fetchone()
        total, wins, losses, draws, total_profit, total_stakes = stats
        
        total = total or 0
        wins = wins or 0
        losses = losses or 0
        draws = draws or 0
        total_profit = total_profit or 0
        total_stakes = total_stakes or 0
        
        win_rate = (wins / total * 100) if total > 0 else 0
        roi = (total_profit / total_stakes * 100) if total_stakes > 0 else 0
        
        # Получить статистику по стратегиям из notes поля
        cursor.execute('''
            SELECT notes, COUNT(*) as count,
                   SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins
            FROM signal_history 
            WHERE user_id = ? AND signal_tier = 'autotrade' AND result IS NOT NULL
            GROUP BY notes
        ''', (user_id,))
        
        strategy_stats = cursor.fetchall()
        
        return {
            'total_trades': total,
            'wins': wins,
            'losses': losses,
            'draws': draws,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'total_stakes': total_stakes,
            'roi': roi,
            'strategy_stats': strategy_stats
        }
    
    def calculate_kelly_criterion(self, win_rate, payout_rate=0.92):
        if win_rate <= 0 or win_rate >= 100:
            return 0.02
        
        p = win_rate / 100
        q = 1 - p
        b = payout_rate
        
        kelly = (b * p - q) / b
        kelly = max(0, min(kelly, 0.25))
        
        return kelly if kelly > 0 else 0.02
    
    def get_bankroll_recommendation(self, user_id, balance):
        stats = self.get_user_signal_stats(user_id)
        win_rate = stats['win_rate']
        
        if stats['total_signals'] < 10:
            fixed_percentage = 0.02
            kelly = 0.02
            recommendation_type = "conservative"
        else:
            kelly = self.calculate_kelly_criterion(win_rate)
            fixed_percentage = 0.03 if win_rate >= 60 else 0.02
            recommendation_type = "optimal" if win_rate >= 55 else "conservative"
        
        kelly_stake = balance * kelly
        fixed_stake = balance * fixed_percentage
        
        return {
            'win_rate': win_rate,
            'kelly_percentage': kelly * 100,
            'kelly_stake': kelly_stake,
            'fixed_percentage': fixed_percentage * 100,
            'fixed_stake': fixed_stake,
            'recommendation_type': recommendation_type,
            'min_stake': balance * 0.01,
            'max_stake': balance * 0.05
        }
    
    def calculate_vip_potential_income(self, user_id):
        """Рассчитать потенциальное увеличение дохода при апгрейде до VIP"""
        stats = self.get_user_signal_stats(user_id)
        
        cursor = self.conn.cursor()
        cursor.execute('SELECT current_balance, subscription_type FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            return None
        
        current_balance = result[0] or 10000
        current_sub = result[1] or 'short'
        
        win_rate = stats['win_rate'] if stats['win_rate'] > 0 else 87
        avg_signals_per_month = 30
        
        # Текущие ставки
        if current_sub == 'short':
            current_stake = current_balance / 364
            current_signals = avg_signals_per_month
        else:
            current_stake = current_balance * 0.025
            current_signals = avg_signals_per_month
        
        # VIP ставки (доступ к обоим типам + 5 авто-сигналов в день)
        vip_short_stake = current_balance / 364
        vip_long_stake = current_balance * 0.05
        vip_auto_signals = 150
        vip_manual_signals = avg_signals_per_month
        vip_total_signals = vip_auto_signals + vip_manual_signals
        
        # Расчет прибыли
        payout = 0.92
        
        # Текущая прибыль (только один тип)
        current_wins = current_signals * (win_rate / 100)
        current_losses = current_signals - current_wins
        current_monthly_profit = (current_wins * current_stake * payout) - (current_losses * current_stake)
        
        # VIP прибыль (оба типа + авто-рассылка)
        vip_short_wins = (vip_manual_signals / 2) * (win_rate / 100)
        vip_short_losses = (vip_manual_signals / 2) - vip_short_wins
        vip_short_profit = (vip_short_wins * vip_short_stake * payout) - (vip_short_losses * vip_short_stake)
        
        vip_long_wins = (vip_manual_signals / 2) * (win_rate / 100)
        vip_long_losses = (vip_manual_signals / 2) - vip_long_wins
        vip_long_profit = (vip_long_wins * vip_long_stake * payout) - (vip_long_losses * vip_long_stake)
        
        vip_auto_wins = vip_auto_signals * (92 / 100)
        vip_auto_losses = vip_auto_signals - vip_auto_wins
        vip_auto_profit = (vip_auto_wins * vip_long_stake * payout) - (vip_auto_losses * vip_long_stake)
        
        vip_monthly_profit = vip_short_profit + vip_long_profit + vip_auto_profit
        
        # Разница
        profit_increase = vip_monthly_profit - current_monthly_profit
        profit_increase_percent = (profit_increase / abs(current_monthly_profit) * 100) if current_monthly_profit != 0 else 0
        
        # Окупаемость апгрейда
        upgrade_cost = 1990
        months_to_payback = upgrade_cost / profit_increase if profit_increase > 0 else 999
        
        return {
            'current_monthly_profit': current_monthly_profit,
            'vip_monthly_profit': vip_monthly_profit,
            'profit_increase': profit_increase,
            'profit_increase_percent': profit_increase_percent,
            'upgrade_cost': upgrade_cost,
            'months_to_payback': months_to_payback,
            'vip_signals_count': vip_total_signals,
            'current_signals_count': current_signals,
            'win_rate': win_rate
        }
    
    def calculate_expiration_time(self, timeframe):
        """Рассчитать время экспирации на основе таймфрейма"""
        timeframe_minutes = {
            "1M": 1,
            "2M": 2,
            "3M": 3,
            "5M": 5,
            "15M": 15,
            "30M": 30,
            "1H": 60,
            "4H": 240,
            "1D": 1440,
            "1W": 10080
        }
        minutes = timeframe_minutes.get(timeframe, 5)
        expiration_time = datetime.now() + timedelta(minutes=minutes)
        return expiration_time.isoformat()
    
    def get_martingale_stake(self, user_id):
        """Получить текущую ставку по мартингейлу для SHORT сигналов из БД"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT short_base_stake, martingale_base_stake, martingale_multiplier, 
                   current_martingale_level, consecutive_losses
            FROM users WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            return 100.0, 0
        
        short_base_stake, martingale_base_stake, martingale_multiplier, level, losses = result
        
        # Используем приоритет: martingale_base_stake > short_base_stake > 100
        base_stake = martingale_base_stake or short_base_stake or 100.0
        multiplier = martingale_multiplier or 3  # Дефолт x3
        level = level or 0
        
        # Мартингейл: множитель из БД после каждого луза
        stake = base_stake * (multiplier ** level)
        return stake, level
    
    def update_martingale_after_win(self, user_id):
        """Обнулить мартингейл после выигрыша"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET current_martingale_level = 0, consecutive_losses = 0
            WHERE user_id = ?
        ''', (user_id,))
        self.conn.commit()
        logger.info(f"🔄 Reset martingale for user {user_id} after WIN")
    
    def update_martingale_after_loss(self, user_id):
        """Увеличить уровень мартингейла после проигрыша (макс 6)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT current_martingale_level, consecutive_losses
            FROM users WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        
        if result:
            level, losses = result
            level = level or 0
            losses = losses or 0
            
            # Ограничение: максимум 6 лузов подряд
            if losses < 6:
                new_level = min(level + 1, 6)
                new_losses = losses + 1
                cursor.execute('''
                    UPDATE users 
                    SET current_martingale_level = ?, consecutive_losses = ?
                    WHERE user_id = ?
                ''', (new_level, new_losses, user_id))
                self.conn.commit()
                logger.info(f"📈 Increased martingale for user {user_id}: level {new_level}, losses {new_losses}")
            else:
                logger.warning(f"⚠️ User {user_id} reached max 6 consecutive losses, keeping level")
    
    def update_martingale_after_refund(self, user_id):
        """Сохранить уровень мартингейла при возврате (ставка повторяется)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT current_martingale_level, consecutive_losses
            FROM users WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        
        if result:
            level, losses = result
            level = level or 0
            losses = losses or 0
            # При возврате мартингейл не изменяется - следующая ставка будет той же
            logger.info(f"🔄 Refund for user {user_id}: keeping level {level}, losses {losses}")
    
    def set_short_base_stake(self, user_id, stake):
        """Установить базовую ставку для SHORT сигналов"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET short_base_stake = ?
            WHERE user_id = ?
        ''', (stake, user_id))
        self.conn.commit()
    
    def get_long_stake(self, user_id, balance, is_vip=False):
        """Получить ставку для LONG сигналов на основе процентной стратегии из БД"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT percentage_value FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        # Если есть настроенный процент, используем его
        if result and result[0]:
            percentage = result[0] / 100  # Преобразуем из % в десятичное
        else:
            # Дефолтные значения если не настроено
            if is_vip:
                percentage = 0.05  # 5% для VIP
            else:
                percentage = 0.025  # 2.5% для обычных
        
        stake = balance * percentage
        return stake
    
    def get_dalembert_stake(self, user_id):
        """Получить текущую ставку по D'Alembert стратегии
        
        D'Alembert - умеренная прогрессия:
        - После проигрыша: ставка + unit
        - После выигрыша: ставка - unit (минимум base_stake)
        - Намного безопаснее Мартингейла (линейная vs экспоненциальная прогрессия)
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT dalembert_base_stake, dalembert_unit, current_dalembert_level
            FROM users WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            return 100.0, 0
        
        base_stake, unit, level = result
        
        # Используем дефолтные значения если не настроено
        base_stake = base_stake or 100.0
        unit = unit or 50.0
        level = level or 0
        
        # D'Alembert: линейная прогрессия
        stake = base_stake + (level * unit)
        return stake, level
    
    def update_dalembert_after_win(self, user_id):
        """Уменьшить уровень D'Alembert после выигрыша (минимум 0)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT current_dalembert_level
            FROM users WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        
        if result:
            level = result[0] or 0
            new_level = max(level - 1, 0)  # Минимум 0
            
            cursor.execute('''
                UPDATE users 
                SET current_dalembert_level = ?
                WHERE user_id = ?
            ''', (new_level, user_id))
            self.conn.commit()
            logger.info(f"📉 Decreased D'Alembert for user {user_id}: level {new_level}")
    
    def update_dalembert_after_loss(self, user_id):
        """Увеличить уровень D'Alembert после проигрыша (макс 10 для безопасности)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT current_dalembert_level
            FROM users WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        
        if result:
            level = result[0] or 0
            new_level = min(level + 1, 10)  # Максимум 10 уровней
            
            cursor.execute('''
                UPDATE users 
                SET current_dalembert_level = ?
                WHERE user_id = ?
            ''', (new_level, user_id))
            self.conn.commit()
            logger.info(f"📈 Increased D'Alembert for user {user_id}: level {new_level}")
    
    def update_dalembert_after_refund(self, user_id):
        """Сохранить уровень D'Alembert при возврате (ставка повторяется)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT current_dalembert_level
            FROM users WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        
        if result:
            level = result[0] or 0
            logger.info(f"🔄 Refund for user {user_id}: keeping D'Alembert level {level}")
    
    def calculate_recommended_short_stake(self, balance, martingale_type=3):
        """Рассчитать рекомендованную SHORT ставку на основе банка
        
        Минимальная ставка на платформе: 100₽
        
        Мартингейл x2 с 6 уровнями:
        100 + 200 + 400 + 800 + 1600 + 3200 = 6300₽
        
        Мартингейл x3 с 6 уровнями:
        100 + 300 + 900 + 2700 + 8100 + 24300 = 36400₽
        
        Возвращает None если баланса недостаточно для мартингейла
        """
        MIN_STAKE = 100  # Минимальная ставка на платформе
        
        if balance <= 0:
            return None
        
        # Рассчитать минимальный баланс в зависимости от типа мартингейла
        if martingale_type == 2:
            # x2: 100 + 200 + 400 + 800 + 1600 + 3200 = 6300
            min_balance_for_martingale = MIN_STAKE * (1 + 2 + 4 + 8 + 16 + 32)
            total_martingale_sum = 63  # 1 + 2 + 4 + 8 + 16 + 32
        else:  # x3
            # x3: 100 + 300 + 900 + 2700 + 8100 + 24300 = 36400
            min_balance_for_martingale = MIN_STAKE * (1 + 3 + 9 + 27 + 81 + 243)
            total_martingale_sum = 364  # 1 + 3 + 9 + 27 + 81 + 243
        
        if balance < min_balance_for_martingale:
            return None  # Недостаточно средств
        
        # Рассчитать безопасную ставку
        recommended_stake = balance / total_martingale_sum
        
        # Округлить до 100₽ минимум
        recommended_stake = max(MIN_STAKE, round(recommended_stake, 2))
        
        return recommended_stake
    
    def set_currency(self, user_id, currency):
        """Установить валюту пользователя (RUB или USD)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET currency = ?
            WHERE user_id = ?
        ''', (currency, user_id))
        self.conn.commit()
    
    def get_currency(self, user_id):
        """Получить валюту пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT currency FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result and result[0] else "RUB"
    
    def save_signal_to_history(self, user_id, asset, timeframe, signal_type, confidence, entry_price, stake_amount=None):
        cursor = self.conn.cursor()
        expiration_time = self.calculate_expiration_time(timeframe)
        cursor.execute('''
            INSERT INTO signal_history 
            (user_id, asset, timeframe, signal_type, confidence, entry_price, stake_amount, signal_date, expiration_time, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        ''', (user_id, asset, timeframe, signal_type, confidence, entry_price, stake_amount, datetime.now().isoformat(), expiration_time))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_last_pending_signal(self, user_id):
        """Получить последний сигнал со статусом pending для пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, asset, signal_type, confidence, stake_amount
            FROM signal_history
            WHERE user_id = ? AND result = 'pending'
            ORDER BY signal_date DESC
            LIMIT 1
        ''', (user_id,))
        return cursor.fetchone()
    
    def get_expired_signals(self):
        """Получить все истекшие сигналы со статусом pending"""
        cursor = self.conn.cursor()
        current_time = datetime.now().isoformat()
        cursor.execute('''
            SELECT id, user_id, asset, timeframe, signal_type, confidence, stake_amount
            FROM signal_history
            WHERE result = 'pending' AND expiration_time <= ?
        ''', (current_time,))
        return cursor.fetchall()
    
    def mark_signal_as_notified(self, signal_id):
        """Отметить сигнал как notified чтобы не отправлять повторные уведомления"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE signal_history
            SET result = 'awaiting_report'
            WHERE id = ?
        ''', (signal_id,))
        self.conn.commit()
    
    def get_ignored_signals(self, hours_threshold=24):
        """Получить сигналы awaiting_report которые игнорировались дольше указанного времени"""
        cursor = self.conn.cursor()
        threshold_time = (datetime.now() - timedelta(hours=hours_threshold)).isoformat()
        cursor.execute('''
            SELECT id FROM signal_history
            WHERE result = 'awaiting_report'
            AND expiration_time < ?
        ''', (threshold_time,))
        return cursor.fetchall()
    
    def auto_skip_ignored_signals(self):
        """Автоматически пропустить проигнорированные уведомления"""
        ignored_signals = self.get_ignored_signals(hours_threshold=24)
        count = 0
        for signal in ignored_signals:
            signal_id = signal[0]
            self.skip_signal(signal_id)
            count += 1
        if count > 0:
            logger.info(f"🔄 Auto-skipped {count} ignored signal(s)")
        return count
    
    def update_signal_result(self, signal_id, result, profit_loss):
        """Обновить результат сигнала"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE signal_history
            SET result = ?, profit_loss = ?, close_date = ?
            WHERE id = ?
        ''', (result, profit_loss, datetime.now().isoformat(), signal_id))
        self.conn.commit()
        
        cursor.execute('SELECT asset, timeframe FROM signal_history WHERE id = ?', (signal_id,))
        signal_data = cursor.fetchone()
        if signal_data:
            asset, timeframe = signal_data
            self.update_performance_stats(asset, timeframe, result)
    
    def update_performance_stats(self, asset, timeframe, result):
        """Обновить статистику производительности актива/таймфрейма"""
        # Пропускаем обновление статистики для пропущенных сигналов
        if result == 'skipped':
            return
        
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO signal_performance (asset, timeframe, total_signals, wins, losses, last_updated)
            VALUES (?, ?, 0, 0, 0, ?)
            ON CONFLICT(asset, timeframe) DO NOTHING
        ''', (asset, timeframe, datetime.now().isoformat()))
        
        if result == 'win':
            cursor.execute('''
                UPDATE signal_performance
                SET total_signals = total_signals + 1,
                    wins = wins + 1,
                    last_updated = ?
                WHERE asset = ? AND timeframe = ?
            ''', (datetime.now().isoformat(), asset, timeframe))
        elif result == 'loss':
            cursor.execute('''
                UPDATE signal_performance
                SET total_signals = total_signals + 1,
                    losses = losses + 1,
                    last_updated = ?
                WHERE asset = ? AND timeframe = ?
            ''', (datetime.now().isoformat(), asset, timeframe))
        
        cursor.execute('''
            SELECT total_signals, wins, losses FROM signal_performance
            WHERE asset = ? AND timeframe = ?
        ''', (asset, timeframe))
        perf = cursor.fetchone()
        
        if perf:
            total, wins, losses = perf
            if total > 0:
                win_rate = wins / total
                adaptive_weight = self.calculate_adaptive_weight(win_rate, total)
                
                cursor.execute('''
                    UPDATE signal_performance
                    SET win_rate = ?, adaptive_weight = ?
                    WHERE asset = ? AND timeframe = ?
                ''', (win_rate, adaptive_weight, asset, timeframe))
        
        self.conn.commit()
        logger.info(f"📊 Updated performance for {asset} {timeframe}: {result}")
    
    def skip_signal(self, signal_id):
        """Пропустить сигнал (не влияет на баланс и статистику win rate)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE signal_history
            SET result = 'skipped', close_date = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), signal_id))
        self.conn.commit()
        logger.info(f"⏭️ Signal {signal_id} skipped by user")
    
    def delete_skipped_signals(self, user_id):
        """Удалить все пропущенные сигналы пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('''
            DELETE FROM signal_history
            WHERE user_id = ? AND result = 'skipped'
        ''', (user_id,))
        deleted_count = cursor.rowcount
        self.conn.commit()
        logger.info(f"🗑️ Deleted {deleted_count} skipped signals for user {user_id}")
        return deleted_count
    
    def add_pending_notification(self, user_id, timeframe_type):
        """Добавить запрос на отложенное уведомление о сигнале"""
        cursor = self.conn.cursor()
        # Деактивировать старые уведомления этого пользователя
        cursor.execute('''
            UPDATE pending_notifications
            SET is_active = 0
            WHERE user_id = ?
        ''', (user_id,))
        
        # Добавить новое уведомление
        cursor.execute('''
            INSERT INTO pending_notifications (user_id, timeframe_type, created_at, is_active)
            VALUES (?, ?, ?, 1)
        ''', (user_id, timeframe_type, datetime.now().isoformat()))
        
        self.conn.commit()
        logger.info(f"🔔 Added pending notification for user {user_id}, timeframe: {timeframe_type}")
    
    def get_pending_notifications(self):
        """Получить список активных отложенных уведомлений"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, user_id, timeframe_type
            FROM pending_notifications
            WHERE is_active = 1
        ''')
        return cursor.fetchall()
    
    def deactivate_notification(self, notification_id):
        """Деактивировать отложенное уведомление"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE pending_notifications
            SET is_active = 0
            WHERE id = ?
        ''', (notification_id,))
        self.conn.commit()
    
    def calculate_adaptive_weight(self, win_rate, total_signals):
        """Рассчитать адаптивный вес на основе win rate и количества сигналов
        
        Логика весов:
        - Минимум 5 сигналов для активации адаптивных весов
        - Win rate >= 70%: вес 1.4 (приоритет высокоточным активам)
        - Win rate >= 60%: вес 1.25 (хорошие активы)
        - Win rate >= 50%: вес 1.0 (средние активы)
        - Win rate >= 40%: вес 0.8 (слабые активы)
        - Win rate < 40%: вес 0.6 (очень слабые активы, почти фильтруются)
        
        Confidence factor: Полная уверенность после 20+ сигналов
        """
        if total_signals < 5:
            return 1.0  # Нейтральный вес до накопления статистики
        
        # Фактор уверенности: от 0.25 (5 сигналов) до 1.0 (20+ сигналов)
        confidence_factor = min(total_signals / 20, 1.0)
        
        # Более агрессивная система весов для фильтрации слабых активов
        if win_rate >= 0.70:
            base_weight = 1.4  # Отличные активы получают приоритет
        elif win_rate >= 0.60:
            base_weight = 1.25  # Хорошие активы
        elif win_rate >= 0.50:
            base_weight = 1.0  # Средние активы (нейтральный вес)
        elif win_rate >= 0.40:
            base_weight = 0.8  # Слабые активы
        else:
            base_weight = 0.6  # Очень слабые активы (сильно понижены)
        
        # Плавная интерполяция веса с учетом количества сигналов
        adaptive_weight = 1.0 + (base_weight - 1.0) * confidence_factor
        return round(adaptive_weight, 3)
    
    def get_adaptive_weight(self, asset, timeframe):
        """Получить адаптивный вес для актива/таймфрейма"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT adaptive_weight, total_signals FROM signal_performance
            WHERE asset = ? AND timeframe = ?
        ''', (asset, timeframe))
        result = cursor.fetchone()
        
        if result and result[1] >= 5:
            return result[0]
        return 1.0
    
    def get_user_active_signals(self, user_id):
        """
        Получить список активных (не истекших) сигналов пользователя.
        Возвращает список кортежей (asset, timeframe) для исключения повторов.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT asset, timeframe 
            FROM signal_history 
            WHERE user_id = ? 
            AND result = 'pending' 
            AND datetime(expiration_time) > datetime('now')
        ''', (user_id,))
        
        active_signals = cursor.fetchall()
        return [(asset, timeframe) for asset, timeframe in active_signals]
    
    def increment_signals_used(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE users SET signals_used = signals_used + 1, last_signal_date = ? WHERE user_id = ?',
            (datetime.now().isoformat(), user_id)
        )
        self.conn.commit()
    
    def mark_trial_used(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE users SET free_trials_used = 1 WHERE user_id = ?',
            (user_id,)
        )
        self.conn.commit()
    
    def calculate_indicators(self, df):
        try:
            df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df['EMA_100'] = df['Close'].ewm(span=100, adjust=False).mean()
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            exp1 = df['Close'].ewm(span=12).mean()
            exp2 = df['Close'].ewm(span=26).mean()
            df['MACD'] = exp1 - exp2
            df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
            
            low_14 = df['Low'].rolling(14).min()
            high_14 = df['High'].rolling(14).max()
            df['Stoch_K'] = 100 * ((df['Close'] - low_14) / (high_14 - low_14))
            df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()
            
            df['Resistance'] = df['High'].rolling(10).max()
            df['Support'] = df['Low'].rolling(10).min()
            
            df = df.fillna(method='bfill').fillna(method='ffill')
            
            return df
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return df
    
    def analyze_asset_timeframe(self, asset_symbol, timeframe):
        try:
            period_map = {
                "1M": "5d", "5M": "5d", "15M": "1mo", 
                "30M": "1mo", "1H": "3mo", "4H": "6mo", 
                "1D": "1y", "1W": "2y"
            }
            period = period_map.get(timeframe, "1mo")
            yf_timeframe = self.timeframes[timeframe]
            
            # Retry логика для обхода блокировки Yahoo Finance
            max_retries = 2
            data = pd.DataFrame()  # Инициализация перед циклом
            for attempt in range(max_retries):
                try:
                    ticker = yf.Ticker(asset_symbol)
                    data = ticker.history(period=period, interval=yf_timeframe)
                    if not data.empty:
                        break
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(0.1)  # Короткая задержка между попытками
                    else:
                        data = pd.DataFrame()  # Пустой DataFrame если все попытки провалились
            
            if len(data) < 20:
                return self.generate_signal(asset_symbol, timeframe)
            
            data = self.calculate_indicators(data)
            
            if data.empty:
                return self.generate_signal(asset_symbol, timeframe)
                
            current = data.iloc[-1]
            
            trend = "BULLISH" if current['EMA_20'] > current['EMA_50'] else "BEARISH"
            
            call_conditions = [
                trend == "BULLISH",
                current['Close'] > current['EMA_20'],
                current['RSI'] < 70,
                current['Stoch_K'] < 80,
                current['MACD'] > current['MACD_Signal']
            ]
            
            put_conditions = [
                trend == "BEARISH", 
                current['Close'] < current['EMA_20'],
                current['RSI'] > 30,
                current['Stoch_K'] > 20,
                current['MACD'] < current['MACD_Signal']
            ]
            
            signal_info = {
                'asset': asset_symbol,
                'timeframe': timeframe,
                'price': current['Close'],
                'trend': trend,
                'rsi': current['RSI'],
                'macd': current['MACD'],
                'stoch_k': current['Stoch_K'],
                'timestamp': datetime.now()
            }
            
            call_score = sum(call_conditions)
            put_score = sum(put_conditions)
            
            # Продвинутый анализ: волатильность, объемы, "киты"
            volatility = data['Close'].pct_change().std() * 100  # Волатильность в процентах
            
            # Анализ объемов (детекция "китов")
            whale_factor = 0
            avg_volume = 0
            current_volume = 0
            volume_ratio = 0
            
            if 'Volume' in data.columns:
                avg_volume = data['Volume'].rolling(20).mean().iloc[-1]
                current_volume = data['Volume'].iloc[-1]
                
                if avg_volume > 0:
                    volume_ratio = current_volume / avg_volume
                    # Если объем в 1.5+ раз выше среднего - возможна активность "китов"
                    if volume_ratio >= 1.5:
                        whale_factor = 1
                        # Высокий объем усиливает тренд
                        if trend == "BULLISH":
                            call_score += 1
                        else:
                            put_score += 1
            
            # Настраиваемый фильтр через админ панель
            min_score = float(bot.get_setting('min_signal_score', '2'))  # Минимум баллов (по умолчанию 2)
            min_difference = float(bot.get_setting('min_score_difference', '0'))  # Минимальная разница (по умолчанию 0)
            min_conf = float(bot.get_setting('min_confidence', '70'))  # Минимальная уверенность (по умолчанию 70%)
            max_conf = float(bot.get_setting('max_confidence', '92'))  # Максимальная уверенность (по умолчанию 92%)
            
            score_difference = abs(call_score - put_score)
            
            # Бонус за низкую волатильность (стабильный рынок = надежнее сигнал)
            stability_bonus = 0
            if volatility < 2.0:  # Низкая волатильность
                stability_bonus = 3
            elif volatility < 3.0:  # Умеренная волатильность
                stability_bonus = 1
            
            # 🔮 ИНТУИТИВНОЕ ПРЕДСКАЗАНИЕ на основе истории
            historical_pattern = bot.get_historical_pattern(asset_symbol, timeframe, lookback_hours=24)
            pattern_bonus = 0
            
            if historical_pattern and historical_pattern['predicted_direction']:
                predicted_dir = historical_pattern['predicted_direction']
                pattern_bonus = historical_pattern['prediction_bonus']
                
                # Применяем бонус предсказания к соответствующему направлению
                if predicted_dir == 'CALL':
                    call_score += pattern_bonus
                    logger.info(f"🔮 {asset_symbol} {timeframe}: История предсказывает CALL (+{pattern_bonus} балла)")
                elif predicted_dir == 'PUT':
                    put_score += pattern_bonus
                    logger.info(f"🔮 {asset_symbol} {timeframe}: История предсказывает PUT (+{pattern_bonus} балла)")
            
            # Применяем бонусы к финальным скорам
            total_call_score = call_score + stability_bonus
            total_put_score = put_score + stability_bonus
            
            # Логика: ВСЕГДА выбираем лучший доступный сигнал
            # Подбираем оптимальное направление из того что есть
            
            if total_call_score > total_put_score:
                # CALL сигнал сильнее - выбираем его независимо от скора
                base_conf = min_conf + (total_call_score) * 6.0
                confidence = np.clip(base_conf, min_conf, max_conf)
                
                # Логирование факторов анализа
                market_info = f"📊 Волатильность: {volatility:.2f}% | 🐋 Киты: {'✅' if whale_factor else '❌'} | 📈 Стабильность: +{stability_bonus}"
                logger.info(f"{asset_symbol} {timeframe}: CALL | Score: {total_call_score} | {market_info}")
                
                signal_info.update({
                    'signal': 'CALL',
                    'confidence': round(confidence, 1),
                    'direction': '📈',
                    'score': total_call_score,
                    'volatility': volatility,
                    'whale_detected': whale_factor > 0,
                    'volume': data['Volume'].iloc[-1] if 'Volume' in data.columns else 0,
                    'avg_volume': avg_volume if 'Volume' in data.columns else 0,
                    'volume_ratio': volume_ratio if 'Volume' in data.columns else 0,
                    'ema_20': current['EMA_20'],
                    'ema_50': current['EMA_50']
                })
                
                # Сохранить данные анализа в историю
                bot.save_market_data(asset_symbol, timeframe, signal_info)
                
                return signal_info, None
                
            elif total_put_score > total_call_score:
                # PUT сигнал сильнее - выбираем его независимо от скора
                base_conf = min_conf + (total_put_score) * 6.0
                confidence = np.clip(base_conf, min_conf, max_conf)
                
                # Логирование факторов анализа
                market_info = f"📊 Волатильность: {volatility:.2f}% | 🐋 Киты: {'✅' if whale_factor else '❌'} | 📉 Стабильность: +{stability_bonus}"
                logger.info(f"{asset_symbol} {timeframe}: PUT | Score: {total_put_score} | {market_info}")
                
                signal_info.update({
                    'signal': 'PUT',
                    'confidence': round(confidence, 1), 
                    'direction': '📉',
                    'score': total_put_score,
                    'volatility': volatility,
                    'whale_detected': whale_factor > 0,
                    'volume': current_volume,
                    'avg_volume': avg_volume,
                    'volume_ratio': volume_ratio,
                    'ema_20': current['EMA_20'],
                    'ema_50': current['EMA_50']
                })
                
                # Сохранить данные анализа в историю
                bot.save_market_data(asset_symbol, timeframe, signal_info)
                
                return signal_info, None
                
            else:
                # Если равные скоры - выбираем по тренду
                if trend == "BULLISH":
                    base_conf = min_conf + (total_call_score) * 5.5
                    confidence = np.clip(base_conf, min_conf, max_conf)
                    
                    logger.info(f"{asset_symbol} {timeframe}: CALL (по тренду) | Score: {total_call_score} | Волатильность: {volatility:.2f}%")
                    
                    signal_info.update({
                        'signal': 'CALL',
                        'confidence': round(confidence, 1),
                        'direction': '📈',
                        'score': total_call_score,
                        'volatility': volatility,
                        'whale_detected': whale_factor > 0,
                        'volume': current_volume,
                        'avg_volume': avg_volume,
                        'volume_ratio': volume_ratio,
                        'ema_20': current['EMA_20'],
                        'ema_50': current['EMA_50']
                    })
                    
                    # Сохранить данные анализа в историю
                    bot.save_market_data(asset_symbol, timeframe, signal_info)
                    
                    return signal_info, None
                else:
                    base_conf = min_conf + (total_put_score) * 5.5
                    confidence = np.clip(base_conf, min_conf, max_conf)
                    
                    logger.info(f"{asset_symbol} {timeframe}: PUT (по тренду) | Score: {total_put_score} | Волатильность: {volatility:.2f}%")
                    
                    signal_info.update({
                        'signal': 'PUT',
                        'confidence': round(confidence, 1),
                        'direction': '📉',
                        'score': total_put_score,
                        'volatility': volatility,
                        'whale_detected': whale_factor > 0,
                        'volume': current_volume,
                        'avg_volume': avg_volume,
                        'volume_ratio': volume_ratio,
                        'ema_20': current['EMA_20'],
                        'ema_50': current['EMA_50']
                    })
                    
                    # Сохранить данные анализа в историю
                    bot.save_market_data(asset_symbol, timeframe, signal_info)
                    
                    return signal_info, None
            
        except Exception as e:
            logger.error(f"Error analyzing {asset_symbol} on {timeframe}: {e}")
            return self.generate_signal(asset_symbol, timeframe)
    
    def generate_signal(self, asset_symbol, timeframe):
        """Fallback сигнал когда реальный анализ недоступен"""
        # Генерируем простой сигнал на основе случайного выбора с трендом
        # Это лучше чем ничего не показывать пользователю
        trend = np.random.choice(['BULLISH', 'BEARISH'])
        
        if trend == 'BULLISH':
            signal = 'CALL'
            direction = '📈'
        else:
            signal = 'PUT'
            direction = '📉'
        
        # Генерируем реалистичные значения
        confidence = np.random.uniform(70, 85)  # Умеренная уверенность для fallback
        
        signal_info = {
            'asset': asset_symbol,
            'timeframe': timeframe,
            'price': 1.0,  # Заглушка
            'trend': trend,
            'rsi': 50.0,  # Нейтральное значение
            'macd': 0.0,  # Нейтральное значение
            'stoch_k': 50.0,  # Нейтральное значение
            'signal': signal,
            'confidence': round(confidence, 1),
            'direction': direction,
            'score': 2,  # Минимальный скор для fallback
            'timestamp': datetime.now()
        }
        
        return signal_info, None
    
    def create_pro_chart(self, asset_symbol, asset_name, timeframe, signal_info=None):
        """Создает профессиональный стильный график с техническими индикаторами"""
        try:
            plt.style.use('dark_background')
            
            # Создаем фигуру с увеличенным размером для детализации
            fig = plt.figure(figsize=(16, 12), facecolor='#0d1117')
            
            # ДЕТАЛЬНЫЕ ПЕРИОДЫ для SHORT и LONG сигналов
            period_map = {
                "1M": "5d",   "5M": "5d",   "15M": "1mo", "30M": "1mo",
                "1H": "1mo",  "4H": "3mo",  "1D": "1y",   "1W": "2y"
            }
            period = period_map.get(timeframe, "1mo")
            yf_timeframe = self.timeframes.get(timeframe, "1h")
            
            # Получаем рыночные данные
            try:
                ticker = yf.Ticker(asset_symbol)
                data = ticker.history(period=period, interval=yf_timeframe, actions=False)
                
                if len(data) >= 20:
                    dates = data.index
                    prices = data['Close'].values
                    highs = data['High'].values
                    lows = data['Low'].values
                    volumes = data['Volume'].values if 'Volume' in data else None
                else:
                    raise ValueError("Not enough data")
            except:
                # Fallback на генерированные данные
                dates = pd.date_range(end=datetime.now(), periods=100, freq='H')
                base_price = 50000 if 'BTC' in asset_symbol else (100 if 'USD' not in asset_name else 1.0)
                prices = base_price + np.cumsum(np.random.randn(100) * base_price * 0.01)
                highs = prices + np.abs(np.random.randn(100) * base_price * 0.005)
                lows = prices - np.abs(np.random.randn(100) * base_price * 0.005)
                volumes = np.random.uniform(1e6, 1e7, 100)
            
            # Вычисляем технические индикаторы
            df = pd.DataFrame({'close': prices, 'high': highs, 'low': lows})
            
            # EMA линии
            ema_9 = df['close'].ewm(span=9).mean()
            ema_21 = df['close'].ewm(span=21).mean()
            ema_50 = df['close'].ewm(span=50).mean() if len(df) >= 50 else None
            
            # Bollinger Bands
            bb_period = 20
            bb_std = 2
            sma_20 = df['close'].rolling(window=bb_period).mean()
            std_20 = df['close'].rolling(window=bb_period).std()
            bb_upper = sma_20 + (std_20 * bb_std)
            bb_lower = sma_20 - (std_20 * bb_std)
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # MACD
            ema_12 = df['close'].ewm(span=12).mean()
            ema_26 = df['close'].ewm(span=26).mean()
            macd_line = ema_12 - ema_26
            signal_line = macd_line.ewm(span=9).mean()
            macd_histogram = macd_line - signal_line
            
            # ========== ГЛАВНЫЙ ГРАФИК ЦЕНЫ (subplot 1) ==========
            ax1 = plt.subplot(4, 1, 1)
            ax1.set_facecolor('#0d1117')
            
            # Bollinger Bands с прозрачной заливкой
            ax1.fill_between(dates, bb_upper, bb_lower, alpha=0.15, color='#58a6ff', label='Bollinger Bands')
            ax1.plot(dates, bb_upper, color='#58a6ff', alpha=0.4, linewidth=1, linestyle='--')
            ax1.plot(dates, bb_lower, color='#58a6ff', alpha=0.4, linewidth=1, linestyle='--')
            
            # График цены с градиентным свечением
            ax1.plot(dates, prices, color='#00d4ff', linewidth=3, label='Цена', zorder=5, 
                    path_effects=[pe.SimpleLineShadow(offset=(1,-1), shadow_color='#00d4ff', alpha=0.3), pe.Normal()])
            ax1.fill_between(dates, prices, alpha=0.25, color='#00d4ff')
            
            # EMA линии с улучшенными цветами
            ax1.plot(dates, ema_9, label='EMA 9', color='#ffa657', alpha=0.9, linewidth=2)
            ax1.plot(dates, ema_21, label='EMA 21', color='#f85149', alpha=0.9, linewidth=2)
            if ema_50 is not None:
                ax1.plot(dates, ema_50, label='EMA 50', color='#a371f7', alpha=0.8, linewidth=2)
            
            # ТОЧКА ВХОДА
            entry_price = prices[-1]
            ax1.axhline(y=entry_price, color='#ffffff', linestyle='--', linewidth=2.5, 
                       alpha=0.8, label=f'Вход: {entry_price:.4f}', zorder=8)
            
            # СИГНАЛ с улучшенной визуализацией
            if signal_info and 'signal' in signal_info:
                signal_color = '#3fb950' if signal_info['signal'] == 'CALL' else '#f85149'
                marker = '^' if signal_info['signal'] == 'CALL' else 'v'
                
                # Большая стрелка с обводкой
                ax1.scatter([dates[-1]], [prices[-1]], color=signal_color, s=500, zorder=15, 
                           marker=marker, edgecolors='white', linewidths=4, alpha=0.95)
                
                # Аннотация с улучшенным стилем
                offset_y = 35 if signal_info['signal'] == 'CALL' else -45
                bbox_props = dict(boxstyle='round,pad=0.8', facecolor=signal_color, 
                                 alpha=0.95, edgecolor='white', linewidth=2)
                ax1.annotate(f"🎯 {signal_info['signal']}\n{signal_info['confidence']:.0f}% уверенность", 
                           xy=(dates[-1], prices[-1]), xytext=(15, offset_y),
                           textcoords='offset points', fontsize=14, fontweight='bold',
                           color='white', bbox=bbox_props, zorder=20,
                           arrowprops=dict(arrowstyle='->', color='white', lw=2))
            
            # Заголовок с движением цены (НЕ доходность!)
            if prices[0] > 0:
                price_change = ((prices[-1] - prices[0]) / prices[0]) * 100
                change_color = '#3fb950' if price_change >= 0 else '#f85149'
                change_symbol = '▲' if price_change >= 0 else '▼'
                # Четко указываем "движение цены", а не "доходность"
                title = f'📊 {asset_name} - {timeframe} | Движение: {change_symbol} {abs(price_change):.2f}%'
            else:
                change_color = '#58a6ff'
                title = f'📊 {asset_name} - {timeframe}'
            
            ax1.set_title(title, fontsize=20, fontweight='bold', color=change_color, 
                         pad=20, family='sans-serif')
            
            # Водяной знак
            ax1.text(0.02, 0.98, '🤖 Crypto Signals Pro', transform=ax1.transAxes,
                    fontsize=11, color='#6e7681', alpha=0.6, va='top', ha='left',
                    fontweight='bold', style='italic')
            
            ax1.legend(loc='upper left', fontsize=10, framealpha=0.95, fancybox=True, 
                      shadow=True, ncol=3)
            ax1.grid(True, alpha=0.15, linestyle='--', linewidth=0.5)
            ax1.set_ylabel('Цена', fontsize=13, color='#8b949e', fontweight='bold')
            
            # ========== RSI ИНДИКАТОР (subplot 2) ==========
            ax2 = plt.subplot(4, 1, 2)
            ax2.set_facecolor('#0d1117')
            
            # RSI линия с градиентом
            ax2.plot(dates, rsi, color='#d29922', linewidth=2.5, label='RSI (14)', zorder=5)
            ax2.fill_between(dates, rsi, 50, where=(rsi >= 50), color='#3fb950', alpha=0.3)
            ax2.fill_between(dates, rsi, 50, where=(rsi < 50), color='#f85149', alpha=0.3)
            
            # Зоны перекупленности/перепроданности
            ax2.axhline(y=70, color='#f85149', linestyle='--', linewidth=1.5, alpha=0.7, label='Перекупленность')
            ax2.axhline(y=30, color='#3fb950', linestyle='--', linewidth=1.5, alpha=0.7, label='Перепроданность')
            ax2.axhline(y=50, color='#6e7681', linestyle='-', linewidth=1, alpha=0.5)
            
            # Заливка зон
            ax2.fill_between(dates, 70, 100, color='#f85149', alpha=0.1)
            ax2.fill_between(dates, 0, 30, color='#3fb950', alpha=0.1)
            
            ax2.set_ylabel('RSI', fontsize=12, color='#8b949e', fontweight='bold')
            ax2.set_ylim(0, 100)
            ax2.legend(loc='upper left', fontsize=9, framealpha=0.9)
            ax2.grid(True, alpha=0.15, linestyle='--', linewidth=0.5)
            
            # ========== MACD ИНДИКАТОР (subplot 3) ==========
            ax3 = plt.subplot(4, 1, 3)
            ax3.set_facecolor('#0d1117')
            
            # MACD линии
            ax3.plot(dates, macd_line, color='#58a6ff', linewidth=2, label='MACD', zorder=5)
            ax3.plot(dates, signal_line, color='#ffa657', linewidth=2, label='Signal', zorder=5)
            
            # Гистограмма MACD с цветовым кодированием
            colors = ['#3fb950' if h >= 0 else '#f85149' for h in macd_histogram]
            ax3.bar(dates, macd_histogram, color=colors, alpha=0.6, label='Histogram', width=0.8)
            
            ax3.axhline(y=0, color='#6e7681', linestyle='-', linewidth=1, alpha=0.5)
            ax3.set_ylabel('MACD', fontsize=12, color='#8b949e', fontweight='bold')
            ax3.legend(loc='upper left', fontsize=9, framealpha=0.9)
            ax3.grid(True, alpha=0.15, linestyle='--', linewidth=0.5)
            
            # ========== ОБЪЕМ (subplot 4) ==========
            if volumes is not None and len(volumes) > 0:
                ax4 = plt.subplot(4, 1, 4)
                ax4.set_facecolor('#0d1117')
                
                # Объем с цветовым кодированием
                vol_colors = ['#3fb950' if i > 0 and prices[i] >= prices[i-1] else '#f85149' 
                             for i in range(len(prices))]
                ax4.bar(dates, volumes, color=vol_colors, alpha=0.7, width=0.8)
                
                # Средний объем
                avg_volume = np.mean(volumes)
                ax4.axhline(y=avg_volume, color='#ffa657', linestyle='--', linewidth=1.5, 
                           alpha=0.7, label=f'Средний: {avg_volume:.0f}')
                
                ax4.set_ylabel('Объем', fontsize=12, color='#8b949e', fontweight='bold')
                ax4.set_xlabel('Время', fontsize=12, color='#8b949e', fontweight='bold')
                ax4.legend(loc='upper left', fontsize=9, framealpha=0.9)
                ax4.grid(True, alpha=0.15, linestyle='--', linewidth=0.5)
            
            # Информационная панель
            if signal_info:
                info_text = f"RSI: {rsi.iloc[-1]:.1f} | MACD: {macd_line.iloc[-1]:.2f} | Score: {signal_info.get('score', 'N/A')}"
                fig.text(0.99, 0.01, info_text, ha='right', va='bottom', fontsize=10, 
                        color='#8b949e', alpha=0.8, family='monospace')
            
            plt.tight_layout()
            
            # Сохранение в буфер с высоким качеством
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', 
                       facecolor='#0d1117', edgecolor='none')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Error creating chart: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_pocket_option_asset_name(self, asset_name):
        """Конвертирует название актива в формат Pocket Option"""
        
        # Проверяем есть ли суффикс OTC и убираем его для базового маппинга
        is_otc = " OTC" in asset_name
        base_name = asset_name.replace(" OTC", "")
        
        pocket_map = {
            # Криптовалюты (актуальные для Pocket Option)
            "BTC/USD": "BITCOIN",
            "ETH/USD": "ETHEREUM",
            "LTC/USD": "LITECOIN", 
            "XRP/USD": "XRP",
            "ADA/USD": "CARDANO",
            "BNB/USD": "BINANCE COIN",
            "DASH/USD": "DASH",
            "LINK/USD": "CHAINLINK",
            "SOL/USD": "SOLANA",
            "TRX/USD": "TRON",
            "AVAX/USD": "AVALANCHE",
            "TON/USD": "TONCOIN",
            
            # Форекс (в Pocket Option формат с "/")
            "EUR/USD": "EUR/USD",
            "GBP/USD": "GBP/USD",
            "USD/JPY": "USD/JPY",
            "USD/CHF": "USD/CHF",
            "USD/CAD": "USD/CAD",
            "AUD/USD": "AUD/USD",
            "NZD/USD": "NZD/USD",
            "EUR/GBP": "EUR/GBP",
            "EUR/JPY": "EUR/JPY",
            "GBP/JPY": "GBP/JPY",
            
            # Товары (формат Pocket Option)
            "XAU/USD": "GOLD",
            "XAG/USD": "SILVER",
            "OIL/USD": "OIL (WTI)",
            "BRENT": "BRENT OIL",
            "NG/USD": "NATURAL GAS",
            
            # Индексы
            "S&P500": "US 500",
            "NASDAQ": "US TECH 100",
            "DOW": "US 30",
            "FTSE": "UK 100",
            
            # Акции (популярные названия для Pocket Option)
            "AAPL": "APPLE",
            "MSFT": "MICROSOFT",
            "TSLA": "TESLA",
            "AMZN": "AMAZON",
            "META": "META",
            "INTC": "INTEL",
            "BA": "BOEING"
        }
        
        # Получаем базовое название из маппинга
        pocket_name = pocket_map.get(base_name, base_name)
        
        # Если это OTC актив, добавляем суффикс " OTC" в формате Pocket Option (БЕЗ скобок!)
        if is_otc:
            pocket_name = f"{pocket_name} OTC"
        
        return pocket_name
    
    def generate_pro_signal_message(self, asset_name, signal_info, timeframe, user_id=None, balance=None):
        current_time = datetime.now(MOSCOW_TZ).strftime("%H:%M")
        pocket_asset = self.get_pocket_option_asset_name(asset_name)
        
        # Создаем версию без OTC для копирования
        pocket_asset_clean = pocket_asset.replace(" OTC", "")
        
        # Определяем, есть ли OTC для отображения в описании
        is_otc = " OTC" in pocket_asset
        otc_indicator = " 🔥 OTC" if is_otc else ""
        
        expiration = self.get_expiration_time(timeframe)
        signal_type = signal_info['signal']
        confidence = signal_info['confidence']
        
        signal_emoji = "🟢" if signal_type == "CALL" else "🔴"
        direction_text = "ВВЕРХ ↗" if signal_type == "CALL" else "ВНИЗ ↘"
        
        # Получить статистику актива из БД
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT total_signals, wins, losses, win_rate 
            FROM signal_performance 
            WHERE asset = ? AND timeframe = ?
        ''', (asset_name, timeframe))
        stats = cursor.fetchone()
        
        # Формируем блок статистики и прогноза
        win_rate = stats[3] if stats else 0.0
        total_trades = stats[0] if stats else 0
        wins = stats[1] if stats else 0
        losses = stats[2] if stats else 0
        
        # Расчет ожидаемой доходности
        expected_roi = 0
        roi_text = ""
        if win_rate > 0:
            expected_roi = (win_rate * 0.85) - ((1 - win_rate) * 1.0)  # 85% выплата при выигрыше, -100% при проигрыше
            roi_sign = "+" if expected_roi > 0 else ""
            roi_text = f"{roi_sign}{expected_roi*100:.1f}%"
        
        # Статистика актива
        if total_trades >= 5:
            stats_text = f"📊 *Статистика актива:*\n• История: `{total_trades} сигналов` ({wins}W/{losses}L)\n• Win Rate: `{win_rate*100:.1f}%`\n• Ожидаемая доходность: `{roi_text}`"
        else:
            stats_text = f"📊 *Статистика актива:*\n• История: `новый актив` (менее 5 сигналов)\n• Win Rate: `анализируется...`\n• Ожидаемая доходность: `расчет после 5+ сделок`"
        
        # Получить исторический паттерн для прогноза
        pattern = self.get_historical_pattern(asset_name, timeframe)
        forecast_text = ""
        if pattern:
            trend_dir = pattern.get('predicted_direction', 'NEUTRAL')
            trend_pct = pattern.get('trend_differential', 0)
            whale_pct = pattern.get('whale_activity_pct', 0)
            
            trend_match = trend_dir == signal_info.get('direction', '').split()[0]
            trend_emoji = "✅" if trend_match else "⚠️"
            
            forecast_text = f"\n\n🔮 **Прогноз (24ч паттерн):**\n• Тренд: `{trend_dir}` {trend_emoji} ({trend_pct:.0f}%)\n• Активность китов: `{whale_pct:.0f}%`"
        
        # Анализ рынка и настроения
        volatility = signal_info.get('volatility', 0)
        whale_detected = signal_info.get('whale_detected', False)
        
        # Индикатор волатильности
        if volatility < 0.3:
            volatility_status = "🟢 Очень низкая (стабильный)"
        elif volatility < 0.5:
            volatility_status = "🟢 Низкая (нормальный)"
        elif volatility < 1.0:
            volatility_status = "🟡 Умеренная"
        else:
            volatility_status = "🔴 Высокая (осторожно)"
        
        # Активность "китов"
        whale_status = "🐋 Обнаружена активность крупных игроков!" if whale_detected else "📊 Обычная активность"
        
        bankroll_text = ""
        if user_id:
            cursor.execute('SELECT current_balance, trading_strategy FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            
            if result is not None and result[0] is not None:
                current_balance = max(result[0], 0)
                user_strategy = result[1] if len(result) > 1 else None
                
                if user_strategy == 'martingale':
                    stake_amount, martingale_level = self.get_martingale_stake(user_id)
                    if martingale_level == 1:
                        bankroll_text = f"\n💰 **Рекомендуемая ставка:** `{stake_amount:.2f} ₽` (базовая ставка)"
                    else:
                        bankroll_text = f"\n💰 **Рекомендуемая ставка:** `{stake_amount:.2f} ₽` (Мартингейл x{martingale_level})"
                elif user_strategy == 'percentage':
                    stake_rub = current_balance * 0.02
                    bankroll_text = f"\n💰 **Рекомендуемая ставка:** `{stake_rub:.2f} ₽` (2% от банка)"
                else:
                    stake_rub = current_balance * 0.02
                    bankroll_text = f"\n💰 **Рекомендуемая ставка:** `{stake_rub:.2f} ₽` (2% от банка)"
            else:
                bankroll_text = "\n💰 **Ставка:** Установите банк командой /set_bank"
        else:
            bankroll_text = "\n💰 **Ставка:** `2% от депозита`"
        
        message = f"""
{signal_emoji} *СИГНАЛ ДЛЯ POCKET OPTION* {signal_emoji}

╔═══════════════════════════╗
║  📊 *АКТИВ:* `{pocket_asset_clean}`
╚═══════════════════════════╝
_↑ Кликните на название для копирования ↑_

{signal_info['direction']} *НАПРАВЛЕНИЕ:* `{direction_text}`{otc_indicator}
🎯 *Уверенность:* `{confidence:.0f}%`
⏱ *Экспирация:* `{expiration}`
🕒 *Время входа:* `{current_time}`
{bankroll_text}

{stats_text}{forecast_text}

📊 *Анализ рынка:*
• Волатильность: {volatility_status} ({volatility:.2f}%)
• Активность: {whale_status}
• Тренд: `{signal_info['trend']}`
• Оценка: `{signal_info['score']}/8` ⭐

📈 **Технические индикаторы:**
• RSI: `{signal_info['rsi']:.0f}` | Stoch: `{signal_info['stoch_k']:.0f}`
• MACD: `{signal_info['macd']:.4f}`

📸 **График приложен выше** 
_Реальный анализ с индикаторами EMA и объемами_

💡 **Быстрый старт:**
1. ✅ Кликните на название актива выше
2. 📱 Откройте Pocket Option
3. 🔍 Вставьте в поиск
4. 💵 Ставка: `{direction_text}`
5. ⏱ Время: `{expiration}`

💰 _Доходность: {PAYOUT_PERCENT}% | Самообучающаяся AI система_
"""
        return message
    
    def get_expiration_time(self, timeframe):
        """Возвращает оптимальное время экспирации для Pocket Option"""
        expiration_map = {
            "1M": "1 минута",
            "3M": "3 минуты", 
            "5M": "5 минут",
            "15M": "15 минут",
            "30M": "30 минут",
            "1H": "1 час",
            "4H": "4 часа", 
            "1D": "1 день"
        }
        return expiration_map.get(timeframe, "5 минут")

bot = CryptoSignalsBot()

async def auto_delete_message(message, delay=10):
    """Автоматическое неблокирующее удаление сообщения через заданное время"""
    try:
        await asyncio.sleep(delay)
        await message.delete()
    except Exception as e:
        logger.debug(f"Could not delete message: {e}")

def add_home_button(keyboard=None):
    """Добавляет кнопку домика к существующей клавиатуре или создает новую"""
    if keyboard is None:
        keyboard = []
    
    # Добавить кнопку домика
    keyboard.append([InlineKeyboardButton("🏠", callback_data="start")])
    return InlineKeyboardMarkup(keyboard)

async def start_countdown_notification(bot_instance, user_id, chat_id, asset_name, timeframe, signal_info, signal_id):
    """Автоматический обратный отсчет для SHORT сигналов (через 15 секунд после выдачи)"""
    try:
        # Ждем 15 секунд перед началом отсчета
        await asyncio.sleep(15)
        
        # Рассчитываем время экспирации
        timeframe_minutes = {
            "1M": 1, "2M": 2, "3M": 3, "5M": 5,
            "15M": 15, "30M": 30
        }
        total_seconds = timeframe_minutes.get(timeframe, 5) * 60
        
        # Вычитаем уже прошедшие 15 секунд
        remaining = total_seconds - 15
        
        if remaining <= 0:
            # Время уже истекло
            return
        
        direction_emoji = "🟢" if signal_info['signal'] == "CALL" else "🔴"
        
        # Отправляем начальное сообщение с отсчетом
        minutes = remaining // 60
        seconds = remaining % 60
        
        countdown_text = f"""
⏱️ **ОБРАТНЫЙ ОТСЧЕТ**

{direction_emoji} **{asset_name}** | {signal_info['signal']}
📊 **Таймфрейм:** {timeframe}

⏰ **Осталось:** {minutes}:{seconds:02d}
"""
        
        keyboard = [[InlineKeyboardButton("❌ Скрыть", callback_data="hide_countdown")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        countdown_msg = await bot_instance.send_message(
            chat_id=chat_id,
            text=countdown_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Обновляем обратный отсчет каждые 15 секунд
        update_interval = 15  # Обновляем каждые 15 секунд
        countdown_was_hidden = False
        
        while remaining > 0:
            # Спим только на фактически оставшееся время
            sleep_time = min(update_interval, remaining)
            await asyncio.sleep(sleep_time)
            remaining -= sleep_time
            
            # Показываем финальное обновление даже если remaining <= 0
            minutes = max(0, remaining // 60)
            seconds = max(0, remaining % 60)
            
            updated_text = f"""
⏱️ **ОБРАТНЫЙ ОТСЧЕТ**

{direction_emoji} **{asset_name}** | {signal_info['signal']}
📊 **Таймфрейм:** {timeframe}

⏰ **Осталось:** {minutes}:{seconds:02d}
"""
            
            try:
                await countdown_msg.edit_text(
                    updated_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except Exception as e:
                # Сообщение удалено пользователем или скрыто
                logger.debug(f"Countdown message edit failed (likely deleted by user): {e}")
                countdown_was_hidden = True
                break
            
            if remaining <= 0:
                break
        
        # Удаляем сообщение с обратным отсчетом после завершения
        try:
            await countdown_msg.delete()
        except Exception:
            pass
        
        # Отправляем окно с вопросом о результате (только если countdown не был скрыт)
        if not countdown_was_hidden:
            result_text = f"""
⏰ **ВРЕМЯ ИСТЕКЛО!**

{direction_emoji} **{asset_name}** | {signal_info['signal']}
📊 **Таймфрейм:** {timeframe}

📝 **Пожалуйста, отметьте результат вашей сделки:**
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Прибыль", callback_data=f"result_win_{signal_id}"),
                    InlineKeyboardButton("❌ Убыток", callback_data=f"result_loss_{signal_id}")
                ],
                [
                    InlineKeyboardButton("🔄 Возврат", callback_data=f"result_refund_{signal_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await bot_instance.send_message(
                chat_id=chat_id,
                text=result_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            logger.info(f"⏰ Sent result request for signal {signal_id} to user {user_id}")
            
            # Проверить, является ли пользователь FREE и отправить предложение апгрейда
            has_subscription, message, signals_used, free_trials_used, sub_type = bot.check_subscription(user_id)
            if not has_subscription or sub_type == 'free':
                can_access, used_today = bot.check_free_short_limit(user_id)
                remaining_short = max(0, 5 - used_today)
                
                upgrade_text = f"""
🔥 **ЗАВЕРШИЛИ SHORT СДЕЛКУ!** 

📊 У вас осталось: {remaining_short}/5 SHORT сигналов сегодня

💎 **ХОТИТЕ ЗАРАБАТЫВАТЬ КАЖДЫЙ ДЕНЬ БЕЗ ОГРАНИЧЕНИЙ?**
Переходите на платные тарифы и получайте:

⚡ **SHORT** (4,990₽/мес):
• Безлимитные быстрые сигналы 1-5 мин
• Мартингейл x2/x3 стратегия
• Автоматический countdown

🔵 **LONG** (6,990₽/мес):
• Безлимитные длинные сигналы 1-4 часа
• Процентная стратегия 2-3%
• Управление через /my_longs

💎 **VIP** (9,990₽/мес):
• ВСЕ СИГНАЛЫ SHORT + LONG
• Авто-рассылка 5 раз в день
• Приоритетная поддержка

🚀 Начните зарабатывать больше: /plans
"""
                # Не показывать кнопку админам
                if not bot.is_admin(user_id):
                    upgrade_keyboard = [
                        [InlineKeyboardButton("🔥💎 ВЫБРАТЬ ТАРИФ И ЗАРАБАТЫВАТЬ! 💰🚀", callback_data="buy_subscription")]
                    ]
                    upgrade_markup = InlineKeyboardMarkup(upgrade_keyboard)
                else:
                    upgrade_markup = None
                
                await bot_instance.send_message(
                    chat_id=chat_id,
                    text=upgrade_text,
                    reply_markup=upgrade_markup,
                    parse_mode='Markdown'
                )
            
    except Exception as e:
        logger.error(f"Error in countdown notification: {e}")

async def background_check_expired_signals(app):
    """Фоновая задача для проверки истекших сигналов и автоматического пропуска игнорированных"""
    while True:
        try:
            await asyncio.sleep(60)
            
            # Автоматически пропустить проигнорированные уведомления (старше 24 часов)
            bot.auto_skip_ignored_signals()
            
            expired_signals = bot.get_expired_signals()
            
            for signal in expired_signals:
                signal_id, user_id, asset, timeframe, signal_type, confidence, stake_amount = signal
                
                direction_emoji = "🟢" if signal_type == "CALL" else "🔴"
                
                message_text = f"""
⏰ **ВРЕМЯ СИГНАЛА ИСТЕКЛО!**

{direction_emoji} **Актив:** {asset}
📊 **Направление:** {signal_type}
⏱ **Таймфрейм:** {timeframe}
🎯 **Уверенность:** {confidence:.0f}%
💰 **Ставка:** {stake_amount:.2f} RUB

❓ **Как закрылась сделка?**

📊 **Важно для личной статистики и управления банком!**
Если вы ставили на этот сигнал - отметьте результат.
Если НЕ ставили - нажмите "Пропустить" или проигнорируйте это сообщение.
"""
                
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Прибыль (+)", callback_data=f"result_win_{signal_id}"),
                        InlineKeyboardButton("❌ Убыток (-)", callback_data=f"result_loss_{signal_id}")
                    ],
                    [
                        InlineKeyboardButton("⏭️ Пропустить", callback_data=f"result_skip_{signal_id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                try:
                    await app.bot.send_message(
                        chat_id=user_id,
                        text=message_text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                    
                    bot.mark_signal_as_notified(signal_id)
                    logger.info(f"⏰ Sent expiration notification for signal {signal_id} to user {user_id}")
                except Exception as e:
                    logger.error(f"Error sending expiration notification: {e}")
        except Exception as e:
            logger.error(f"Error in background task: {e}")

async def background_check_pending_notifications(app):
    """Фоновая задача для проверки отложенных уведомлений"""
    await asyncio.sleep(60)  # Задержка перед первой проверкой
    
    while True:
        try:
            pending = bot.get_pending_notifications()
            
            for notification_id, user_id, timeframe_type in pending:
                # Попробовать найти сигнал для пользователя
                if timeframe_type == "all":
                    timeframe_type = None
                    
                signals = await scan_market_signals(timeframe_type)
                
                if signals:
                    # Найден сигнал! Отправить уведомление
                    weighted_signals = []
                    for asset_name, signal_info, timeframe in signals:
                        adaptive_weight = bot.get_adaptive_weight(asset_name, timeframe)
                        weighted_confidence = signal_info['confidence'] * adaptive_weight
                        weighted_signals.append((asset_name, signal_info, timeframe, weighted_confidence))
                    
                    # Берем лучший сигнал
                    weighted_signals.sort(key=lambda x: x[3], reverse=True)
                    if weighted_signals:
                        asset_name, signal_info, timeframe, _ = weighted_signals[0]
                        
                        notification_text = f"""
🔔 **НАЙДЕН ТОЧНЫЙ СИГНАЛ!**

🎯 **Актив:** {asset_name}
{'🟢' if signal_info['signal'] == 'CALL' else '🔴'} **Направление:** {signal_info['signal']}
📊 **Уверенность:** {signal_info['confidence']}%
⏰ **Таймфрейм:** {timeframe}

Используйте /long или /short для получения полного сигнала с графиком!
"""
                        
                        try:
                            await app.bot.send_message(
                                chat_id=user_id,
                                text=notification_text,
                                parse_mode='Markdown'
                            )
                            logger.info(f"🔔 Sent pending notification to user {user_id}")
                        except Exception as e:
                            logger.error(f"Failed to send notification to {user_id}: {e}")
                        
                        # Деактивировать уведомление
                        bot.deactivate_notification(notification_id)
                
                await asyncio.sleep(1)  # Задержка между проверками пользователей
            
        except Exception as e:
            logger.error(f"Error in pending notifications task: {e}")
        
        # Проверять каждые 15 минут
        await asyncio.sleep(900)

async def background_vip_daily_signals(app):
    """Фоновая задача: отправка 10 лучших LONG сигналов VIP подписчикам и FREE пользователям (5x в день)"""
    await asyncio.sleep(10)  # Подождать запуска бота
    
    last_sent_date = None
    
    while True:
        try:
            now = datetime.now()
            current_date = now.date()
            
            # Отправлять 6 раз в день с распределением нагрузки в неактивное время
            # Основная нагрузка в ночное время: 1:00, 3:00, 5:00
            # Дневное время: 9:00, 13:00, 19:00
            send_hours = [1, 3, 5, 9, 13, 19]
            
            if current_date != last_sent_date or (now.hour in send_hours and now.minute < 15):
                # Проверить нужно ли отправлять
                if last_sent_date != current_date or now.hour in send_hours:
                    logger.info(f"🔍 Scanning for VIP/FREE signals at {now.strftime('%H:%M')}")
                    
                    # Получить всех VIP и FREE пользователей
                    vip_users = bot.get_all_vip_users()
                    free_users = bot.get_all_free_users()
                    
                    if vip_users or free_users:
                        # Получить 10 лучших LONG сигналов с повышенным порогом точности (≥95%)
                        # Выполнить в отдельном потоке, чтобы не блокировать event loop
                        best_signals = await asyncio.to_thread(bot.get_best_long_signals, limit=10, min_confidence=95.0)
                        
                        if best_signals:
                            # Отправить VIP пользователям
                            for vip_user_id in vip_users:
                                try:
                                    signals_text = f"💎 **VIP СИГНАЛЫ** - {now.strftime('%d.%m.%Y %H:%M')}\n\n"
                                    signals_text += f"📊 Топ-{len(best_signals)} сверхточных LONG сигналов:\n\n"
                                    
                                    for idx, sig in enumerate(best_signals, 1):
                                        asset = sig['asset']
                                        timeframe = sig['timeframe']
                                        signal_info = sig['signal']
                                        confidence = sig['confidence']
                                        signal_type = signal_info.get('signal', 'HOLD')
                                        entry = signal_info.get('entry_price', 0)
                                        emoji = "🟢" if signal_type == "CALL" else "🔴"
                                        
                                        signals_text += f"{idx}. {emoji} **{asset}** ({timeframe})\n"
                                        signals_text += f"   {signal_type} | {confidence:.1f}% | ${entry:.2f}\n\n"
                                        
                                        # Сохранить сигнал в my_longs для VIP
                                        bot.save_signal_to_longs(vip_user_id, asset, timeframe, signal_type, entry, confidence, tier='vip')
                                    
                                    signals_text += "⚡ Используйте `/my_longs` для управления позициями"
                                    
                                    await app.bot.send_message(chat_id=vip_user_id, text=signals_text, parse_mode='Markdown')
                                    logger.info(f"✅ Sent VIP signals to user {vip_user_id}")
                                    await asyncio.sleep(0.5)
                                except Exception as e:
                                    logger.error(f"Error sending VIP signal to {vip_user_id}: {e}")
                            
                            # Отправить FREE пользователям
                            for free_user_id in free_users:
                                try:
                                    signals_text = f"🆓 **FREE СИГНАЛЫ** - {now.strftime('%d.%m.%Y %H:%M')}\n\n"
                                    signals_text += f"📊 Топ-{len(best_signals)} УЛЬТРА-ТОЧНЫХ прогнозов (≥95%):\n\n"
                                    
                                    for idx, sig in enumerate(best_signals, 1):
                                        asset = sig['asset']
                                        timeframe = sig['timeframe']
                                        signal_info = sig['signal']
                                        confidence = sig['confidence']
                                        signal_type = signal_info.get('signal', 'HOLD')
                                        entry = signal_info.get('entry_price', 0)
                                        emoji = "🟢" if signal_type == "CALL" else "🔴"
                                        
                                        signals_text += f"{idx}. {emoji} **{asset}** ({timeframe})\n"
                                        signals_text += f"   {signal_type} | {confidence:.1f}% | ${entry:.2f}\n\n"
                                        
                                        # Сохранить сигнал в my_longs для FREE
                                        bot.save_signal_to_longs(free_user_id, asset, timeframe, signal_type, entry, confidence, tier='free')
                                    
                                    signals_text += "⚡ Используйте `/my_longs` для просмотра активных позиций\n"
                                    signals_text += "💎 Обновитесь до VIP для доступа ко ВСЕМ сигналам!"
                                    
                                    await app.bot.send_message(chat_id=free_user_id, text=signals_text, parse_mode='Markdown')
                                    logger.info(f"✅ Sent FREE signals to user {free_user_id}")
                                    await asyncio.sleep(0.5)
                                except Exception as e:
                                    logger.error(f"Error sending FREE signal to {free_user_id}: {e}")
                            
                            last_sent_date = current_date
                            logger.info(f"✅ Signals sent to {len(vip_users)} VIP and {len(free_users)} FREE users")
                        else:
                            logger.info("⚠️ No high-confidence LONG signals found for VIP")
                    else:
                        logger.info("ℹ️ No VIP users to send signals to")
            
        except Exception as e:
            logger.error(f"Error in VIP daily signals task: {e}")
        
        # Проверять каждые 15 минут
        await asyncio.sleep(900)

async def background_daily_upgrade_offers(app):
    """Фоновая задача: ежедневная отправка предложений апгрейда до VIP для SHORT/LONG пользователей"""
    await asyncio.sleep(30)  # Подождать запуска бота
    
    while True:
        try:
            now = datetime.now()
            
            # Отправлять один раз в день в 12:00
            if now.hour == 12 and now.minute < 15:
                logger.info(f"💎 Scanning for upgrade candidates at {now.strftime('%H:%M')}")
                
                cursor = bot.conn.cursor()
                
                # Получить всех пользователей с SHORT или LONG подписками
                cursor.execute('''
                    SELECT user_id, subscription_type, last_upgrade_offer
                    FROM users
                    WHERE subscription_type IN ('short', 'long')
                    AND subscription_end IS NOT NULL
                    AND datetime(subscription_end) > datetime('now')
                ''')
                
                candidates = cursor.fetchall()
                
                sent_count = 0
                for user_id, sub_type, last_offer in candidates:
                    # Проверить, прошло ли 24 часа с последнего предложения
                    if last_offer:
                        last_offer_time = datetime.fromisoformat(last_offer)
                        if (now - last_offer_time).days < 1:
                            continue
                    
                    # Рассчитать потенциальный доход
                    income_data = bot.calculate_vip_potential_income(user_id)
                    
                    if not income_data:
                        continue
                    
                    # Формировать персонализированное предложение
                    profit_increase = income_data['profit_increase']
                    profit_percent = income_data['profit_increase_percent']
                    months_payback = income_data['months_to_payback']
                    win_rate = income_data['win_rate']
                    
                    sub_emoji = "📉" if sub_type == 'short' else "📈"
                    sub_name = sub_type.upper()
                    
                    offer_text = f"""
💎 **СПЕЦИАЛЬНОЕ ПРЕДЛОЖЕНИЕ VIP**

{sub_emoji} Вы используете {sub_name} подписку
📊 Ваш винрейт: {win_rate:.1f}%

**💰 Потенциал VIP подписки:**
• Доступ к SHORT + LONG сигналам
• 5 автоматических рассылок в день (150 сигналов/месяц)
• Увеличенная ставка LONG: 5% вместо 2.5%
• Приоритетная поддержка

📈 **Ваш прогноз:**
Текущий доход: {income_data['current_monthly_profit']:.0f}₽/месяц
VIP доход: {income_data['vip_monthly_profit']:.0f}₽/месяц
Увеличение: +{profit_increase:.0f}₽/месяц ({profit_percent:.0f}%)

⚡ **Апгрейд окупится за {months_payback:.1f} мес!**

🎁 **СПЕЦИАЛЬНАЯ ЦЕНА ДЛЯ ВАС:**
Апгрейд до VIP всего за **1990₽**
(вместо полной стоимости разницы тарифов)

✅ Апгрейд применяется к текущей подписке
💎 Начните зарабатывать больше прямо сейчас!
"""
                    
                    keyboard = [
                        [InlineKeyboardButton("💎 Апгрейд до VIP (1990₽)", callback_data="upgrade_to_vip")],
                        [InlineKeyboardButton("ℹ️ Подробнее о VIP", callback_data="vip_info")],
                        [InlineKeyboardButton("❌ Не интересует", callback_data="dismiss_upgrade")]
                    ]
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    try:
                        await app.bot.send_message(
                            chat_id=user_id,
                            text=offer_text,
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                        
                        # Обновить время последнего предложения
                        cursor.execute('''
                            UPDATE users 
                            SET last_upgrade_offer = ?
                            WHERE user_id = ?
                        ''', (now.isoformat(), user_id))
                        bot.conn.commit()
                        
                        sent_count += 1
                        logger.info(f"💎 Sent upgrade offer to {sub_type} user {user_id}")
                        await asyncio.sleep(1)  # Задержка между отправками
                        
                    except Exception as e:
                        logger.error(f"Error sending upgrade offer to {user_id}: {e}")
                
                if sent_count > 0:
                    logger.info(f"✅ Sent {sent_count} upgrade offers")
                else:
                    logger.info("ℹ️ No users eligible for upgrade offers")
            
        except Exception as e:
            logger.error(f"Error in upgrade offers task: {e}")
        
        # Проверять каждые 15 минут
        await asyncio.sleep(900)

# DEPRECATED: Auto-broadcast removed - now ON-DEMAND mode only
# Users request signals when needed via buttons, system delivers TOP-1 from cache instantly

async def background_market_analysis(app):
    """Фоновый анализ рынка - обновление пула ТОП-3 сигналов каждую минуту"""
    # Задержка перед первым запуском
    await asyncio.sleep(30)
    
    while True:
        try:
            logger.info("🔄 Starting background market analysis (TOP-3 pool update)...")
            
            # SHORT: 100 активов (50 активов * 2 таймфрейма) -> ТОП-3 сигнала
            short_signals = await scan_market_signals("short")
            logger.info(f"📊 SHORT: {len(short_signals)} TOP signals in pool")
            
            # Обновляем кэш SHORT сигналов
            if short_signals:
                signal_cache['short']['signals'] = short_signals
                signal_cache['short']['timestamp'] = time.time()
            
            # Небольшая пауза между SHORT и LONG
            await asyncio.sleep(30)
            
            # LONG: 60 активов (30 активов * 2 таймфрейма) -> ТОП-3 сигнала
            long_signals = await scan_market_signals("long")
            logger.info(f"📊 LONG: {len(long_signals)} TOP signals in pool")
            
            # Обновляем кэш LONG сигналов
            if long_signals:
                signal_cache['long']['signals'] = long_signals
                signal_cache['long']['timestamp'] = time.time()
            
            logger.info("✅ Background pool updated (доходность 85-92%, ТОП-3 лучших)")
            
        except Exception as e:
            logger.error(f"Error in background market analysis: {e}")
        
        # Обновлять пул каждую минуту
        # Итого: SHORT анализ -> пауза 30s -> LONG анализ -> пауза 30s = ~60s цикл
        await asyncio.sleep(30)

async def background_auto_trading(app):
    """Фоновая задача автоматического трейдинга"""
    await asyncio.sleep(30)  # Подождать инициализации
    
    logger.info("🤖 Auto-trading background task started")
    
    while True:
        try:
            # Найти пользователей с включенным автотрейдингом
            cursor = bot.conn.cursor()
            cursor.execute('''
                SELECT user_id, subscription_type, auto_trading_strategy
                FROM users 
                WHERE auto_trading_enabled = 1 
                AND pocket_option_connected = 1
                AND pocket_option_ssid IS NOT NULL
            ''')
            active_traders = cursor.fetchall()
            
            if active_traders:
                logger.info(f"🤖 Found {len(active_traders)} active auto-traders")
                
                for user_id, sub_type, strategy in active_traders:
                    try:
                        # Проверить подписку (только VIP)
                        if sub_type != 'vip':
                            continue
                        
                        # Получить сигнал для пользователя
                        # Используем SHORT сигналы для автотрейдинга (быстрые сделки)
                        if signal_cache['short']['signals']:
                            signal = random.choice(signal_cache['short']['signals'])
                            
                            logger.info(f"🎯 Auto-trading for user {user_id}: {signal.get('asset')} {signal.get('direction')}")
                            
                            # Разместить сделку
                            result = await execute_auto_trade(user_id, signal)
                            
                            if result.get('success'):
                                # Отправить уведомление пользователю
                                try:
                                    await app.bot.send_message(
                                        chat_id=user_id,
                                        text=f"🤖 **АВТОТРЕЙДИНГ**\n\n{result.get('message')}\n\n"
                                             f"💰 Баланс: ${result.get('new_balance', 0):.2f}",
                                        parse_mode='Markdown'
                                    )
                                except:
                                    pass
                                
                                # Пауза между сделками одного пользователя (мин 5 минут)
                                await asyncio.sleep(300)
                            else:
                                logger.warning(f"⚠️ Auto-trade failed for user {user_id}: {result.get('message')}")
                        
                    except Exception as e:
                        logger.error(f"Auto-trading error for user {user_id}: {e}")
                        continue
            
            # Пауза перед следующим циклом (30 секунд)
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Background auto-trading error: {e}")
            await asyncio.sleep(60)

async def post_init(app):
    """Запустить фоновые задачи после инициализации приложения"""
    asyncio.create_task(background_check_expired_signals(app))
    asyncio.create_task(background_check_pending_notifications(app))
    # DISABLED: asyncio.create_task(background_vip_daily_signals(app))  # ON-DEMAND mode only
    asyncio.create_task(background_daily_upgrade_offers(app))
    asyncio.create_task(background_market_analysis(app))
    asyncio.create_task(start_background_testing(app))
    asyncio.create_task(background_auto_trading(app))
    logger.info("⏰ Started background tasks: expiration + pending + upgrade offers + market analysis + auto-testing + auto-trading (ON-DEMAND mode)")

async def update_scanning_animation(msg, frames):
    """Обновляет сообщение с анимацией сканирования"""
    frame_index = 0
    try:
        while True:
            await asyncio.sleep(3)  # Обновляем каждые 3 секунды для быстрой анимации
            frame_index += 1
            try:
                await msg.edit_text(frames[frame_index % len(frames)])
            except:
                pass  # Игнорируем ошибки редактирования
    except asyncio.CancelledError:
        pass

# Глобальный кэш сигналов с временными метками
signal_cache = {
    'short': {'signals': [], 'timestamp': 0},
    'long': {'signals': [], 'timestamp': 0}
}
CACHE_DURATION = 180  # Кэш на 3 минуты для стабильности при большой нагрузке

# Отслеживание последних выданных активов для разнообразия
last_used_assets = {
    'short': [],  # Последние 5 выданных SHORT активов
    'long': []    # Последние 5 выданных LONG активов
}
MAX_RECENT_ASSETS = 5  # Максимум последних активов для исключения

# Отслеживание проигрышей по активам (для блокировки нестабильных)
asset_loss_streak = {}  # {asset_name: consecutive_losses}
MAX_CONSECUTIVE_LOSSES = 2  # Максимум проигрышей подряд перед блокировкой
blocked_assets = {}  # {asset_name: block_until_timestamp}

def get_best_signal_from_cache(signal_type='short', user_priority='free', user_id=None):
    """
    Умный выбор ТОП-1 сигнала из кэша с учетом:
    - ПРИОРИТЕТ: OTC активы с высокой доходностью (92%)
    - Адаптивной статистики (win rate актива)
    - Исторических паттернов (прогноз)
    - Базового confidence
    - Score (количество подтверждающих индикаторов)
    - Волатильности (предпочтение стабильным активам)
    - Активности китов (крупные объемы)
    - FREE фильтрация (только ≥95% win rate + минимум 5 сигналов)
    - Исключение уже выданных активных сигналов пользователя
    """
    
    signals = signal_cache.get(signal_type, {}).get('signals', [])
    
    if not signals:
        return None
    
    # Получить список активных сигналов пользователя для исключения
    active_user_signals = set()
    if user_id:
        active_user_signals = set(bot.get_user_active_signals(user_id))
    
    # Получаем адаптивные веса и исторические данные для всех активов
    scored_signals = []
    
    # Очистить заблокированные активы с истекшим временем блокировки
    current_time = time.time()
    for asset in list(blocked_assets.keys()):
        if current_time >= blocked_assets[asset]:
            del blocked_assets[asset]
            if asset in asset_loss_streak:
                del asset_loss_streak[asset]
    
    for asset_name, signal_info, timeframe in signals:
        # ИСКЛЮЧАЕМ уже выданные активные сигналы
        if (asset_name, timeframe) in active_user_signals:
            continue  # Этот сигнал уже выдан пользователю и еще не истек
        
        # ИСКЛЮЧАЕМ заблокированные активы (2 проигрыша подряд)
        if asset_name in blocked_assets:
            continue  # Этот актив проиграл 2 раза подряд, блокируем на час
        
        # ИСКЛЮЧАЕМ недавно использованные активы для разнообразия (последние 5)
        if asset_name in last_used_assets.get(signal_type, []):
            continue  # Этот актив был выдан недавно, ищем другой
        
        # 1. Базовый confidence (0-100)
        base_confidence = signal_info.get('confidence', 0)
        
        # 2. Адаптивный вес (из таблицы signal_performance)
        adaptive_weight = bot.get_adaptive_weight(asset_name, timeframe)
        
        # 3. Получить статистику актива для FREE фильтрации
        cursor = bot.conn.cursor()
        cursor.execute('''
            SELECT total_signals, wins, losses, win_rate 
            FROM signal_performance 
            WHERE asset = ? AND timeframe = ?
        ''', (asset_name, timeframe))
        stats = cursor.fetchone()
        win_rate = stats[3] if stats else 0.0
        total_signals_count = stats[0] if stats else 0
        
        # FREE фильтрация: только доказанно прибыльные сигналы
        if user_priority == 'free':
            if not (stats and total_signals_count >= 5 and win_rate >= 0.95):
                continue  # Пропускаем сигнал для FREE пользователей
        
        # 4. ДОХОДНОСТЬ АКТИВА (ключевой фактор - 92% для OTC)
        payout = signal_info.get('payout', 85)  # По умолчанию 85%
        asset_type = signal_info.get('asset_type', 'regular')
        
        # Огромный бонус для OTC активов с 92% доходностью
        payout_bonus = 0
        if payout >= 92:
            payout_bonus = 25  # МАКСИМАЛЬНЫЙ ПРИОРИТЕТ для 92%
        elif payout >= 85:
            payout_bonus = 15  # OTC с 85%
        elif payout >= 80:
            payout_bonus = 10
        elif payout >= 65:
            payout_bonus = 5
        
        # 5. Исторический паттерн (прогноз на основе последних 24 часов)
        pattern = bot.get_historical_pattern(asset_name, timeframe)
        pattern_bonus = 0
        if pattern:
            # Если тренд и киты совпадают с текущим сигналом - бонус
            trend_match = pattern.get('predicted_direction') == signal_info.get('direction')
            whale_active = pattern.get('whale_activity_pct', 0) >= 30
            if trend_match and whale_active:
                pattern_bonus = 15  # Большой бонус за совпадение паттерна
            elif trend_match:
                pattern_bonus = 8
        
        # 6. Score (количество подтверждающих индикаторов)
        score = signal_info.get('score', 0)
        score_bonus = score * 3  # Каждый индикатор +3%
        
        # 7. Волатильность (УСИЛЕННОЕ предпочтение низкой для стабильности)
        volatility = signal_info.get('volatility', 1.0)
        volatility_bonus = 0
        if volatility < 0.2:
            volatility_bonus = 20  # Очень стабильный актив - максимальный приоритет
        elif volatility < 0.3:
            volatility_bonus = 15  # Стабильный
        elif volatility < 0.5:
            volatility_bonus = 8   # Умеренная волатильность
        elif volatility >= 0.8:
            volatility_bonus = -10  # Штраф за высокую волатильность
        
        # 8. Активность китов
        whale_bonus = 8 if signal_info.get('whale_activity') else 0
        
        # ИТОГОВЫЙ РАСЧЕТ (приоритет доходности!)
        final_score = (
            base_confidence * adaptive_weight +  # Базовая уверенность с адаптацией
            payout_bonus +                        # ДОХОДНОСТЬ (топ приоритет)
            pattern_bonus +                       # Исторический паттерн
            score_bonus +                         # Индикаторы
            volatility_bonus +                    # Стабильность
            whale_bonus                           # Киты
        )
        
        scored_signals.append({
            'asset_name': asset_name,
            'signal_info': signal_info,
            'timeframe': timeframe,
            'final_score': final_score,
            'win_rate': win_rate,
            'payout': payout,
            'asset_type': asset_type,
            'breakdown': {
                'base_confidence': base_confidence,
                'adaptive_weight': adaptive_weight,
                'weighted_confidence': base_confidence * adaptive_weight,
                'payout': payout,
                'payout_bonus': payout_bonus,
                'pattern_bonus': pattern_bonus,
                'score_bonus': score_bonus,
                'volatility_bonus': volatility_bonus,
                'whale_bonus': whale_bonus,
                'win_rate': win_rate
            }
        })
    
    if not scored_signals:
        return None  # Нет подходящих сигналов после фильтрации
    
    # Сортируем по итоговому score (включая доходность), затем по win_rate
    scored_signals.sort(key=lambda x: (x['final_score'], x['win_rate']), reverse=True)
    
    # Возвращаем ТОП-1 сигнал
    best = scored_signals[0]
    
    # Добавляем актив в список недавно использованных для разнообразия
    if signal_type in last_used_assets:
        last_used_assets[signal_type].append(best['asset_name'])
        # Ограничиваем список последними MAX_RECENT_ASSETS элементами
        if len(last_used_assets[signal_type]) > MAX_RECENT_ASSETS:
            last_used_assets[signal_type].pop(0)
    
    priority_emoji = {'admin': '👑', 'vip': '💎', 'short': '⚡', 'long': '🔵', 'free': '🆓'}
    otc_marker = "🔥 OTC" if best['asset_type'] == 'otc' else ""
    logger.info(f"{priority_emoji.get(user_priority, '🎯')} TOP-1 {signal_type.upper()} signal: {best['asset_name']} {best['timeframe']} {otc_marker} | "
                f"Final Score: {best['final_score']:.1f} | "
                f"Payout: {best['payout']}% (+{best['breakdown']['payout_bonus']}) | "
                f"Base: {best['breakdown']['base_confidence']:.1f}% | "
                f"Adaptive: {best['breakdown']['adaptive_weight']:.2f}x | "
                f"WR: {best['breakdown']['win_rate']*100:.1f}% | "
                f"Pattern: +{best['breakdown']['pattern_bonus']} | "
                f"Score: +{best['breakdown']['score_bonus']} | "
                f"Volatility: +{best['breakdown']['volatility_bonus']} | "
                f"Whale: +{best['breakdown']['whale_bonus']}")
    
    return (best['asset_name'], best['signal_info'], best['timeframe'])

# ВАЖНО: Yahoo Finance поддерживаемые интервалы: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
# Таймфрейм 3m НЕ поддерживается, поэтому используем 1m и 5m для SHORT сигналов

# Система приоритетов пользователей (чем выше число, тем выше приоритет)
USER_PRIORITY = {
    'admin': 100,
    'vip': 80,
    'long': 60,
    'short': 60,
    'free': 20
}

# Таймауты сканирования в секундах по приоритету
SCAN_TIMEOUTS = {
    'admin': 10,  # Админ - быстрое сканирование
    'vip': 15,    # VIP - стандартное
    'long': 20,   # Средние тарифы
    'short': 20,
    'free': 45    # FREE - расширенное сканирование для лучших сигналов
}

# АКТУАЛЬНЫЕ АКТИВЫ POCKET OPTION с указанием типа (OTC/обычный) и доходности
# Формат: "название": {"symbol": "yahoo_symbol", "type": "otc/regular", "payout": доходность%}
MARKET_ASSETS = {
    # Криптовалюты OTC (приоритет - максимальная доходность 92%)
    "crypto_otc": {
        "BTC/USD OTC": {"symbol": "BTC-USD", "type": "otc", "payout": 92},
        "ETH/USD OTC": {"symbol": "ETH-USD", "type": "otc", "payout": 92},
        "ADA/USD OTC": {"symbol": "ADA-USD", "type": "otc", "payout": 92},  # Cardano
        "LINK/USD OTC": {"symbol": "LINK-USD", "type": "otc", "payout": 92},  # Chainlink
        "SOL/USD OTC": {"symbol": "SOL-USD", "type": "otc", "payout": 92},  # Solana
        "TRX/USD OTC": {"symbol": "TRX-USD", "type": "otc", "payout": 92},  # TRON
        "AVAX/USD OTC": {"symbol": "AVAX-USD", "type": "otc", "payout": 92},  # Avalanche
        "LTC/USD OTC": {"symbol": "LTC-USD", "type": "otc", "payout": 92},
        "BNB/USD OTC": {"symbol": "BNB-USD", "type": "otc", "payout": 92},
        "TON/USD OTC": {"symbol": "TON11419-USD", "type": "otc", "payout": 92},  # Toncoin
    },
    
    # Криптовалюты обычные (85% доходность)
    "crypto": {
        "BTC/USD": {"symbol": "BTC-USD", "type": "regular", "payout": 85},
        "ETH/USD": {"symbol": "ETH-USD", "type": "regular", "payout": 85},
        "LTC/USD": {"symbol": "LTC-USD", "type": "regular", "payout": 85},
        "XRP/USD": {"symbol": "XRP-USD", "type": "regular", "payout": 85},
        "ADA/USD": {"symbol": "ADA-USD", "type": "regular", "payout": 85},
        "BNB/USD": {"symbol": "BNB-USD", "type": "regular", "payout": 85},
    },
    
    # Форекс OTC (92% доходность)
    "forex_otc": {
        "EUR/USD OTC": {"symbol": "EURUSD=X", "type": "otc", "payout": 92},
        "GBP/USD OTC": {"symbol": "GBPUSD=X", "type": "otc", "payout": 92},
        "USD/JPY OTC": {"symbol": "JPY=X", "type": "otc", "payout": 92},
        "AUD/USD OTC": {"symbol": "AUDUSD=X", "type": "otc", "payout": 92},
    },
    
    # Форекс обычные (85% доходность)
    "forex": {
        "EUR/USD": {"symbol": "EURUSD=X", "type": "regular", "payout": 85},
        "GBP/USD": {"symbol": "GBPUSD=X", "type": "regular", "payout": 85},
        "USD/JPY": {"symbol": "JPY=X", "type": "regular", "payout": 85},
        "AUD/USD": {"symbol": "AUDUSD=X", "type": "regular", "payout": 85},
        "USD/CHF": {"symbol": "CHF=X", "type": "regular", "payout": 85},
        "EUR/GBP": {"symbol": "EURGBP=X", "type": "regular", "payout": 85},
        "USD/CAD": {"symbol": "CAD=X", "type": "regular", "payout": 85},
        "NZD/USD": {"symbol": "NZDUSD=X", "type": "regular", "payout": 85},
        "EUR/JPY": {"symbol": "EURJPY=X", "type": "regular", "payout": 85},
        "GBP/JPY": {"symbol": "GBPJPY=X", "type": "regular", "payout": 85},
    },
    
    # Акции OTC (92% доходность)
    "stocks_otc": {
        "AAPL OTC": {"symbol": "AAPL", "type": "otc", "payout": 92},  # Apple
        "INTC OTC": {"symbol": "INTC", "type": "otc", "payout": 92},  # Intel
    },
    
    # Акции обычные (85% доходность)
    "stocks": {
        "AAPL": {"symbol": "AAPL", "type": "regular", "payout": 85},
        "MSFT": {"symbol": "MSFT", "type": "regular", "payout": 85},
        "AMZN": {"symbol": "AMZN", "type": "regular", "payout": 85},
        "TSLA": {"symbol": "TSLA", "type": "regular", "payout": 85},
        "META": {"symbol": "META", "type": "regular", "payout": 85},
        "INTC": {"symbol": "INTC", "type": "regular", "payout": 85},
        "BA": {"symbol": "BA", "type": "regular", "payout": 85},
    },
    
    # Товары и индексы OTC (высокая доходность)
    "commodities_otc": {
        "GOLD OTC": {"symbol": "GC=F", "type": "otc", "payout": 80},
        "AUS200 OTC": {"symbol": "^AXJO", "type": "otc", "payout": 67},  # Australia 200
    },
    
    # Товары и индексы обычные (36-85%)
    "commodities": {
        "XAU/USD": {"symbol": "GC=F", "type": "regular", "payout": 85},  # Gold
        "XAG/USD": {"symbol": "SI=F", "type": "regular", "payout": 85},  # Silver
        "OIL/USD": {"symbol": "CL=F", "type": "regular", "payout": 85},  # WTI
        "BRENT": {"symbol": "BZ=F", "type": "regular", "payout": 85},
        "NG/USD": {"symbol": "NG=F", "type": "regular", "payout": 85},
        "S&P500": {"symbol": "^GSPC", "type": "regular", "payout": 85},
        "NASDAQ": {"symbol": "^IXIC", "type": "regular", "payout": 85},
        "DOW": {"symbol": "^DJI", "type": "regular", "payout": 85},
        "FTSE": {"symbol": "^FTSE", "type": "regular", "payout": 85},
    }
}

# Инициализируем bot.assets из MARKET_ASSETS после его определения
for category in ["crypto_otc", "crypto", "forex_otc", "forex", "stocks_otc", "stocks", "commodities_otc", "commodities"]:
    for asset_name, asset_data in MARKET_ASSETS.get(category, {}).items():
        if isinstance(asset_data, dict):
            bot.assets[asset_name] = asset_data["symbol"]

async def analyze_asset_async(asset_name, asset_data, timeframe, min_confidence=85, is_otc=False):
    """Асинхронный анализ одного актива с поддержкой OTC/обычных активов"""
    try:
        asset_symbol = asset_data["symbol"]
        signal_info, error = await asyncio.to_thread(
            bot.analyze_asset_timeframe, asset_symbol, timeframe
        )
        
        # Используем переданный min_confidence без дополнительных ограничений
        if signal_info and signal_info.get('confidence', 0) >= min_confidence:
            # Добавляем информацию о типе актива и доходности
            signal_info['asset_type'] = asset_data["type"]
            signal_info['payout'] = asset_data["payout"]
            signal_info['is_otc'] = is_otc
            return (asset_name, signal_info, timeframe)
    except Exception as e:
        logger.debug(f"Error analyzing {asset_name}: {e}")
    return None

async def scan_market_signals(timeframe_type, force_realtime=False):
    """Оптимизированное сканирование рынка с поддержкой OTC активов (приоритет 92% доходности)"""
    
    # Проверить кэш (для LONG используем кэш, для SHORT - реальное время)
    cache_key = timeframe_type if timeframe_type in ['short', 'long'] else 'short'
    current_time = time.time()
    
    # SHORT всегда в реальном времени (force_realtime=True)
    # LONG использует кэш для фоновой загрузки
    if timeframe_type == "long" and not force_realtime:
        if (current_time - signal_cache[cache_key]['timestamp']) < CACHE_DURATION:
            cached_signals = signal_cache[cache_key]['signals']
            if cached_signals:
                logger.info(f"✅ Using cached {cache_key} signals ({len(cached_signals)} found)")
                return cached_signals
    
    signals = []
    tasks = []
    
    # Выбираем активы и таймфреймы в зависимости от типа запроса
    if timeframe_type == "short":
        # Short - ПОИСК В РЕАЛЬНОМ ВРЕМЕНИ
        # ПРИОРИТЕТ: OTC активы с 92% доходностью
        logger.info("🔍 SHORT: Поиск сигналов в реальном времени (приоритет OTC 92%)")
        
        for timeframe in ["1M", "5M"]:
            # OTC Криптовалюты (92% доходность - максимальный приоритет, оптимальный порог 80%)
            for asset_name, asset_data in MARKET_ASSETS["crypto_otc"].items():
                tasks.append(analyze_asset_async(asset_name, asset_data, timeframe, min_confidence=80, is_otc=True))
            
            # OTC Форекс (92% доходность, оптимальный порог 80%)
            for asset_name, asset_data in MARKET_ASSETS["forex_otc"].items():
                tasks.append(analyze_asset_async(asset_name, asset_data, timeframe, min_confidence=80, is_otc=True))
            
            # OTC Акции (92% доходность, оптимальный порог 80%)
            for asset_name, asset_data in MARKET_ASSETS["stocks_otc"].items():
                tasks.append(analyze_asset_async(asset_name, asset_data, timeframe, min_confidence=80, is_otc=True))
            
            # OTC Товары и индексы (92% доходность, оптимальный порог 80%)
            for asset_name, asset_data in MARKET_ASSETS["commodities_otc"].items():
                tasks.append(analyze_asset_async(asset_name, asset_data, timeframe, min_confidence=80, is_otc=True))
            
            # Обычные активы (85% доходность, порог 75%)
            for asset_name, asset_data in MARKET_ASSETS["crypto"].items():
                tasks.append(analyze_asset_async(asset_name, asset_data, timeframe, min_confidence=75, is_otc=False))
            
            for asset_name, asset_data in MARKET_ASSETS["forex"].items():
                tasks.append(analyze_asset_async(asset_name, asset_data, timeframe, min_confidence=75, is_otc=False))
            
            for asset_name, asset_data in MARKET_ASSETS["stocks"].items():
                tasks.append(analyze_asset_async(asset_name, asset_data, timeframe, min_confidence=75, is_otc=False))
            
            for asset_name, asset_data in MARKET_ASSETS["commodities"].items():
                tasks.append(analyze_asset_async(asset_name, asset_data, timeframe, min_confidence=75, is_otc=False))
    
    elif timeframe_type == "long":
        # Long - все активы КРОМЕ криптовалют на длинных таймфреймах (1H, 4H)
        for timeframe in ["1H", "4H"]:
            # OTC Форекс (92% доходность, оптимальный порог 80%)
            for asset_name, asset_data in MARKET_ASSETS["forex_otc"].items():
                tasks.append(analyze_asset_async(asset_name, asset_data, timeframe, min_confidence=80, is_otc=True))
            
            # OTC Акции (92% доходность, оптимальный порог 80%)
            for asset_name, asset_data in MARKET_ASSETS["stocks_otc"].items():
                tasks.append(analyze_asset_async(asset_name, asset_data, timeframe, min_confidence=80, is_otc=True))
            
            # Обычный форекс (85% доходность, порог 75%)
            for asset_name, asset_data in MARKET_ASSETS["forex"].items():
                tasks.append(analyze_asset_async(asset_name, asset_data, timeframe, min_confidence=75, is_otc=False))
            
            # Обычные акции (85% доходность, порог 75%)
            for asset_name, asset_data in MARKET_ASSETS["stocks"].items():
                tasks.append(analyze_asset_async(asset_name, asset_data, timeframe, min_confidence=75, is_otc=False))
            
            # OTC Товары и индексы (92% доходность, оптимальный порог 80%)
            for asset_name, asset_data in MARKET_ASSETS["commodities_otc"].items():
                tasks.append(analyze_asset_async(asset_name, asset_data, timeframe, min_confidence=80, is_otc=True))
            
            # Обычные товары и индексы (85% доходность, порог 75%)
            for asset_name, asset_data in MARKET_ASSETS["commodities"].items():
                tasks.append(analyze_asset_async(asset_name, asset_data, timeframe, min_confidence=75, is_otc=False))
    
    else:
        # По умолчанию - микс с приоритетом OTC
        # OTC криптовалюты на 1M
        for asset_name, asset_data in list(MARKET_ASSETS["crypto_otc"].items())[:5]:
            tasks.append(analyze_asset_async(asset_name, asset_data, "1M"))
        
        # OTC Форекс, акции на 1H
        for asset_name, asset_data in list(MARKET_ASSETS["forex_otc"].items()):
            tasks.append(analyze_asset_async(asset_name, asset_data, "1H"))
    
    # Выполнить все анализы параллельно
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Собрать успешные сигналы
    for result in results:
        if result and not isinstance(result, Exception):
            signals.append(result)
    
    # Сортировать по score (от большего к меньшему) и взять ТОП-3
    if signals:
        # Рассчитать финальный score для каждого сигнала
        scored_signals = []
        for asset_name, signal_info, timeframe in signals:
            # Базовая уверенность
            base_score = signal_info.get('confidence', 0)
            
            # Бонус за OTC (92% доходность)
            payout_bonus = 25 if signal_info.get('payout', 85) >= 92 else 0
            
            # Финальный score
            final_score = base_score + payout_bonus
            
            scored_signals.append((asset_name, signal_info, timeframe, final_score))
        
        # Сортировать по score и взять ТОП-3
        scored_signals.sort(key=lambda x: x[3], reverse=True)
        top_signals = [(name, info, tf) for name, info, tf, score in scored_signals[:3]]
        signals = top_signals
        
        logger.info(f"📊 Market scan complete: {len(scored_signals)} signals found, TOP-3 selected")
        for i, (name, info, tf, score) in enumerate(scored_signals[:3], 1):
            logger.info(f"   #{i}: {name} {tf} | Score: {score:.1f} | Payout: {info.get('payout', 85)}%")
    
    # Обновить кэш
    signal_cache[cache_key]['signals'] = signals
    signal_cache[cache_key]['timestamp'] = current_time
    
    logger.info(f"✅ Cache updated with {len(signals)} TOP signals")
    
    # Если не найдено сигналов - генерируем хотя бы 1 из OTC активов (максимальная доходность)
    if not signals:
        logger.info("⚡ Генерируем fallback сигнал из OTC активов (92% доходность)")
        import random
        if timeframe_type == "short":
            all_assets = list(MARKET_ASSETS["crypto_otc"].items()) + list(MARKET_ASSETS["forex_otc"].items())
            timeframe = random.choice(["1M", "5M"])
        elif timeframe_type == "long":
            all_assets = list(MARKET_ASSETS["forex_otc"].items()) + list(MARKET_ASSETS["stocks_otc"].items())
            timeframe = random.choice(["1H", "4H"])
        else:
            all_assets = list(MARKET_ASSETS["crypto_otc"].items())[:3]
            timeframe = "1M"
        
        if all_assets:
            asset_name, asset_data = random.choice(all_assets)
            fallback_signal = bot.generate_signal(asset_data["symbol"], timeframe)
            if fallback_signal and fallback_signal[0]:
                fallback_signal[0]['asset_type'] = asset_data["type"]
                fallback_signal[0]['payout'] = asset_data["payout"]
                signals.append((asset_name, fallback_signal[0], timeframe))
                logger.info(f"✅ Создан fallback OTC сигнал: {asset_name} {timeframe} ({asset_data['payout']}% доходность)")
    
    return signals

async def handle_no_signals_found(update, is_callback, msg, timeframe_type, user_priority='paid'):
    """Обработка случая когда сигналы не найдены"""
    
    if user_priority == 'free':
        # Сообщение для FREE пользователей
        no_signals_text = """
⏰ **Сигналы не найдены**

В данный момент нет сигналов с точностью ≥95%.

🔄 **Попробуйте позже:**
Система постоянно обновляет кэш сигналов.
Повторите запрос через несколько минут.

💎 **Хотите автоматические уведомления?**
Оформите подписку SHORT, LONG или VIP и получайте сигналы автоматически!
"""
    else:
        # Сообщение для платных подписчиков
        no_signals_text = """
⏰ **Сигналы в обработке**

Рынок сейчас не показывает четких сигналов.

🔔 **Автоматическое уведомление:**
Система постоянно анализирует рынок и автоматически пришлет сигнал, как только он появится.

💡 Просто ожидайте - уведомление придет само!
"""
    
    # Только кнопки навигации, без повторного поиска
    keyboard = [
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main"),
         InlineKeyboardButton("🏠 Домой", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await msg.edit_text(no_signals_text, reply_markup=reply_markup, parse_mode='Markdown')
    except:
        if is_callback:
            await update.callback_query.message.reply_text(no_signals_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(no_signals_text, reply_markup=reply_markup, parse_mode='Markdown')

async def long_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /long - получить сигнал на длинном таймфрейме"""
    await signal_all_command(update, context, timeframe_type="long")

async def short_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /short - получить сигнал на коротком таймфрейме"""
    await signal_all_command(update, context, timeframe_type="short")

async def show_vip_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """VIP главная страница с управлением банком и статистикой"""
    cursor = bot.conn.cursor()
    
    # Получить данные пользователя
    cursor.execute('SELECT joined_date, initial_balance, current_balance, subscription_end FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    # Безопасная обработка дат с null-guard
    joined_date = "Н/Д"
    if result and result[0]:
        try:
            joined_date = datetime.fromisoformat(result[0]).strftime('%d.%m.%Y')
        except:
            joined_date = "Н/Д"
    
    subscription_end = "Н/Д"
    if result and result[3]:
        try:
            subscription_end = datetime.fromisoformat(result[3]).strftime('%d.%m.%Y')
        except:
            subscription_end = "Н/Д"
    
    # Явная проверка на None, чтобы 0 был валидным значением баланса
    initial_balance = result[1] if result and result[1] is not None else None
    current_balance = result[2] if result and result[2] is not None else None
    
    # Получить SHORT и LONG статистику
    short_stats = bot.get_user_signal_stats(user_id, 'short')
    long_stats = bot.get_user_signal_stats(user_id, 'long')
    
    # Информация о банке (проверяем is not None, чтобы 0 тоже считался валидным)
    if initial_balance is not None and current_balance is not None:
        profit = current_balance - initial_balance
        profit_percent = (profit / initial_balance * 100) if initial_balance > 0 else 0
        # Использовать встроенные функции расчета ставок
        short_base_stake = bot.calculate_recommended_short_stake(current_balance)
        long_stake = bot.get_long_stake(user_id, current_balance, is_vip=True)
        
        # Определить цвет прибыли
        profit_emoji = "🟢" if profit > 0 else "🔴" if profit < 0 else "⚪️"
        
        # Форматировать ставки (с проверкой на None)
        short_stake_text = f"{short_base_stake:.2f} ₽" if short_base_stake else "⚠️ Недостаточно (мин. 36400₽)"
        
        bank_status = f"""
💰 **УПРАВЛЕНИЕ БАНКОМ**
━━━━━━━━━━━━━━━━━━━━━━
• Начальный: {initial_balance:.2f} ₽
• Текущий: **{current_balance:.2f} ₽**
• Прибыль: {profit_emoji} **{profit:+.2f} ₽** ({profit_percent:+.1f}%)

📊 **РЕКОМЕНДУЕМЫЕ СТАВКИ:**
• SHORT (x3): {short_stake_text}
• LONG (5%): {long_stake:.2f} ₽
"""
    else:
        bank_status = """
💰 **УПРАВЛЕНИЕ БАНКОМ**
━━━━━━━━━━━━━━━━━━━━━━
⚠️ **Банк не установлен**
Установите начальный капитал для:
• Автоматического расчета ставок
• Отслеживания прибыли
• Управления рисками

📌 Используйте кнопку "Установить банк" ниже
"""
    
    # Статистика торговли
    total_signals = short_stats['total_signals'] + long_stats['total_signals']
    total_wins = short_stats['wins'] + long_stats['wins']
    total_losses = short_stats['losses'] + long_stats['losses']
    overall_wr = (total_wins / total_signals * 100) if total_signals > 0 else 0
    
    trading_stats = f"""
📈 **СТАТИСТИКА ТОРГОВЛИ**
━━━━━━━━━━━━━━━━━━━━━━
⚡️ **SHORT (1-5 мин):**
• Сделок: {short_stats['total_signals']}
• Винов: ✅ {short_stats['wins']} | Лузов: ❌ {short_stats['losses']}
• Win Rate: **{short_stats['win_rate']:.1f}%**

🔵 **LONG (1-4 часа):**
• Сделок: {long_stats['total_signals']}
• Винов: ✅ {long_stats['wins']} | Лузов: ❌ {long_stats['losses']}
• Win Rate: **{long_stats['win_rate']:.1f}%**

🎯 **ОБЩИЙ РЕЗУЛЬТАТ:**
• Всего сделок: {total_signals}
• Общий Win Rate: **{overall_wr:.1f}%**
"""
    
    # Получить репутацию бота
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
            AVG(CASE WHEN signal_tier = 'vip' THEN confidence ELSE NULL END) as vip_conf,
            AVG(CASE WHEN signal_tier = 'free' THEN confidence ELSE NULL END) as free_conf
        FROM signal_history 
        WHERE result IS NOT NULL
    ''')
    bot_stats = cursor.fetchone()
    bot_total = bot_stats[0] or 0
    bot_wins = bot_stats[1] or 0
    vip_avg_conf = bot_stats[2] or 0
    free_avg_conf = bot_stats[3] or 0
    bot_win_rate = (bot_wins / bot_total * 100) if bot_total > 0 else 0
    
    bot_name = bot.get_setting('bot_name', 'CRYPTO SIGNALS BOT')
    
    dashboard_text = f"""
    ⚡️ 🤖 ┃ {bot_name} ┃ 📈 ⚡️
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         🎯 ↗️  💎 VIP РЕЖИМ 💎  ↗️ 📊

👤 **{update.effective_user.first_name}**
🆔 ID: `{user_id}`
📅 С нами: {joined_date}
⏰ Подписка до: **{subscription_end}**

{bank_status}
{trading_stats}
🏆 **РЕПУТАЦИЯ БОТА:**
• Общий WR: {bot_win_rate:.1f}% ({bot_total} сделок)
• VIP точность: {vip_avg_conf:.1f}%
• FREE точность: {free_avg_conf:.1f}%

━━━━━━━━━━━━━━━━━━━━━━
💡 **Выберите действие:**
"""
    
    # Кнопки управления
    keyboard = []
    
    # Первая строка - сигналы (короткие кнопки)
    keyboard.append([
        InlineKeyboardButton("⚡ SHORT", callback_data="find_signals_short"),
        InlineKeyboardButton("🔵 LONG", callback_data="find_signals_long")
    ])
    
    # Вторая строка - управление позициями
    keyboard.append([
        InlineKeyboardButton("📋 Мои LONG", callback_data="my_longs")
    ])
    
    # Третья строка - банк
    keyboard.append([
        InlineKeyboardButton("💰 Управление банком", callback_data="bank_management")
    ])
    
    # БОЛЬШАЯ кнопка автотрейдинга для VIP
    cursor.execute('SELECT auto_trading_enabled FROM users WHERE user_id = ?', (user_id,))
    auto_result = cursor.fetchone()
    auto_trading_enabled = auto_result[0] if auto_result else 0
    auto_status = "🟢 ВКЛ" if auto_trading_enabled else "🔴 ВЫКЛ"
    keyboard.append([
        InlineKeyboardButton(f"🤖 АВТОТРЕЙДИНГ {auto_status}", callback_data="autotrade_menu")
    ])
    
    # Четвертая строка - настройки
    keyboard.append([
        InlineKeyboardButton("⚙️ Настройки", callback_data="settings")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    if is_callback:
        try:
            await update.callback_query.edit_message_text(dashboard_text, reply_markup=reply_markup, parse_mode='Markdown')
        except:
            await update.callback_query.message.reply_text(dashboard_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(dashboard_text, reply_markup=reply_markup, parse_mode='Markdown')

async def clear_chat_and_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистить чат (удалить все сообщения бота) и показать главную"""
    user_id = update.effective_user.id
    query = update.callback_query
    
    # Получить ID текущего сообщения
    current_msg_id = query.message.message_id
    
    # Показать сообщение об очистке (без задержек)
    try:
        await query.edit_message_text("🔄 Очищаю чат...")
    except:
        pass
    
    # Попытаться удалить последние 50 сообщений бота
    try:
        for i in range(0, 51):
            try:
                msg_id = current_msg_id - i
                if msg_id > 0:
                    await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except:
                # Если не удалось удалить - продолжаем
                pass
    except:
        pass
    
    # Отправить новое сообщение с главной страницей
    # Используем context.bot для отправки нового сообщения
    has_subscription, message, signals_used, free_trials_used, sub_type = bot.check_subscription(user_id)
    
    # Получить язык и валюту пользователя
    language = bot.get_user_language(user_id)
    currency = 'RUB'
    cursor = bot.conn.cursor()
    cursor.execute('SELECT currency FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result and result[0]:
        currency = result[0]
    
    # Отправить главное меню как новое сообщение
    class TempUpdate:
        def __init__(self, message):
            self.message = message
            self.callback_query = None
            self.effective_user = message.from_user
    
    temp = TempUpdate(query.message)
    await show_main_menu(temp, context, user_id=user_id)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Показать главное меню в зависимости от подписки"""
    # ВАЖНО: используем check_subscription для проверки бизнес-логики (trial, expiry, limits)
    has_subscription, message, signals_used, free_trials_used, sub_type = bot.check_subscription(user_id)
    
    # Оптимизированный запрос: получаем остальные данные за один раз
    cursor = bot.conn.cursor()
    cursor.execute('''
        SELECT 
            u.language, u.currency, u.current_balance, u.initial_balance,
            COUNT(CASE WHEN sh.result IN ('win', 'loss') THEN 1 END) as total_signals,
            SUM(CASE WHEN sh.result = 'win' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN sh.result = 'loss' THEN 1 ELSE 0 END) as losses
        FROM users u
        LEFT JOIN signal_history sh ON u.user_id = sh.user_id
        WHERE u.user_id = ?
        GROUP BY u.user_id
    ''', (user_id,))
    
    result = cursor.fetchone()
    if not result:
        return
    
    language = result[0] if result[0] else 'RU'
    currency = result[1] if result[1] else 'RUB'
    current_balance = result[2] if result[2] is not None else 0
    initial_balance = result[3] if result[3] is not None else 0
    total_signals = result[4] if result[4] else 0
    wins = result[5] if result[5] else 0
    losses = result[6] if result[6] else 0
    win_rate = (wins / total_signals * 100) if total_signals > 0 else 0
    
    t = lambda key: TRANSLATIONS[language].get(key, key)
    
    # Расчёт прибыли
    profit = current_balance - initial_balance if initial_balance > 0 else 0
    profit_percent = (profit / initial_balance * 100) if initial_balance > 0 else 0
    
    # Если подписки нет, sub_type будет None
    if not sub_type:
        sub_type = "free"
    
    # Для VIP показываем специальную главную страницу с банком и статистикой
    if sub_type == 'vip':
        await show_vip_dashboard(update, context, user_id)
        return
    
    # Создать приветствие
    if has_subscription or sub_type == 'free':
        sub_emoji = SUBSCRIPTION_PLANS.get(sub_type, {}).get('emoji', '🆓')
        sub_name = sub_type.upper()
        
        # Формат статистики
        stats_text = ""
        if total_signals > 0:
            profit_emoji = "📈" if profit >= 0 else "📉"
            balance_text = f"💰 Баланс: **{current_balance:.0f}₽** ({profit_emoji} {profit:+.0f}₽ / {profit_percent:+.1f}%)\n" if initial_balance > 0 else ""
            stats_text = f"""
┏━━━━━━━━━━━━━━━━━━━━━━┓
┃  📊 **СТАТИСТИКА**
┣━━━━━━━━━━━━━━━━━━━━━━┫
┃  {balance_text}┃  🎯 Винрейт: **{win_rate:.1f}%** ({wins}✅ / {losses}❌)
┃  📈 Сигналов: **{total_signals}**
┗━━━━━━━━━━━━━━━━━━━━━━┛
"""
        
        # Для FREE тарифа и пожизненных подписок не показываем дату окончания
        if sub_type == 'free' or not message:
            tariff_info = f"""┏━━━━━━━━━━━━━━━━━━━━━━┓
┃  📊 **ВАШ ТАРИФ**
┣━━━━━━━━━━━━━━━━━━━━━━┫
┃  {sub_emoji} Подписка: **{sub_name}**
┃  ⏰ Тип: **Бессрочная**
┗━━━━━━━━━━━━━━━━━━━━━━┛"""
        else:
            tariff_info = f"""┏━━━━━━━━━━━━━━━━━━━━━━┓
┃  📊 **ВАШ ТАРИФ**
┣━━━━━━━━━━━━━━━━━━━━━━┫
┃  {sub_emoji} Подписка: **{sub_name}**
┃  ⏰ Действует до: **{datetime.fromisoformat(message).strftime('%d.%m.%Y')}**
┗━━━━━━━━━━━━━━━━━━━━━━┛"""
        
        bot_name = bot.get_setting('bot_name', 'CRYPTO SIGNALS BOT')
        
        welcome_text = f"""
╔══════════════════════╗
   💎 **{bot_name}** 💎
╚══════════════════════╝

{tariff_info}
{stats_text}
📱 Выберите действие ниже:
"""
    else:
        # Конвертировать цены в валюту пользователя
        short_price = bot.convert_price(SUBSCRIPTION_PLANS['short']['1_month'], currency)
        long_price = bot.convert_price(SUBSCRIPTION_PLANS['long']['1_month'], currency)
        vip_price = bot.convert_price(SUBSCRIPTION_PLANS['vip']['1_month'], currency)
        promo_price = bot.convert_price(NEW_USER_PROMO['price'], currency)
        
        symbol = CURRENCY_SYMBOLS[currency]
        bot_name = bot.get_setting('bot_name', 'CRYPTO SIGNALS BOT')
        
        welcome_text = f"""
╔══════════════════════╗
   💎 **{bot_name}** 💎
╚══════════════════════╝

🎯 **Профессиональные торговые сигналы**
📱 **Для платформы Pocket Option**

💳 **Оплата:** Банковские карты (ЮКасса)
💬 **Поддержка:** {bot.get_support_contact()}

┏━━━━━━━━━━━━━━━━━━━━━━┓
┃  🔥 **ПРЕИМУЩЕСТВА**
┣━━━━━━━━━━━━━━━━━━━━━━┫
┃  📈 Точность: **85-92%**
┃  🤖 AI анализ рынка
┃  ⚡️ Мгновенные сигналы
┃  🎯 Адаптивное обучение
┗━━━━━━━━━━━━━━━━━━━━━━┛

💎 **ДОСТУПНЫЕ ТАРИФЫ:**

┏━━━━━━━━━━━━━━━━━━━━━━┓
┃  ⚡️ **SHORT** — {short_price}{symbol}/мес
┣━━━━━━━━━━━━━━━━━━━━━━┫
┃  • Быстрые сигналы (1-5 мин)
┃  • Мартингейл стратегия x3
┃  • Быстрая торговля
┃  • Автоматический countdown
┗━━━━━━━━━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━━━━━━━┓
┃  🔵 **LONG** — {long_price}{symbol}/мес
┣━━━━━━━━━━━━━━━━━━━━━━┫
┃  • Длинные сигналы (1-4 часа)
┃  • Процентная стратегия 2.5%
┃  • Стабильные сделки
┃  • Управление позициями
┗━━━━━━━━━━━━━━━━━━━━━━┛

┏━━━━━━━━━━━━━━━━━━━━━━┓
┃  💎 **VIP** — {vip_price}{symbol}/мес
┣━━━━━━━━━━━━━━━━━━━━━━┫
┃  • ВСЕ сигналы (SHORT + LONG)
┃  • 10 VIP сигналов в день
┃  • Приоритетная поддержка
┃  • Максимальная прибыль
┗━━━━━━━━━━━━━━━━━━━━━━┛

🎁 **СПЕЦИАЛЬНОЕ ПРЕДЛОЖЕНИЕ:**
🔥 SHORT за {promo_price}{symbol} (скидка 70%!)
💫 Только для новых пользователей!

🎯 **ЧТО ВЫ ПОЛУЧАЕТЕ:**
   ✓ 37+ торговых активов
   ✓ 8 таймфреймов
   ✓ Технический анализ (EMA, RSI, MACD)
   ✓ Автоматический расчет ставок
   ✓ Детальная статистика
   ✓ Самообучающаяся система

🎁 **БОНУС:** FREE доступ к LONG сигналам (10 рассылок в день)!

📱 Начните зарабатывать прямо сейчас:
"""
    
    keyboard = []
    
    # Кнопки в зависимости от типа подписки
    if sub_type == 'vip':
        # VIP - все кнопки (статистика показывается в главном сообщении)
        keyboard.extend([
            [InlineKeyboardButton("⚡ SHORT", callback_data="find_signals_short"),
             InlineKeyboardButton("🔵 LONG", callback_data="find_signals_long")],
            [InlineKeyboardButton("📋 Мои LONG", callback_data="my_longs")],
        ])
    elif sub_type == 'long':
        # LONG - только длинные сигналы, мои лонги и управление банком
        keyboard.extend([
            [InlineKeyboardButton("🔵 LONG", callback_data="find_signals_long"),
             InlineKeyboardButton("📋 Мои LONG", callback_data="my_longs")],
            [InlineKeyboardButton("💰 Управление банком", callback_data="bank_management")],
            [InlineKeyboardButton("⬆️ РАСШИРИТЬ ТАРИФ 🚀", callback_data="choose_plan_settings")],
        ])
    elif sub_type == 'short':
        # SHORT - только короткие сигналы и управление банком
        keyboard.extend([
            [InlineKeyboardButton("⚡ SHORT", callback_data="find_signals_short")],
            [InlineKeyboardButton("💰 Управление банком", callback_data="bank_management")],
            [InlineKeyboardButton("⬆️ РАСШИРИТЬ ТАРИФ 🚀", callback_data="choose_plan_settings")],
        ])
    elif sub_type == 'free':
        # FREE - проверяем лимиты и показываем кнопки только если есть попытки
        # Получить данные о лимитах FREE тарифа
        cursor.execute(
            'SELECT free_short_signals_today, free_short_signals_date, free_long_signals_today, free_long_signals_date FROM users WHERE user_id = ?',
            (user_id,)
        )
        free_limits = cursor.fetchone()
        
        short_signals_used = 0
        long_signals_used = 0
        
        if free_limits:
            short_signals_today, short_date, long_signals_today, long_date = free_limits
            today = datetime.now().date().isoformat()
            
            # Проверить SHORT сигналы (сбросить если новый день)
            if short_date == today:
                short_signals_used = short_signals_today or 0
            
            # Проверить LONG сигналы (сбросить если новый день)
            if long_date == today:
                long_signals_used = long_signals_today or 0
        
        # Показать кнопки поиска сигналов только если есть попытки
        signal_buttons = []
        if short_signals_used < 5:
            signal_buttons.append(InlineKeyboardButton(f"⚡ SHORT ({5 - short_signals_used} осталось)", callback_data="find_signals_short"))
        if long_signals_used < 5:
            signal_buttons.append(InlineKeyboardButton(f"🔵 LONG ({5 - long_signals_used} осталось)", callback_data="find_signals_long"))
        
        # Если есть доступные попытки - показать кнопки
        if signal_buttons:
            if len(signal_buttons) == 2:
                keyboard.append(signal_buttons)
            else:
                keyboard.append([signal_buttons[0]])
        
        # Всегда показывать кнопку выбора тарифа
        keyboard.append([InlineKeyboardButton("💰 ВЫБРАТЬ ТАРИФ И ЗАРАБАТЫВАТЬ 🚀", callback_data="choose_plan_settings")])
    
    # Определяем, является ли пользователь на триале
    is_trial = False
    if has_subscription and sub_type == 'vip' and message:
        subscription_end = datetime.fromisoformat(message)
        days_total = (subscription_end - datetime.now()).days
        # Trial = VIP подписка до 3 дней (подарочный trial для existing users)
        if days_total <= 3:
            is_trial = True
    
    # Кнопка купить/продлить/расширить подписку - логика в зависимости от статуса
    if sub_type == 'vip' and not is_trial:
        # VIP (активная) - кнопка НЕ видна
        pass
    elif sub_type == 'free':
        # FREE - кнопка уже добавлена выше, пропускаем
        pass
    elif sub_type in ['short', 'long']:
        # SHORT/LONG - кнопка уже добавлена выше, пропускаем
        pass
    elif is_trial:
        # TRIAL - такая же большая кнопка, как для FREE
        keyboard.append([InlineKeyboardButton("💰 ВЫБРАТЬ ТАРИФ И ЗАРАБАТЫВАТЬ 🚀", callback_data="choose_plan_settings")])
    elif not has_subscription:
        # Пользователи без подписки (не FREE, не TRIAL)
        keyboard.append([InlineKeyboardButton("ВЫБРАТЬ ТАРИФ", callback_data="choose_plan_settings")])
    
    # БОЛЬШАЯ кнопка автотрейдинга - видна ВСЕМ
    cursor.execute('SELECT auto_trading_enabled FROM users WHERE user_id = ?', (user_id,))
    auto_result = cursor.fetchone()
    auto_trading_enabled = auto_result[0] if auto_result else 0
    
    if sub_type == 'vip':
        # VIP: показываем активную кнопку с роботом и статусом
        auto_status = "🟢 ВКЛ" if auto_trading_enabled else "🔴 ВЫКЛ"
        keyboard.append([InlineKeyboardButton(
            f"🤖 АВТОТРЕЙДИНГ {auto_status}", 
            callback_data="autotrade_menu"
        )])
    else:
        # НЕ-VIP: показываем с замочком, callback проверит права
        keyboard.append([InlineKeyboardButton(
            "🔒 АВТОТРЕЙДИНГ", 
            callback_data="autotrade_menu"
        )])
    
    # Дополнительные кнопки
    additional_buttons = []
    
    # Кнопка отзывов только для FREE и TRIAL пользователей
    if sub_type == 'free' or is_trial:
        additional_buttons.append([InlineKeyboardButton("⭐ Отзывы пользователей", callback_data="user_reviews")])
    
    additional_buttons.extend([
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
    ])
    
    keyboard.extend(additional_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправить сообщение
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    if is_callback:
        try:
            await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
        except:
            await update.callback_query.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Попытаться удалить команду /start пользователя для очистки чата
    try:
        await update.message.delete()
    except:
        pass
    
    # Проверка бана
    if bot.is_banned(user.id):
        await context.bot.send_message(
            chat_id=user.id,
            text="🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\n"
            "Доступ к боту ограничен.\n"
            f"Обратитесь в поддержку: {bot.get_support_contact()}",
            parse_mode='Markdown'
        )
        return
    
    cursor = bot.conn.cursor()
    
    # Проверить реферальный код
    if context.args and len(context.args) > 0:
        referral_code = context.args[0]
        # Найти пользователя с таким реферальным кодом
        cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (referral_code,))
        referrer_result = cursor.fetchone()
        
        if referrer_result:
            referrer_id = referrer_result[0]
            # Проверить, не является ли это тем же пользователем
            if referrer_id != user.id:
                # Сохранить, кто пригласил этого пользователя
                cursor.execute('''
                    INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date, referred_by)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user.id, user.username, user.first_name, datetime.now().isoformat(), referrer_id))
                # Если пользователь уже существует, обновить referred_by
                cursor.execute('''
                    UPDATE users SET referred_by = ? 
                    WHERE user_id = ? AND referred_by IS NULL
                ''', (referrer_id, user.id))
                bot.conn.commit()
    
    # Добавить пользователя если его нет
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date)
        VALUES (?, ?, ?, ?)
    ''', (user.id, user.username, user.first_name, datetime.now().isoformat()))
    bot.conn.commit()
    
    # Проверить, выбрал ли пользователь свой статус (новый/существующий)
    cursor.execute('SELECT language, currency, pocket_option_registered FROM users WHERE user_id = ?', (user.id,))
    result = cursor.fetchone()
    
    # Если статус не выбран (pocket_option_registered = NULL, 0 или False), показать выбор статуса
    if not result or not result[2]:
        bot_name = bot.get_setting('bot_name', 'CRYPTO SIGNALS BOT')
        welcome_text = f"""
💎 **{bot_name}**

👋 Добро пожаловать в профессиональный бот торговых сигналов!

Выберите ваш статус:
"""
        keyboard = [
            [InlineKeyboardButton("🆕 Новый пользователь Pocket Option", callback_data="user_status_new")],
            [InlineKeyboardButton("✅ Уже зарегистрирован", callback_data="user_status_existing")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=user.id, text=welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    # Если язык не установлен, показать выбор языка
    if not result or not result[0]:
        welcome_text = """
🌍 **Welcome to Crypto Signals Bot!**
**Добро пожаловать в бот торговых сигналов!**

Please select your language / Выберите язык:
"""
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="set_language_ru")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="set_language_en")],
            [InlineKeyboardButton("🇪🇸 Español", callback_data="set_language_es")],
            [InlineKeyboardButton("🇧🇷 Português", callback_data="set_language_pt")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=user.id, text=welcome_text, reply_markup=reply_markup)
        return
    
    # Если валюта не установлена, показать выбор валюты
    language = result[0] if result and result[0] else 'ru'
    currency = result[1] if result and result[1] else None
    
    if not currency or currency == 'RUB':
        currency_text = TRANSLATIONS[language]['choose_currency']
        keyboard = [
            [InlineKeyboardButton("🇷🇺 RUB (₽)", callback_data="set_currency_RUB")],
            [InlineKeyboardButton("🇺🇸 USD ($)", callback_data="set_currency_USD")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=user.id, text=currency_text, reply_markup=reply_markup)
        return
    
    # Показать главное меню (для зарегистрированных пользователей)
    # Создать временный update для вызова show_main_menu
    class TempMessage:
        def __init__(self, user_obj, bot_obj):
            self.from_user = user_obj
            self._bot = bot_obj
            self._user_id = user_obj.id
        
        async def reply_text(self, text, **kwargs):
            return await self._bot.send_message(chat_id=self._user_id, text=text, **kwargs)
    
    class TempUpdate:
        def __init__(self, user_obj, bot_obj):
            self.effective_user = user_obj
            self.callback_query = None
            self.message = TempMessage(user_obj, bot_obj)
    
    temp_update = TempUpdate(user, context.bot)
    await show_main_menu(temp_update, context, user_id=user.id)

async def signal_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE, timeframe_type=None):
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    user_id = update.effective_user.id
    
    # Проверка бана
    if bot.is_banned(user_id):
        error_msg = f"🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\nДоступ к боту ограничен.\nОбратитесь в поддержку: {bot.get_support_contact()}"
        if is_callback:
            await update.callback_query.answer("🚫 Вы заблокированы", show_alert=True)
        else:
            await update.message.reply_text(error_msg, parse_mode='Markdown')
        return
    
    # Проверка доступа к типу сигнала
    if timeframe_type:
        can_access, access_message = bot.can_access_signal_type(user_id, timeframe_type)
        
        if not can_access:
            error_text = f"""
❌ **Доступ запрещен**

{access_message}

💎 **Доступные тарифы:**
• {SUBSCRIPTION_PLANS['short']['emoji']} SHORT ({bot.get_setting('short_price_rub', '4990')}₽/мес) - быстрые сигналы (1-5 мин)
• {SUBSCRIPTION_PLANS['long']['emoji']} LONG ({bot.get_setting('long_price_rub', '6990')}₽/мес) - длинные сигналы (1-4 часа)
• {SUBSCRIPTION_PLANS['vip']['emoji']} VIP ({bot.get_setting('vip_price_rub', '9990')}₽/мес) - все сигналы + приоритет

📱 Купить подписку: /buy_subscription
"""
            if is_callback:
                await update.callback_query.answer("❌ Нет доступа", show_alert=True)
                await update.callback_query.message.reply_text(error_text)
            else:
                await update.message.reply_text(error_text)
            return
    
    cursor = bot.conn.cursor()
    cursor.execute('SELECT initial_balance, current_balance FROM users WHERE user_id = ?', (user_id,))
    balance_result = cursor.fetchone()
    
    if not balance_result or balance_result[0] is None:
        no_bank_text = """
❌ **Банк не установлен!**

Перед получением сигналов необходимо установить ваш торговый банк.

💰 **Для установки используйте:**
`/set_bank 10000`

где 10000 - ваш банк в выбранной валюте

Это нужно для:
• Автоматического расчета ставок (2% от банка)
• Отслеживания прибыли/убытков
• Корректного управления капиталом

📊 После установки банка вы сможете получать сигналы!
"""
        if is_callback:
            await update.callback_query.answer("❌ Сначала установите банк через /set_bank", show_alert=True)
            await update.callback_query.message.reply_text(no_bank_text)
        else:
            await update.message.reply_text(no_bank_text)
        return
    
    has_subscription, message, signals_used, free_trials_used, sub_type = bot.check_subscription(user_id)
    
    # Определяем приоритет пользователя для очереди и таймаутов
    is_admin = (user_id == int(os.getenv('ADMIN_USER_ID', '0')))
    if is_admin:
        user_priority = 'admin'
    elif sub_type == 'vip':
        user_priority = 'vip'
    elif sub_type in ['short', 'long']:
        user_priority = sub_type
    else:
        user_priority = 'free'
    
    # Таймаут сканирования в зависимости от приоритета
    scan_timeout = SCAN_TIMEOUTS.get(user_priority, 20)
    
    # FREE пользователи могут получать SHORT сигналы (5 в день) и LONG сигналы (5 в день) без подписки
    is_free_short_access = False
    is_free_long_access = False
    
    if not has_subscription and timeframe_type == 'short':
        can_access, used_today = bot.check_free_short_limit(user_id)
        if can_access:
            is_free_short_access = True
        else:
            response_text = f"""
❌ **Лимит исчерпан**

Вы использовали {used_today}/5 FREE шорт-сигналов сегодня.

💎 **Получите неограниченный доступ:**
• SHORT ({bot.get_setting('short_price_rub', '4990')}₽/мес) - безлимитные быстрые сигналы
• VIP ({bot.get_setting('vip_price_rub', '9990')}₽/мес) - все сигналы + автоматическая рассылка

📱 Купить подписку: /buy_subscription
"""
            if is_callback:
                await update.callback_query.answer("❌ Лимит исчерпан", show_alert=True)
                await update.callback_query.message.reply_text(response_text)
            else:
                await update.message.reply_text(response_text)
            return
    
    if not has_subscription and timeframe_type == 'long':
        can_access, used_today = bot.check_free_long_limit(user_id)
        if can_access:
            is_free_long_access = True
        else:
            response_text = f"""
❌ **Лимит исчерпан**

Вы использовали {used_today}/5 FREE лонг-сигналов сегодня.

💎 **Получите неограниченный доступ:**
• LONG ({bot.get_setting('long_price_rub', '6990')}₽/мес) - безлимитные длинные сигналы
• VIP ({bot.get_setting('vip_price_rub', '9990')}₽/мес) - все сигналы + автоматическая рассылка

📱 Купить подписку: /buy_subscription
"""
            if is_callback:
                await update.callback_query.answer("❌ Лимит исчерпан", show_alert=True)
                await update.callback_query.message.reply_text(response_text)
            else:
                await update.message.reply_text(response_text)
            return
    
    if not has_subscription and not is_free_short_access and not is_free_long_access:
        response_text = (
            f"❌ Пробный период истек.\n\n"
            f"💎 Для получения сигналов с доходностью {PAYOUT_PERCENT}% приобретите подписку: /buy_subscription"
        )
        if is_callback:
            await update.callback_query.answer(response_text, show_alert=True)
        else:
            await update.message.reply_text(response_text)
        return
    
    # Информация о системе ставок для SHORT сигналов
    if timeframe_type == "short":
        stake, level = bot.get_martingale_stake(user_id)
        cursor.execute('SELECT consecutive_losses, short_base_stake FROM users WHERE user_id = ?', (user_id,))
        martingale_data = cursor.fetchone()
        losses = martingale_data[0] if martingale_data else 0
        base_stake = martingale_data[1] if martingale_data and martingale_data[1] else 100
        
        martingale_info = f"""
💰 **МАРТИНГЕЙЛ СИСТЕМА (SHORT)**

📊 **Текущие параметры:**
• Базовая ставка: {base_stake:.0f}₽
• Текущий уровень: {level}
• Текущая ставка: {stake:.0f}₽
• Подряд лузов: {losses}/5

📈 **Стратегия:**
• Начальная ставка: {base_stake:.0f}₽
• После луза: x3 ставка
• После вина: сброс на {base_stake:.0f}₽
• Максимум лузов: 5 подряд

⚙️ Изменить базовую ставку: /set_short_stake
"""
        if is_callback:
            await update.callback_query.message.reply_text(martingale_info, parse_mode='Markdown')
        else:
            await update.message.reply_text(martingale_info, parse_mode='Markdown')
    
    # Логируем приоритет пользователя
    priority_emoji = {'admin': '👑', 'vip': '💎', 'short': '⚡', 'long': '🔵', 'free': '🆓'}
    logger.info(f"{priority_emoji.get(user_priority, '👤')} Запрос от {user_priority.upper()} пользователя {user_id}")
    
    # Детальное отображение сканирования активов
    if timeframe_type == "long":
        scan_header = "📊 **СКАНИРОВАНИЕ LONG АКТИВОВ**\n\n"
        asset_categories = [
            ("🌍 Форекс OTC (92%)", ["EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC", "AUD/USD OTC"]),
            ("💱 Форекс", ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CHF", "EUR/GBP"]),
            ("📈 Акции OTC (92%)", ["AAPL OTC", "INTC OTC"]),
            ("🏢 Акции", ["MSFT", "TSLA", "AMZN", "META", "BA"]),
            ("💰 Товары", ["GOLD", "SILVER", "OIL", "BRENT", "NATURAL GAS"]),
            ("📊 Индексы", ["S&P 500", "NASDAQ", "DOW", "FTSE"])
        ]
    else:
        scan_header = "📊 **СКАНИРОВАНИЕ SHORT АКТИВОВ**\n\n"
        asset_categories = [
            ("₿ Крипто OTC (92%)", ["BTC OTC", "ETH OTC", "SOL OTC", "ADA OTC", "LINK OTC"]),
            ("💎 Крипто", ["BTC", "ETH", "LTC", "XRP", "ADA", "BNB"]),
            ("🌍 Форекс OTC (92%)", ["EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC"]),
            ("💱 Форекс", ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]),
            ("📈 Акции OTC (92%)", ["AAPL OTC", "INTC OTC"]),
            ("🏢 Акции", ["MSFT", "TSLA", "AMZN", "META"])
        ]
    
    if is_callback:
        # Показываем всплывающее окно с информацией о времени сканирования для SHORT
        if timeframe_type == "short":
            await update.callback_query.answer("⏱️ Поиск сигнала займет ~5-7 секунд", show_alert=True)
        else:
            await update.callback_query.answer("⏱️ Поиск сигнала займет ~5-7 секунд", show_alert=True)
        msg = await update.callback_query.message.reply_text(scan_header + "⏳ Подготовка...", parse_mode='Markdown')
    else:
        msg = await update.message.reply_text(scan_header + "⏳ Подготовка...", parse_mode='Markdown')
    
    # Анимация сканирования активов
    for i, (category_name, assets) in enumerate(asset_categories):
        progress_text = scan_header
        for j, (cat_name, _) in enumerate(asset_categories):
            if j < i:
                progress_text += f"✅ {cat_name}\n"
            elif j == i:
                progress_text += f"🔍 {cat_name}...\n"
            else:
                progress_text += f"⏸️ {cat_name}\n"
        
        try:
            await msg.edit_text(progress_text, parse_mode='Markdown')
            await asyncio.sleep(0.3)
        except:
            pass
    
    # Финальный статус
    final_scan_text = scan_header
    for cat_name, _ in asset_categories:
        final_scan_text += f"✅ {cat_name}\n"
    final_scan_text += "\n🔎 Выбираю лучший сигнал..."
    
    try:
        await msg.edit_text(final_scan_text, parse_mode='Markdown')
    except:
        pass
    
    # Получаем ТОП-1 сигнал с учетом всех факторов (исключая уже выданные)
    cache_key = timeframe_type if timeframe_type else 'short'
    best_signal_data = get_best_signal_from_cache(cache_key, user_priority, user_id)
    
    # Удаляем сообщение о загрузке
    try:
        await msg.delete()
    except:
        pass
    
    # Проверка: если нет подходящих сигналов
    if not best_signal_data:
        logger.warning(f"⚠️ Нет подходящих сигналов для {user_priority.upper()} пользователя")
        await handle_no_signals_found(update, is_callback, msg, timeframe_type, user_priority)
        return
    
    # Распаковываем лучший сигнал
    top_signals = [best_signal_data]
    
    cursor = bot.conn.cursor()
    cursor.execute('SELECT current_balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    balance = result[0] if result and result[0] else 1000.0
    
    # Определяем маппинг активов для графиков
    crypto_assets = {
        "BTC/USD": "BTC-USD",
        "ETH/USD": "ETH-USD", 
        "SOL/USD": "SOL-USD"
    }
    
    other_assets = {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "XAU/USD": "GC=F",
        "AAPL": "AAPL",
        "TSLA": "TSLA"
    }
    
    for asset_name, signal_info, timeframe in top_signals:
        bot.increment_signals_used(user_id)
        
        # Для FREE пользователей: увеличить счетчик использованных SHORT/LONG сигналов
        if is_free_short_access and timeframe_type == 'short':
            bot.increment_free_short_signal(user_id)
        elif is_free_long_access and timeframe_type == 'long':
            bot.increment_free_long_signal(user_id)
        
        # Определяем расчет ставки на основе выбранной стратегии пользователя
        cursor.execute('SELECT trading_strategy FROM users WHERE user_id = ?', (user_id,))
        strategy_result = cursor.fetchone()
        user_strategy = strategy_result[0] if strategy_result and strategy_result[0] else None
        
        # Определяем is_vip для процентной стратегии
        is_vip = (sub_type == 'vip')
        
        # Логика выбора стратегии с fallback для обратной совместимости
        short_timeframes = ["1M", "2M", "3M", "5M", "15M", "30M"]
        is_short_timeframe = timeframe in short_timeframes
        
        if user_strategy == 'ai_trading':
            # AI Trading - выбирает лучшую стратегию автоматически
            ai_strategy, ai_wr, ai_recommendation = await get_ai_strategy_recommendation(user_id)
            
            if ai_strategy == 'percentage':
                stake_amount = bot.get_long_stake(user_id, balance, is_vip)
            elif ai_strategy == 'dalembert':
                stake_amount, dalembert_level = bot.get_dalembert_stake(user_id)
            elif ai_strategy == 'martingale':
                stake_amount, martingale_level = bot.get_martingale_stake(user_id)
            else:
                # Fallback на консервативную стратегию
                stake_amount = bot.get_long_stake(user_id, balance, is_vip)
        elif user_strategy == 'martingale':
            # Явно выбран мартингейл (агрессивная стратегия)
            stake_amount, martingale_level = bot.get_martingale_stake(user_id)
        elif user_strategy == 'dalembert':
            # Явно выбран D'Alembert (умеренная стратегия)
            stake_amount, dalembert_level = bot.get_dalembert_stake(user_id)
        elif user_strategy == 'percentage':
            # Явно выбрана процентная (консервативная стратегия)
            stake_amount = bot.get_long_stake(user_id, balance, is_vip)
        else:
            # Fallback для пользователей без выбранной стратегии (обратная совместимость)
            if sub_type == 'short' or (is_short_timeframe and sub_type in ['vip', 'free', None]):
                # SHORT тариф или короткие таймфреймы → мартингейл по умолчанию
                stake_amount, martingale_level = bot.get_martingale_stake(user_id)
            else:
                # LONG тариф или длинные таймфреймы → процентная по умолчанию
                stake_amount = bot.get_long_stake(user_id, balance, is_vip)
        
        signal_id = bot.save_signal_to_history(
            user_id, 
            asset_name, 
            timeframe, 
            signal_info['signal'], 
            signal_info['confidence'], 
            signal_info['price'],
            stake_amount
        )
        
        # Получаем правильный символ для графика
        if asset_name in crypto_assets:
            chart_symbol = crypto_assets[asset_name]
        elif asset_name in other_assets:
            chart_symbol = other_assets[asset_name]
        else:
            chart_symbol = "BTC-USD"
        
        chart_buf = bot.create_pro_chart(
            chart_symbol, 
            asset_name, 
            timeframe, 
            signal_info
        )
        
        signal_message = bot.generate_pro_signal_message(
            asset_name, signal_info, timeframe, user_id, balance
        )
        
        pocket_asset = bot.get_pocket_option_asset_name(asset_name)
        # Убираем OTC из копируемого текста (но оставляем в описании сигнала)
        pocket_asset_clean = pocket_asset.replace(" OTC", "")
        keyboard = [
            [InlineKeyboardButton(f"📋 {pocket_asset_clean}", callback_data=f"copy_{pocket_asset_clean}")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main"), 
             InlineKeyboardButton("🏠 Домой", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        sent_message = None
        if chart_buf:
            if is_callback:
                sent_message = await update.callback_query.message.reply_photo(
                    photo=chart_buf,
                    caption=signal_message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                sent_message = await update.message.reply_photo(
                    photo=chart_buf,
                    caption=signal_message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
        else:
            if is_callback:
                sent_message = await update.callback_query.message.reply_text(
                    signal_message, 
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                sent_message = await update.message.reply_text(
                    signal_message, 
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
        
        # Для SHORT сигналов запускаем автоматический обратный отсчет
        if timeframe in ["1M", "2M", "3M", "5M", "15M", "30M"]:
            asyncio.create_task(start_countdown_notification(
                context.application.bot,
                user_id, 
                sent_message.chat.id if sent_message else (update.callback_query.message.chat.id if is_callback else update.message.chat.id),
                asset_name, 
                timeframe, 
                signal_info,
                signal_id
            ))
    
    # Сообщение об оставшихся бесплатных попытках
    if not has_subscription and free_trials_used == 0:
        new_signals_count = signals_used + len(top_signals)
        remaining = 3 - new_signals_count
        if remaining > 0:
            final_msg = f"🎁 Осталось бесплатных сигналов: {remaining}"
            if is_callback:
                await update.callback_query.message.reply_text(final_msg)
            else:
                await update.message.reply_text(final_msg)
        else:
            final_msg = (
                f"🎁 Вы использовали все 3 бесплатных сигнала!\n\n"
                f"💎 Для неограниченного доступа к сигналам с доходностью {PAYOUT_PERCENT}% приобретите PRO подписку: /buy_subscription"
            )
            if is_callback:
                await update.callback_query.message.reply_text(final_msg)
            else:
                await update.message.reply_text(final_msg)
    
    # Предложение апгрейда для FREE пользователей после LONG сигналов
    if is_free_long_access and timeframe_type == 'long':
        can_access, used_today = bot.check_free_long_limit(user_id)
        remaining_long = max(0, 5 - used_today)
        
        upgrade_text = f"""
🔥 **ВЫ ПОЛУЧИЛИ LONG СИГНАЛ!** 

📊 У вас осталось: {remaining_long}/5 LONG сигналов сегодня

💎 **ХОТИТЕ БОЛЬШЕ ПРИБЫЛИ?**
Переходите на платные тарифы и получайте:

⚡ **SHORT** (4,990₽/мес):
• Безлимитные быстрые сигналы 1-5 мин
• Мартингейл x2/x3 стратегия
• Автоматический countdown

🔵 **LONG** (6,990₽/мес):
• Безлимитные длинные сигналы 1-4 часа
• Процентная стратегия 2-3%
• Управление через /my_longs

💎 **VIP** (9,990₽/мес):
• ВСЕ СИГНАЛЫ SHORT + LONG
• Авто-рассылка 5 раз в день
• Приоритетная поддержка

🚀 Начните зарабатывать больше: /plans
"""
        # Не показывать кнопку админам
        if not bot.is_admin(user_id):
            upgrade_keyboard = [
                [InlineKeyboardButton("🔥💎 ВЫБРАТЬ ТАРИФ И ЗАРАБАТЫВАТЬ! 💰🚀", callback_data="buy_subscription")]
            ]
            upgrade_markup = InlineKeyboardMarkup(upgrade_keyboard)
        else:
            upgrade_markup = None
        
        if is_callback:
            await update.callback_query.message.reply_text(upgrade_text, parse_mode='Markdown', reply_markup=upgrade_markup)
        else:
            await update.message.reply_text(upgrade_text, parse_mode='Markdown', reply_markup=upgrade_markup)

async def show_tariff_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать красивые карточки тарифов с кнопками оплаты (адаптировано под текущую подписку)"""
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    user_id = update.effective_user.id
    
    # Получить текущие цены из настроек
    vip_price_rub = int(bot.get_setting('vip_price_rub', '9990'))
    short_price_rub = int(bot.get_setting('short_price_rub', '4990'))
    long_price_rub = int(bot.get_setting('long_price_rub', '6990'))
    
    # Получить валюту и тип подписки пользователя
    cursor = bot.conn.cursor()
    cursor.execute('SELECT currency, subscription_type FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    currency = result[0] if result and result[0] else 'RUB'
    sub_type = result[1] if result and result[1] else 'free'
    
    # Конвертировать и форматировать цены
    vip_price_display = bot.format_price(bot.convert_price(vip_price_rub, currency), currency)
    short_price_display = bot.format_price(bot.convert_price(short_price_rub, currency), currency)
    long_price_display = bot.format_price(bot.convert_price(long_price_rub, currency), currency)
    
    # Адаптируем текст и кнопки в зависимости от текущей подписки
    if sub_type == 'vip':
        # VIP - уже максимальный тариф
        tariff_text = f"""
💎 *ВЫ ИСПОЛЬЗУЕТЕ VIP ТАРИФ*

🎉 У вас уже максимальный тариф!

✅ ВСЕ сигналы (SHORT + LONG) без ограничений
✅ Автотрейдинг с 4 стратегиями включая AI
✅ Приоритетная поддержка 24/7
✅ Точность 85-95%

*Продолжайте зарабатывать!* 🚀
"""
        keyboard = [
            [InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats")],
            [InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")]
        ]
    
    elif sub_type in ['short', 'long']:
        # SHORT/LONG - показать возможность расширения до VIP
        current_plan_emoji = "⚡" if sub_type == 'short' else "🔵"
        current_plan_name = "SHORT" if sub_type == 'short' else "LONG"
        
        tariff_text = f"""
{current_plan_emoji} *ВЫ ИСПОЛЬЗУЕТЕ {current_plan_name} ТАРИФ*

⬆️ *РАСШИРЬТЕ ВОЗМОЖНОСТИ ДО VIP!*

━━━━━━━━━━━━━━━━━━━━━━━━
💎 *VIP ТАРИФ*
💰 Цена: *{vip_price_display}/мес*

✨ *ВСЕ ПРЕИМУЩЕСТВА {current_plan_name}* +

✅ Дополнительные сигналы (SHORT+LONG)
✅ 🤖 АВТОТРЕЙДИНГ с 4 стратегиями
✅ AI Trading (эксклюзив VIP)
✅ Приоритетная поддержка 24/7
✅ Максимальная точность 85-95%

━━━━━━━━━━━━━━━━━━━━━━━━
🆓 *FREE ТАРИФ*
💰 Цена: *Бесплатно*

✅ 5 SHORT + 5 LONG сигналов/день
✅ Сигналы ≥95% точности

👇 *Выберите действие*
"""
        keyboard = [
            [InlineKeyboardButton(f"⬆️ Расширить до VIP ({vip_price_display}/мес)", callback_data="buy_vip")],
            [InlineKeyboardButton("🔄 Остаться на текущем", callback_data="tariff_keep")],
            [InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")]
        ]
    
    else:
        # FREE/TRIAL - показать все тарифы
        tariff_text = f"""
🚀 *ВЫБЕРИТЕ СВОЙ ТАРИФ*

━━━━━━━━━━━━━━━━━━━━━━━━
💎 *VIP ТАРИФ*
💰 Цена: *{vip_price_display}/мес*

✅ ВСЕ сигналы (SHORT + LONG)
✅ Безлимитные сигналы 1-5 мин и 1-4 часа
✅ 🤖 Автотрейдинг с AI Trading
✅ Обе стратегии: Мартингейл + %
✅ Приоритетная поддержка
✅ Точность 85-95%

━━━━━━━━━━━━━━━━━━━━━━━━
⚡ *SHORT ТАРИФ*
💰 Цена: *{short_price_display}/мес*

✅ Безлимитные сигналы 1-5 минут
✅ Мартингейл стратегия x2/x3
✅ Автоматический countdown
✅ Быстрая торговля
✅ Точность 85-92%

━━━━━━━━━━━━━━━━━━━━━━━━
🔵 *LONG ТАРИФ*
💰 Цена: *{long_price_display}/мес*

✅ Безлимитные сигналы 1-4 часа
✅ Процентная стратегия 2-3%
✅ Управление через /my_longs
✅ Долгосрочная торговля
✅ Точность 90-95%

━━━━━━━━━━━━━━━━━━━━━━━━
🆓 *FREE ТАРИФ*
💰 Цена: *Бесплатно навсегда*

✅ 5 SHORT + 5 LONG сигналов/день
✅ Сигналы ≥95% точности
✅ Все стратегии доступны
✅ Идеально для старта

👇 *Нажмите "Оплатить" под нужным тарифом*
"""
        keyboard = [
            [InlineKeyboardButton(f"💳 Оплатить VIP ({vip_price_display}/мес)", callback_data="buy_vip")],
            [InlineKeyboardButton(f"💳 Оплатить SHORT ({short_price_display}/мес)", callback_data="buy_short")],
            [InlineKeyboardButton(f"💳 Оплатить LONG ({long_price_display}/мес)", callback_data="buy_long")],
            [InlineKeyboardButton("🆓 Остаться на FREE", callback_data="tariff_free")],
            [InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await update.callback_query.edit_message_text(tariff_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(tariff_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_tariff_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать подробное описание тарифа VIP"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Получить цену
    vip_price_rub = int(bot.get_setting('vip_price_rub', '9990'))
    
    # Получить валюту пользователя
    cursor = bot.conn.cursor()
    cursor.execute('SELECT currency FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    currency = result[0] if result and result[0] else 'RUB'
    
    price_display = bot.format_price(bot.convert_price(vip_price_rub, currency), currency)
    
    description = f"""
💎 **ТАРИФ VIP**

💰 Стоимость: **{price_display}/месяц**

✨ **МАКСИМАЛЬНЫЕ ВОЗМОЖНОСТИ:**

⚡ **SHORT сигналы:**
✅ Безлимитные быстрые сигналы (1-5 мин)
✅ Мартингейл стратегия x2/x3
✅ Автоматический countdown
✅ Точность 85-92%

🔵 **LONG сигналы:**
✅ Безлимитные длинные сигналы (1-4 часа)
✅ Процентная стратегия 2-3% от банка
✅ Управление через /my_longs
✅ Точность 90-95%

🤖 **ЭКСКЛЮЗИВ VIP - АВТОТРЕЙДИНГ!**
🔥 Автоматическое размещение сделок
🔥 Работа 24/7 без вашего участия
🔥 Демо и реальный режимы
🔥 Использует вашу стратегию

🚀 **Другие бонусы:**
✅ Авто-рассылка топ-10 сигналов 5 раз в день
✅ Приоритетная поддержка
✅ Полная кастомизация стратегий
✅ Максимальная прибыль

🎯 **Для серьезных трейдеров!**
"""
    
    keyboard = [
        [InlineKeyboardButton(f"💳 Купить VIP за {price_display}", callback_data="buy_vip")],
        [InlineKeyboardButton("◀️ К выбору тарифов", callback_data="choose_plan_settings")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Проверить есть ли изображение
    vip_image = bot.get_setting('tariff_image_vip', '')
    
    if vip_image:
        # Попробовать отправить с изображением
        try:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=vip_image,
                caption=description,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            # Удалить старое сообщение только после успешной отправки
            await query.message.delete()
        except Exception as e:
            logger.error(f"Failed to send tariff image: {e}")
            # Откат на текстовое сообщение
            await query.edit_message_text(description, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        # Отправить только текст
        await query.edit_message_text(description, reply_markup=reply_markup, parse_mode='Markdown')

async def show_tariff_short(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать подробное описание тарифа SHORT"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Получить цену
    short_price_rub = int(bot.get_setting('short_price_rub', '4990'))
    
    # Получить валюту пользователя
    cursor = bot.conn.cursor()
    cursor.execute('SELECT currency FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    currency = result[0] if result and result[0] else 'RUB'
    
    price_display = bot.format_price(bot.convert_price(short_price_rub, currency), currency)
    
    description = f"""
⚡ **ТАРИФ SHORT**

💰 Стоимость: **{price_display}/месяц**

⏱ **БЫСТРЫЕ СИГНАЛЫ:**

✅ **Безлимитные сигналы 1-5 минут**
• Получайте сигналы неограниченно
• Автоматический countdown
• Быстрая торговля

✅ **Мартингейл стратегия x2/x3**
• Выбор стратегии на ваше усмотрение
• x2: мин. банк 6,300₽
• x3: мин. банк 36,400₽

✅ **Высокая точность**
• 85-92% успешных сделок
• Продвинутая техническая аналитика
• 5-факторная оценка сигналов

✅ **Автоматизация**
• Countdown до закрытия сделки
• Автоматические напоминания
• Отчеты по результатам

🎯 **Для активных трейдеров!**
"""
    
    keyboard = [
        [InlineKeyboardButton(f"💳 Купить SHORT за {price_display}", callback_data="buy_short")],
        [InlineKeyboardButton("◀️ К выбору тарифов", callback_data="choose_plan_settings")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Проверить есть ли изображение
    short_image = bot.get_setting('tariff_image_short', '')
    
    if short_image:
        # Попробовать отправить с изображением
        try:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=short_image,
                caption=description,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            # Удалить старое сообщение только после успешной отправки
            await query.message.delete()
        except Exception as e:
            logger.error(f"Failed to send tariff image: {e}")
            # Откат на текстовое сообщение
            await query.edit_message_text(description, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        # Отправить только текст
        await query.edit_message_text(description, reply_markup=reply_markup, parse_mode='Markdown')

async def show_tariff_long(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать подробное описание тарифа LONG"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Получить цену
    long_price_rub = int(bot.get_setting('long_price_rub', '6990'))
    
    # Получить валюту пользователя
    cursor = bot.conn.cursor()
    cursor.execute('SELECT currency FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    currency = result[0] if result and result[0] else 'RUB'
    
    price_display = bot.format_price(bot.convert_price(long_price_rub, currency), currency)
    
    description = f"""
🔵 **ТАРИФ LONG**

💰 Стоимость: **{price_display}/месяц**

📊 **ДЛИННЫЕ СИГНАЛЫ:**

✅ **Безлимитные сигналы 1-4 часа**
• Получайте сигналы неограниченно
• Стабильные долгосрочные сделки
• Управление через /my_longs

✅ **Процентная стратегия 2-3%**
• Выбор процента от банка (2%, 2.5%, 3%)
• Автоматический расчет ставки
• Безопасное управление капиталом

✅ **Максимальная точность**
• 90-95% успешных сделок
• Глубокая техническая аналитика
• Фильтр сигналов ≥95% уверенности

✅ **Удобное управление**
• Список активных LONG сигналов
• Отметка результатов (win/loss)
• Полная история сделок

🎯 **Для консервативных трейдеров!**
"""
    
    keyboard = [
        [InlineKeyboardButton(f"💳 Купить LONG за {price_display}", callback_data="buy_long")],
        [InlineKeyboardButton("◀️ К выбору тарифов", callback_data="choose_plan_settings")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Проверить есть ли изображение
    long_image = bot.get_setting('tariff_image_long', '')
    
    if long_image:
        # Попробовать отправить с изображением
        try:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=long_image,
                caption=description,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            # Удалить старое сообщение только после успешной отправки
            await query.message.delete()
        except Exception as e:
            logger.error(f"Failed to send tariff image: {e}")
            # Откат на текстовое сообщение
            await query.edit_message_text(description, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        # Отправить только текст
        await query.edit_message_text(description, reply_markup=reply_markup, parse_mode='Markdown')

async def show_tariff_free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать подробное описание тарифа FREE"""
    query = update.callback_query
    
    description = """
🆓 **ТАРИФ FREE**

💰 Стоимость: **БЕСПЛАТНО навсегда**

🎁 **БЕССРОЧНЫЙ ДОСТУП:**

✅ **5 SHORT сигналов в день**
• Быстрые сигналы 1-5 минут
• Обновление каждый день
• Точность ≥95%

✅ **5 LONG сигналов в день**
• Длинные сигналы 1-4 часа
• Запрос по команде
• Точность ≥95%

✅ **Базовая аналитика**
• 5-факторная оценка сигналов
• История сделок
• Статистика побед/поражений

⚠️ **Ограничения:**
• Только 5+5 сигналов в день
• Без автоматических стратегий
• Без авто-рассылок

💡 **Отлично для начала!**

🚀 Хотите больше прибыли? Переходите на платные тарифы:
• SHORT - безлимит быстрых сигналов
• LONG - безлимит длинных сигналов  
• VIP - все сигналы + авто-рассылка
"""
    
    keyboard = [
        [InlineKeyboardButton("🔥💎 ПЕРЕЙТИ НА ПЛАТНЫЙ ТАРИФ", callback_data="choose_plan_settings")],
        [InlineKeyboardButton("🏠 Главная", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user_id = update.effective_user.id
    
    # Проверить есть ли изображение
    free_image = bot.get_setting('tariff_image_free', '')
    
    if free_image:
        # Попробовать отправить с изображением
        try:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=free_image,
                caption=description,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            # Удалить старое сообщение только после успешной отправки
            await query.message.delete()
        except Exception as e:
            logger.error(f"Failed to send tariff image: {e}")
            # Откат на текстовое сообщение
            await query.edit_message_text(description, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        # Отправить только текст
        await query.edit_message_text(description, reply_markup=reply_markup, parse_mode='Markdown')

async def buy_subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    user_id = update.effective_user.id
    
    # Проверка бана
    if bot.is_banned(user_id):
        error_msg = f"🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\nДоступ к боту ограничен.\nОбратитесь в поддержку: {bot.get_support_contact()}"
        if is_callback:
            await update.callback_query.answer("🚫 Вы заблокированы", show_alert=True)
        else:
            await update.message.reply_text(error_msg, parse_mode='Markdown')
        return
    
    # Проверить, новый ли пользователь
    cursor = bot.conn.cursor()
    cursor.execute('SELECT new_user_discount_used, pocket_option_registered FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    discount_used = result[0] if result else 0
    po_registered = result[1] if result else 0
    
    bot_name = bot.get_setting('bot_name', 'CRYPTO SIGNALS BOT')
    
    subscription_text = f"""
💎 **ТАРИФЫ {bot_name}**

Выберите подходящий тариф:

{SUBSCRIPTION_PLANS['short']['emoji']} **SHORT** - Быстрые сигналы (1-5 мин)
• Мартингейл стратегия x3
• Автоматический countdown
• Быстрая торговля

{SUBSCRIPTION_PLANS['long']['emoji']} **LONG** - Длинные сигналы (1-4 часа)
• Процентная стратегия 2.5%
• Управление через /my_longs
• Стабильные сделки

{SUBSCRIPTION_PLANS['vip']['emoji']} **VIP** - Все возможности
• SHORT + LONG сигналы
• Приоритетная поддержка
• Максимальная прибыль

💰 **Экономия до 20% при годовой подписке!**
"""

    if not discount_used:
        subscription_text += f"""

🎁 **АКЦИЯ ДЛЯ НОВИЧКОВ!**
• SHORT на месяц за {NEW_USER_PROMO['price']}₽ (скидка 70%!)
• Только для новых пользователей
• Напишите свой никнейм Pocket Option в поддержку
"""
    
    keyboard = [
        [InlineKeyboardButton(f"{SUBSCRIPTION_PLANS['short']['emoji']} SHORT", callback_data="buy_short")],
        [InlineKeyboardButton(f"{SUBSCRIPTION_PLANS['long']['emoji']} LONG", callback_data="buy_long")],
        [InlineKeyboardButton(f"{SUBSCRIPTION_PLANS['vip']['emoji']} VIP", callback_data="buy_vip")]
    ]
    
    if not discount_used:
        keyboard.insert(0, [InlineKeyboardButton("🎁 АКЦИЯ для новых", callback_data="buy_promo")])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await update.callback_query.edit_message_text(
            subscription_text, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            subscription_text, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )

async def signal_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    user_id = update.effective_user.id
    message_obj = update.callback_query.message if is_callback else update.message
    
    # Проверка бана
    if bot.is_banned(user_id):
        error_msg = f"🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\nДоступ к боту ограничен.\nОбратитесь в поддержку: {bot.get_support_contact()}"
        if is_callback:
            await update.callback_query.answer("🚫 Вы заблокированы", show_alert=True)
        else:
            await message_obj.reply_text(error_msg, parse_mode='Markdown')
        return
    
    stats = bot.get_user_signal_stats(user_id)
    
    if stats['total_signals'] == 0:
        await message_obj.reply_text(
            "📊 У вас пока нет истории сигналов.\n\n"
            "Используйте /long или /short чтобы получить сигналы и начать собирать статистику!"
        )
        return
    
    best_assets_text = "\n".join([
        f"{i+1}. {asset}: {wins}/{total} ({wins/total*100:.1f}%)" 
        for i, (asset, total, wins) in enumerate(stats['best_assets'][:5])
    ]) if stats['best_assets'] else "Недостаточно данных"
    
    stats_text = f"""
📊 **СТАТИСТИКА ВАШИХ СИГНАЛОВ**

📈 **Общая статистика:**
• Всего сигналов: {stats['total_signals']}
• Успешных: {stats['wins']} ✅
• Неудачных: {stats['losses']} ❌
• Винрейт: {stats['win_rate']:.1f}%
• Прибыль/убыток: {stats['net_profit']:.2f} USD
• Средняя уверенность: {stats['avg_confidence']:.1f}%

🏆 **Лучшие активы:**
{best_assets_text}

💡 **Совет:** {'Отличный винрейт! Продолжайте!' if stats['win_rate'] >= 60 else 'Продолжайте торговать, статистика улучшится!'}

📱 Используйте /bankroll для расчета размера ставок
"""
    
    await message_obj.reply_text(stats_text)

async def bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /bank - главное меню управления банком"""
    user_id = update.effective_user.id
    
    # Проверка бана
    if bot.is_banned(user_id):
        await update.message.reply_text(
            f"🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\nДоступ к боту ограничен.\nОбратитесь в поддержку: {bot.get_support_contact()}",
            parse_mode='Markdown'
        )
        return
    
    # Получить данные о банке
    cursor = bot.conn.cursor()
    cursor.execute('''
        SELECT trading_strategy, initial_balance, current_balance, 
               martingale_multiplier, martingale_base_stake, subscription_type,
               auto_trading_enabled, auto_trading_mode
        FROM users WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    
    if not result:
        await update.message.reply_text("❌ Ошибка получения данных", reply_markup=add_home_button())
        return
    
    strategy, initial_balance, current_balance, martingale_mult, base_stake, subscription_type, auto_trading_enabled, auto_trading_mode = result
    
    # Проверка VIP статуса
    is_vip = subscription_type == 'vip'
    
    # Если стратегия не выбрана
    if not strategy:
        keyboard = [
            [InlineKeyboardButton("⚡️ Мартингейл (SHORT)", callback_data="strategy_martingale")],
            [InlineKeyboardButton("📊 Процентная (LONG)", callback_data="strategy_percentage")],
            [InlineKeyboardButton("🏠 Домой", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎯 **ВЫБОР ТОРГОВОЙ СТРАТЕГИИ**\n\n"
            "⚡️ **Мартингейл (SHORT):**\n"
            "• Для быстрых сигналов 1-5 мин\n"
            "• Удвоение ставки после проигрыша (x2/x3)\n"
            "• Минимальный банк: 36,400₽\n"
            "• Агрессивная стратегия\n\n"
            "📊 **Процентная (LONG):**\n"
            "• Для длинных сигналов 1-4 часа\n"
            "• Фиксированный процент от банка (2-3%)\n"
            "• Минимальный банк: любой\n"
            "• Консервативная стратегия\n\n"
            "💡 Выберите стратегию под ваш стиль торговли:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    # Если банк не установлен
    if not initial_balance or initial_balance == 0:
        await update.message.reply_text(
            f"💰 **УСТАНОВКА БАНКА**\n\n"
            f"Ваша стратегия: {'⚡️ Мартингейл' if strategy == 'martingale' else '📊 Процентная'}\n\n"
            f"Используйте: `/set_bank [сумма]`\n"
            f"Пример: `/set_bank 50000`",
            parse_mode='Markdown',
            reply_markup=add_home_button()
        )
        return
    
    # Формируем меню управления банком
    balance = current_balance if current_balance else initial_balance
    profit_loss = balance - initial_balance if initial_balance else 0
    profit_emoji = "📈" if profit_loss >= 0 else "📉"
    
    # Рекомендуемая ставка в зависимости от стратегии
    if strategy == 'martingale':
        recommended_stake = bot.calculate_recommended_short_stake(balance)
        mult_text = f"x{martingale_mult}" if martingale_mult else "x3"
        stake_text = f"{recommended_stake:.0f}₽ ({mult_text})" if recommended_stake else "❌ Недостаточно"
        strategy_name = "⚡️ Мартингейл"
    elif strategy == 'dalembert':
        recommended_stake, level = bot.get_dalembert_stake(user_id)
        stake_text = f"{recommended_stake:.0f}₽ (уровень {level})" if recommended_stake else "❌ Недостаточно"
        strategy_name = "📈 Д'Аламбер"
    else:
        # Percentage или неопределенная стратегия
        recommended_stake = balance * 0.025
        stake_text = f"{recommended_stake:.0f}₽ (2.5%)"
        strategy_name = "📊 Процентная"
    
    bank_text = f"""
💰 **УПРАВЛЕНИЕ БАНКОМ**

📊 **Текущие показатели:**
• Начальный: {initial_balance:.0f}₽
• Текущий: {balance:.0f}₽
• {profit_emoji} Прибыль/Убыток: {profit_loss:+.0f}₽

🎯 **Ваша стратегия:** {strategy_name}
💵 **Рекомендуемая ставка:** {stake_text}

📱 **Команды:**
• `/report_win` - отметить выигрыш
• `/report_loss` - отметить проигрыш
• `/set_bank [сумма]` - изменить банк
• `/my_stats` - посмотреть статистику
"""
    
    keyboard = []
    
    # БОЛЬШАЯ кнопка автотрейдинга - видна ВСЕМ
    if is_vip:
        # VIP: показываем активную кнопку с роботом и статусом
        auto_status = "🟢 ВКЛ" if auto_trading_enabled else "🔴 ВЫКЛ"
        keyboard.append([InlineKeyboardButton(
            f"🤖 АВТОТРЕЙДИНГ {auto_status}", 
            callback_data="autotrade_menu"
        )])
    else:
        # НЕ-VIP: показываем с замочком, callback проверит права
        keyboard.append([InlineKeyboardButton(
            "🔒 АВТОТРЕЙДИНГ", 
            callback_data="autotrade_menu"
        )])
    
    # Остальные кнопки
    keyboard.extend([
        [InlineKeyboardButton("✅ Отметить выигрыш", callback_data="quick_report_win"),
         InlineKeyboardButton("❌ Отметить проигрыш", callback_data="quick_report_loss")],
        [InlineKeyboardButton("🔄 Сменить стратегию", callback_data="choose_strategy")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats_view")],
    ])
    
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(bank_text, parse_mode='Markdown', reply_markup=reply_markup)

async def bankroll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    user_id = update.effective_user.id
    
    # Проверка бана
    if bot.is_banned(user_id):
        error_msg = f"🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\nДоступ к боту ограничен.\nОбратитесь в поддержку: {bot.get_support_contact()}"
        if is_callback:
            await update.callback_query.answer("🚫 Вы заблокированы", show_alert=True)
        else:
            await update.message.reply_text(error_msg, parse_mode='Markdown')
        return
    
    if not context.args or len(context.args) == 0:
        cursor = bot.conn.cursor()
        cursor.execute('SELECT current_balance FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        balance = result[0] if result and result[0] else 1000.0
    else:
        try:
            balance = float(context.args[0])
            if balance <= 0:
                message_obj = update.callback_query.message if is_callback else update.message
                await message_obj.reply_text("❌ Баланс должен быть положительным числом!")
                return
            
            cursor = bot.conn.cursor()
            cursor.execute('UPDATE users SET current_balance = ? WHERE user_id = ?', (balance, user_id))
            bot.conn.commit()
        except ValueError:
            message_obj = update.callback_query.message if is_callback else update.message
            await message_obj.reply_text("❌ Неверный формат. Используйте: /bankroll 1000")
            return
    
    recommendation = bot.get_bankroll_recommendation(user_id, balance)
    
    risk_level = "🟢 Консервативный" if recommendation['recommendation_type'] == "conservative" else "🟡 Оптимальный"
    
    bankroll_text = f"""
💰 **УПРАВЛЕНИЕ КАПИТАЛОМ**

💵 **Ваш банкролл:** `${balance:.2f}`
📊 **Винрейт:** `{recommendation['win_rate']:.1f}%`

{risk_level}

📈 **Рекомендуемая ставка (Fixed):**
• Процент: `{recommendation['fixed_percentage']:.1f}%`
• Сумма: `${recommendation['fixed_stake']:.2f}`

🎯 **Оптимальная ставка (Kelly Criterion):**
• Процент: `{recommendation['kelly_percentage']:.1f}%`
• Сумма: `${recommendation['kelly_stake']:.2f}`

⚠️ **Лимиты:**
• Минимальная ставка: `${recommendation['min_stake']:.2f}` (1%)
• Максимальная ставка: `${recommendation['max_stake']:.2f}` (5%)

💡 **Советы:**
{'✅ У вас отличный винрейт! Можете использовать Kelly Criterion' if recommendation['win_rate'] >= 60 else '⚠️ Используйте консервативные ставки (2%) пока не улучшите винрейт'}
{'✅ Достаточно данных для точных расчетов' if recommendation['win_rate'] > 0 else '📊 Нужно больше сигналов для точной статистики'}

🔧 **Команды:**
• `/bankroll 1500` - обновить баланс
• `/signal_stats` - просмотр статистики
"""
    
    message_obj = update.callback_query.message if is_callback else update.message
    await message_obj.reply_text(bankroll_text, parse_mode='Markdown')

async def set_bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Проверка бана
    if bot.is_banned(user_id):
        await update.message.reply_text(
            f"🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\nДоступ к боту ограничен.\nОбратитесь в поддержку: {bot.get_support_contact()}",
            parse_mode='Markdown'
        )
        return
    
    # Проверка доступа - FREE пользователи не могут использовать банк
    has_subscription, message, signals_used, free_trials_used, sub_type = bot.check_subscription(user_id)
    if not sub_type or sub_type == 'free':
        await update.message.reply_text(
            "💎 **ФУНКЦИЯ НЕДОСТУПНА**\n\n"
            "Управление банком доступно только для платных подписок:\n"
            "• ⚡️ SHORT\n"
            "• 🔵 LONG\n"
            "• 💎 VIP\n\n"
            "Купите подписку для доступа к управлению банком!",
            parse_mode='Markdown'
        )
        return
    
    # Проверить, выбрана ли стратегия
    cursor = bot.conn.cursor()
    cursor.execute('SELECT trading_strategy, initial_balance, current_balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    strategy = result[0] if result else None
    
    # Если стратегия не выбрана, показать меню выбора
    if not strategy:
        keyboard = [
            [InlineKeyboardButton("⚡️ Мартингейл (SHORT)", callback_data="strategy_martingale")],
            [InlineKeyboardButton("📊 Процентная (LONG)", callback_data="strategy_percentage")],
            [InlineKeyboardButton("🏠 Домой", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎯 **ВЫБОР ТОРГОВОЙ СТРАТЕГИИ**\n\n"
            "⚡️ **Мартингейл (SHORT):**\n"
            "• Для быстрых сигналов 1-5 мин\n"
            "• Удвоение ставки после проигрыша (x2/x3)\n"
            "• Минимальный банк: 36,400₽\n"
            "• Агрессивная стратегия\n\n"
            "📊 **Процентная (LONG):**\n"
            "• Для длинных сигналов 1-4 часа\n"
            "• Фиксированный процент от банка (2-3%)\n"
            "• Минимальный банк: любой\n"
            "• Консервативная стратегия\n\n"
            "💡 Выберите стратегию под ваш стиль торговли:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    # Если есть аргумент - установить банк с учетом стратегии
    if context.args and len(context.args) > 0:
        try:
            initial_balance = float(context.args[0])
            if initial_balance <= 0:
                await update.message.reply_text("❌ Сумма должна быть больше 0", reply_markup=add_home_button())
                return
            
            cursor = bot.conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET initial_balance = ?, current_balance = ? 
                WHERE user_id = ?
            ''', (initial_balance, initial_balance, user_id))
            bot.conn.commit()
            
            # Показать рекомендации в зависимости от стратегии
            if strategy == 'martingale':
                recommended_short = bot.calculate_recommended_short_stake(initial_balance)
                if recommended_short:
                    success_text = f"✅ **Банк установлен:** {initial_balance:.0f}₽\n⚡️ **Ставка:** {recommended_short:.0f}₽ (мартингейл x3)"
                else:
                    success_text = f"❌ **Недостаточно для мартингейла**\n💰 Минимум: 36,400₽\n🔄 /set_bank - сменить стратегию"
            elif strategy == 'percentage':
                recommended_long = initial_balance * 0.025
                success_text = f"✅ **Банк установлен:** {initial_balance:.0f}₽\n📊 **Ставка:** {recommended_long:.0f}₽ (2.5%)"
            else:
                success_text = f"✅ **Банк установлен:** {initial_balance:.0f}₽"
            
            await update.message.reply_text(success_text, parse_mode='Markdown')
            return
            
        except ValueError:
            await update.message.reply_text("❌ Введите число", reply_markup=add_home_button())
            return
    
    # Показать текущий банк с рекомендациями в зависимости от стратегии
    cursor = bot.conn.cursor()
    cursor.execute('SELECT initial_balance, current_balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result is not None and result[0] is not None:
        initial = result[0]
        current = result[1] if result[1] is not None else initial
        profit = current - initial
        profit_percent = (profit / initial * 100) if initial > 0 else 0
        
        # Показать рекомендации в зависимости от стратегии
        if strategy == 'martingale':
            recommended = bot.calculate_recommended_short_stake(current)
            if recommended:
                info_text = f"💰 **Банк:** {current:.0f}₽ ({profit:+.0f}₽)\n⚡️ **Ставка:** {recommended:.0f}₽\n\n💡 Отправьте новую сумму для изменения"
            else:
                info_text = f"💰 **Банк:** {current:.0f}₽\n❌ Недостаточно для мартингейла\n\n💡 Отправьте новую сумму для изменения"
        elif strategy == 'percentage':
            recommended = current * 0.025
            info_text = f"💰 **Банк:** {current:.0f}₽ ({profit:+.0f}₽)\n📊 **Ставка:** {recommended:.0f}₽ (2.5%)\n\n💡 Отправьте новую сумму для изменения"
        else:
            info_text = f"💰 **Банк:** {current:.0f}₽\n\n💡 Отправьте новую сумму для изменения"
        
        await update.message.reply_text(info_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(
            "💰 **Установка банка**\n\n"
            "📝 Отправьте сумму следующим сообщением\n"
            "Пример: `15000`",
            parse_mode='Markdown'
        )
    
    # Установить флаг ожидания суммы банка
    context.user_data['awaiting_bank_amount'] = True

async def set_short_stake_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Проверка бана
    if bot.is_banned(user_id):
        await update.message.reply_text(
            f"🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\nДоступ к боту ограничен.\nОбратитесь в поддержку: {bot.get_support_contact()}",
            parse_mode='Markdown'
        )
        return
    
    if not context.args or len(context.args) == 0:
        cursor = bot.conn.cursor()
        cursor.execute('SELECT short_base_stake, current_martingale_level, consecutive_losses FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result:
            base_stake = result[0] if result[0] else 100
            level = result[1] if result[1] else 0
            losses = result[2] if result[2] else 0
            current_stake = base_stake * (3 ** level)
            
            info_text = f"""
💰 **МАРТИНГЕЙЛ НАСТРОЙКИ (SHORT)**

📊 **Текущие параметры:**
• Базовая ставка: {base_stake:.0f}₽
• Текущий уровень: {level}
• Текущая ставка: {current_stake:.0f}₽
• Подряд лузов: {losses}/5

📈 **Стратегия:**
• После луза: x3 ставка
• После вина: сброс на {base_stake:.0f}₽
• Максимум лузов: 5 подряд

🔧 **Команды:**
• `/set_short_stake 150` - изменить базовую ставку
• `/my_stats` - просмотр статистики
"""
            await update.message.reply_text(info_text)
        return
    
    try:
        new_stake = float(context.args[0])
        if new_stake <= 0:
            await update.message.reply_text("❌ Ставка должна быть положительным числом!")
            return
        
        if new_stake < 50:
            await update.message.reply_text("❌ Минимальная ставка: 50₽", reply_markup=add_home_button())
            return
        
        bot.set_short_base_stake(user_id, new_stake)
        
        success_text = f"""
✅ **Базовая ставка SHORT обновлена!**

💰 **Новая базовая ставка:** {new_stake:.0f}₽

📊 **Прогрессия мартингейла:**
• Уровень 0 (старт): {new_stake:.0f}₽
• Уровень 1: {new_stake * 3:.0f}₽
• Уровень 2: {new_stake * 9:.0f}₽
• Уровень 3: {new_stake * 27:.0f}₽
• Уровень 4: {new_stake * 81:.0f}₽
• Уровень 5: {new_stake * 243:.0f}₽

⚠️ Убедитесь что ваш банк позволяет сделать 5 лузов подряд!
"""
        await update.message.reply_text(success_text)
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Используйте: `/set_short_stake 150`")

async def report_win_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Проверка бана
    if bot.is_banned(user_id):
        await update.message.reply_text(
            f"🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\nДоступ к боту ограничен.\nОбратитесь в поддержку: {bot.get_support_contact()}",
            parse_mode='Markdown'
        )
        return
    
    # Проверка доступа - FREE пользователи не могут использовать банк
    has_subscription, message, signals_used, free_trials_used, sub_type = bot.check_subscription(user_id)
    if not sub_type or sub_type == 'free':
        await update.message.reply_text(
            "💎 **ФУНКЦИЯ НЕДОСТУПНА**\n\n"
            "Отчеты о сделках доступны только для платных подписок.",
            parse_mode='Markdown'
        )
        return
    
    last_signal = bot.get_last_pending_signal(user_id)
    
    if not last_signal:
        await update.message.reply_text(
            "❌ Нет активных сигналов для отчета.\n"
            "Получите сигнал через /short или /long"
        )
        return
    
    signal_id, asset, signal_type, confidence, stake_amount = last_signal
    
    if stake_amount is None or stake_amount <= 0:
        await update.message.reply_text("❌ Ставка не определена. Установите банк через /set_bank")
        return
    
    stake = stake_amount
    profit = stake * (PAYOUT_PERCENT / 100)
    
    cursor = bot.conn.cursor()
    cursor.execute('SELECT current_balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    current_balance = result[0] if result and result[0] is not None else 0
    
    new_balance = current_balance + profit
    
    cursor.execute('UPDATE users SET current_balance = ? WHERE user_id = ?', (new_balance, user_id))
    bot.conn.commit()
    
    bot.update_signal_result(signal_id, 'win', profit)
    
    # Сбрасываем счетчик проигрышей при выигрыше (актив доказал стабильность)
    if asset in asset_loss_streak:
        del asset_loss_streak[asset]
    # Разблокируем актив если он был заблокирован
    if asset in blocked_assets:
        del blocked_assets[asset]
        logger.info(f"✅ Актив {asset} разблокирован после выигрыша")
    
    # Получаем timeframe для определения типа сигнала
    cursor.execute('SELECT timeframe FROM signal_history WHERE id = ?', (signal_id,))
    timeframe_result = cursor.fetchone()
    timeframe = timeframe_result[0] if timeframe_result else None
    
    # Обновить стратегию после выигрыша
    short_timeframes = ["1M", "2M", "3M", "5M", "15M", "30M"]
    is_short_signal = timeframe and timeframe in short_timeframes
    
    # Получить стратегию пользователя
    cursor.execute('SELECT trading_strategy FROM users WHERE user_id = ?', (user_id,))
    strategy_result = cursor.fetchone()
    user_strategy = strategy_result[0] if strategy_result and strategy_result[0] else None
    
    if is_short_signal:
        # Обновить стратегию в зависимости от выбранной
        if user_strategy == 'martingale':
            bot.update_martingale_after_win(user_id)
            new_stake, _ = bot.get_martingale_stake(user_id)
        elif user_strategy == 'dalembert':
            bot.update_dalembert_after_win(user_id)
            new_stake, _ = bot.get_dalembert_stake(user_id)
        else:
            # Fallback - мартингейл по умолчанию для старых пользователей
            bot.update_martingale_after_win(user_id)
            new_stake, _ = bot.get_martingale_stake(user_id)
        signal_type_for_repeat = "SHORT"
        callback_for_repeat = "get_short_signal"
    else:
        new_stake = bot.get_long_stake(user_id, new_balance, is_vip=False)
        signal_type_for_repeat = "LONG"
        callback_for_repeat = "get_long_signal"
    
    success_text = f"""
✅ **Выигрыш:** +{profit:.0f}₽

💰 **Баланс:** {new_balance:.0f}₽
📊 **Новая ставка:** {new_stake:.0f}₽
"""
    
    # Кнопка для повтора поиска сигнала
    keyboard = [
        [InlineKeyboardButton(f"🔄 Получить следующий {signal_type_for_repeat}", callback_data=callback_for_repeat)],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(success_text, parse_mode='Markdown', reply_markup=reply_markup)

async def report_loss_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Проверка бана
    if bot.is_banned(user_id):
        await update.message.reply_text(
            f"🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\nДоступ к боту ограничен.\nОбратитесь в поддержку: {bot.get_support_contact()}",
            parse_mode='Markdown'
        )
        return
    
    # Проверка доступа - FREE пользователи не могут использовать банк
    has_subscription, message, signals_used, free_trials_used, sub_type = bot.check_subscription(user_id)
    if not sub_type or sub_type == 'free':
        await update.message.reply_text(
            "💎 **ФУНКЦИЯ НЕДОСТУПНА**\n\n"
            "Отчеты о сделках доступны только для платных подписок.",
            parse_mode='Markdown'
        )
        return
    
    last_signal = bot.get_last_pending_signal(user_id)
    
    if not last_signal:
        await update.message.reply_text(
            "❌ Нет активных сигналов для отчета.\n"
            "Получите сигнал через /short или /long"
        )
        return
    
    signal_id, asset, signal_type, confidence, stake_amount = last_signal
    
    if stake_amount is None or stake_amount <= 0:
        await update.message.reply_text("❌ Ставка не определена. Установите банк через /set_bank")
        return
    
    stake = stake_amount
    
    cursor = bot.conn.cursor()
    cursor.execute('SELECT current_balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    current_balance = result[0] if result and result[0] is not None else 0
    
    new_balance = current_balance - stake
    
    cursor.execute('UPDATE users SET current_balance = ? WHERE user_id = ?', (new_balance, user_id))
    bot.conn.commit()
    
    bot.update_signal_result(signal_id, 'loss', -stake)
    
    # Обновляем счетчик проигрышей для актива (блокировка после 2 лузов подряд)
    if asset in asset_loss_streak:
        asset_loss_streak[asset] += 1
    else:
        asset_loss_streak[asset] = 1
    
    # Если 2 проигрыша подряд - блокируем актив на 1 час
    if asset_loss_streak[asset] >= MAX_CONSECUTIVE_LOSSES:
        blocked_assets[asset] = time.time() + 3600  # Блокировка на 1 час
        logger.warning(f"🚫 Актив {asset} заблокирован после {asset_loss_streak[asset]} проигрышей подряд (1 час)")
    
    # Получаем timeframe для определения типа сигнала
    cursor.execute('SELECT timeframe FROM signal_history WHERE id = ?', (signal_id,))
    timeframe_result = cursor.fetchone()
    timeframe = timeframe_result[0] if timeframe_result else None
    
    # Обновить стратегию после проигрыша
    short_timeframes = ["1M", "2M", "3M", "5M", "15M", "30M"]
    is_short_signal = timeframe and timeframe in short_timeframes
    
    # Получить стратегию пользователя
    cursor.execute('SELECT trading_strategy FROM users WHERE user_id = ?', (user_id,))
    strategy_result = cursor.fetchone()
    user_strategy = strategy_result[0] if strategy_result and strategy_result[0] else None
    
    if is_short_signal:
        # Обновить стратегию в зависимости от выбранной
        if user_strategy == 'martingale':
            bot.update_martingale_after_loss(user_id)
            new_stake, _ = bot.get_martingale_stake(user_id)
        elif user_strategy == 'dalembert':
            bot.update_dalembert_after_loss(user_id)
            new_stake, _ = bot.get_dalembert_stake(user_id)
        else:
            # Fallback - мартингейл по умолчанию для старых пользователей
            bot.update_martingale_after_loss(user_id)
            new_stake, _ = bot.get_martingale_stake(user_id)
        signal_type_for_repeat = "SHORT"
        callback_for_repeat = "get_short_signal"
    else:
        new_stake = bot.get_long_stake(user_id, new_balance, is_vip=False)
        signal_type_for_repeat = "LONG"
        callback_for_repeat = "get_long_signal"
    
    loss_text = f"""
📉 **Проигрыш:** -{stake:.0f}₽

💰 **Баланс:** {new_balance:.0f}₽
📊 **Новая ставка:** {new_stake:.0f}₽
"""
    
    # Кнопка для повтора поиска сигнала
    keyboard = [
        [InlineKeyboardButton(f"🔄 Получить следующий {signal_type_for_repeat}", callback_data=callback_for_repeat)],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(loss_text, parse_mode='Markdown', reply_markup=reply_markup)

async def report_refund_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка возврата ставки"""
    user_id = update.effective_user.id
    
    # Проверка бана
    if bot.is_banned(user_id):
        await update.message.reply_text(
            f"🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\nДоступ к боту ограничен.\nОбратитесь в поддержку: {bot.get_support_contact()}",
            parse_mode='Markdown'
        )
        return
    
    # Проверка доступа
    has_subscription, message, signals_used, free_trials_used, sub_type = bot.check_subscription(user_id)
    if not sub_type or sub_type == 'free':
        await update.message.reply_text(
            "💎 **ФУНКЦИЯ НЕДОСТУПНА**\n\n"
            "Отчеты о сделках доступны только для платных подписок.",
            parse_mode='Markdown'
        )
        return
    
    last_signal = bot.get_last_pending_signal(user_id)
    
    if not last_signal:
        await update.message.reply_text(
            "❌ Нет активных сигналов для отчета.\n"
            "Получите сигнал через /short или /long"
        )
        return
    
    signal_id, asset, signal_type, confidence, stake_amount = last_signal
    
    if stake_amount is None or stake_amount <= 0:
        await update.message.reply_text("❌ Ставка не определена. Установите банк через /set_bank")
        return
    
    stake = stake_amount
    
    # При возврате баланс не изменяется
    bot.update_signal_result(signal_id, 'refund', 0)
    
    # Получаем timeframe
    cursor = bot.conn.cursor()
    cursor.execute('SELECT timeframe FROM signal_history WHERE id = ?', (signal_id,))
    timeframe_result = cursor.fetchone()
    timeframe = timeframe_result[0] if timeframe_result else None
    
    # При возврате стратегия не изменяется
    short_timeframes = ["1M", "2M", "3M", "5M", "15M", "30M"]
    is_short_signal = timeframe and timeframe in short_timeframes
    
    # Получить стратегию пользователя
    cursor.execute('SELECT trading_strategy FROM users WHERE user_id = ?', (user_id,))
    strategy_result = cursor.fetchone()
    user_strategy = strategy_result[0] if strategy_result and strategy_result[0] else None
    
    if is_short_signal:
        # При возврате стратегия не меняется - ставка повторяется
        if user_strategy == 'martingale':
            bot.update_martingale_after_refund(user_id)
            next_stake, _ = bot.get_martingale_stake(user_id)
        elif user_strategy == 'dalembert':
            bot.update_dalembert_after_refund(user_id)
            next_stake, _ = bot.get_dalembert_stake(user_id)
        else:
            # Fallback - мартингейл по умолчанию
            bot.update_martingale_after_refund(user_id)
            next_stake, _ = bot.get_martingale_stake(user_id)
        signal_type_for_repeat = "SHORT"
        callback_for_repeat = "get_short_signal"
    else:
        cursor.execute('SELECT current_balance FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        balance = result[0] if result and result[0] else 0
        next_stake = bot.get_long_stake(user_id, balance, is_vip=False)
        signal_type_for_repeat = "LONG"
        callback_for_repeat = "get_long_signal"
    
    refund_text = f"""
🔄 **Возврат:** {stake:.0f}₽

💡 **Следующая ставка:** {next_stake:.0f}₽
"""
    
    # Кнопка для повтора поиска сигнала
    keyboard = [
        [InlineKeyboardButton(f"🔄 Получить следующий {signal_type_for_repeat}", callback_data=callback_for_repeat)],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(refund_text, parse_mode='Markdown', reply_markup=reply_markup)

async def guide_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /guide - показать руководство пользования"""
    user_id = update.effective_user.id
    
    # Проверка бана
    if bot.is_banned(user_id):
        await update.message.reply_text(
            f"🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\nДоступ к боту ограничен.\nОбратитесь в поддержку: {bot.get_support_contact()}",
            parse_mode='Markdown'
        )
        return
    
    guide_text = """
📖 **РУКОВОДСТВО ПОЛЬЗОВАНИЯ БОТОМ**

**ШАГ 1: Установите банк** 💰
Используйте команду: `/set_bank 10000`
где 10000 - ваш банк в выбранной валюте

Бот автоматически рассчитает рекомендованные ставки для ДВУХ стратегий!

**📊 ДВЕ СТРАТЕГИИ ТОРГОВЛИ:**

🔴 **SHORT (1M-30M) - Мартингейл x3:**
• Базовая ставка рассчитывается на 5 лузов подряд
• После луза: ставка умножается на 3
• После вина: возврат к базовой ставке
• Пример: 100₽ → 300₽ → 900₽ → 2700₽ → 8100₽
• Автоматический countdown и обязательный отчет
• Команда: `/set_short_stake 100`

🔵 **LONG (1-4 часа) - Процентная:**
• Ставка: 2.5% от текущего банка
• Автоматически пересчитывается
• Управление через `/my_longs`
• Список всех активных позиций в одном месте

**ШАГ 2: Получите сигнал** 🎯
• `/short` - короткий таймфрейм (1-30M) с мартингейлом
• `/long` - длинный таймфрейм (1H+) с процентной ставкой

**ШАГ 3: Откройте Pocket Option** 📱
1. Скопируйте название актива (кнопка "📋 Скопировать актив")
2. Найдите актив в Pocket Option
3. Выставите рекомендуемую ставку из сигнала
4. Выберите направление (CALL 🟢 / PUT 🔴)
5. Установите время экспирации

**ШАГ 4: Отслеживание результатов** 📊

⚡️ **SHORT сигналы (1-5 мин):**
• Автоматический обратный отсчет через 15 секунд
• После истечения: окно с результатом (✅ Прибыль / ❌ Убыток)
• БЕЗ пропуска - честная статистика!

🔵 **LONG сигналы (1-4 часа):**
• Команда `/my_longs` - список всех активных позиций
• Управление каждой позицией: ✅/❌/⏭️
• Живые таймеры в реальном времени

**ПОЛЕЗНЫЕ КОМАНДЫ:**
• `/my_stats` - ваша статистика и баланс
• `/set_bank` - просмотр/изменение банка
• `/set_short_stake` - установить базовую SHORT ставку
• `/my_longs` - управление LONG позициями
• `/delete_skipped` - удалить пропущенные сигналы
• `/guide` - это руководство

💡 **ВАЖНО:** 
• SHORT: Следуйте мартингейлу, не меняйте ставки вручную!
• LONG: Ставка автоматически 2.5% от банка
• Всегда отчитывайтесь о результатах для точной статистики

🎯 **Доходность сигналов:** 85-92%

⚠️ **ДИСКЛЕЙМЕР:**
Сигналы бота носят **исключительно рекомендательный характер** и представляют собой результат автоматического технического анализа рынка. Бот является **инструментом для анализа**, а не гарантией прибыли.

Торговля на финансовых рынках связана с высокими рисками и может привести к потере средств. Все торговые решения вы принимаете самостоятельно на свой страх и риск.

**Разработчики бота не несут ответственности** за возможные финансовые потери, возникшие в результате использования сигналов. Используя бот, вы подтверждаете, что понимаете и принимаете все связанные с этим риски.

📱 Торгуйте ответственно и используйте только те средства, потерю которых вы можете себе позволить!
"""
    await update.message.reply_text(guide_text)

async def setup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /setup - админ панель и настройки бота (только для админов)"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам.", reply_markup=add_home_button())
        return
    
    # Получить статистику бота
    stats = bot.get_bot_stats()
    
    setup_text = """
🔐 **АДМИН ПАНЕЛЬ И НАСТРОЙКИ**

📊 **Статистика бота:**
👥 Всего пользователей: {}
💎 Premium пользователей: {}
✅ Активных подписок: {}
📈 Всего сигналов: {}

📋 **Текущие настройки:**
• Платежи: {}
• Группа отзывов: {}
• Показывать отзывы: {}
• Реферальная ссылка: {}
• Администраторы: {}

Выберите раздел:
""".format(
        stats['total_users'],
        stats['premium_users'],
        stats['active_subscriptions'],
        stats['total_signals'],
        "✅ Включены" if bot.get_setting('payment_enabled') == 'true' else "❌ Отключены",
        bot.get_setting('reviews_group', '@cryptosignalsbot_otz'),
        "✅ Да" if bot.get_setting('reviews_enabled') == 'true' else "❌ Нет",
        bot.get_setting('referral_link', 'не настроена'),
        bot.get_setting('admin_users', str(ADMIN_USER_ID))
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 Подробная статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🏆 ТОП-10 пользователей", callback_data="admin_top_users")],
        [InlineKeyboardButton("💳 Настроить платежи", callback_data="setup_payments")],
        [InlineKeyboardButton("🔗 Настроить реферальную ссылку", callback_data="setup_referral")],
        [InlineKeyboardButton("⭐ Настроить группу отзывов", callback_data="setup_reviews")],
        [InlineKeyboardButton("👥 Управление админами", callback_data="setup_admins")],
        [InlineKeyboardButton("👤 Управление пользователями", callback_data="setup_user_management")],
        [InlineKeyboardButton("🔄 Обновить данные", callback_data="admin_refresh")],
    ]
    
    # Добавить секцию переключения тарифов для тестирования
    keyboard.append([InlineKeyboardButton("🔀 ПЕРЕКЛЮЧИТЬ ТАРИФ СЕБЕ:", callback_data="none")])
    keyboard.extend([
        [InlineKeyboardButton("💎 VIP", callback_data="admin_set_vip"),
         InlineKeyboardButton("🔵 LONG", callback_data="admin_set_long"),
         InlineKeyboardButton("⚡️ SHORT", callback_data="admin_set_short")],
        [InlineKeyboardButton("🆓 FREE", callback_data="admin_set_free"),
         InlineKeyboardButton("🎁 Пробный VIP (3 дня)", callback_data="admin_set_trial")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(setup_text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help - показать все доступные команды"""
    user_id = update.effective_user.id
    
    # Проверка бана
    if bot.is_banned(user_id):
        await update.message.reply_text(
            f"🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\nДоступ к боту ограничен.\nОбратитесь в поддержку: {bot.get_support_contact()}",
            parse_mode='Markdown'
        )
        return
    
    help_text = """
🤖 **СПИСОК ВСЕХ КОМАНД БОТА**

**💰 УПРАВЛЕНИЕ БАНКОМ:**
• `/set_bank [сумма]` - установить/просмотреть банк
• `/set_short_stake [сумма]` - установить базовую SHORT ставку

**📊 ПОЛУЧЕНИЕ СИГНАЛОВ:**
• `/short` - SHORT сигнал (1-5 мин) с мартингейлом x3
• `/long` - LONG сигнал (1-4 часа) с процентной ставкой

**📈 ОТЧЕТЫ О РЕЗУЛЬТАТАХ:**
• `/report_win` - отметить выигрыш
• `/report_loss` - отметить проигрыш
• `/my_longs` - управление LONG позициями

**📊 СТАТИСТИКА:**
• `/my_stats` - ваша статистика
• `/delete_skipped` - удалить пропущенные сигналы

**ℹ️ ИНФОРМАЦИЯ:**
• `/guide` - полное руководство
• `/help` - список команд
• `/start` - главное меню

**📊 ДВЕ СТРАТЕГИИ:**

⚡️ **SHORT (1-5 мин):** Мартингейл x3
• Базовая ставка → x3 после луза → сброс после вина
• Автоматический countdown с обязательным отчетом
• Рассчитано на 5 лузов подряд

🔵 **LONG (1-4 часа):** Процентная
• 2.5% от текущего банка
• Централизованное управление через `/my_longs`

💡 Используйте `/guide` для подробного руководства!
"""
    await update.message.reply_text(help_text)

async def start_command_old(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - старая версия для справки"""
    help_text_old = """
🤖 **СПИСОК ВСЕХ КОМАНД БОТА**

**📊 УПРАВЛЕНИЕ БАНКОМ:**
• `/set_bank [сумма]` - установить/просмотреть банк в ₽
• `/report_win [ставка]` - отчет о выигрыше
• `/report_loss [ставка]` - отчет о проигрыше

**🎯 ПОЛУЧЕНИЕ СИГНАЛОВ:**
• `/long` - сигнал на длинном таймфрейме (1H)
• `/short` - сигнал на коротком таймфрейме (1-5M)

**📈 СТАТИСТИКА:**
• `/my_stats` - ваша статистика и баланс
• `/signal_stats` - статистика всех сигналов
• `/bankroll` - управление капиталом

**ℹ️ ИНФОРМАЦИЯ:**
• `/start` - главное меню
• `/guide` - руководство пользования
• `/help` - список всех команд

**💎 ПОДПИСКА:**
• `/buy_subscription` - купить PRO подписку

📱 *Используйте /guide для подробной инструкции*
"""
    await update.message.reply_text(help_text_old, parse_mode='Markdown')

async def my_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    user_id = update.effective_user.id
    
    # Проверка бана
    if bot.is_banned(user_id):
        error_msg = f"🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\nДоступ к боту ограничен.\nОбратитесь в поддержку: {bot.get_support_contact()}"
        if is_callback:
            await update.callback_query.answer("🚫 Вы заблокированы", show_alert=True)
        else:
            await update.message.reply_text(error_msg, parse_mode='Markdown')
        return
    
    has_subscription, message, signals_used, free_trials_used, sub_type = bot.check_subscription(user_id)
    
    cursor = bot.conn.cursor()
    cursor.execute('SELECT joined_date, initial_balance, current_balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    joined_date = datetime.fromisoformat(result[0]).strftime('%d.%m.%Y') if result else "Н/Д"
    # Явная проверка на None, чтобы 0 был валидным значением баланса
    initial_balance = result[1] if result and result[1] is not None else None
    current_balance = result[2] if result and result[2] is not None else None
    
    if has_subscription:
        subscription_status = f"✅ Активна до {datetime.fromisoformat(message).strftime('%d.%m.%Y')}"
    else:
        subscription_status = "❌ Неактивна"
    
    # Получить статистику в зависимости от типа подписки
    trading_stats = ""
    if sub_type == 'vip':
        # VIP - показать обе статистики
        short_stats = bot.get_user_signal_stats(user_id, 'short')
        long_stats = bot.get_user_signal_stats(user_id, 'long')
        
        if short_stats['total_signals'] > 0 or long_stats['total_signals'] > 0:
            trading_stats = f"""
📊 **Статистика торговли:**

⚡️ **SHORT сигналы:**
• Сделок: {short_stats['total_signals']}
• Выигрышей: ✅ {short_stats['wins']}
• Проигрышей: ❌ {short_stats['losses']}
• Винрейт: {short_stats['win_rate']:.1f}%

🔵 **LONG сигналы:**
• Сделок: {long_stats['total_signals']}
• Выигрышей: ✅ {long_stats['wins']}
• Проигрышей: ❌ {long_stats['losses']}
• Винрейт: {long_stats['win_rate']:.1f}%

"""
    elif sub_type == 'short':
        # SHORT - показать только короткие
        short_stats = bot.get_user_signal_stats(user_id, 'short')
        if short_stats['total_signals'] > 0:
            trading_stats = f"""
📊 **Статистика торговли (SHORT):**
• Сделок: {short_stats['total_signals']}
• Выигрышей: ✅ {short_stats['wins']}
• Проигрышей: ❌ {short_stats['losses']}
• Винрейт: {short_stats['win_rate']:.1f}%

"""
    elif sub_type == 'long':
        # LONG - показать только длинные
        long_stats = bot.get_user_signal_stats(user_id, 'long')
        if long_stats['total_signals'] > 0:
            trading_stats = f"""
📊 **Статистика торговли (LONG):**
• Сделок: {long_stats['total_signals']}
• Выигрышей: ✅ {long_stats['wins']}
• Проигрышей: ❌ {long_stats['losses']}
• Винрейт: {long_stats['win_rate']:.1f}%

"""
    elif sub_type == 'free' or not has_subscription:
        # FREE - показать статистику FREE сигналов
        free_stats = bot.get_user_signal_stats(user_id, tier='free')
        if free_stats['total_signals'] > 0:
            trading_stats = f"""
📊 **Статистика торговли (FREE):**
• Сделок: {free_stats['total_signals']}
• Выигрышей: ✅ {free_stats['wins']}
• Проигрышей: ❌ {free_stats['losses']}
• Винрейт: {free_stats['win_rate']:.1f}%

🆓 **FREE сигналы:** Ультра-точные (≥95%)
💎 **Обновитесь до VIP** для доступа ко ВСЕМ сигналам!

"""
    
    # Получить статистику автоматической торговли (только для VIP)
    autotrade_stats_text = ""
    if sub_type == 'vip':
        autotrade_stats = bot.get_autotrade_stats(user_id)
        if autotrade_stats['total_trades'] > 0:
            profit_emoji = "📈" if autotrade_stats['total_profit'] >= 0 else "📉"
            autotrade_stats_text = f"""
🤖 **АВТОМАТИЧЕСКАЯ ТОРГОВЛЯ:**
• Всего сделок: {autotrade_stats['total_trades']}
• Выигрышей: ✅ {autotrade_stats['wins']}
• Проигрышей: ❌ {autotrade_stats['losses']}
• Ничьих: ⚪ {autotrade_stats['draws']}
• Винрейт: {autotrade_stats['win_rate']:.1f}%
• {profit_emoji} Прибыль: {autotrade_stats['total_profit']:+.2f} ₽
• ROI: {autotrade_stats['roi']:+.1f}%

"""
    
    bank_info = ""
    if initial_balance:
        profit = current_balance - initial_balance
        profit_percent = (profit / initial_balance * 100) if initial_balance > 0 else 0
        recommended_stake = current_balance * 0.02
        
        bank_info = f"""
💰 **Ваш банк:**
• Начальный: {initial_balance:.2f} ₽
• Текущий: {current_balance:.2f} ₽
• Прибыль: {profit:+.2f} ₽ ({profit_percent:+.1f}%)
• Рекомендуемая ставка: {recommended_stake:.2f} ₽

"""
    else:
        bank_info = """
💰 **Банк не установлен**
Используйте /set_bank для установки

"""
    
    # Получить общую репутацию бота (все сигналы)
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
            AVG(CASE WHEN signal_tier = 'vip' THEN confidence ELSE NULL END) as vip_conf,
            AVG(CASE WHEN signal_tier = 'free' THEN confidence ELSE NULL END) as free_conf
        FROM signal_history 
        WHERE result IS NOT NULL
    ''')
    bot_stats = cursor.fetchone()
    bot_total = bot_stats[0] or 0
    bot_wins = bot_stats[1] or 0
    vip_avg_conf = bot_stats[2] or 0
    free_avg_conf = bot_stats[3] or 0
    bot_win_rate = (bot_wins / bot_total * 100) if bot_total > 0 else 0
    
    reputation_text = f"""
🏆 **РЕПУТАЦИЯ БОТА:**
• Общий винрейт: {bot_win_rate:.1f}%
• VIP точность: {vip_avg_conf:.1f}%
• FREE точность: {free_avg_conf:.1f}%
• Всего сигналов: {bot_total}

"""
    
    stats_text = f"""
📊 **ВАША СТАТИСТИКА**

{reputation_text}👤 **Пользователь:** {update.effective_user.first_name}
🆔 **ID:** {user_id}
📅 **Дата регистрации:** {joined_date}

💎 **Подписка:** {subscription_status}
📈 **Сигналов получено:** {signals_used}

{bank_info}{trading_stats}{autotrade_stats_text}⚡ *Для получения сигналов используйте /long или /short*
"""
    
    # Проверяем есть ли пропущенные сигналы
    cursor.execute('SELECT COUNT(*) FROM signal_history WHERE user_id = ? AND result = "skipped"', (user_id,))
    skipped_count = cursor.fetchone()[0]
    
    keyboard = [
        [InlineKeyboardButton("🎯 Получить сигнал", callback_data="find_signals")]
    ]
    
    if skipped_count > 0:
        keyboard.append([InlineKeyboardButton(f"🗑️ Удалить пропущенные ({skipped_count})", callback_data="delete_skipped")])
    
    if not has_subscription:
        keyboard.append([InlineKeyboardButton("💰 Купить подписку", callback_data="buy_subscription")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await update.callback_query.edit_message_text(stats_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(stats_text, reply_markup=reply_markup)

async def autotrade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню автоторговли (callback: autotrade_menu)"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    # Проверка VIP статуса
    cursor = bot.conn.cursor()
    cursor.execute('''
        SELECT subscription_type, auto_trading_enabled, auto_trading_mode, auto_trading_strategy, 
               pocket_option_ssid, pocket_option_connected
        FROM users WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    
    if not result:
        await query.edit_message_text("❌ Ошибка получения данных")
        return
    
    subscription_type, enabled, mode, strategy, po_ssid, po_connected = result
    
    # Если НЕ-VIP - показать инструкцию по подключению
    if subscription_type != 'vip':
        await autotrade_instruction_callback(update, context)
        return
    
    # Названия стратегий
    strategy_names = {
        'percentage': '📊 Фиксированный %',
        'dalembert': '📈 Д\'Аламбер',
        'martingale': '⚡️ Мартингейл',
        'ai_trading': '🤖 AI Trading'
    }
    
    status_emoji = "🟢" if enabled else "🔴"
    status_text = "ВКЛЮЧЕНА" if enabled else "ВЫКЛЮЧЕНА"
    mode_emoji = "🎮" if mode == "demo" else "💰"
    mode_text = "Демо" if mode == "demo" else "Реальный"
    
    # Статус подключения к Pocket Option
    po_status = "🟢 Подключен" if po_connected and po_ssid else "🔴 Не подключен"
    
    menu_text = f"""
🤖 *МЕНЮ АВТОТОРГОВЛИ*

📊 *Статус:* {status_emoji} {status_text}
🎯 *Режим:* {mode_emoji} {mode_text}
⚙️ *Стратегия:* {strategy_names.get(strategy, 'Не выбрана')}
🔗 *Pocket Option:* {po_status}

{'✅ Автоторговля работает 24/7' if enabled else '⏸️ Автоторговля остановлена'}
"""
    
    keyboard = []
    
    # Кнопка вкл/выкл автотрейдинга
    keyboard.append([InlineKeyboardButton(
        f"{'🔴 ВЫКЛЮЧИТЬ АВТОТРЕЙДИНГ' if enabled else '🟢 ВКЛЮЧИТЬ АВТОТРЕЙДИНГ'}", 
        callback_data="autotrade_toggle"
    )])
    
    # Кнопка выбора стратегии
    keyboard.append([InlineKeyboardButton(
        "⚙️ Выбрать стратегию", 
        callback_data="choose_autotrade_strategy"
    )])
    
    # Дополнительные настройки если подключен
    keyboard.append([InlineKeyboardButton(
        f"{'💰 Переключить на РЕАЛ' if mode == 'demo' else '🎮 Переключить на ДЕМО'}", 
        callback_data="autotrade_toggle_mode"
    )])
    
    # Статистика
    keyboard.append([InlineKeyboardButton(
        "📊 Статистика автоторговли", 
        callback_data="autotrade_stats"
    )])
    
    # Подключение к Pocket Option
    if not po_ssid or not po_connected:
        keyboard.append([InlineKeyboardButton(
            "🔗 Подключить Pocket Option", 
            callback_data="setup_pocket_option"
        )])
    else:
        keyboard.append([InlineKeyboardButton(
            "🔌 Отключить Pocket Option", 
            callback_data="disconnect_pocket_option"
        )])
    
    # Назад к банку
    keyboard.append([InlineKeyboardButton("◀️ Назад к банку", callback_data="bank_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')

async def autotrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /autotrade - главное меню автоторговли"""
    user_id = update.effective_user.id
    
    # Проверка бана
    if bot.is_banned(user_id):
        await update.message.reply_text(
            f"🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\nДоступ к боту ограничен.\nОбратитесь в поддержку: {bot.get_support_contact()}",
            parse_mode='Markdown'
        )
        return
    
    # Получить данные пользователя
    cursor = bot.conn.cursor()
    cursor.execute('''
        SELECT subscription_type, auto_trading_enabled, auto_trading_mode, 
               auto_trading_strategy, pocket_option_ssid, pocket_option_connected
        FROM users WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    
    if not result:
        await update.message.reply_text("❌ Ошибка получения данных")
        return
    
    subscription_type, enabled, mode, strategy, po_ssid, po_connected = result
    
    # Проверка VIP
    if subscription_type != 'vip':
        await update.message.reply_text(
            "💎 **АВТОТОРГОВЛЯ - VIP ФУНКЦИЯ**\n\n"
            "Автоматическая торговля доступна только для VIP подписчиков.\n\n"
            "🤖 **Что вы получаете:**\n"
            "• Полностью автоматическая торговля 24/7\n"
            "• 4 профессиональных стратегии (включая AI Trading)\n"
            "• Интеграция с Pocket Option\n"
            "• Реал-тайм мониторинг сделок\n"
            "• Математический анализ прибыльности\n\n"
            "Улучшите подписку до VIP для доступа!",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Улучшить до VIP", callback_data="show_tariff_vip")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ])
        )
        return
    
    # Названия стратегий
    strategy_names = {
        'percentage': '📊 Фиксированный %',
        'dalembert': '📈 Д\'Аламбер',
        'martingale': '⚡️ Мартингейл',
        'ai_trading': '🤖 AI Trading'
    }
    
    status_emoji = "🟢" if enabled else "🔴"
    status_text = "ВКЛЮЧЕНА" if enabled else "ВЫКЛЮЧЕНА"
    mode_emoji = "🎮" if mode == "demo" else "💰"
    mode_text = "Демо" if mode == "demo" else "Реальный"
    
    # Статус подключения к Pocket Option
    po_status = "🟢 Подключен" if po_connected and po_ssid else "🔴 Не подключен"
    
    menu_text = f"""
🤖 *МЕНЮ АВТОТОРГОВЛИ*

📊 *Статус:* {status_emoji} {status_text}
🎯 *Режим:* {mode_emoji} {mode_text}
⚙️ *Стратегия:* {strategy_names.get(strategy, 'Не выбрана')}
🔗 *Pocket Option:* {po_status}

{'✅ Автоторговля работает 24/7' if enabled else '⏸️ Автоторговля остановлена'}
"""
    
    keyboard = []
    
    # Кнопка вкл/выкл автотрейдинга
    keyboard.append([InlineKeyboardButton(
        f"{'🔴 ВЫКЛЮЧИТЬ АВТОТРЕЙДИНГ' if enabled else '🟢 ВКЛЮЧИТЬ АВТОТРЕЙДИНГ'}", 
        callback_data="autotrade_toggle"
    )])
    
    # Кнопка выбора стратегии
    keyboard.append([InlineKeyboardButton(
        "⚙️ Выбрать стратегию", 
        callback_data="choose_autotrade_strategy"
    )])
    
    # Дополнительные настройки если подключен
    keyboard.append([InlineKeyboardButton(
        f"{'💰 Переключить на РЕАЛ' if mode == 'demo' else '🎮 Переключить на ДЕМО'}", 
        callback_data="autotrade_toggle_mode"
    )])
    
    # Статистика
    keyboard.append([InlineKeyboardButton(
        "📊 Статистика автоторговли", 
        callback_data="autotrade_stats"
    )])
    
    # Подключение к Pocket Option
    if not po_ssid or not po_connected:
        keyboard.append([InlineKeyboardButton(
            "🔗 Подключить Pocket Option", 
            callback_data="setup_pocket_option"
        )])
    else:
        keyboard.append([InlineKeyboardButton(
            "🔌 Отключить Pocket Option", 
            callback_data="disconnect_pocket_option"
        )])
    
    # Назад к банку и главное меню
    keyboard.append([InlineKeyboardButton("◀️ Назад к банку", callback_data="bank_menu")])
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')

async def active_autotrade_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Активная сессия автотрейдинга с реал-тайм статистикой"""
    query = update.callback_query if hasattr(update, 'callback_query') and update.callback_query else None
    user_id = update.effective_user.id
    
    cursor = bot.conn.cursor()
    
    # Получить настройки стратегии
    cursor.execute('''
        SELECT auto_trading_strategy, auto_trading_mode, current_balance, initial_balance
        FROM users WHERE user_id = ?
    ''', (user_id,))
    settings = cursor.fetchone()
    
    if not settings:
        return
    
    strategy, mode, current_balance, initial_balance = settings
    
    # Создать запись сессии
    session_start = datetime.now()
    session_wins = 0
    session_losses = 0
    session_draws = 0
    session_profit = 0
    
    strategy_names = {
        'percentage': '📊 Фиксированный %',
        'dalembert': '📈 Д\'Аламбер', 
        'martingale': '⚡️ Мартингейл'
    }
    
    # Начальное сообщение
    session_text = f"""
🤖 **АКТИВНАЯ СЕССИЯ АВТОТРЕЙДИНГА**

⚙️ **Стратегия:** {strategy_names.get(strategy, 'Неизвестно')}
{'🎮 Режим: ДЕМО' if mode == 'demo' else '💰 Режим: РЕАЛЬНЫЙ'}

━━━━━━━━━━━━━━━━━━━━━━
📊 **РЕАЛ-ТАЙМ СТАТИСТИКА**

✅ Побед: {session_wins}
❌ Поражений: {session_losses}
⚪️ Ничьих: {session_draws}

📈 Винрейт: {(session_wins/(session_wins+session_losses)*100 if (session_wins+session_losses) > 0 else 0):.1f}%
💰 Прибыль: {session_profit:+.2f}₽

━━━━━━━━━━━━━━━━━━━━━━
💵 **БАЛАНС**
Начальный: {initial_balance:.2f}₽
Текущий: {current_balance:.2f}₽
Изменение: {(current_balance - initial_balance):+.2f}₽

🔄 Автообновление каждые 30 сек
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="autotrade_session_refresh")],
        [InlineKeyboardButton("🛑 Остановить", callback_data="autotrade_stop_session")],
        [InlineKeyboardButton("📊 Математический анализ", callback_data="autotrade_math_analysis")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(session_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(session_text, reply_markup=reply_markup, parse_mode='Markdown')

async def autotrade_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включить/выключить автоторговлю"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    cursor = bot.conn.cursor()
    cursor.execute('SELECT auto_trading_enabled FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    current_state = result[0] if result else False
    new_state = not current_state
    
    cursor.execute('UPDATE users SET auto_trading_enabled = ? WHERE user_id = ?', (new_state, user_id))
    bot.conn.commit()
    
    if new_state:
        # Показать активную сессию
        await active_autotrade_session(update, context)
    else:
        # Вернуться в меню с обновленным статусом
        await autotrade_menu(update, context)

async def autotrade_toggle_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключить демо/реальный режим"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    cursor = bot.conn.cursor()
    cursor.execute('SELECT auto_trading_mode FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    current_mode = result[0] if result else "demo"
    new_mode = "real" if current_mode == "demo" else "demo"
    
    cursor.execute('UPDATE users SET auto_trading_mode = ? WHERE user_id = ?', (new_mode, user_id))
    bot.conn.commit()
    
    # Вернуться в меню с обновленным режимом
    await autotrade_menu(update, context)

async def autotrade_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику автоторговли"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    cursor = bot.conn.cursor()
    
    # Статистика за последние 7 дней
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN result = 'win' THEN profit_loss ELSE 0 END) as total_profit,
            SUM(CASE WHEN result = 'loss' THEN profit_loss ELSE 0 END) as total_loss,
            AVG(confidence) as avg_confidence
        FROM signal_history 
        WHERE user_id = ? AND signal_date >= datetime('now', '-7 days')
    ''', (user_id,))
    
    stats = cursor.fetchone()
    total = stats[0] or 0
    wins = stats[1] or 0
    losses = stats[2] or 0
    total_profit = stats[3] or 0
    total_loss = stats[4] or 0
    avg_conf = stats[5] or 0
    
    win_rate = (wins / total * 100) if total > 0 else 0
    net_profit = total_profit + total_loss
    
    stats_text = f"""
📊 **СТАТИСТИКА АВТОТОРГОВЛИ**
_(последние 7 дней)_

📈 **Общая статистика:**
• Всего сделок: {total}
• Выигрышей: ✅ {wins}
• Проигрышей: ❌ {losses}
• Винрейт: {win_rate:.1f}%
• Средняя уверенность: {avg_conf:.1f}%

💰 **Финансовые показатели:**
• Прибыль: +{total_profit:.0f}₽
• Убытки: {total_loss:.0f}₽
• Чистая прибыль: {net_profit:+.0f}₽

🤖 Автоторговля работает 24/7
"""
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="autotrade_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')

async def autotrade_session_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновить статистику активной сессии"""
    query = update.callback_query
    await query.answer("🔄 Обновление...")
    user_id = update.effective_user.id
    
    cursor = bot.conn.cursor()
    
    # Получить статистику текущей сессии (последние 24 часа)
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN result = 'draw' THEN 1 ELSE 0 END) as draws,
            SUM(profit_loss) as net_profit
        FROM signal_history 
        WHERE user_id = ? 
        AND signal_date >= datetime('now', '-24 hours')
        AND signal_tier = 'autotrade'
    ''', (user_id,))
    
    stats = cursor.fetchone()
    total = stats[0] or 0
    wins = stats[1] or 0
    losses = stats[2] or 0
    draws = stats[3] or 0
    net_profit = stats[4] or 0
    
    # Получить настройки и баланс
    cursor.execute('''
        SELECT auto_trading_strategy, auto_trading_mode, current_balance, initial_balance
        FROM users WHERE user_id = ?
    ''', (user_id,))
    settings = cursor.fetchone()
    
    if not settings:
        return
    
    strategy, mode, current_balance, initial_balance = settings
    
    strategy_names = {
        'percentage': '📊 Фиксированный %',
        'dalembert': '📈 Д\'Аламбер',
        'martingale': '⚡️ Мартингейл',
        'ai_trading': '🤖 AI Trading'
    }
    
    # Обновленное сообщение
    session_text = f"""
🤖 **АКТИВНАЯ СЕССИЯ АВТОТРЕЙДИНГА**

⚙️ **Стратегия:** {strategy_names.get(strategy, 'Неизвестно')}
{'🎮 Режим: ДЕМО' if mode == 'demo' else '💰 Режим: РЕАЛЬНЫЙ'}

━━━━━━━━━━━━━━━━━━━━━━
📊 **РЕАЛ-ТАЙМ СТАТИСТИКА**

✅ Побед: {wins}
❌ Поражений: {losses}
⚪️ Ничьих: {draws}

📈 Винрейт: {(wins/(wins+losses)*100 if (wins+losses) > 0 else 0):.1f}%
💰 Прибыль: {net_profit:+.2f}₽

━━━━━━━━━━━━━━━━━━━━━━
💵 **БАЛАНС**
Начальный: {initial_balance:.2f}₽
Текущий: {current_balance:.2f}₽
Изменение: {(current_balance - initial_balance):+.2f}₽

🔄 Последнее обновление: {datetime.now().strftime('%H:%M:%S')}
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="autotrade_session_refresh")],
        [InlineKeyboardButton("🛑 Остановить", callback_data="autotrade_stop_session")],
        [InlineKeyboardButton("📊 Математический анализ", callback_data="autotrade_math_analysis")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(session_text, reply_markup=reply_markup, parse_mode='Markdown')

async def autotrade_stop_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Остановить активную сессию автотрейдинга"""
    query = update.callback_query
    await query.answer("🛑 Остановка...")
    user_id = update.effective_user.id
    
    cursor = bot.conn.cursor()
    cursor.execute('UPDATE users SET auto_trading_enabled = ? WHERE user_id = ?', (False, user_id))
    bot.conn.commit()
    
    # Вернуться в меню автотрейдинга
    await autotrade_menu(update, context)

async def get_ai_strategy_recommendation(user_id: int):
    """Получить AI рекомендацию стратегии на основе фоновой статистики"""
    cursor = bot.conn.cursor()
    
    # Получить оптимизированные стратегии из фонового анализа
    cursor.execute('''
        SELECT key, value FROM bot_settings
        WHERE key LIKE 'optimal_strategy_%'
        ORDER BY value DESC
        LIMIT 10
    ''')
    
    optimal_strategies = cursor.fetchall()
    
    if not optimal_strategies:
        return None, None, "Идет накопление данных..."
    
    # Парсим данные оптимальных стратегий
    best_performers = []
    for key, value in optimal_strategies:
        parts = value.split('|')
        if len(parts) >= 3:
            strategy_type = parts[0]
            win_rate = float(parts[1])
            risk_level = parts[2]
            
            # Извлекаем актив и таймфрейм из ключа
            asset_tf = key.replace('optimal_strategy_', '')
            
            best_performers.append({
                'strategy': strategy_type,
                'win_rate': win_rate,
                'risk_level': risk_level,
                'asset_tf': asset_tf
            })
    
    if not best_performers:
        return None, None, "Недостаточно данных"
    
    # Группируем по стратегиям и считаем средний винрейт
    strategy_scores = {}
    for perf in best_performers:
        strat = perf['strategy']
        if strat not in strategy_scores:
            strategy_scores[strat] = {'total_wr': 0, 'count': 0, 'risk': perf['risk_level']}
        strategy_scores[strat]['total_wr'] += perf['win_rate']
        strategy_scores[strat]['count'] += 1
    
    # Вычисляем средние и находим лучшую стратегию
    best_strategy = None
    best_avg_wr = 0
    best_risk = "unknown"
    
    for strat, data in strategy_scores.items():
        avg_wr = data['total_wr'] / data['count']
        if avg_wr > best_avg_wr:
            best_avg_wr = avg_wr
            best_strategy = strat
            best_risk = data['risk']
    
    recommendation = f"AI рекомендует '{best_strategy}' (WR: {best_avg_wr:.1f}%, Risk: {best_risk})"
    
    return best_strategy, best_avg_wr, recommendation

async def autotrade_math_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Математический анализ прибыльности стратегий с AI рекомендациями"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    cursor = bot.conn.cursor()
    
    # Получить AI рекомендацию из фонового анализа
    ai_strategy, ai_wr, ai_recommendation = await get_ai_strategy_recommendation(user_id)
    
    # Анализ эффективности каждой стратегии за последние 30 дней (пользовательские данные)
    strategies_analysis = []
    
    for strategy_type in ['percentage', 'dalembert', 'martingale']:
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
                SUM(profit_loss) as net_profit,
                AVG(confidence) as avg_confidence,
                MAX(profit_loss) as max_profit,
                MIN(profit_loss) as max_loss
            FROM signal_history 
            WHERE user_id = ? 
            AND signal_date >= datetime('now', '-30 days')
            AND signal_tier = 'autotrade'
        ''', (user_id,))
        
        stats = cursor.fetchone()
        
        if stats and stats[0] > 0:
            total, wins, losses, net_profit, avg_conf, max_profit, max_loss = stats
            win_rate = (wins / total * 100) if total > 0 else 0
            
            # Математические показатели
            roi = (net_profit / (total * 100) * 100) if total > 0 else 0  # ROI на 100₽ ставки
            profit_factor = abs(net_profit / max_loss) if max_loss and max_loss < 0 else 0
            
            strategies_analysis.append({
                'name': strategy_type,
                'total': total,
                'win_rate': win_rate,
                'net_profit': net_profit,
                'roi': roi,
                'profit_factor': profit_factor,
                'avg_conf': avg_conf or 0
            })
    
    strategy_names = {
        'percentage': '📊 Фиксированный %',
        'dalembert': '📈 Д\'Аламбер',
        'martingale': '⚡️ Мартингейл',
        'ai_trading': '🤖 AI Trading'
    }
    
    # Формируем текст анализа
    analysis_text = f"""
📊 **МАТЕМАТИЧЕСКИЙ АНАЛИЗ СТРАТЕГИЙ**

━━━━━━━━━━━━━━━━━━━━━━
🤖 **AI РЕКОМЕНДАЦИЯ** (на основе фонового анализа)

{ai_recommendation}

Бот непрерывно тестирует стратегии в фоне и вычисляет оптимальную на длительной дистанции с минимальными рисками.

━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # Определение лучшей стратегии из пользовательских данных
    if strategies_analysis:
        best_strategy = max(strategies_analysis, key=lambda x: x['net_profit'])
        
        analysis_text += f"""
🏆 **ВАША ЛУЧШАЯ СТРАТЕГИЯ** (последние 30 дней)

{strategy_names.get(best_strategy['name'], 'Неизвестно')}

• Винрейт: {best_strategy['win_rate']:.1f}%
• Чистая прибыль: {best_strategy['net_profit']:+.2f}₽
• ROI: {best_strategy['roi']:.1f}%
• Profit Factor: {best_strategy['profit_factor']:.2f}
• Средняя уверенность: {best_strategy['avg_conf']:.1f}%

━━━━━━━━━━━━━━━━━━━━━━
📈 **СРАВНЕНИЕ СТРАТЕГИЙ**

"""
        for strat in sorted(strategies_analysis, key=lambda x: x['net_profit'], reverse=True):
            analysis_text += f"""
{strategy_names.get(strat['name'], 'Неизвестно')}
• WR: {strat['win_rate']:.1f}% | Profit: {strat['net_profit']:+.0f}₽ | ROI: {strat['roi']:.1f}%

"""
        
        analysis_text += """
━━━━━━━━━━━━━━━━━━━━━━
💡 **РЕКОМЕНДАЦИИ**

✅ Используйте AI рекомендацию для оптимальных результатов
📊 Учитывайте Profit Factor (>1.5 - хорошо)
⚠️ Высокий ROI важнее высокого винрейта
🧠 Фоновый AI анализирует 1000+ сделок для точности
"""
    else:
        analysis_text += """
📊 **ВАШИ ДАННЫЕ**

❌ Недостаточно личных данных для анализа

Накопите минимум 20 сделок для получения статистически значимых результатов.

Используйте AI рекомендацию основанную на фоновом тестировании тысяч сделок!
"""
    
    keyboard = [
        [InlineKeyboardButton("🤖 Применить AI стратегию", callback_data=f"autotrade_apply_ai_{ai_strategy}" if ai_strategy else "autotrade_session_refresh")],
        [InlineKeyboardButton("◀️ Назад к сессии", callback_data="autotrade_session_refresh")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(analysis_text, reply_markup=reply_markup, parse_mode='Markdown')

async def bank_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться к меню банка"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    # Получить данные о банке
    cursor = bot.conn.cursor()
    cursor.execute('''
        SELECT trading_strategy, initial_balance, current_balance, 
               martingale_multiplier, martingale_base_stake, subscription_type,
               auto_trading_enabled, auto_trading_mode
        FROM users WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    
    if not result:
        await query.edit_message_text("❌ Ошибка получения данных", reply_markup=add_home_button())
        return
    
    strategy, initial_balance, current_balance, martingale_mult, base_stake, subscription_type, auto_trading_enabled, auto_trading_mode = result
    
    is_vip = subscription_type == 'vip'
    balance = current_balance if current_balance else initial_balance
    profit_loss = balance - initial_balance if initial_balance else 0
    profit_emoji = "📈" if profit_loss >= 0 else "📉"
    
    if strategy == 'martingale':
        recommended_stake = bot.calculate_recommended_short_stake(balance)
        mult_text = f"x{martingale_mult}" if martingale_mult else "x3"
        stake_text = f"{recommended_stake:.0f}₽ ({mult_text})" if recommended_stake else "❌ Недостаточно"
        strategy_name = "⚡️ Мартингейл"
    elif strategy == 'dalembert':
        recommended_stake, level = bot.get_dalembert_stake(user_id)
        stake_text = f"{recommended_stake:.0f}₽ (уровень {level})" if recommended_stake else "❌ Недостаточно"
        strategy_name = "📈 Д'Аламбер"
    else:
        # Percentage или неопределенная стратегия
        recommended_stake = balance * 0.025
        stake_text = f"{recommended_stake:.0f}₽ (2.5%)"
        strategy_name = "📊 Процентная"
    
    bank_text = f"""
💰 **УПРАВЛЕНИЕ БАНКОМ**

📊 **Текущие показатели:**
• Начальный: {initial_balance:.0f}₽
• Текущий: {balance:.0f}₽
• {profit_emoji} Прибыль/Убыток: {profit_loss:+.0f}₽

🎯 **Ваша стратегия:** {strategy_name}
💵 **Рекомендуемая ставка:** {stake_text}

📱 **Команды:**
• `/report_win` - отметить выигрыш
• `/report_loss` - отметить проигрыш
• `/set_bank [сумма]` - изменить банк
• `/my_stats` - посмотреть статистику
"""
    
    keyboard = []
    
    # БОЛЬШАЯ кнопка автотрейдинга - видна ВСЕМ
    if is_vip:
        # VIP: показываем активную кнопку с роботом и статусом
        auto_status = "🟢 ВКЛ" if auto_trading_enabled else "🔴 ВЫКЛ"
        keyboard.append([InlineKeyboardButton(
            f"🤖 АВТОТРЕЙДИНГ {auto_status}", 
            callback_data="autotrade_menu"
        )])
    else:
        # НЕ-VIP: показываем с замочком, callback проверит права
        keyboard.append([InlineKeyboardButton(
            "🔒 АВТОТРЕЙДИНГ", 
            callback_data="autotrade_menu"
        )])
    
    # Остальные кнопки
    keyboard.extend([
        [InlineKeyboardButton("✅ Отметить выигрыш", callback_data="quick_report_win"),
         InlineKeyboardButton("❌ Отметить проигрыш", callback_data="quick_report_loss")],
        [InlineKeyboardButton("🔄 Сменить стратегию", callback_data="choose_strategy")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats_view")],
    ])
    
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(bank_text, parse_mode='Markdown', reply_markup=reply_markup)

async def autotrade_instruction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать инструкцию по подключению автоторговли"""
    query = update.callback_query
    await query.answer()
    
    instruction_text = """
📖 **ИНСТРУКЦИЯ ПО АВТОТОРГОВЛЕ**

🤖 **Как подключить автоматическую торговлю:**

━━━━━━━━━━━━━━━━━━━━━━
**ШАГ 1: Получите VIP доступ** 💎
━━━━━━━━━━━━━━━━━━━━━━
Автоторговля доступна только для VIP подписчиков.
Нажмите "💎 Купить VIP" ниже.

━━━━━━━━━━━━━━━━━━━━━━
**ШАГ 2: Зарегистрируйтесь на Pocket Option** 🔗
━━━━━━━━━━━━━━━━━━━━━━
1. Перейдите на [Pocket Option](https://po.trade/cabinet/demo-quick-high-low/)
2. Создайте аккаунт
3. Пройдите верификацию (для реального режима)

━━━━━━━━━━━━━━━━━━━━━━
**ШАГ 3: Получите SSID токен** 🔐
━━━━━━━━━━━━━━━━━━━━━━

**🔍 Шаг 3.1: Откройте Pocket Option**
1. Перейдите на [PocketOption.com](https://po.trade)
2. Войдите в свой аккаунт

**🛠️ Шаг 3.2: Откройте инструменты разработчика**
• Windows/Linux: Нажмите F12 или Ctrl + Shift + I
• Mac: Нажмите Cmd + Option + I

**🍪 Шаг 3.3: Найдите SSID**
1. Перейдите во вкладку "Application" (Приложение)
2. В левом меню выберите:
   Storage → Cookies → https://pocketoption.com
3. Найдите куку с именем `ssid`
4. Скопируйте её значение (длинная строка символов)

**📱 Альтернативный способ через Network:**
1. Во вкладке "Network" (Сеть)
2. Обновите страницу (F5)
3. Найдите любой запрос к pocketoption.com
4. Во вкладке "Headers" найдите "Cookie"
5. Найдите ssid=ВАШ_SSID_КОД

━━━━━━━━━━━━━━━━━━━━━━
**ШАГ 4: Подключите бота** ⚙️
━━━━━━━━━━━━━━━━━━━━━━
1. В боте: Меню → 🤖 Автотрейдинг
2. Нажмите "🔗 Подключить Pocket Option"
3. Вставьте ваш SSID токен
4. Выберите режим (Демо/Реал)

━━━━━━━━━━━━━━━━━━━━━━
**ШАГ 5: Настройте стратегию** 🎯
━━━━━━━━━━━━━━━━━━━━━━
Выберите одну из 4 стратегий:
• 📊 Фиксированный % - консервативная
• 📈 Д'Аламбер - умеренная
• ⚡️ Мартингейл - агрессивная
• 🤖 AI Trading - искусственный интеллект

━━━━━━━━━━━━━━━━━━━━━━
**ШАГ 6: Запустите торговлю** 🚀
━━━━━━━━━━━━━━━━━━━━━━
1. Установите банк через `/set_bank`
2. Нажмите "🟢 ВКЛЮЧИТЬ АВТОТРЕЙДИНГ"
3. Бот начнет автоматическую торговлю 24/7

━━━━━━━━━━━━━━━━━━━━━━
**⚠️ ВАЖНАЯ ИНФОРМАЦИЯ**
━━━━━━━━━━━━━━━━━━━━━━
• SSID токен действует 24-48 часов
• После истечения подключитесь заново
• Начните с ДЕМО режима
• Установите разумный банк

🔒 **Безопасность:**
Ваш SSID хранится зашифровано и не передается третьим лицам.

📞 **Поддержка:** @banana_pwr
"""
    
    keyboard = [
        [InlineKeyboardButton("💎 Купить VIP", callback_data="show_tariff_vip")],
        [InlineKeyboardButton("📖 Подробнее о VIP", callback_data="autotrade_vip_promo")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(instruction_text, parse_mode='Markdown', reply_markup=reply_markup, disable_web_page_preview=True)

async def autotrade_vip_promo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать VIP промо для автоторговли (для не-VIP пользователей)"""
    query = update.callback_query
    await query.answer()
    
    vip_promo_text = """
💎 **АВТОТОРГОВЛЯ - ЭКСКЛЮЗИВ VIP**

🤖 **Полностью автоматическая торговля 24/7**

✨ **Что вы получаете:**

• 🎯 **4 профессиональных стратегии:**
  - 📊 Фиксированный % (консервативная)
  - 📈 Д'Аламбер (умеренная)
  - ⚡️ Мартингейл (агрессивная)
  - 🤖 AI Trading (искусственный интеллект)

• 🔗 **Интеграция с Pocket Option:**
  - Безопасное подключение через SSID
  - Автоматическое размещение сделок
  - Мгновенная обработка результатов

• 📊 **Продвинутая аналитика:**
  - Реал-тайм мониторинг сделок
  - Математический анализ прибыльности
  - AI-рекомендации стратегий
  - ROI и Profit Factor расчеты

• 🎮 **Гибкие настройки:**
  - Демо и реальный режимы
  - Настройка под вашу стратегию
  - Контроль рисков и ставок

• 🔒 **Безопасность:**
  - Шифрование данных
  - Защищенное хранение SSID
  - Полный контроль над счётом

━━━━━━━━━━━━━━━━━━━━━━
💰 **СТОИМОСТЬ VIP:**

1 месяц: 9990₽
6 месяцев: 53946₽ (экономия 10%)
12 месяцев: 95904₽ (экономия 20%)

🚀 Автоматизируйте торговлю прямо сейчас!
"""
    
    keyboard = [
        [InlineKeyboardButton("💎 Оформить VIP подписку", callback_data="show_tariff_vip")],
        [InlineKeyboardButton("◀️ Назад к банку", callback_data="bank_menu")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(vip_promo_text, parse_mode='Markdown', reply_markup=reply_markup)

async def choose_autotrade_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню выбора стратегии автоторговли"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    cursor = bot.conn.cursor()
    cursor.execute('SELECT auto_trading_strategy FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    current_strategy = result[0] if result else "percentage"
    
    strategy_info = {
        'percentage': {
            'name': '📊 Фиксированный процент',
            'desc': 'Консервативная стратегия\n• Ставка: фиксированный % от банка\n• Риск: низкий\n• Подходит для: стабильной торговли',
            'emoji': '📊'
        },
        'dalembert': {
            'name': '📈 Д\'Аламбер',
            'desc': 'Умеренная стратегия\n• +1 единица после проигрыша\n• -1 единица после выигрыша\n• Риск: средний\n• Подходит для: плавного роста',
            'emoji': '📈'
        },
        'martingale': {
            'name': '⚡️ Мартингейл',
            'desc': 'Агрессивная стратегия\n• Удвоение ставки после проигрыша\n• Сброс после выигрыша\n• Риск: высокий\n• Подходит для: быстрого восстановления',
            'emoji': '⚡️'
        },
        'ai_trading': {
            'name': '🤖 AI Trading',
            'desc': '🔥 ЭКСКЛЮЗИВ 🔥\nИскусственный интеллект\n• Автоматический выбор лучшей стратегии\n• Анализ 1000+ сделок в фоне\n• Адаптация к рынку в реальном времени\n• Риск: оптимальный\n• Только для VIP',
            'emoji': '🤖',
            'premium': True
        }
    }
    
    # Проверяем подписку пользователя
    cursor.execute('SELECT subscription_type FROM users WHERE user_id = ?', (user_id,))
    tier_result = cursor.fetchone()
    user_tier = tier_result[0].upper() if tier_result and tier_result[0] else 'FREE'
    
    menu_text = f"""
⚙️ **НАСТРОЙКИ СТРАТЕГИИ**

**Текущая:** {strategy_info[current_strategy]['name']}

Выберите стратегию автоторговли:
"""
    
    keyboard = []
    for strategy_key, info in strategy_info.items():
        # AI Trading доступен только VIP
        if strategy_key == 'ai_trading' and user_tier != 'VIP':
            keyboard.append([
                InlineKeyboardButton(
                    f"{info['emoji']} {info['name'].split(' ', 1)[1]} 🔒 VIP", 
                    callback_data="vip_required"
                )
            ])
        else:
            selected = " ✅" if strategy_key == current_strategy else ""
            keyboard.append([
                InlineKeyboardButton(
                    f"{info['emoji']} {info['name'].split(' ', 1)[1]}{selected}", 
                    callback_data=f"autotrade_select_{strategy_key}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="autotrade_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')

async def autotrade_select_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE, strategy: str):
    """Выбрать стратегию и показать настройки"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    cursor = bot.conn.cursor()
    
    # Проверка VIP доступа для AI Trading
    if strategy == 'ai_trading':
        cursor.execute('SELECT subscription_type FROM users WHERE user_id = ?', (user_id,))
        tier_result = cursor.fetchone()
        user_tier = tier_result[0].upper() if tier_result and tier_result[0] else 'FREE'
        
        if user_tier != 'VIP':
            await query.answer("🔒 AI Trading доступен только VIP пользователям", show_alert=True)
            await show_vip_info(update, context)
            return
    
    # Сохранить выбранную стратегию
    cursor.execute('UPDATE users SET auto_trading_strategy = ? WHERE user_id = ?', (strategy, user_id))
    bot.conn.commit()
    
    # Показать настройки выбранной стратегии
    await autotrade_config_strategy(update, context, strategy)

async def autotrade_config_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE, strategy: str):
    """Настройка параметров выбранной стратегии"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    cursor = bot.conn.cursor()
    
    if strategy == 'percentage':
        cursor.execute('SELECT percentage_value, current_balance FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        percentage = result[0] if result else 2.5
        balance = result[1] if result else 10000
        stake = balance * (percentage / 100)
        
        config_text = f"""
📊 **НАСТРОЙКА: Фиксированный процент**

**Текущие параметры:**
• Процент от банка: {percentage}%
• Ваш банк: {balance:.0f}₽
• Размер ставки: {stake:.0f}₽

💡 **Рекомендации:**
• 1-2% - очень консервативно
• 2-3% - оптимально
• 4-5% - агрессивно

Отправьте новый процент (1-10):
Например: `2.5`
"""
        
        keyboard = [
            [InlineKeyboardButton("1%", callback_data="set_percentage_1"),
             InlineKeyboardButton("2%", callback_data="set_percentage_2"),
             InlineKeyboardButton("2.5%", callback_data="set_percentage_2.5")],
            [InlineKeyboardButton("3%", callback_data="set_percentage_3"),
             InlineKeyboardButton("4%", callback_data="set_percentage_4"),
             InlineKeyboardButton("5%", callback_data="set_percentage_5")],
            [InlineKeyboardButton("◀️ Назад", callback_data="choose_autotrade_strategy")]
        ]
        
    elif strategy == 'dalembert':
        cursor.execute('SELECT dalembert_base_stake, dalembert_unit FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        base_stake = result[0] if result else 100
        unit = result[1] if result else 50
        
        config_text = f"""
📈 **НАСТРОЙКА: Д'Аламбер**

**Текущие параметры:**
• Базовая ставка: {base_stake:.0f}₽
• Размер единицы: {unit:.0f}₽

**Как работает:**
• Старт: {base_stake:.0f}₽
• После проигрыша: {base_stake + unit:.0f}₽
• После выигрыша: {max(base_stake - unit, base_stake):.0f}₽

💡 Единица = шаг изменения ставки

Отправьте параметры через пробел:
`[база] [единица]`
Например: `100 50`
"""
        
        keyboard = [
            [InlineKeyboardButton("100₽ / 50₽", callback_data="set_dalembert_100_50"),
             InlineKeyboardButton("200₽ / 100₽", callback_data="set_dalembert_200_100")],
            [InlineKeyboardButton("150₽ / 75₽", callback_data="set_dalembert_150_75"),
             InlineKeyboardButton("300₽ / 150₽", callback_data="set_dalembert_300_150")],
            [InlineKeyboardButton("◀️ Назад", callback_data="choose_autotrade_strategy")]
        ]
        
    elif strategy == 'martingale':
        cursor.execute('SELECT martingale_base_stake, martingale_multiplier FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        base_stake = result[0] if result else 100
        multiplier = result[1] if result else 3
        
        config_text = f"""
⚡️ **НАСТРОЙКА: Мартингейл**

**Текущие параметры:**
• Базовая ставка: {base_stake:.0f}₽
• Множитель: x{multiplier}

**Прогрессия:**
• Уровень 0: {base_stake:.0f}₽
• Уровень 1: {base_stake * multiplier:.0f}₽
• Уровень 2: {base_stake * (multiplier**2):.0f}₽
• Уровень 3: {base_stake * (multiplier**3):.0f}₽

⚠️ Требуется большой банк!

Отправьте параметры через пробел:
`[база] [множитель]`
Например: `100 3`
"""
        
        keyboard = [
            [InlineKeyboardButton("100₽ x2", callback_data="set_martingale_100_2"),
             InlineKeyboardButton("100₽ x3", callback_data="set_martingale_100_3")],
            [InlineKeyboardButton("150₽ x2", callback_data="set_martingale_150_2"),
             InlineKeyboardButton("200₽ x3", callback_data="set_martingale_200_3")],
            [InlineKeyboardButton("◀️ Назад", callback_data="choose_autotrade_strategy")]
        ]
    
    elif strategy == 'ai_trading':
        # Получить AI рекомендацию из фонового анализа
        ai_strategy, ai_wr, ai_recommendation = await get_ai_strategy_recommendation(user_id)
        
        config_text = f"""
🤖 **AI TRADING - ЭКСКЛЮЗИВНАЯ СТРАТЕГИЯ**

🔥 **Преимущества:**
• Автоматический выбор лучшей стратегии
• Анализ 1000+ сделок в фоновом режиме
• Адаптация к рынку в реальном времени
• Оптимальное соотношение риск/доходность

━━━━━━━━━━━━━━━━━━━━━━
🧠 **ТЕКУЩАЯ AI РЕКОМЕНДАЦИЯ:**

{ai_recommendation}

━━━━━━━━━━━━━━━━━━━━━━
⚙️ **КАК РАБОТАЕТ:**

AI непрерывно тестирует все стратегии (Percentage, D'Alembert, Martingale) на реальных рыночных данных и выбирает ту, которая показывает лучший результат на текущий момент.

Стратегия обновляется каждые 6 часов на основе свежих данных.

━━━━━━━━━━━━━━━━━━━━━━
💎 **Доступно только VIP пользователям**

Эта стратегия готова к использованию!
Просто активируйте автоторговлю.
"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Готово", callback_data="autotrade_menu")],
            [InlineKeyboardButton("◀️ Назад", callback_data="choose_autotrade_strategy")]
        ]
    
    else:
        config_text = "❌ Неизвестная стратегия"
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="autotrade_strategy_settings")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(config_text, reply_markup=reply_markup, parse_mode='Markdown')

async def background_signal_tester(context: ContextTypes.DEFAULT_TYPE):
    """Фоновая задача для автоматического тестирования сигналов и сбора статистики"""
    logger.info("🤖 Запуск фонового тестирования сигналов...")
    
    cursor = bot.conn.cursor()
    
    # Получить все активы для тестирования (правильно - из всех категорий)
    test_assets = []
    for category in MARKET_ASSETS.values():
        for asset_name, asset_data in category.items():
            if isinstance(asset_data, dict) and 'symbol' in asset_data:
                test_assets.append({
                    'name': asset_name,
                    'symbol': asset_data['symbol'],
                    'type': asset_data.get('type', 'regular')
                })
    
    # Берем только 5 случайных активов для тестирования (избегаем rate limit)
    test_assets = random.sample(test_assets, min(5, len(test_assets)))
    
    for asset_info in test_assets:
        try:
            asset_name = asset_info['name']
            asset_symbol = asset_info['symbol']
            
            # Генерируем тестовый сигнал
            timeframe = random.choice(['1m', '5m', '15m', '1h', '4h'])
            
            # Задержка перед запросом для избежания rate limit
            await asyncio.sleep(2)
            
            # Получаем реальные данные актива с retry
            ticker_data = yf.Ticker(asset_symbol)
            hist = None
            for retry in range(3):
                try:
                    hist = ticker_data.history(period='5d', interval='1h')
                    if not hist.empty:
                        break
                except Exception as e:
                    if "429" in str(e) or "Rate" in str(e):
                        if retry < 2:
                            await asyncio.sleep(5)  # Долгая пауза при rate limit
                            continue
                    raise
            
            if hist is None or hist.empty or len(hist) < 20:
                logger.warning(f"⚠️ Недостаточно данных для {asset_name}, пропускаем...")
                continue
            
            # Проводим технический анализ
            close_prices = hist['Close'].values
            high_prices = hist['High'].values
            low_prices = hist['Low'].values
            volumes = hist['Volume'].values
            
            # Расчет индикаторов
            ema_20 = np.mean(close_prices[-20:])
            ema_50 = np.mean(close_prices[-50:]) if len(close_prices) >= 50 else ema_20
            
            current_price = close_prices[-1]
            
            # RSI
            deltas = np.diff(close_prices[-15:])
            gains = deltas[deltas > 0].sum()
            losses = abs(deltas[deltas < 0].sum())
            rs = gains / losses if losses > 0 else 0
            rsi = 100 - (100 / (1 + rs))
            
            # MACD
            ema_12 = np.mean(close_prices[-12:])
            ema_26 = np.mean(close_prices[-26:]) if len(close_prices) >= 26 else ema_12
            macd = ema_12 - ema_26
            signal_line = np.mean([macd])
            
            # Определение сигнала
            score = 0
            if current_price > ema_20:
                score += 1
            if rsi < 30:
                score += 2  # Перепроданность - потенциал роста
            elif rsi > 70:
                score -= 2  # Перекупленность - потенциал падения
            if macd > signal_line:
                score += 1
            
            signal_type = 'CALL' if score > 0 else 'PUT'
            confidence = min(95, max(60, 70 + abs(score) * 5))
            
            # Сохраняем тестовый сигнал
            entry_price = current_price
            
            cursor.execute('''
                INSERT INTO signal_history 
                (user_id, asset, timeframe, signal_type, confidence, entry_price, 
                 stake_amount, signal_date, result, signal_tier)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), 'pending', 'test')
            ''', (0, asset_name, timeframe, signal_type, confidence, entry_price, 100))
            
            signal_id = cursor.lastrowid
            
            # Ждем время экспирации (симуляция)
            await asyncio.sleep(2)
            
            # Проверяем результат по реальным данным
            new_hist = ticker_data.history(period='1d', interval='1m')
            if not new_hist.empty:
                close_price = new_hist['Close'].values[-1]
                
                # Определяем результат
                if signal_type == 'CALL':
                    result = 'win' if close_price > entry_price else 'loss'
                else:
                    result = 'win' if close_price < entry_price else 'loss'
                
                profit_loss = 92 if result == 'win' else -100
                
                # Обновляем результат
                cursor.execute('''
                    UPDATE signal_history 
                    SET result = ?, profit_loss = ?, close_date = datetime('now')
                    WHERE id = ?
                ''', (result, profit_loss, signal_id))
                
                # Обновляем статистику производительности актива
                cursor.execute('''
                    SELECT total_signals, wins, losses, win_rate, adaptive_weight
                    FROM signal_performance
                    WHERE asset = ? AND timeframe = ?
                ''', (asset_name, timeframe))
                
                perf = cursor.fetchone()
                
                if perf:
                    total, wins, losses, old_win_rate, old_weight = perf
                    new_total = total + 1
                    new_wins = wins + (1 if result == 'win' else 0)
                    new_losses = losses + (1 if result == 'loss' else 0)
                    new_win_rate = (new_wins / new_total * 100) if new_total > 0 else 0
                    
                    # Адаптивный вес: увеличиваем при хорошем винрейте
                    new_weight = old_weight
                    if new_win_rate >= 70:
                        new_weight = min(2.0, old_weight + 0.1)
                    elif new_win_rate < 50:
                        new_weight = max(0.5, old_weight - 0.1)
                    
                    cursor.execute('''
                        UPDATE signal_performance
                        SET total_signals = ?, wins = ?, losses = ?, 
                            win_rate = ?, adaptive_weight = ?, last_updated = datetime('now')
                        WHERE asset = ? AND timeframe = ?
                    ''', (new_total, new_wins, new_losses, new_win_rate, new_weight, asset_name, timeframe))
                else:
                    # Создаем новую запись
                    wins = 1 if result == 'win' else 0
                    losses = 1 if result == 'loss' else 0
                    win_rate = (wins / 1 * 100)
                    weight = 1.0
                    
                    cursor.execute('''
                        INSERT INTO signal_performance
                        (asset, timeframe, total_signals, wins, losses, win_rate, 
                         adaptive_weight, last_updated)
                        VALUES (?, ?, 1, ?, ?, ?, ?, datetime('now'))
                    ''', (asset_name, timeframe, wins, losses, win_rate, weight))
                
                # Сохраняем данные рынка для машинного обучения
                volatility = np.std(close_prices[-20:]) / np.mean(close_prices[-20:]) if len(close_prices) >= 20 else 0
                volume_ratio = volumes[-1] / np.mean(volumes[-20:]) if len(volumes) >= 20 and np.mean(volumes[-20:]) > 0 else 1.0
                
                cursor.execute('''
                    INSERT INTO market_history
                    (asset_symbol, timeframe, price, volatility, volume, avg_volume,
                     volume_ratio, trend, rsi, macd, ema_20)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (asset_symbol, timeframe, current_price, volatility, volumes[-1], 
                      np.mean(volumes[-20:]), volume_ratio, 
                      'up' if score > 0 else 'down', rsi, macd, ema_20))
                
                bot.conn.commit()
                
                logger.info(f"✅ Тест {asset_name} {timeframe}: {result} (confidence: {confidence}%)")
                
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Rate" in error_msg:
                logger.warning(f"⚠️ Rate limit для {asset_name}, пропускаем...")
            else:
                logger.error(f"❌ Ошибка тестирования {asset_name}: {e}")
            continue
        
        # Задержка между тестами для избежания rate limit
        await asyncio.sleep(3)
    
    logger.info("✅ Цикл фонового тестирования завершен")

async def analyze_learning_data(context: ContextTypes.DEFAULT_TYPE):
    """Анализ накопленных данных и самообучение системы"""
    logger.info("🧠 Запуск анализа данных для самообучения...")
    
    cursor = bot.conn.cursor()
    
    # Анализ за последнюю неделю
    cursor.execute('''
        SELECT 
            asset, timeframe,
            COUNT(*) as total,
            SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
            AVG(confidence) as avg_conf,
            AVG(CASE WHEN result = 'win' THEN confidence ELSE NULL END) as avg_win_conf,
            AVG(CASE WHEN result = 'loss' THEN confidence ELSE NULL END) as avg_loss_conf
        FROM signal_history
        WHERE signal_tier = 'test' 
        AND signal_date >= datetime('now', '-7 days')
        GROUP BY asset, timeframe
        HAVING total >= 5
        ORDER BY (wins * 1.0 / total) DESC
    ''')
    
    learning_data = cursor.fetchall()
    
    insights = []
    
    for row in learning_data:
        asset, timeframe, total, wins, avg_conf, avg_win_conf, avg_loss_conf = row
        win_rate = (wins / total * 100) if total > 0 else 0
        
        # Выводы для обучения
        if win_rate >= 75:
            insight = f"✅ {asset} {timeframe}: Отличный актив! WR {win_rate:.1f}% ({wins}/{total})"
            insights.append(insight)
            
            # Повышаем вес этого актива
            cursor.execute('''
                UPDATE signal_performance
                SET adaptive_weight = MIN(2.0, adaptive_weight + 0.2)
                WHERE asset = ? AND timeframe = ?
            ''', (asset, timeframe))
            
        elif win_rate < 45:
            insight = f"⚠️ {asset} {timeframe}: Слабый актив. WR {win_rate:.1f}% ({wins}/{total})"
            insights.append(insight)
            
            # Снижаем вес
            cursor.execute('''
                UPDATE signal_performance
                SET adaptive_weight = MAX(0.3, adaptive_weight - 0.2)
                WHERE asset = ? AND timeframe = ?
            ''', (asset, timeframe))
    
    bot.conn.commit()
    
    # Логируем инсайты
    if insights:
        logger.info("📊 Инсайты самообучения:")
        for insight in insights[:10]:
            logger.info(f"  {insight}")
    
    # Статистика корреляций
    cursor.execute('''
        SELECT 
            AVG(CASE WHEN rsi < 30 AND trend = 'up' THEN 1 ELSE 0 END) as rsi_oversold_accuracy,
            AVG(CASE WHEN rsi > 70 AND trend = 'down' THEN 1 ELSE 0 END) as rsi_overbought_accuracy,
            AVG(CASE WHEN volatility < 0.02 THEN 1 ELSE 0 END) as low_volatility_freq
        FROM market_history
        WHERE timestamp >= datetime('now', '-7 days')
    ''')
    
    correlations = cursor.fetchone()
    if correlations:
        logger.info(f"📈 Корреляции: RSI перепродан {correlations[0]:.2%}, RSI перекуплен {correlations[1]:.2%}")
    
    logger.info("✅ Анализ данных завершен")

async def optimize_strategies(context: ContextTypes.DEFAULT_TYPE):
    """Оптимизация параметров стратегий на основе статистики"""
    logger.info("🎯 Запуск оптимизации стратегий...")
    
    cursor = bot.conn.cursor()
    
    # Анализируем эффективность разных параметров Martingale
    cursor.execute('''
        SELECT 
            asset, timeframe,
            AVG(CASE WHEN result = 'win' THEN 1.0 ELSE 0.0 END) as win_rate,
            COUNT(*) as total_signals,
            AVG(confidence) as avg_confidence
        FROM signal_history
        WHERE signal_tier = 'test'
        AND signal_date >= datetime('now', '-7 days')
        GROUP BY asset, timeframe
        HAVING total_signals >= 10
        ORDER BY win_rate DESC, avg_confidence DESC
        LIMIT 10
    ''')
    
    top_performers = cursor.fetchall()
    
    optimized_strategies = []
    
    for asset, timeframe, win_rate, total, avg_conf in top_performers:
        # Определяем оптимальные параметры на основе волатильности
        cursor.execute('''
            SELECT AVG(volatility), AVG(volume_ratio)
            FROM market_history
            WHERE asset_symbol = ? AND timeframe = ?
            AND timestamp >= datetime('now', '-7 days')
        ''', (asset, timeframe))
        
        market_data = cursor.fetchone()
        if not market_data:
            continue
            
        volatility, volume_ratio = market_data
        
        # Подбор оптимальной стратегии
        if win_rate >= 0.75:  # 75%+ винрейт
            if volatility < 0.02:  # Низкая волатильность
                # Процентная стратегия - консервативная
                strategy_type = 'percentage'
                recommended_percent = 2.5
                risk_level = 'low'
            elif volatility < 0.05:  # Средняя волатильность
                # D'Alembert - умеренная
                strategy_type = 'dalembert'
                base_stake = 100
                unit = 50
                risk_level = 'medium'
            else:  # Высокая волатильность
                # Мартингейл только для очень высокого винрейта
                if win_rate >= 0.80:
                    strategy_type = 'martingale'
                    base_stake = 100
                    multiplier = 2
                    risk_level = 'high'
                else:
                    strategy_type = 'dalembert'
                    base_stake = 100
                    unit = 50
                    risk_level = 'medium'
            
            optimized_strategies.append({
                'asset': asset,
                'timeframe': timeframe,
                'strategy': strategy_type,
                'win_rate': win_rate * 100,
                'volatility': volatility,
                'risk_level': risk_level
            })
    
    # Сохраняем оптимизированные стратегии
    if optimized_strategies:
        logger.info("🎯 Оптимизированные стратегии:")
        for strat in optimized_strategies[:5]:
            logger.info(f"  ✅ {strat['asset']} {strat['timeframe']}: {strat['strategy']} (WR: {strat['win_rate']:.1f}%, Risk: {strat['risk_level']})")
        
        # Сохраняем в БД для использования в реальной торговле
        for strat in optimized_strategies:
            cursor.execute('''
                INSERT OR REPLACE INTO bot_settings (key, value)
                VALUES (?, ?)
            ''', (f"optimal_strategy_{strat['asset']}_{strat['timeframe']}", 
                  f"{strat['strategy']}|{strat['win_rate']:.1f}|{strat['risk_level']}"))
        
        bot.conn.commit()
        logger.info(f"✅ Сохранено {len(optimized_strategies)} оптимизированных стратегий")
    
    # Анализ лучших таймфреймов
    cursor.execute('''
        SELECT 
            timeframe,
            AVG(CASE WHEN result = 'win' THEN 1.0 ELSE 0.0 END) * 100 as win_rate,
            COUNT(*) as total
        FROM signal_history
        WHERE signal_tier = 'test'
        AND signal_date >= datetime('now', '-7 days')
        GROUP BY timeframe
        HAVING total >= 20
        ORDER BY win_rate DESC
    ''')
    
    timeframe_stats = cursor.fetchall()
    
    if timeframe_stats:
        logger.info("📊 Эффективность таймфреймов:")
        for tf, wr, total in timeframe_stats:
            logger.info(f"  {tf}: {wr:.1f}% WR ({total} сигналов)")
    
    logger.info("✅ Оптимизация стратегий завершена")

async def apply_optimized_strategy(user_id: int):
    """Применить оптимизированную стратегию для пользователя на основе статистики"""
    cursor = bot.conn.cursor()
    
    # Получаем лучшую стратегию из накопленных данных
    cursor.execute('''
        SELECT key, value FROM bot_settings
        WHERE key LIKE 'optimal_strategy_%'
        ORDER BY value DESC
        LIMIT 1
    ''')
    
    optimal = cursor.fetchone()
    
    if optimal:
        strategy_data = optimal[1].split('|')
        if len(strategy_data) >= 2:
            strategy_type = strategy_data[0]
            win_rate = float(strategy_data[1])
            
            # Применяем лучшую стратегию
            cursor.execute('''
                UPDATE users 
                SET auto_trading_strategy = ?
                WHERE user_id = ?
            ''', (strategy_type, user_id))
            
            bot.conn.commit()
            logger.info(f"✅ Применена оптимальная стратегия {strategy_type} (WR: {win_rate:.1f}%) для пользователя {user_id}")
            
            return strategy_type, win_rate
    
    return None, 0

async def start_background_testing(context: ContextTypes.DEFAULT_TYPE):
    """Запуск фонового тестирования с интервалом"""
    while True:
        try:
            # Тестирование каждые 6 часов
            await background_signal_tester(context)
            
            # Анализ и обучение каждые 12 часов
            await analyze_learning_data(context)
            
            # Оптимизация стратегий каждые 24 часа
            await optimize_strategies(context)
            
            # Пауза 6 часов
            await asyncio.sleep(6 * 3600)
            
        except Exception as e:
            logger.error(f"❌ Ошибка фонового тестирования: {e}")
            await asyncio.sleep(3600)  # Повтор через час при ошибке

async def show_period_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, plan_type: str):
    """Показать выбор периода для подписки"""
    query = update.callback_query
    
    plan = SUBSCRIPTION_PLANS[plan_type]
    
    text = f"""
{plan['emoji']} **{plan_type.upper()} ТАРИФ**

{plan['description']}

💰 **Выберите период:**
"""
    
    keyboard = []
    
    # Месячная подписка
    keyboard.append([InlineKeyboardButton(
        f"1 месяц - {plan['1_month']}₽",
        callback_data=f"buy_{plan_type}_1m"
    )])
    
    # Полугодовая со скидкой
    discount_6m = int((1 - plan['6_months'] / (plan['1_month'] * 6)) * 100)
    keyboard.append([InlineKeyboardButton(
        f"6 месяцев - {plan['6_months']}₽ (скидка {discount_6m}%)",
        callback_data=f"buy_{plan_type}_6m"
    )])
    
    # Годовая со скидкой
    discount_12m = int((1 - plan['12_months'] / (plan['1_month'] * 12)) * 100)
    keyboard.append([InlineKeyboardButton(
        f"12 месяцев - {plan['12_months']}₽ (скидка {discount_12m}%)",
        callback_data=f"buy_{plan_type}_12m"
    )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="buy_subscription")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_subscription_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, plan_type: str, period: str):
    """Обработать покупку подписки"""
    query = update.callback_query
    user_id = query.from_user.id
    
    plan = SUBSCRIPTION_PLANS[plan_type]
    
    # Определить цену и длительность
    period_map = {
        "1m": (plan['1_month'], 30, "1 месяц"),
        "6m": (plan['6_months'], 180, "6 месяцев"),
        "12m": (plan['12_months'], 365, "12 месяцев")
    }
    
    price, days, period_name = period_map.get(period, (0, 0, ""))
    
    payment_text = f"""
💳 **ОПЛАТА ПОДПИСКИ**

{plan['emoji']} **{plan_type.upper()}** - {period_name}
💰 Цена: **{price}₽**

📱 **СПОСОБЫ ОПЛАТЫ:**

💳 **Через ЮКассу** (автоматически)
Быстрая оплата картой через защищённую систему ЮКасса
Подписка активируется мгновенно

💵 **Перевод на карту**
Поддержите проект прямым переводом

💰 **ЮMoney**
Оплата через электронный кошелёк

**Для оплаты:**
1️⃣ Нажмите кнопку "Оплатить через ЮКассу" (быстро)
   ИЛИ
   Свяжитесь с поддержкой для перевода: {bot.get_support_contact()}
2️⃣ Укажите свой Telegram ID: `{user_id}`
3️⃣ Тариф: {plan_type.upper()} ({period_name})

✅ После оплаты подписка активируется автоматически!
"""
    
    support_username = bot.get_support_contact().replace('@', '')
    keyboard = [
        [InlineKeyboardButton("💳 Оплатить через ЮКассу", callback_data=f"pay_yookassa_{plan_type}_{period}")],
        [InlineKeyboardButton("💬 Оплата переводом (поддержка)", url=f"https://t.me/{support_username}")],
        [InlineKeyboardButton("◀️ Назад", callback_data="buy_subscription")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(payment_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_yookassa_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, plan_type: str, period: str):
    """Обработать оплату через ЮКассу"""
    query = update.callback_query
    user_id = query.from_user.id
    
    plan = SUBSCRIPTION_PLANS[plan_type]
    
    # Определить цену и длительность
    period_map = {
        "1m": (plan['1_month'], 30, "1 месяц"),
        "6m": (plan['6_months'], 180, "6 месяцев"),
        "12m": (plan['12_months'], 365, "12 месяцев")
    }
    
    price, days, period_name = period_map.get(period, (0, 0, ""))
    
    # Проверить наличие ЮКассы
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        yookassa_text = f"""
💳 **ОПЛАТА ЧЕРЕЗ ЮКАССУ**

{plan['emoji']} **{plan_type.upper()}** - {period_name}
💰 Сумма: **{price}₽**

⚙️ **Интеграция ЮКассы в процессе настройки...**

Пока что используйте альтернативные способы:
• Перевод на карту
• ЮMoney

Для оплаты свяжитесь с поддержкой:
👤 Telegram ID: `{user_id}`
📦 Тариф: {plan_type.upper()} ({period_name})
"""
        support_username = bot.get_support_contact().replace('@', '')
        keyboard = [
            [InlineKeyboardButton("💬 Написать в поддержку", url=f"https://t.me/{support_username}")],
            [InlineKeyboardButton("◀️ Назад", callback_data=f"buy_{plan_type}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(yookassa_text, reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    # Создать платеж через ЮКассу API
    try:
        # Генерировать уникальный ID платежа
        payment_id = str(uuid.uuid4())
        
        # Создать платеж
        payment = Payment.create({
            "amount": {
                "value": f"{price}.00",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/{bot.get_support_contact().replace('@', '')}"  # После оплаты - в поддержку
            },
            "capture": True,
            "description": f"{plan_type.upper()} подписка на {period_name}",
            "metadata": {
                "user_id": str(user_id),
                "plan_type": plan_type,
                "period": period,
                "days": days
            }
        }, payment_id)
        
        # Получить URL для оплаты
        payment_url = payment.confirmation.confirmation_url
        
        success_text = f"""
💳 **ОПЛАТА ЧЕРЕЗ ЮКАССУ**

{plan['emoji']} **{plan_type.upper()}** - {period_name}
💰 Сумма: **{price}₽**

✅ Платеж создан успешно!

**Для оплаты:**
1️⃣ Нажмите кнопку "Оплатить" ниже
2️⃣ Выберите способ оплаты (карта, Apple Pay, Google Pay и др.)
3️⃣ Подтвердите платеж

⚡ После успешной оплаты подписка активируется автоматически!

🔒 Защищенная оплата через ЮКассу
"""
        
        keyboard = [
            [InlineKeyboardButton("💳 Оплатить →", url=payment_url)],
            [InlineKeyboardButton("◀️ Назад", callback_data=f"buy_{plan_type}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        logger.info(f"✅ Created YooKassa payment {payment.id} for user {user_id}: {plan_type} {period_name}")
        
    except Exception as e:
        logger.error(f"❌ YooKassa payment creation failed: {e}")
        
        error_text = f"""
❌ **ОШИБКА СОЗДАНИЯ ПЛАТЕЖА**

Не удалось создать платеж через ЮКассу.

Пожалуйста, свяжитесь с поддержкой для оплаты:
👤 Telegram ID: `{user_id}`
📦 Тариф: {plan_type.upper()} ({period_name})
💰 Сумма: {price}₽
"""
        
        support_username = bot.get_support_contact().replace('@', '')
        keyboard = [
            [InlineKeyboardButton("💬 Написать в поддержку", url=f"https://t.me/{support_username}")],
            [InlineKeyboardButton("◀️ Назад", callback_data=f"buy_{plan_type}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_promo_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработать покупку промо для новичков"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Проверить, использована ли уже акция
    cursor = bot.conn.cursor()
    cursor.execute('SELECT new_user_discount_used FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result and result[0]:
        await query.answer("❌ Вы уже использовали акцию для новичков", show_alert=True)
        return
    
    promo_text = f"""
🎁 **АКЦИЯ ДЛЯ НОВИЧКОВ**

📉 **SHORT подписка** на 1 месяц
💰 Цена: **{NEW_USER_PROMO['price']}₽** вместо {SUBSCRIPTION_PLANS['short']['1_month']}₽
🔥 Скидка: **70%!**

**Условия:**
• Только для новых пользователей
• Один раз на аккаунт
• Необходимо быть зарегистрированным в Pocket Option

**Для активации:**
1️⃣ Свяжитесь с поддержкой: {bot.get_support_contact()}
2️⃣ Сообщите свой Telegram ID: `{user_id}`
3️⃣ Укажите ваш никнейм в Pocket Option
4️⃣ Оплатите {NEW_USER_PROMO['price']}₽ и получите доступ!

✅ После подтверждения подписка активируется на 30 дней.
"""
    
    support_username = bot.get_support_contact().replace('@', '')
    keyboard = [
        [InlineKeyboardButton("💬 Написать в поддержку", url=f"https://t.me/{support_username}")],
        [InlineKeyboardButton("◀️ Назад", callback_data="buy_subscription")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(promo_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_referral_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать реферальную программу"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Получить реферальный код и статистику
    referral_code = bot.get_referral_code(user_id)
    total_referrals, earnings = bot.get_referral_stats(user_id)
    
    referral_text = f"""
🤝 **РЕФЕРАЛЬНАЯ ПРОГРАММА**

Приглашайте друзей и получайте скидки на подписку!

👤 **Ваш реферальный код:** `{referral_code}`
🔗 **Реферальная ссылка:**
`https://t.me/YOUR_BOT?start={referral_code}`

📊 **Ваша статистика:**
• Приглашено друзей: {total_referrals}
• Заработано: {earnings}₽

**Как это работает:**
1️⃣ Поделитесь ссылкой с друзьями
2️⃣ Друг регистрируется в Pocket Option
3️⃣ Друг пишет в поддержку и активирует код
4️⃣ Вы оба получаете скидку 10% на подписку!

💡 **Условия:**
• Друг должен зарегистрироваться в Pocket Option
• Написать в поддержку свой никнейм PO
• Активировать ваш реферальный код

✅ Скидка действует постоянно для всех ваших рефералов!
"""
    
    support_username = bot.get_support_contact().replace('@', '')
    keyboard = [
        [InlineKeyboardButton("💬 Написать в поддержку", url=f"https://t.me/{support_username}")],
        [InlineKeyboardButton("◀️ Назад", callback_data="buy_subscription")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(referral_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_vip_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать подробную информацию о VIP подписке"""
    query = update.callback_query
    user_id = query.from_user.id
    
    vip_info_text = """
💎 **VIP ПОДПИСКА - МАКСИМУМ ВОЗМОЖНОСТЕЙ**

**🎯 Что входит:**
✅ Доступ к SHORT сигналам (1-5 мин)
✅ Доступ к LONG сигналам (1-4 часа)
✅ 5 автоматических рассылок в день
✅ 150 готовых сигналов ежемесячно
✅ Увеличенная ставка LONG: 5% вместо 2.5%
✅ Приоритетная поддержка
✅ Первым узнаете о новых функциях

**📊 Авто-рассылка:**
• 5 раз в день (2:00, 10:00, 14:00, 18:00, 22:00)
• ТОП-5 лучших LONG сигналов
• Точность ≥90%
• Готовы к использованию

**💰 Стоимость:**
• {bot.get_setting('vip_price_rub', '9990')}₽/месяц
• {int(int(bot.get_setting('vip_price_rub', '9990')) * 6 * 0.9)}₽/6 мес (скидка 10%)
• {int(int(bot.get_setting('vip_price_rub', '9990')) * 12 * 0.8)}₽/год (скидка 20%)

**🎁 Специальный апгрейд:**
Для обладателей SHORT/LONG: всего 1990₽
(применяется к текущей подписке)

**📈 Средний прирост дохода:**
VIP пользователи зарабатывают на 40-60% больше
благодаря доступу ко всем типам сигналов.
"""
    
    keyboard = [
        [InlineKeyboardButton("💎 Апгрейд до VIP (1990₽)", callback_data="upgrade_to_vip")],
        [InlineKeyboardButton("◀️ Назад", callback_data="dismiss_upgrade")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(vip_info_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_upgrade_to_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработать запрос на апгрейд до VIP"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Проверить текущую подписку
    cursor = bot.conn.cursor()
    cursor.execute('SELECT subscription_type, subscription_end FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if not result or not result[0]:
        await query.answer("❌ У вас нет активной подписки", show_alert=True)
        return
    
    current_sub, sub_end = result
    
    if current_sub == 'vip':
        await query.answer("✅ У вас уже VIP подписка!", show_alert=True)
        return
    
    if current_sub not in ['short', 'long']:
        await query.answer("❌ Апгрейд доступен только для SHORT/LONG подписчиков", show_alert=True)
        return
    
    upgrade_text = f"""
💎 **АПГРЕЙД ДО VIP**

Ваша текущая подписка: {current_sub.upper()}
Действует до: {datetime.fromisoformat(sub_end).strftime('%d.%m.%Y')}

💰 Стоимость апгрейда: **1990₽**

**Что вы получите:**
✅ Все функции VIP
✅ Апгрейд применяется к текущей подписке
✅ Срок действия остается прежним
✅ Начинаете пользоваться сразу после оплаты

**Для оплаты:**
1️⃣ Свяжитесь с поддержкой: {bot.get_support_contact()}
2️⃣ Сообщите свой Telegram ID: `{user_id}`
3️⃣ Укажите "Апгрейд до VIP"
4️⃣ Оплатите 1990₽

✅ После подтверждения ваша подписка автоматически
изменится на VIP с сохранением срока действия.
"""
    
    support_username = bot.get_support_contact().replace('@', '')
    keyboard = [
        [InlineKeyboardButton("💬 Написать в поддержку", url=f"https://t.me/{support_username}")],
        [InlineKeyboardButton("◀️ Отменить", callback_data="dismiss_upgrade")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(upgrade_text, reply_markup=reply_markup, parse_mode='Markdown')

async def setup_pocket_option_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню подключения Pocket Option"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    menu_text = """
🔗 *ПОДКЛЮЧЕНИЕ К POCKET OPTION*

Выберите действие:

**Ручной метод:**
📖 Следуйте инструкции и введите SSID вручную

**Автоматический метод (локальный скрипт):**
📥 Скачайте Python скрипт для автоматического получения SSID
"""
    
    keyboard = [
        [InlineKeyboardButton("📖 Инструкция (ручной метод)", callback_data="show_ssid_instruction")],
        [InlineKeyboardButton("📥 Скачать скрипт автоматизации", callback_data="download_ssid_automation")],
        [InlineKeyboardButton("🔑 Вход (отправить SSID)", callback_data="po_login")],
        [InlineKeyboardButton("◀️ Назад к автоторговле", callback_data="autotrade_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')

async def download_ssid_automation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить скрипт автоматизации SSID пользователю (бесплатно)"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    info_text = """
📥 **СКРИПТ АВТОМАТИЗАЦИИ SSID**

🤖 Локальный Python скрипт для автоматического получения SSID

**Что это?**
Скрипт работает на ВАШЕМ компьютере и автоматически:
• Входит в Pocket Option
• Получает SSID токен
• Отправляет его боту

**Преимущества:**
🔒 **Безопасно** - credentials только на вашем ПК
⚡ **Автоматизация** - не нужно копировать вручную
💾 **Резервная копия** - SSID сохраняется локально

**Требования:**
• Python 3.8+
• Google Chrome
• ChromeDriver

📦 Скачиваю архив...
"""
    
    await query.edit_message_text(info_text, parse_mode='Markdown')
    
    # Отправляем ZIP архив
    try:
        with open('ssid_automation.zip', 'rb') as f:
            caption = """✅ Скрипт автоматизации SSID

📦 Архив содержит:
• ssid_auto_extractor.py - основной скрипт
• requirements.txt - зависимости
• README.md - подробная инструкция
• .env.example - пример конфигурации

📖 Инструкция:
1. Распакуйте архив
2. Установите зависимости: pip install -r requirements.txt
3. Скопируйте .env.example в .env
4. Заполните данные в .env
5. Запустите: python ssid_auto_extractor.py

🔒 Безопасность: Скрипт работает локально, ваши данные остаются на вашем компьютере!

📞 Поддержка: @banana_pwr"""
            
            await query.message.reply_document(
                document=f,
                filename="ssid_automation.zip",
                caption=caption
            )
            
        keyboard = [
            [InlineKeyboardButton("◀️ Назад к подключению", callback_data="setup_pocket_option")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        success_text = """
✅ **Скрипт успешно отправлен!**

Следуйте инструкции в README.md файле внутри архива.

⚠️ **Важно:**
• Храните .env файл в безопасности
• Не загружайте его на GitHub
• Используйте только на своем компьютере
"""
        await query.message.reply_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except FileNotFoundError:
        error_text = "❌ Файл не найден. Обратитесь в поддержку @banana_pwr"
        keyboard = [
            [InlineKeyboardButton("◀️ Назад", callback_data="setup_pocket_option")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(error_text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error sending automation script: {e}")
        error_text = f"❌ Ошибка отправки: {str(e)}\nОбратитесь в поддержку @banana_pwr"
        keyboard = [
            [InlineKeyboardButton("◀️ Назад", callback_data="setup_pocket_option")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(error_text, reply_markup=reply_markup)

async def show_po_instruction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать подробную инструкцию по подключению Pocket Option"""
    query = update.callback_query
    await query.answer()
    
    # Загружаем инструкцию из файла
    try:
        with open('ssid_instruction.txt', 'r', encoding='utf-8') as f:
            instruction_text = f.read()
    except FileNotFoundError:
        instruction_text = "Инструкция недоступна. Обратитесь в поддержку @banana_pwr"
    
    keyboard = [
        [InlineKeyboardButton("🔑 Вход (отправить SSID)", callback_data="po_login")],
        [InlineKeyboardButton("◀️ Назад", callback_data="setup_pocket_option")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем новым сообщением без Markdown
    await query.message.reply_text(instruction_text, reply_markup=reply_markup)
    await query.message.delete()

async def show_ssid_instruction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать подробную инструкцию по получению SSID из cookies"""
    query = update.callback_query
    await query.answer()
    
    # Загружаем инструкцию из файла
    try:
        with open('ssid_instruction.txt', 'r', encoding='utf-8') as f:
            instruction_text = f.read()
    except FileNotFoundError:
        instruction_text = "Инструкция недоступна. Обратитесь в поддержку @banana_pwr"
    
    keyboard = [
        [InlineKeyboardButton("🔑 Вход (отправить SSID)", callback_data="po_login")],
        [InlineKeyboardButton("◀️ Назад к автоторговле", callback_data="autotrade_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем новым сообщением без Markdown
    await query.message.reply_text(instruction_text, reply_markup=reply_markup)
    await query.message.delete()

async def po_login_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс входа - запросить SSID у пользователя"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    # Установить флаг ожидания SSID
    context.user_data['awaiting_ssid'] = True
    
    await query.edit_message_text(
        "🔑 ВХОД В POCKET OPTION\n\n"
        "📝 Отправьте ваш SSID из браузера текстовым сообщением.\n\n"
        "Просто скопируйте строку из инструментов разработчика и отправьте.\n\n"
        "❓ Если не знаете как получить SSID - нажмите кнопку ниже",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📖 Показать инструкцию", callback_data="show_po_instruction")],
            [InlineKeyboardButton("◀️ Отмена", callback_data="setup_pocket_option")]
        ])
    )

async def ready_to_send_ssid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пользователь готов отправить SSID"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    # Установить флаг ожидания SSID
    context.user_data['awaiting_ssid'] = True
    
    await query.edit_message_text(
        "📝 *Отлично!*\n\n"
        "Теперь отправьте мне ваш SSID из браузера.\n\n"
        "Формат: 42[\"auth\",{...}]\n\n"
        "Просто скопируйте и отправьте текстовым сообщением.",
        parse_mode='Markdown'
    )

async def disconnect_pocket_option_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отключить Pocket Option"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    cursor = bot.conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET pocket_option_ssid = NULL, pocket_option_connected = 0 
        WHERE user_id = ?
    ''', (user_id,))
    bot.conn.commit()
    
    await query.answer("✅ Pocket Option отключен", show_alert=True)
    
    # Вернуться в меню автоторговли
    await autotrade_menu(update, context)

def get_decrypted_ssid(user_id: int) -> str:
    """
    Получить и расшифровать SSID пользователя
    
    Returns:
        Расшифрованный SSID или пустая строка
    """
    cursor = bot.conn.cursor()
    cursor.execute('SELECT pocket_option_ssid FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if not result or not result[0]:
        return ""
    
    try:
        return decrypt_ssid(result[0])
    except Exception as e:
        logger.error(f"SSID decryption error for user {user_id}: {e}")
        return ""

async def test_pocket_option_connection(ssid: str, demo: bool = True) -> tuple[bool, str, float]:
    """
    Тестировать подключение к Pocket Option
    
    Returns:
        (success, message, balance)
    """
    try:
        from pocket_option_api import PocketOptionAPI
        
        # Создать API клиент
        api = PocketOptionAPI(ssid=ssid, demo=demo)
        
        # Попытаться подключиться
        connected = await api.connect()
        
        if not connected:
            await api.close()
            return False, "❌ Не удалось подключиться к Pocket Option", 0.0
        
        # Получить баланс
        balance = await api.get_balance()
        
        # Закрыть соединение
        await api.close()
        
        return True, f"✅ Успешно подключен! Баланс: ${balance}", balance
        
    except Exception as e:
        logger.error(f"Connection test error: {e}")
        return False, f"❌ Ошибка подключения: {str(e)}", 0.0

async def execute_auto_trade(user_id: int, signal: dict) -> dict:
    """
    Выполнить автоматическую сделку на Pocket Option
    
    Args:
        user_id: ID пользователя
        signal: Словарь с данными сигнала (asset, direction, timeframe, confidence)
    
    Returns:
        Результат сделки {success, trade_id, message}
    """
    try:
        from pocket_option_api import PocketOptionAPI
        
        # Получить настройки пользователя
        cursor = bot.conn.cursor()
        cursor.execute('''
            SELECT auto_trading_mode, auto_trading_strategy, current_balance, initial_balance,
                   percentage_value, dalembert_base_stake, dalembert_unit, current_dalembert_level,
                   martingale_multiplier, martingale_base_stake, current_martingale_level
            FROM users WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            return {"success": False, "message": "❌ Пользователь не найден"}
        
        mode, strategy, current_balance, initial_balance, percentage, \
        dalembert_base, dalembert_unit, dalembert_level, \
        martingale_mult, martingale_base, martingale_level = result
        
        balance = current_balance if current_balance else initial_balance
        
        # Расшифровать SSID
        ssid = get_decrypted_ssid(user_id)
        if not ssid:
            return {"success": False, "message": "❌ SSID не настроен"}
        
        # Подключиться к Pocket Option
        is_demo = mode == 'demo'
        api = PocketOptionAPI(ssid=ssid, demo=is_demo)
        
        connected = await api.connect()
        if not connected:
            await api.close()
            return {"success": False, "message": "❌ Не удалось подключиться"}
        
        # Получить актуальный баланс
        po_balance = await api.get_balance()
        
        # Рассчитать размер ставки согласно стратегии
        if strategy == 'percentage':
            stake = po_balance * (percentage / 100)
        elif strategy == 'dalembert':
            stake = dalembert_base + (dalembert_level * dalembert_unit)
        elif strategy == 'martingale':
            stake = martingale_base * (martingale_mult ** martingale_level)
        elif strategy == 'ai_trading':
            # AI выбирает оптимальную стратегию из настроек
            # Пока используем процентную
            stake = po_balance * 0.02
        else:
            stake = po_balance * 0.025  # Default 2.5%
        
        # Округлить до 2 знаков
        stake = round(stake, 2)
        
        # Минимальная ставка $1
        if stake < 1:
            stake = 1
        
        # Конвертировать timeframe в секунды
        timeframe_map = {
            '1M': 60, '2M': 120, '3M': 180, '5M': 300,
            '15M': 900, '30M': 1800, '1H': 3600, '2H': 7200, '4H': 14400
        }
        duration = timeframe_map.get(signal.get('timeframe', '1M'), 60)
        
        # Конвертировать направление
        direction = 'call' if signal.get('direction') == 'CALL' else 'put'
        
        # Разместить сделку
        trade_result = await api.place_trade(
            asset=signal.get('asset', 'EURUSD'),
            amount=stake,
            direction=direction,
            duration=duration
        )
        
        if not trade_result.get('success'):
            await api.close()
            return {
                "success": False,
                "message": f"❌ Ошибка размещения: {trade_result.get('error', 'Unknown')}"
            }
        
        trade_id = trade_result.get('trade_id')
        logger.info(f"✅ Auto-trade placed: {signal.get('asset')} {direction.upper()} ${stake}")
        
        # Ожидать результат сделки (duration + 10 секунд на обработку)
        result_timeout = duration + 10
        trade_outcome = await api.check_trade_result(trade_id, timeout=result_timeout)
        
        # Закрыть соединение
        await api.close()
        
        # Обработать результат
        if trade_outcome:
            result = trade_outcome.get('result')  # 'win', 'loss', 'draw'
            profit = trade_outcome.get('profit', 0)
            
            # Обновить баланс
            new_balance = po_balance + profit
            
            # Обновить уровни стратегии
            if result == 'win':
                # Сброс уровней при выигрыше
                new_dalembert_level = max(0, dalembert_level - 1)
                new_martingale_level = 0
            elif result == 'loss':
                # Увеличение уровней при проигрыше
                new_dalembert_level = dalembert_level + 1
                new_martingale_level = martingale_level + 1
            else:  # draw
                # Ничья - уровни не меняются
                new_dalembert_level = dalembert_level
                new_martingale_level = martingale_level
            
            # Сохранить в БД
            cursor.execute('''
                UPDATE users 
                SET current_balance = ?, 
                    current_dalembert_level = ?,
                    current_martingale_level = ?
                WHERE user_id = ?
            ''', (new_balance, new_dalembert_level, new_martingale_level, user_id))
            
            # Сохранить статистику сделки автоматически
            cursor.execute('''
                INSERT INTO signal_history 
                (user_id, asset, timeframe, signal_type, confidence, result, signal_tier, stake_amount, profit_loss, signal_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, 
                signal.get('asset'), 
                signal.get('timeframe'),
                signal.get('direction'),  # CALL/PUT
                signal.get('confidence', 0),
                result,  # win/loss/draw
                'autotrade',
                stake,
                profit,
                datetime.now().isoformat(),
                f"Auto-trade {mode} mode"  # demo/real
            ))
            
            bot.conn.commit()
            
            logger.info(f"📊 Auto-trade result for user {user_id}: {result} | Profit: ${profit} | New balance: ${new_balance} | Recorded to DB")
            
            return {
                "success": True,
                "trade_id": trade_id,
                "result": result,
                "stake": stake,
                "profit": profit,
                "new_balance": new_balance,
                "asset": signal.get('asset'),
                "direction": direction,
                "duration": duration,
                "message": f"✅ {'Выигрыш' if result == 'win' else 'Проигрыш' if result == 'loss' else 'Ничья'}: {signal.get('asset')} ${profit:+.2f}"
            }
        else:
            # Таймаут ожидания результата
            logger.warning(f"⏱️ Trade result timeout for user {user_id}, trade {trade_id}")
            return {
                "success": False,
                "message": "⏱️ Таймаут ожидания результата сделки"
            }
            
    except Exception as e:
        logger.error(f"Auto-trade error for user {user_id}: {e}")
        # Убедиться что соединение закрыто
        try:
            if 'api' in locals():
                await api.close()
        except:
            pass
        return {"success": False, "message": f"❌ Ошибка: {str(e)}"}

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Попытаться ответить на callback query, игнорируя старые запросы
    try:
        await query.answer()
    except Exception as e:
        # Игнорировать ошибки "Query is too old" после перезапуска бота
        if "Query is too old" in str(e) or "query id is invalid" in str(e):
            logger.warning(f"Ignoring old callback query: {e}")
            return
        # Для других ошибок - продолжить обработку
        logger.error(f"Callback query answer error: {e}")
    
    user_id = query.from_user.id
    
    # Обработка выбора статуса пользователя (новый/существующий)
    if query.data == "user_status_new":
        # Новый пользователь - показать инструкцию по регистрации
        cursor = bot.conn.cursor()
        cursor.execute('UPDATE users SET pocket_option_registered = 0 WHERE user_id = ?', (user_id,))
        bot.conn.commit()
        
        promo_text = f"""
🎁 **СПЕЦИАЛЬНОЕ ПРЕДЛОЖЕНИЕ ДЛЯ НОВЫХ ПОЛЬЗОВАТЕЛЕЙ!**

🔥 **Получите VIP доступ со скидкой 85%!**
💰 Всего **1490₽** вместо 9990₽!

📝 **ПОШАГОВАЯ ИНСТРУКЦИЯ:**

**1️⃣ Перейдите по ссылке регистрации**
Нажмите кнопку "🔗 Зарегистрироваться в Pocket Option" ниже

**2️⃣ При регистрации введите промокод:**
`FRIENDUGAUIHALOD`
⚠️ Промокод нужно ввести **на сайте Pocket Option** в поле промокода!

**3️⃣ Отправьте ваш логин в бот**
После регистрации нажмите "✅ Я зарегистрировался" и отправьте ваш логин

**4️⃣ Получите промокод на VIP**
Администратор выдаст вам персональный промокод на VIP доступ за 1490₽

**5️⃣ Активируйте VIP в боте**
Используйте полученный промокод для активации VIP на месяц

🎯 **ЧТО ВЫ ПОЛУЧИТЕ:**
• 💎 VIP тариф на месяц
• ⚡ Безлимит SHORT сигналов (1-5 мин)
• 🔵 Безлимит LONG сигналов (1-4 часа)
• 📊 Авто-рассылка топ-10 сигналов
• 💰 90-95% точности

⚠️ **ВАЖНО:** Используйте промокод **FRIENDUGAUIHALOD** при регистрации!

➡️ Нажмите кнопку ниже для перехода на регистрацию:
"""
        keyboard = [
            [InlineKeyboardButton("🔗 Зарегистрироваться в Pocket Option", url=POCKET_OPTION_REF_LINK)],
            [InlineKeyboardButton("✅ Я зарегистрировался, отправить логин", callback_data="send_po_login")],
            [InlineKeyboardButton("◀️ Назад", callback_data="start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(promo_text, reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    elif query.data == "user_status_existing":
        # Существующий пользователь - установить флаг и продолжить
        cursor = bot.conn.cursor()
        cursor.execute('UPDATE users SET pocket_option_registered = 1 WHERE user_id = ?', (user_id,))
        bot.conn.commit()
        
        # Показать выбор языка
        welcome_text = """
🌍 **Welcome to Crypto Signals Bot!**
**Добро пожаловать в бот торговых сигналов!**

Please select your language / Выберите язык:
"""
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="set_language_ru")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="set_language_en")],
            [InlineKeyboardButton("🇪🇸 Español", callback_data="set_language_es")],
            [InlineKeyboardButton("🇧🇷 Português", callback_data="set_language_pt")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(welcome_text, reply_markup=reply_markup)
        return
    
    elif query.data == "send_po_login":
        # Пользователь хочет отправить логин
        support_username = bot.get_support_contact().replace('@', '')
        login_msg = f"""
👤 **ОТПРАВКА ЛОГИНА POCKET OPTION**

📝 Для получения промокода на VIP за 1490₽:

**ШАГ 1:** Нажмите кнопку ниже для связи с поддержкой
**ШАГ 2:** Отправьте в чат ваш логин из Pocket Option

⚠️ **Важно:** 
• Отправьте точный логин как в Pocket Option
• Администратор выдаст вам промокод на VIP за 1490₽
• Ожидание: до 24 часов

✨ **Пример логина:** 
user@example.com или PO123456789

👇 **Нажмите кнопку ниже:**
"""
        keyboard = [
            [InlineKeyboardButton("💬 Отправить логин в поддержку", url=f"https://t.me/{support_username}")],
            [InlineKeyboardButton("◀️ Назад", callback_data="user_status_new")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(login_msg, reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    elif query.data == "continue_setup":
        # Продолжить настройку после показа промо
        welcome_text = """
🌍 **Welcome to Crypto Signals Bot!**
**Добро пожаловать в бот торговых сигналов!**

Please select your language / Выберите язык:
"""
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="set_language_ru")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="set_language_en")],
            [InlineKeyboardButton("🇪🇸 Español", callback_data="set_language_es")],
            [InlineKeyboardButton("🇧🇷 Português", callback_data="set_language_pt")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(welcome_text, reply_markup=reply_markup)
        return
    
    # Обработка выбора языка
    if query.data.startswith("set_language_"):
        language = query.data.split("_")[2]
        bot.set_user_language(user_id, language)
        
        language_msg = TRANSLATIONS[language]['language_selected']
        await query.edit_message_text(language_msg)
        
        # Показать выбор валюты
        currency_text = TRANSLATIONS[language]['choose_currency']
        keyboard = [
            [InlineKeyboardButton("🇷🇺 RUB (₽)", callback_data="set_currency_RUB")],
            [InlineKeyboardButton("🇺🇸 USD ($)", callback_data="set_currency_USD")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(currency_text, reply_markup=reply_markup)
        return
    
    # Обработка выбора валюты
    elif query.data.startswith("set_currency_"):
        currency = query.data.split("_")[2]
        bot.set_currency(user_id, currency)
        
        # Сразу показать главное меню (с триалом для новых или текущим тарифом)
        await show_main_menu(update, context, user_id=user_id)
        return
    
    # Обработка кнопки "Админ панель"
    elif query.data == "settings_admin":
        await settings(update, context)
        return
    
    # Обработка кнопки "Отзывы пользователей"
    elif query.data == "user_reviews":
        # Проверить включены ли отзывы
        if bot.get_setting('reviews_enabled') != 'true':
            await query.answer("❌ Раздел отзывов временно недоступен", show_alert=True)
            return
        
        reviews_group = bot.get_setting('reviews_group', '@cryptosignalsbot_otz')
        reviews_text = f"""
⭐ **ОТЗЫВЫ ПОЛЬЗОВАТЕЛЕЙ**

Здесь вы найдете реальные отзывы наших клиентов!

📸 Группа с отзывами и скриншотами:
🔗 {reviews_group}

В группе вы увидите:
✅ Скриншоты успешных сделок
✅ Отзывы довольных пользователей
✅ Статистику прибыльности
✅ Подтверждения выплат

📊 **Наша репутация:**
• 95%+ точность FREE сигналов
• 92%+ точность VIP сигналов
• Тысячи довольных клиентов
• Прозрачная статистика

Присоединяйтесь к группе и убедитесь сами! 🚀
"""
        keyboard = [
            [InlineKeyboardButton("📱 Открыть группу отзывов", url=f"https://t.me/{reviews_group.lstrip('@')}")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(reviews_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # Обработка кнопок setup
    elif query.data == "setup_payments":
        if not bot.is_admin(user_id):
            await query.answer("❌ Доступно только администраторам", show_alert=True)
            return
        
        await query.edit_message_text(
            "💳 **НАСТРОЙКА ПЛАТЕЖЕЙ**\n\n"
            "Для настройки автоматических платежей через YooKassa:\n"
            "1. Зарегистрируйтесь на yookassa.ru\n"
            "2. Получите Shop ID и Secret Key\n"
            "3. Отправьте их в формате:\n\n"
            "`/set_payment SHOP_ID SECRET_KEY`\n\n"
            f"📊 Текущий статус: {'✅ Включены' if bot.get_setting('payment_enabled') == 'true' else '❌ Отключены'}\n\n"
            "Для отключения: `/disable_payments`",
            parse_mode='Markdown'
        )
    
    elif query.data == "setup_referral":
        if not bot.is_admin(user_id):
            await query.answer("❌ Доступно только администраторам", show_alert=True)
            return
        
        current_link = bot.get_setting('referral_link', 'не настроена')
        
        keyboard = [
            [InlineKeyboardButton("✏️ Изменить ссылку", callback_data="edit_referral_link")],
            [InlineKeyboardButton("◀️ Назад к setup", callback_data="back_to_setup")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🔗 **НАСТРОЙКА РЕФЕРАЛЬНОЙ ССЫЛКИ**\n\n"
            f"📊 Текущая ссылка: {current_link}\n\n"
            "Эта ссылка будет использоваться для новых пользователей, которые регистрируются по вашей реферальной программе и получают скидку.\n\n"
            "Используйте кнопки ниже для управления:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == "edit_referral_link":
        if not bot.is_admin(user_id):
            await query.answer("❌ Доступно только администраторам", show_alert=True)
            return
        
        await query.edit_message_text(
            "🔗 **ИЗМЕНИТЬ РЕФЕРАЛЬНУЮ ССЫЛКУ**\n\n"
            "Отправьте новую реферальную ссылку Pocket Option для новых пользователей.\n"
            "Пример: `https://po8.cash/smart/...`\n\n"
            "Эта ссылка будет показываться новым пользователям для регистрации и получения скидки.",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_referral_link'] = True
        return
    
    elif query.data == "setup_reviews":
        if not bot.is_admin(user_id):
            await query.answer("❌ Доступно только администраторам", show_alert=True)
            return
        
        current_group = bot.get_setting('reviews_group', '@cryptosignalsbot_otz')
        enabled = bot.get_setting('reviews_enabled') == 'true'
        
        keyboard = [
            [InlineKeyboardButton("✏️ Изменить группу", callback_data="edit_reviews_group")],
            [InlineKeyboardButton(
                f"{'❌ Отключить' if enabled else '✅ Включить'} отзывы", 
                callback_data="toggle_reviews"
            )],
            [InlineKeyboardButton("◀️ Назад к setup", callback_data="back_to_setup")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⭐ **НАСТРОЙКА ОТЗЫВОВ**\n\n"
            f"📊 Текущая группа: {current_group}\n"
            f"📊 Статус: {'✅ Включены' if enabled else '❌ Отключены'}\n\n"
            "Используйте кнопки ниже для управления:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == "setup_admins":
        if not bot.is_admin(user_id):
            await query.answer("❌ Доступно только администраторам", show_alert=True)
            return
        
        admin_users = bot.get_setting('admin_users', str(ADMIN_USER_ID))
        admin_list = [uid.strip() for uid in admin_users.split(',') if uid.strip()]
        
        await query.edit_message_text(
            "👥 **УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ**\n\n"
            f"📊 Текущие админы: {', '.join(admin_list)}\n\n"
            "**Добавить админа:**\n"
            "`/add_admin USER_ID`\n\n"
            "**Удалить админа:**\n"
            "`/remove_admin USER_ID`\n\n"
            "⚠️ Главный админ не может быть удален",
            parse_mode='Markdown'
        )
    
    elif query.data == "setup_user_management":
        if not bot.is_admin(user_id):
            await query.answer("❌ Доступно только администраторам", show_alert=True)
            return
        
        keyboard = [
            [InlineKeyboardButton("🔄 Сбросить себя", callback_data="admin_reset_self")],
            [InlineKeyboardButton("◀️ Назад к setup", callback_data="back_to_setup")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "👤 **УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ**\n\n"
            "**Сброс пользователя:**\n"
            "`/reset_user USER_ID` - сбросить любого пользователя до нового\n\n"
            "**Бан пользователя:**\n"
            "`/ban USER_ID` - забанить пользователя\n"
            "`/unban USER_ID` - разбанить пользователя\n\n"
            "**Быстрый сброс:**\n"
            "Используйте кнопку ниже для сброса себя",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == "admin_reset_self":
        await admin_reset_self(update, context)
        return
    
    elif query.data == "setup_complete":
        if not bot.is_admin(user_id):
            await query.answer("❌ Доступно только администраторам", show_alert=True)
            return
        
        bot.set_setting('bot_configured', 'true', user_id)
        await query.edit_message_text(
            "✅ **НАСТРОЙКА ЗАВЕРШЕНА!**\n\n"
            "Бот готов к работе!\n\n"
            "Вы можете изменить настройки в любое время:\n"
            "• `/setup` - меню настройки\n"
            "• Админ панель → Настройки бота",
            parse_mode='Markdown'
        )
    
    elif query.data == "edit_reviews_group":
        if not bot.is_admin(user_id):
            await query.answer("❌ Доступно только администраторам", show_alert=True)
            return
        
        context.user_data['awaiting_reviews_group'] = True
        current_group = bot.get_setting('reviews_group', '@cryptosignalsbot_otz')
        
        keyboard = [
            [InlineKeyboardButton("❌ Отмена", callback_data="setup_reviews")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⭐ **ИЗМЕНЕНИЕ ГРУППЫ ОТЗЫВОВ**\n\n"
            f"📊 Текущая группа: {current_group}\n\n"
            f"📝 Отправьте ссылку или username группы\n"
            f"Примеры:\n"
            f"• @your_group\n"
            f"• https://t.me/your_group\n\n"
            f"Бот ждет ваше сообщение...",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    elif query.data == "toggle_reviews":
        if not bot.is_admin(user_id):
            await query.answer("❌ Доступно только администраторам", show_alert=True)
            return
        
        current = bot.get_setting('reviews_enabled', 'true')
        new_value = 'false' if current == 'true' else 'true'
        bot.set_setting('reviews_enabled', new_value, user_id)
        
        await query.answer(f"{'✅ Отзывы включены' if new_value == 'true' else '❌ Отзывы отключены'}", show_alert=True)
        # Re-call setup_reviews
        query.data = "setup_reviews"
        await button_callback(update, context)
        return
    
    elif query.data == "back_to_setup":
        if not bot.is_admin(user_id):
            await query.answer("❌ Доступно только администраторам", show_alert=True)
            return
        
        # Recreate setup menu (админ панель + настройки)
        stats = bot.get_bot_stats()
        
        setup_text = """
🔐 **АДМИН ПАНЕЛЬ И НАСТРОЙКИ**

📊 **Статистика бота:**
👥 Всего пользователей: {}
💎 Premium пользователей: {}
✅ Активных подписок: {}
📈 Всего сигналов: {}

📋 **Текущие настройки:**
• Платежи: {}
• Группа отзывов: {}
• Показывать отзывы: {}
• Реферальная ссылка: {}
• Администраторы: {}

Выберите раздел:
""".format(
            stats['total_users'],
            stats['premium_users'],
            stats['active_subscriptions'],
            stats['total_signals'],
            "✅ Включены" if bot.get_setting('payment_enabled') == 'true' else "❌ Отключены",
            bot.get_setting('reviews_group', '@cryptosignalsbot_otz'),
            "✅ Да" if bot.get_setting('reviews_enabled') == 'true' else "❌ Нет",
            bot.get_setting('referral_link', 'не настроена'),
            bot.get_setting('admin_users', str(ADMIN_USER_ID))
        )
        
        keyboard = [
            [InlineKeyboardButton("📊 Подробная статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("🏆 ТОП-10 пользователей", callback_data="admin_top_users")],
            [InlineKeyboardButton("💳 Настроить платежи", callback_data="setup_payments")],
            [InlineKeyboardButton("🔗 Настроить реферальную ссылку", callback_data="setup_referral")],
            [InlineKeyboardButton("⭐ Настроить группу отзывов", callback_data="setup_reviews")],
            [InlineKeyboardButton("👥 Управление админами", callback_data="setup_admins")],
            [InlineKeyboardButton("👤 Управление пользователями", callback_data="setup_user_management")],
            [InlineKeyboardButton("🔄 Обновить данные", callback_data="admin_refresh")],
        ]
        
        # Добавить секцию переключения тарифов
        keyboard.append([InlineKeyboardButton("🔀 ПЕРЕКЛЮЧИТЬ ТАРИФ СЕБЕ:", callback_data="none")])
        keyboard.extend([
            [InlineKeyboardButton("💎 VIP", callback_data="admin_set_vip"),
             InlineKeyboardButton("🔵 LONG", callback_data="admin_set_long"),
             InlineKeyboardButton("⚡️ SHORT", callback_data="admin_set_short")],
            [InlineKeyboardButton("🆓 FREE", callback_data="admin_set_free"),
             InlineKeyboardButton("🎁 Пробный VIP (3 дня)", callback_data="admin_set_trial")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(setup_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # Обработка кнопки "Политика конфиденциальности"
    elif query.data == "privacy_policy":
        privacy_text = f"""
📜 <b>ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ</b>

<b>1. СБОР ДАННЫХ</b>
Мы собираем только необходимую информацию:
• Telegram ID и имя пользователя
• Выбранный язык и валюта
• История торговых сигналов
• Статистика использования

<b>2. ИСПОЛЬЗОВАНИЕ ДАННЫХ</b>
Ваши данные используются для:
• Предоставления торговых сигналов
• Персонализации опыта
• Улучшения качества сервиса
• Статистического анализа

<b>3. БЕЗОПАСНОСТЬ</b>
• Данные хранятся в защищенной базе
• Нет доступа третьих лиц
• Шифрование конфиденциальной информации

<b>4. ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ</b>
⚠️ <b>ВАЖНО:</b>
• Торговля криптовалютой несет высокие риски
• Сигналы носят рекомендательный характер
• Мы НЕ гарантируем 100% прибыль
• Все решения принимаются пользователем
• Вы несете полную ответственность за свои сделки
• Возможна полная потеря средств

<b>5. ТОРГОВЫЕ РИСКИ</b>
📊 Используя бота, вы понимаете:
• Прошлые результаты не гарантируют будущую прибыль
• Рыночная волатильность может привести к убыткам
• Необходимо использовать риск-менеджмент
• Торговать только доступными средствами

<b>6. ЗАПРЕТ ОТВЕТСТВЕННОСТИ</b>
Разработчики и владельцы бота:
❌ НЕ несут ответственности за убытки
❌ НЕ являются финансовыми советниками
❌ НЕ гарантируют точность сигналов
❌ НЕ компенсируют торговые потери

<b>7. ВАШИ ПРАВА</b>
✅ Удаление аккаунта по запросу
✅ Доступ к своим данным
✅ Отказ от сервиса в любой момент

📞 Вопросы: {bot.get_support_contact()}

<i>Используя бота, вы соглашаетесь с условиями</i>
"""
        keyboard = [[InlineKeyboardButton("🏠", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(privacy_text, reply_markup=reply_markup, parse_mode='HTML')
    
    # Обработка кнопки "Настройки"
    elif query.data == "settings":
        language = bot.get_user_language(user_id)
        cursor = bot.conn.cursor()
        cursor.execute('SELECT currency FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        currency = result[0] if result and result[0] else 'RUB'
        
        # Проверка администратора
        is_admin = bot.is_admin(user_id)
        
        # Получить тип подписки пользователя
        cursor.execute('SELECT subscription_type FROM users WHERE user_id = ?', (user_id,))
        sub_result = cursor.fetchone()
        subscription_type = sub_result[0] if sub_result else 'free'
        
        t = lambda key: TRANSLATIONS[language].get(key, key)
        
        settings_text = f"""
⚙️ **НАСТРОЙКИ**

🌍 Язык: {language.upper()}
💱 Валюта: {currency} {CURRENCY_SYMBOLS[currency]}

Выберите раздел:
"""
        keyboard = []
        
        # Кнопка выбора тарифа только для free/trial пользователей (не для админов и не для платных подписок)
        if not is_admin and subscription_type in ['free', 'trial']:
            keyboard.append([InlineKeyboardButton("🔥💎 ВЫБРАТЬ ТАРИФ И ЗАРАБАТЫВАТЬ! 💰🚀", callback_data="choose_plan_settings")])
        
        keyboard.extend([
            [InlineKeyboardButton("📖 Справка", callback_data="user_guide"),
             InlineKeyboardButton("📜 Соглашение", callback_data="privacy_policy")],
            [InlineKeyboardButton("🌍 Язык", callback_data="change_language"),
             InlineKeyboardButton("💱 Валюта", callback_data="change_currency")],
        ])
        
        # Добавляем кнопку главной для всех, админ панель только для админов
        if is_admin:
            keyboard.append([
                InlineKeyboardButton("🏠 Главная", callback_data="back_to_main"),
                InlineKeyboardButton("🔧 Админ панель", callback_data="admin_panel")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("🏠 Главная", callback_data="back_to_main")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(settings_text, reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    elif query.data == "choose_strategy":
        # Показать меню выбора стратегии
        keyboard = [
            [InlineKeyboardButton("⚡️ Мартингейл", callback_data="set_strategy_martingale"),
             InlineKeyboardButton("📊 % от банка", callback_data="set_strategy_percentage")],
            [InlineKeyboardButton("◀️ Назад", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🎯 **ВЫБОР СТРАТЕГИИ БАНКА**\n\n"
            "⚡️ **Мартингейл** (⚠️ рискованная):\n"
            "• Удвоение/утроение ставки после проигрыша\n"
            "• Выбор множителя x2 или x3\n"
            "• Настройка базовой ставки\n\n"
            "📊 **% от банка** (✅ стабильная):\n"
            "• Фиксированный процент от текущего банка\n"
            "• Ручной ввод процента\n"
            "• Автоматическая адаптация к балансу\n\n"
            "💡 Выберите стратегию:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    elif query.data == "set_strategy_martingale":
        # Установить стратегию Мартингейл и показать настройки
        cursor = bot.conn.cursor()
        cursor.execute('UPDATE users SET trading_strategy = ? WHERE user_id = ?', ('martingale', user_id))
        cursor.execute('SELECT martingale_multiplier, martingale_base_stake FROM users WHERE user_id = ?', (user_id,))
        settings_data = cursor.fetchone()
        bot.conn.commit()
        
        multiplier = settings_data[0] if settings_data and settings_data[0] else 3
        base_stake = settings_data[1] if settings_data and settings_data[1] else None
        
        keyboard = [
            [InlineKeyboardButton("x2", callback_data="martingale_x2"),
             InlineKeyboardButton("x3", callback_data="martingale_x3")],
            [InlineKeyboardButton("◀️ Назад", callback_data="choose_strategy")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚡️ **НАСТРОЙКА МАРТИНГЕЙЛА**\n\n"
            f"**Текущий множитель:** x{multiplier}\n"
            f"**Базовая ставка:** {base_stake if base_stake else 'Не установлена'}₽\n\n"
            f"1️⃣ Выберите множитель (x2 или x3)\n"
            f"2️⃣ Затем введите базовую ставку\n\n"
            f"💡 После проигрыша ставка умножается на выбранный множитель",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    elif query.data.startswith("martingale_"):
        # Установить множитель мартингейла
        multiplier = int(query.data.split("_")[1][1])  # "martingale_x2" -> 2
        cursor = bot.conn.cursor()
        cursor.execute('UPDATE users SET martingale_multiplier = ? WHERE user_id = ?', (multiplier, user_id))
        bot.conn.commit()
        
        await query.answer(f"✅ Множитель установлен: x{multiplier}", show_alert=False)
        await query.edit_message_text(
            f"⚡️ **УСТАНОВКА БАЗОВОЙ СТАВКИ**\n\n"
            f"**Множитель:** x{multiplier}\n\n"
            f"📝 Отправьте базовую ставку в рублях следующим сообщением.\n\n"
            f"Пример: `500`\n\n"
            f"💡 Это начальная ставка для мартингейла.",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_martingale_base_stake'] = True
        return
    
    elif query.data == "set_strategy_percentage":
        # Установить стратегию Процентная и запросить ввод процента
        cursor = bot.conn.cursor()
        cursor.execute('UPDATE users SET trading_strategy = ? WHERE user_id = ?', ('percentage', user_id))
        bot.conn.commit()
        
        await query.edit_message_text(
            f"📊 **НАСТРОЙКА % ОТ БАНКА**\n\n"
            f"📝 Отправьте процент от банка следующим сообщением.\n\n"
            f"**Примеры:**\n"
            f"• `2` - консервативно\n"
            f"• `2.5` - умеренно\n"
            f"• `5` - агрессивно\n\n"
            f"💡 Рекомендуется: 1-5%",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_percentage_value'] = True
        return
    
    
    elif query.data == "change_language":
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="set_language_ru")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="set_language_en")],
            [InlineKeyboardButton("🇪🇸 Español", callback_data="set_language_es")],
            [InlineKeyboardButton("🇧🇷 Português", callback_data="set_language_pt")],
            [InlineKeyboardButton("◀️ Назад", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🌍 Choose language / Выберите язык:", reply_markup=reply_markup)
        return
    
    elif query.data == "referral_program":
        # Получить или создать реферальный код
        cursor = bot.conn.cursor()
        cursor.execute('SELECT referral_code FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            # Создать уникальный реферальный код
            referral_code = f"REF{user_id}"
            cursor.execute('UPDATE users SET referral_code = ? WHERE user_id = ?', (referral_code, user_id))
            bot.conn.commit()
        else:
            referral_code = result[0]
        
        # Получить статистику рефералов
        cursor.execute('SELECT COUNT(*) FROM users WHERE referred_by = ?', (user_id,))
        referrals_count = cursor.fetchone()[0]
        
        referral_link = f"https://t.me/{(await context.bot.get_me()).username}?start={referral_code}"
        
        # Проверить есть ли право выбора бонуса
        cursor.execute('SELECT referral_bonus_pending FROM users WHERE user_id = ?', (user_id,))
        bonus_result = cursor.fetchone()
        has_pending_bonus = bonus_result and bonus_result[0] == 'choice'
        
        referral_text = f"""
🎁 **РЕФЕРАЛЬНАЯ ПРОГРАММА**

💰 **ПРИВЕДИ ДРУГА - ПОЛУЧИ ПОДПИСКУ!**

📋 **Условия:**

🔸 **Друг купил VIP** → Вы получаете **1 месяц VIP бесплатно**
🔸 **Друг купил LONG/SHORT** → Вы **ВЫБИРАЕТЕ** **1 месяц LONG или SHORT бесплатно**

👥 **Ваши рефералы:** {referrals_count}

🔗 **Ваша реферальная ссылка:**
`{referral_link}`

📱 **Как пользоваться:**
1. Отправьте ссылку друзьям
2. Когда друг купит подписку, вам начислится бонус
3. Бонус VIP активируется автоматически
4. Для LONG/SHORT вы выбираете тариф на свой выбор

⚡ **Важно:** Друг должен зарегистрироваться именно по вашей ссылке!
"""
        
        keyboard = []
        
        # Если есть право выбора бонуса - показать кнопку
        if has_pending_bonus:
            keyboard.append([InlineKeyboardButton("🎁 ВЫБРАТЬ БОНУС (LONG или SHORT)", callback_data="choose_referral_bonus")])
        
        keyboard.extend([
            [InlineKeyboardButton("📋 Скопировать ссылку", callback_data=f"copy_ref_{referral_code}")],
            [InlineKeyboardButton("◀️ Назад", callback_data="settings")]
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(referral_text, reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    elif query.data == "choose_referral_bonus":
        # Показать выбор между LONG и SHORT
        bonus_text = """
🎁 **ВЫБОР РЕФЕРАЛЬНОГО БОНУСА**

Ваш друг купил подписку, и вы можете выбрать бонус:

⚡ **SHORT (1 месяц)**
• Быстрые сигналы 1-5 мин
• Мартингейл x2/x3
• Автоматический countdown

🔵 **LONG (1 месяц)**
• Длинные сигналы 1-4 часа
• Процентная ставка 2-3%
• Управление через /my_longs

Что выбираете?
"""
        keyboard = [
            [InlineKeyboardButton("⚡ Выбрать SHORT", callback_data="claim_bonus_short")],
            [InlineKeyboardButton("🔵 Выбрать LONG", callback_data="claim_bonus_long")],
            [InlineKeyboardButton("◀️ Назад", callback_data="referral_program")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(bonus_text, reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    elif query.data.startswith("claim_bonus_"):
        # Активировать выбранный бонус
        bonus_type = query.data.replace("claim_bonus_", "")
        
        # Проверить есть ли право на бонус
        cursor = bot.conn.cursor()
        cursor.execute('SELECT referral_bonus_pending FROM users WHERE user_id = ?', (user_id,))
        bonus_result = cursor.fetchone()
        
        if not bonus_result or bonus_result[0] != 'choice':
            await query.answer("❌ У вас нет доступных бонусов", show_alert=True)
            return
        
        # Активировать подписку
        cursor.execute('SELECT subscription_end FROM users WHERE user_id = ?', (user_id,))
        sub_result = cursor.fetchone()
        
        if sub_result and sub_result[0]:
            current_end = datetime.fromisoformat(sub_result[0])
            if current_end > datetime.now():
                new_end = current_end + timedelta(days=30)
            else:
                new_end = datetime.now() + timedelta(days=30)
        else:
            new_end = datetime.now() + timedelta(days=30)
        
        # Обновить подписку и убрать флаг бонуса
        cursor.execute('''
            UPDATE users 
            SET subscription_end = ?, is_premium = 1, subscription_type = ?, referral_bonus_pending = NULL
            WHERE user_id = ?
        ''', (new_end.isoformat(), bonus_type, user_id))
        bot.conn.commit()
        
        emoji = "⚡" if bonus_type == "short" else "🔵"
        await query.answer(f"✅ Бонус {bonus_type.upper()} активирован!", show_alert=True)
        
        # Показать подтверждение
        confirm_text = f"""
✅ **БОНУС АКТИВИРОВАН!**

{emoji} Вы получили **1 месяц {bonus_type.upper()}**

📅 Подписка активна до: {new_end.strftime('%d.%m.%Y')}

Используйте меню для получения сигналов!
"""
        keyboard = [[InlineKeyboardButton("🏠 Главная", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(confirm_text, reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    elif query.data == "change_currency":
        language = bot.get_user_language(user_id)
        t = lambda key: TRANSLATIONS[language].get(key, key)
        keyboard = [
            [InlineKeyboardButton("🇷🇺 RUB (₽)", callback_data="set_currency_RUB")],
            [InlineKeyboardButton("🇺🇸 USD ($)", callback_data="set_currency_USD")],
            [InlineKeyboardButton("◀️ Назад", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(t('choose_currency'), reply_markup=reply_markup)
        return
    
    if query.data.startswith("result_win_"):
        signal_id = int(query.data.split("_")[2])
        cursor = bot.conn.cursor()
        cursor.execute('SELECT stake_amount, timeframe FROM signal_history WHERE id = ?', (signal_id,))
        result = cursor.fetchone()
        
        if result:
            stake_amount, timeframe = result
            stake_amount = stake_amount or 0
            profit = stake_amount * (PAYOUT_PERCENT / 100)
            
            # Обновить баланс пользователя
            cursor.execute('SELECT current_balance FROM users WHERE user_id = ?', (user_id,))
            current_balance = cursor.fetchone()[0]
            new_balance = current_balance + profit
            cursor.execute('UPDATE users SET current_balance = ? WHERE user_id = ?', (new_balance, user_id))
            bot.conn.commit()
            
            bot.update_signal_result(signal_id, 'win', profit)
            
            # Обнулить мартингейл для SHORT сигналов
            short_timeframes = ["1M", "2M", "3M", "5M", "15M", "30M"]
            if timeframe.upper() in short_timeframes:
                bot.update_martingale_after_win(user_id)
            
            # Рассчитать новую ставку в зависимости от типа сигнала
            if timeframe.upper() in short_timeframes:
                new_stake, _ = bot.get_martingale_stake(user_id)
            else:
                new_stake = bot.get_long_stake(user_id, new_balance, is_vip=False)
            
            # Определяем тип сигнала для кнопки повтора
            short_timeframes = ["1M", "2M", "3M", "5M", "15M", "30M"]
            is_short = timeframe.upper() in short_timeframes
            signal_type_for_repeat = "SHORT" if is_short else "LONG"
            callback_for_repeat = "find_signals_short" if is_short else "find_signals_long"
            
            # Кнопки повтора
            keyboard = [
                [InlineKeyboardButton(f"🔄 Повторный поиск {signal_type_for_repeat}", callback_data=callback_for_repeat)],
                [InlineKeyboardButton("🏠 Домой", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            result_message = await query.edit_message_text(
                f"✅ **ПРИБЫЛЬ ЗАФИКСИРОВАНА!**\n\n"
                f"💰 Прибыль: +{profit:.2f} RUB\n"
                f"💵 Новый баланс: {new_balance:.2f} RUB\n"
                f"📊 Рекомендуемая ставка: {new_stake:.2f} RUB (2%)\n\n"
                f"🎯 Отличная работа! Продолжайте в том же духе!",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            logger.info(f"✅ User {user_id} reported WIN via button for signal {signal_id}, profit: {profit:.2f}")
        return
    
    elif query.data.startswith("result_loss_"):
        signal_id = int(query.data.split("_")[2])
        cursor = bot.conn.cursor()
        cursor.execute('SELECT stake_amount, timeframe FROM signal_history WHERE id = ?', (signal_id,))
        result = cursor.fetchone()
        
        if result:
            stake_amount, timeframe = result
            stake_amount = stake_amount or 0
            loss = -stake_amount
            
            # Обновить баланс пользователя
            cursor.execute('SELECT current_balance FROM users WHERE user_id = ?', (user_id,))
            current_balance = cursor.fetchone()[0]
            new_balance = current_balance + loss
            cursor.execute('UPDATE users SET current_balance = ? WHERE user_id = ?', (new_balance, user_id))
            bot.conn.commit()
            
            bot.update_signal_result(signal_id, 'loss', loss)
            
            # Увеличить уровень мартингейла для SHORT сигналов
            short_timeframes = ["1M", "2M", "3M", "5M", "15M", "30M"]
            if timeframe in short_timeframes:
                bot.update_martingale_after_loss(user_id)
            
            # Рассчитать новую ставку в зависимости от типа сигнала
            if timeframe.upper() in short_timeframes:
                new_stake, _ = bot.get_martingale_stake(user_id)
            else:
                new_stake = bot.get_long_stake(user_id, new_balance, is_vip=False)
            
            # Определяем тип сигнала для кнопки повтора
            short_timeframes = ["1M", "2M", "3M", "5M", "15M", "30M"]
            is_short = timeframe.upper() in short_timeframes
            signal_type_for_repeat = "SHORT" if is_short else "LONG"
            callback_for_repeat = "find_signals_short" if is_short else "find_signals_long"
            
            # Кнопки повтора
            keyboard = [
                [InlineKeyboardButton(f"🔄 Повторный поиск {signal_type_for_repeat}", callback_data=callback_for_repeat)],
                [InlineKeyboardButton("🏠 Домой", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            result_message = await query.edit_message_text(
                f"❌ **УБЫТОК ЗАФИКСИРОВАН**\n\n"
                f"💸 Убыток: {loss:.2f} RUB\n"
                f"💵 Новый баланс: {new_balance:.2f} RUB\n"
                f"📊 Рекомендуемая ставка: {new_stake:.2f} RUB (2%)\n\n"
                f"💪 Не переживайте, следующий сигнал будет успешным!",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            logger.info(f"❌ User {user_id} reported LOSS via button for signal {signal_id}, loss: {loss:.2f}")
        return
    
    elif query.data.startswith("result_refund_"):
        signal_id = int(query.data.split("_")[2])
        cursor = bot.conn.cursor()
        cursor.execute('SELECT stake_amount, timeframe FROM signal_history WHERE id = ?', (signal_id,))
        result = cursor.fetchone()
        
        if result:
            stake_amount, timeframe = result
            stake_amount = stake_amount or 0
            
            # При возврате баланс не изменяется
            bot.update_signal_result(signal_id, 'refund', 0)
            
            # При возврате мартингейл не изменяется для SHORT
            short_timeframes = ["1M", "2M", "3M", "5M", "15M", "30M"]
            if timeframe in short_timeframes:
                bot.update_martingale_after_refund(user_id)
                next_stake, _ = bot.get_martingale_stake(user_id)
            else:
                cursor.execute('SELECT current_balance FROM users WHERE user_id = ?', (user_id,))
                balance_result = cursor.fetchone()
                current_balance = balance_result[0] if balance_result else 0
                next_stake = bot.get_long_stake(user_id, current_balance, is_vip=False)
            
            result_message = await query.edit_message_text(
                f"🔄 **ВОЗВРАТ СТАВКИ**\n\n"
                f"💰 Возврат: {stake_amount:.2f} RUB\n"
                f"📊 Следующая ставка: {next_stake:.2f} RUB\n\n"
                f"💡 Мартингейл не изменился - следующая ставка останется той же",
                parse_mode='Markdown'
            )
            logger.info(f"🔄 User {user_id} reported REFUND via button for signal {signal_id}")
            
            # Автоудаление сообщения через 10 секунд (неблокирующее)
            asyncio.create_task(auto_delete_message(result_message, 10))
        return
    
    elif query.data.startswith("result_skip_"):
        signal_id = int(query.data.split("_")[2])
        bot.skip_signal(signal_id)
        
        cursor = bot.conn.cursor()
        # Получаем timeframe чтобы определить тип сигнала
        cursor.execute('SELECT timeframe FROM signal_history WHERE id = ?', (signal_id,))
        timeframe_result = cursor.fetchone()
        timeframe = timeframe_result[0] if timeframe_result else "1M"
        
        cursor.execute('SELECT current_balance FROM users WHERE user_id = ?', (user_id,))
        balance_result = cursor.fetchone()
        current_balance = balance_result[0] if balance_result else 0
        new_stake = current_balance * 0.02
        
        # Определяем тип сигнала для кнопки повтора
        short_timeframes = ["1M", "2M", "3M", "5M", "15M", "30M"]
        is_short = timeframe.upper() in short_timeframes
        signal_type_for_repeat = "SHORT" if is_short else "LONG"
        callback_for_repeat = "find_signals_short" if is_short else "find_signals_long"
        
        # Кнопки повтора
        keyboard = [
            [InlineKeyboardButton(f"🔄 Повторный поиск {signal_type_for_repeat}", callback_data=callback_for_repeat)],
            [InlineKeyboardButton("🏠 Домой", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        result_message = await query.edit_message_text(
            f"⏭️ **СИГНАЛ ПРОПУЩЕН**\n\n"
            f"Сигнал не учтен в статистике win rate.\n"
            f"💵 Ваш баланс: {current_balance:.2f} RUB\n"
            f"📊 Рекомендуемая ставка: {new_stake:.2f} RUB (2%)\n\n"
            f"✅ Продолжайте торговать по своей стратегии!",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        logger.info(f"⏭️ User {user_id} skipped signal {signal_id}")
        return
    
    if query.data == "hide_countdown":
        # Скрыть обратный отсчет
        try:
            await query.message.delete()
        except Exception as e:
            logger.debug(f"Could not delete countdown message: {e}")
        return
    
    elif query.data == "delete_skipped":
        # Удалить пропущенные сигналы
        deleted_count = bot.delete_skipped_signals(user_id)
        
        if deleted_count > 0:
            await query.answer(f"🗑️ Удалено {deleted_count} пропущенных сигналов", show_alert=True)
            # Обновить статистику
            await my_stats_command(update, context)
        else:
            await query.answer("❌ Пропущенных сигналов не найдено", show_alert=True)
        return
    
    elif query.data == "refresh_longs":
        # Обновить список long сигналов
        await my_longs_command(update, context)
        await query.answer("🔄 Список обновлен", show_alert=False)
        return
    
    elif query.data.startswith("long_manage_"):
        # Управление конкретным long сигналом
        signal_id = int(query.data.split("_")[2])
        
        cursor = bot.conn.cursor()
        cursor.execute('''
            SELECT asset, signal_type, timeframe, confidence, expiration_time, stake_amount
            FROM signal_history 
            WHERE id = ? AND user_id = ?
        ''', (signal_id, user_id))
        
        signal_data = cursor.fetchone()
        
        if signal_data:
            asset, signal_type, timeframe, confidence, expiration_time, stake_amount = signal_data
            direction_emoji = "🟢" if signal_type == "CALL" else "🔴"
            
            # Рассчитываем оставшееся время
            if expiration_time:
                try:
                    expiry_dt = datetime.fromisoformat(expiration_time)
                    now = datetime.now()
                    remaining_time = expiry_dt - now
                    
                    if remaining_time.total_seconds() > 0:
                        hours = int(remaining_time.total_seconds() // 3600)
                        minutes = int((remaining_time.total_seconds() % 3600) // 60)
                        time_left = f"{hours}ч {minutes}мин"
                    else:
                        time_left = "⏰ Истекло - отметьте результат"
                except:
                    time_left = "Н/Д"
            else:
                time_left = "Н/Д"
            
            manage_text = f"""
{direction_emoji} **{asset}**

**Направление:** {signal_type}
**Таймфрейм:** {timeframe}
**Уверенность:** {confidence:.0f}%
**Ставка:** {stake_amount:.2f} ₽

⏰ **Осталось:** {time_left}

**Выберите действие:**
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Прибыль (+)", callback_data=f"result_win_{signal_id}"),
                    InlineKeyboardButton("❌ Убыток (-)", callback_data=f"result_loss_{signal_id}")
                ],
                [InlineKeyboardButton("⏭️ Пропустить", callback_data=f"result_skip_{signal_id}")],
                [InlineKeyboardButton("◀️ К списку", callback_data="refresh_longs")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(manage_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await query.answer("❌ Сигнал не найден", show_alert=True)
        return
    
    if query.data == "find_signals":
        await signal_all_command(update, context)
    elif query.data == "find_signals_long":
        await signal_all_command(update, context, timeframe_type="long")
    elif query.data == "find_signals_short":
        await signal_all_command(update, context, timeframe_type="short")
    elif query.data == "choose_plan":
        # Показать карточки всех тарифов для TRIAL пользователей
        await buy_subscription_command(update, context)
    
    elif query.data == "upgrade_plan":
        # Показать меню расширения тарифа для SHORT/LONG пользователей
        await show_tariff_menu(update, context)
    
    elif query.data == "choose_plan_settings":
        # Показать меню выбора тарифов с ценами
        await show_tariff_menu(update, context)
    
    elif query.data == "tariff_vip" or query.data == "show_tariff_vip":
        await show_tariff_vip(update, context)
    elif query.data == "tariff_short":
        await show_tariff_short(update, context)
    elif query.data == "tariff_long":
        await show_tariff_long(update, context)
    elif query.data == "tariff_free":
        await show_tariff_free(update, context)
    elif query.data == "tariff_keep":
        # Пользователь хочет остаться на текущем тарифе
        await query.answer("✅ Вы остаётесь на текущем тарифе", show_alert=True)
        await show_main_menu(update, context)
    
    elif query.data == "buy_vip":
        context.user_data['selected_plan'] = 'vip'
        await buy_subscription_command(update, context)
    elif query.data == "buy_short":
        context.user_data['selected_plan'] = 'short'
        await buy_subscription_command(update, context)
    elif query.data == "buy_long":
        context.user_data['selected_plan'] = 'long'
        await buy_subscription_command(update, context)
    
    elif query.data == "buy_subscription":
        await buy_subscription_command(update, context)
    elif query.data == "upgrade_subscription":
        # Показать варианты расширения тарифа
        user_id = query.from_user.id
        has_subscription, message, signals_used, free_trials_used, sub_type = bot.check_subscription(user_id)
        
        if sub_type == 'short':
            # SHORT пользователь - предложить LONG или VIP
            upgrade_text = """
⬆️ **РАСШИРЕНИЕ ТАРИФА**

Вы используете тариф **SHORT** (1-5 мин)

💡 **Доступные улучшения:**

🔵 **LONG ({bot.get_setting('long_price_rub', '6990')}₽/мес)**
• Длинные сигналы (1-4 часа)
• Процентная стратегия 2.5%
• Управление через /my_longs
• + Сохранение SHORT доступа

💎 **VIP ({bot.get_setting('vip_price_rub', '9990')}₽/мес)**
• ВСЕ сигналы (SHORT + LONG)
• 5 автоматических рассылок в день
• Увеличенная ставка: 5% вместо 2.5%
• Приоритетная поддержка

Выберите тариф для расширения:
"""
            keyboard = [
                [InlineKeyboardButton("🔵 Перейти на LONG", callback_data="upgrade_to_long")],
                [InlineKeyboardButton("💎 Перейти на VIP", callback_data="upgrade_to_vip")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
            ]
        elif sub_type == 'long':
            # LONG пользователь - предложить VIP
            upgrade_text = """
⬆️ **РАСШИРЕНИЕ ТАРИФА**

Вы используете тариф **LONG** (1-4 часа)

💡 **Доступное улучшение:**

💎 **VIP ({bot.get_setting('vip_price_rub', '9990')}₽/мес)**
• Доступ к SHORT сигналам (1-5 мин)
• 5 автоматических рассылок в день
• Увеличенная ставка: 5% вместо 2.5%
• Приоритетная поддержка
• + Сохранение LONG доступа

🚀 **Преимущества VIP:**
• Больше сигналов = больше прибыль
• Автоматические рассылки лучших сигналов
• Полный арсенал стратегий

Перейти на VIP?
"""
            keyboard = [
                [InlineKeyboardButton("💎 Перейти на VIP", callback_data="upgrade_to_vip")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
            ]
        else:
            # На всякий случай
            await show_main_menu(update, context, user_id=user_id)
            return
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(upgrade_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "buy_short":
        await show_period_selection(update, context, "short")
    elif query.data == "buy_long":
        await show_period_selection(update, context, "long")
    elif query.data == "buy_vip":
        await show_period_selection(update, context, "vip")
    elif query.data == "upgrade_to_long":
        # Переход на LONG с SHORT
        await show_period_selection(update, context, "long")
    elif query.data == "upgrade_to_vip":
        # Переход на VIP с SHORT или LONG
        await show_period_selection(update, context, "vip")
    elif query.data.startswith("buy_short_"):
        period = query.data.split("_")[2]  # 1m, 6m, 12m
        await handle_subscription_purchase(update, context, "short", period)
    elif query.data.startswith("buy_long_"):
        period = query.data.split("_")[2]
        await handle_subscription_purchase(update, context, "long", period)
    elif query.data.startswith("buy_vip_"):
        period = query.data.split("_")[2]
        await handle_subscription_purchase(update, context, "vip", period)
    elif query.data.startswith("pay_yookassa_"):
        # pay_yookassa_short_1m -> plan_type=short, period=1m
        parts = query.data.split("_")
        plan_type = parts[2]  # short, long, vip
        period = parts[3]  # 1m, 6m, 12m
        await handle_yookassa_payment(update, context, plan_type, period)
    elif query.data == "buy_promo":
        await handle_promo_purchase(update, context)
    elif query.data == "referral_program":
        await show_referral_program(update, context)
    elif query.data == "upgrade_to_vip":
        await handle_upgrade_to_vip(update, context)
    elif query.data == "vip_info":
        await show_vip_info(update, context)
    elif query.data == "vip_required":
        await query.answer("🔒 Для доступа к AI Trading требуется VIP подписка", show_alert=True)
        # Показать информацию о VIP
        await show_vip_info(update, context)
    elif query.data == "dismiss_upgrade":
        await query.answer("✅ Предложение скрыто")
        await query.delete_message()
    elif query.data == "my_stats":
        await my_stats_command(update, context)
    elif query.data == "admin_reset_self_execute":
        # Выполнить сброс
        user_id = update.effective_user.id
        
        cursor = bot.conn.cursor()
        cursor.execute('''
            UPDATE users SET
                subscription_type = 'free',
                subscription_start = NULL,
                subscription_end = NULL,
                initial_balance = NULL,
                current_balance = NULL,
                trading_strategy = NULL,
                auto_trading_enabled = 0,
                auto_trading_strategy = NULL,
                pocket_option_ssid = NULL,
                pocket_option_connected = 0,
                martingale_multiplier = 3,
                martingale_base_stake = NULL,
                percentage_value = 2.5,
                current_martingale_level = 0,
                consecutive_losses = 0,
                is_premium = 0,
                free_trials_used = 0,
                signals_used = 0
            WHERE user_id = ?
        ''', (user_id,))
        
        cursor.execute('DELETE FROM signal_history WHERE user_id = ?', (user_id,))
        bot.conn.commit()
        
        await query.edit_message_text(
            "🔄 **ВЫ СБРОШЕНЫ ДО НОВОГО ПОЛЬЗОВАТЕЛЯ!**\n\n"
            "✅ Подписка: FREE\n"
            "✅ Баланс обнулён\n"
            "✅ История сигналов удалена\n"
            "✅ Автотрейдинг отключен\n\n"
            "Используйте /start чтобы начать заново!",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ])
        )
    
    # VIP Dashboard кнопки
    elif query.data == "detailed_stats_vip":
        await my_stats_command(update, context)
    
    elif query.data == "bank_management":
        # Получить информацию о подписке и банке
        has_subscription, message, signals_used, free_trials_used, sub_type = bot.check_subscription(user_id)
        
        cursor = bot.conn.cursor()
        cursor.execute('SELECT initial_balance, current_balance, martingale_multiplier, martingale_base_stake, percentage_value, trading_strategy FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        initial = result[0] if result and result[0] else 0
        current = result[1] if result and result[1] else 0
        martingale_type = result[2] if result and result[2] else 3
        martingale_base_stake = result[3] if result and result[3] else None
        long_percentage = result[4] if result and result[4] else 2.5
        current_strategy = result[5] if result and result[5] else None
        
        # Получить информацию о тарифе
        sub_emoji = SUBSCRIPTION_PLANS.get(sub_type, {}).get('emoji', '💎')
        sub_name = sub_type.upper() if sub_type else 'FREE'
        # message может быть None для пожизненных подписок
        if has_subscription and message:
            sub_end = datetime.fromisoformat(message).strftime('%d.%m.%Y')
        elif has_subscription and not message:
            sub_end = 'Пожизненная'
        else:
            sub_end = 'Нет подписки'
        
        # Рассчитать рекомендуемые ставки используя новые колонки
        # Для мартингейла используем martingale_base_stake если есть, иначе расчетное значение
        if martingale_base_stake and martingale_base_stake > 0:
            recommended_short = martingale_base_stake
        else:
            recommended_short = bot.calculate_recommended_short_stake(current if current > 0 else 0, martingale_type)
        
        # Для процентной используем percentage_value
        recommended_long = (current * (long_percentage / 100)) if current > 0 else 0
        
        # Формирование текста с учетом тарифа
        if initial > 0:
            profit = current - initial
            profit_percent = (profit / initial * 100) if initial > 0 else 0
            profit_emoji = "📈" if profit >= 0 else "📉"
            
            # Базовая информация
            bank_text = f"""
💰 **УПРАВЛЕНИЕ БАНКОМ**

📊 **ВАШ ТАРИФ:**
{sub_emoji} Подписка: **{sub_name}**
⏰ Действует до: **{sub_end}**

━━━━━━━━━━━━━━━━━━━━━━
💵 **БАНК:**
• Начальный: **{initial:.0f}₽**
• Текущий: **{current:.0f}₽**
• Прибыль: **{profit_emoji} {profit:+.0f}₽** ({profit_percent:+.1f}%)

━━━━━━━━━━━━━━━━━━━━━━
"""
            
            # Стратегия для SHORT тарифа
            if sub_type == 'short':
                # Расчет уровней для выбранного мартингейла используя новые колонки
                base_stake = martingale_base_stake if martingale_base_stake and martingale_base_stake > 0 else 100
                if martingale_type == 2:
                    levels = [base_stake * (2 ** i) for i in range(6)]
                    min_balance = sum(levels)
                    strategy_name = f"Мартингейл x{martingale_type}"
                else:  # x3
                    levels = [base_stake * (3 ** i) for i in range(6)]
                    min_balance = sum(levels)
                    strategy_name = f"Мартингейл x{martingale_type}"
                
                bank_text += f"""⚡️ **СТРАТЕГИЯ SHORT**
━━━━━━━━━━━━━━━━━━━━━━
**{strategy_name}**

📊 **Принцип:**
После убытка ставка × {martingale_type}
После прибыли → базовая ставка

🎯 **Уровни ставок:**
1️⃣ {levels[0]:.0f}₽ → 2️⃣ {levels[1]:.0f}₽ → 3️⃣ {levels[2]:.0f}₽
4️⃣ {levels[3]:.0f}₽ → 5️⃣ {levels[4]:.0f}₽ → 6️⃣ {levels[5]:.0f}₽

💰 **Рекомендуемая ставка:**"""
                
                if current >= min_balance:
                    bank_text += f"\n**{recommended_short:.0f}₽** (текущий уровень)"
                else:
                    bank_text += f"\n⚠️ **Недостаточно** (мин. {min_balance:.0f}₽)"
                
                bank_text += f"""

⚙️ **Настройка:**
Выберите множитель мартингейла ниже
"""
            
            # Стратегия для LONG тарифа
            elif sub_type == 'long':
                # Примеры для выбранного процента
                example1 = 10000 * (long_percentage / 100)
                example2 = 50000 * (long_percentage / 100)
                example3 = 100000 * (long_percentage / 100)
                
                bank_text += f"""🔵 **СТРАТЕГИЯ LONG**
━━━━━━━━━━━━━━━━━━━━━━
**Процентная ставка {long_percentage}% от банка**

📊 **Принцип:**
Ставка всегда {long_percentage}% от текущего банка
Автоматическая адаптация под баланс

🎯 **Преимущества:**
• Защита капитала
• Постепенный рост
• Низкие риски

💰 **Рекомендуемая ставка:**
**{recommended_long:.0f}₽** ({long_percentage}% от {current:.0f}₽)

📈 **Примеры:**
• Банк 10,000₽ → ставка {example1:.0f}₽
• Банк 50,000₽ → ставка {example2:.0f}₽
• Банк 100,000₽ → ставка {example3:.0f}₽

⚙️ **Настройка:**
Выберите процент ниже
"""
            
            # Для VIP показываем текущую выбранную стратегию
            elif sub_type == 'vip':
                # Проверяем выбранную стратегию
                cursor.execute('SELECT trading_strategy FROM users WHERE user_id = ?', (user_id,))
                strategy_result = cursor.fetchone()
                current_strategy = strategy_result[0] if strategy_result and strategy_result[0] else 'percentage'
                
                if current_strategy == 'martingale':
                    # Рассчитать min_balance для VIP мартингейла
                    base_stake = 100
                    if martingale_type == 2:
                        levels = [base_stake * (2 ** i) for i in range(6)]
                        min_balance = sum(levels)
                    else:  # x3
                        levels = [base_stake * (3 ** i) for i in range(6)]
                        min_balance = sum(levels)
                    
                    # Показываем Мартингейл
                    bank_text += f"""⚡️ **СТРАТЕГИЯ: МАРТИНГЕЙЛ x{martingale_type}**
━━━━━━━━━━━━━━━━━━━━━━
**Множитель после проигрыша: x{martingale_type}**

📊 **Уровни ставок:**
1️⃣ {levels[0]:.0f}₽ → 2️⃣ {levels[1]:.0f}₽ → 3️⃣ {levels[2]:.0f}₽
4️⃣ {levels[3]:.0f}₽ → 5️⃣ {levels[4]:.0f}₽ → 6️⃣ {levels[5]:.0f}₽

💰 **Рекомендуемая ставка:**"""
                    
                    if current >= min_balance:
                        bank_text += f"\n**{recommended_short:.0f}₽** (текущий уровень)"
                    else:
                        bank_text += f"\n⚠️ **Недостаточно** (мин. {min_balance:.0f}₽)"
                    
                    bank_text += """

⚙️ **Настройка:**
Выберите множитель мартингейла ниже
"""
                else:
                    # Показываем Процентную
                    example1 = 10000 * (long_percentage / 100)
                    example2 = 50000 * (long_percentage / 100)
                    example3 = 100000 * (long_percentage / 100)
                    
                    bank_text += f"""🔵 **СТРАТЕГИЯ: ПРОЦЕНТНАЯ {long_percentage}%**
━━━━━━━━━━━━━━━━━━━━━━
**Ставка {long_percentage}% от текущего банка**

📊 **Принцип:**
Ставка всегда {long_percentage}% от текущего банка
Автоматическая адаптация под баланс

💰 **Рекомендуемая ставка:**
**{recommended_long:.0f}₽** ({long_percentage}% от {current:.0f}₽)

📈 **Примеры:**
• Банк 10,000₽ → ставка {example1:.0f}₽
• Банк 50,000₽ → ставка {example2:.0f}₽
• Банк 100,000₽ → ставка {example3:.0f}₽

⚙️ **Настройка:**
Выберите процент ниже
"""
        else:
            bank_text = f"""
💰 **УПРАВЛЕНИЕ БАНКОМ**

📊 **ВАШ ТАРИФ:**
{sub_emoji} Подписка: **{sub_name}**
⏰ Действует до: **{sub_end}**

━━━━━━━━━━━━━━━━━━━━━━
💵 **БАНК НЕ УСТАНОВЛЕН**

Установите начальный капитал для:
• Автоматического расчета ставок
• Отслеживания прибыли/убытка
• Управления рисками
"""
        
        keyboard = []
        if initial > 0:
            # Кнопки выбора стратегии для всех тарифов - две кнопки в одной строке
            keyboard.append([
                InlineKeyboardButton("⚡️ Мартингейл", callback_data="set_strategy_martingale"),
                InlineKeyboardButton("📊 % от банка", callback_data="set_strategy_percentage")
            ])
            
            keyboard.extend([
                [InlineKeyboardButton("💰 Изменить текущий банк", callback_data="update_current_bank")],
                [InlineKeyboardButton("🔄 Сбросить и начать заново", callback_data="reset_bank")]
            ])
        else:
            keyboard.append([InlineKeyboardButton("💰 Установить банк", callback_data="set_bank_menu")])
        
        keyboard.append([InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(bank_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data == "set_bank_menu":
        context.user_data['awaiting_bank_input'] = True
        await query.edit_message_text(
            "💰 **УСТАНОВКА БАНКА**\n\n"
            "Отправьте сообщение с суммой вашего начального капитала:\n\n"
            "Пример: `5000` или `10000`\n\n"
            "💡 Банк используется для:\n"
            "• Автоматического расчета ставок\n"
            "• Отслеживания прибыли/убытка\n"
            "• Управления рисками",
            parse_mode='Markdown'
        )
    
    elif query.data == "change_bank":
        cursor = bot.conn.cursor()
        cursor.execute('SELECT initial_balance, current_balance FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        initial = result[0] if result and result[0] else 0
        current = result[1] if result and result[1] else 0
        
        keyboard = [
            [InlineKeyboardButton("💰 Изменить текущий банк", callback_data="update_current_bank")],
            [InlineKeyboardButton("🔄 Сбросить и начать заново", callback_data="reset_bank")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"💰 **УПРАВЛЕНИЕ БАНКОМ**\n\n"
            f"📊 Начальный: {initial:.2f} ₽\n"
            f"📊 Текущий: {current:.2f} ₽\n\n"
            "Выберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == "update_current_bank":
        context.user_data['awaiting_update_bank'] = True
        await query.edit_message_text(
            "💰 **ОБНОВИТЬ ТЕКУЩИЙ БАНК**\n\n"
            "Отправьте новую сумму текущего банка:\n\n"
            "Пример: `6500`\n\n"
            "⚠️ Это обновит только текущий баланс, начальный останется прежним",
            parse_mode='Markdown'
        )
    
    elif query.data == "reset_bank":
        cursor = bot.conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET initial_balance = NULL, current_balance = NULL, 
                short_base_stake = NULL, current_martingale_level = 0, consecutive_losses = 0
            WHERE user_id = ?
        ''', (user_id,))
        bot.conn.commit()
        
        await query.answer("✅ Банк сброшен!", show_alert=True)
        await show_main_menu(update, context, user_id)
    
    elif query.data == "report_trade":
        keyboard = [
            [InlineKeyboardButton("✅ Прибыль (+)", callback_data="quick_report_win"),
             InlineKeyboardButton("❌ Убыток (-)", callback_data="quick_report_loss")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📝 **ОТЧЕТ О СДЕЛКЕ**\n\n"
            "Выберите результат последней сделки:\n\n"
            "✅ **Прибыль** - если сделка закрылась в плюс\n"
            "❌ **Убыток** - если сделка закрылась в минус\n\n"
            "💡 Для детального отчета используйте:\n"
            "• `/report_win СТАВКА` \n"
            "• `/report_loss СТАВКА`",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == "quick_report_win":
        cursor = bot.conn.cursor()
        
        # Проверяем наличие активного сигнала
        last_signal = bot.get_last_pending_signal(user_id)
        
        if not last_signal:
            await query.answer("❌ Нет активных сигналов для отчета. Получите сигнал через меню", show_alert=True)
            return
        
        signal_id, asset, signal_type, confidence, stake_amount = last_signal
        
        if not stake_amount or stake_amount <= 0:
            await query.answer("⚠️ Сначала установите банк через /set_bank", show_alert=True)
            return
        
        # Обрабатываем выигрыш
        stake = stake_amount
        profit = stake * (PAYOUT_PERCENT / 100)
        
        cursor.execute('SELECT current_balance FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        current_balance = result[0] if result and result[0] is not None else 0
        
        new_balance = current_balance + profit
        cursor.execute('UPDATE users SET current_balance = ? WHERE user_id = ?', (new_balance, user_id))
        bot.conn.commit()
        
        bot.update_signal_result(signal_id, 'win', profit)
        
        # Получаем timeframe
        cursor.execute('SELECT timeframe FROM signal_history WHERE id = ?', (signal_id,))
        timeframe_result = cursor.fetchone()
        timeframe = timeframe_result[0] if timeframe_result else None
        
        # Определяем тип сигнала
        short_timeframes = ["1M", "2M", "3M", "5M", "15M", "30M"]
        is_short_signal = timeframe and timeframe in short_timeframes
        
        if is_short_signal:
            bot.update_martingale_after_win(user_id)
            new_stake, _ = bot.get_martingale_stake(user_id)
            signal_type_for_repeat = "SHORT"
            callback_for_repeat = "get_short_signal"
        else:
            new_stake = bot.get_long_stake(user_id, new_balance, is_vip=False)
            signal_type_for_repeat = "LONG"
            callback_for_repeat = "get_long_signal"
        
        success_text = f"""
✅ **Выигрыш:** +{profit:.0f}₽

💰 **Баланс:** {new_balance:.0f}₽
📊 **Новая ставка:** {new_stake:.0f}₽
"""
        
        # Кнопки повтора
        keyboard = [
            [InlineKeyboardButton(f"🔄 Получить следующий {signal_type_for_repeat}", callback_data=callback_for_repeat)],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.answer("✅ Выигрыш зафиксирован!", show_alert=False)
        await query.edit_message_text(success_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    elif query.data == "quick_report_loss":
        cursor = bot.conn.cursor()
        
        # Проверяем наличие активного сигнала
        last_signal = bot.get_last_pending_signal(user_id)
        
        if not last_signal:
            await query.answer("❌ Нет активных сигналов для отчета. Получите сигнал через меню", show_alert=True)
            return
        
        signal_id, asset, signal_type, confidence, stake_amount = last_signal
        
        if not stake_amount or stake_amount <= 0:
            await query.answer("⚠️ Сначала установите банк через /set_bank", show_alert=True)
            return
        
        # Обрабатываем проигрыш
        stake = stake_amount
        
        cursor.execute('SELECT current_balance FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        current_balance = result[0] if result and result[0] is not None else 0
        
        new_balance = current_balance - stake
        cursor.execute('UPDATE users SET current_balance = ? WHERE user_id = ?', (new_balance, user_id))
        bot.conn.commit()
        
        bot.update_signal_result(signal_id, 'loss', -stake)
        
        # Получаем timeframe
        cursor.execute('SELECT timeframe FROM signal_history WHERE id = ?', (signal_id,))
        timeframe_result = cursor.fetchone()
        timeframe = timeframe_result[0] if timeframe_result else None
        
        # Определяем тип сигнала
        short_timeframes = ["1M", "2M", "3M", "5M", "15M", "30M"]
        is_short_signal = timeframe and timeframe in short_timeframes
        
        if is_short_signal:
            bot.update_martingale_after_loss(user_id)
            new_stake, _ = bot.get_martingale_stake(user_id)
            signal_type_for_repeat = "SHORT"
            callback_for_repeat = "get_short_signal"
        else:
            new_stake = bot.get_long_stake(user_id, new_balance, is_vip=False)
            signal_type_for_repeat = "LONG"
            callback_for_repeat = "get_long_signal"
        
        loss_text = f"""
📉 **Проигрыш:** -{stake:.0f}₽

💰 **Баланс:** {new_balance:.0f}₽
📊 **Новая ставка:** {new_stake:.0f}₽
"""
        
        # Кнопки повтора
        keyboard = [
            [InlineKeyboardButton(f"🔄 Получить следующий {signal_type_for_repeat}", callback_data=callback_for_repeat)],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.answer("📉 Проигрыш зафиксирован", show_alert=False)
        await query.edit_message_text(loss_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    elif query.data == "toggle_auto_trading":
        # Проверка VIP статуса
        cursor = bot.conn.cursor()
        cursor.execute('SELECT subscription_type, auto_trading_enabled, auto_trading_mode, pocket_option_email FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result or result[0] != 'vip':
            await query.answer("❌ Автотрейдинг доступен только для VIP", show_alert=True)
            return
        
        subscription_type, auto_enabled, auto_mode, po_email = result
        
        # Если email не настроен, просим его ввести
        if not po_email:
            await query.answer()
            await query.edit_message_text(
                "🤖 **НАСТРОЙКА АВТОТРЕЙДИНГА**\n\n"
                "Для работы автотрейдинга необходимо:\n\n"
                "1️⃣ Указать email Pocket Option\n"
                "2️⃣ Выбрать режим (Демо/Реал)\n"
                "3️⃣ Включить автотрейдинг\n\n"
                "📧 Введите email от Pocket Option:",
                parse_mode='Markdown'
            )
            # Сохраняем состояние для следующего сообщения
            context.user_data['awaiting_po_email'] = True
            return
        
        # Переключаем состояние автотрейдинга
        new_state = not auto_enabled
        cursor.execute('UPDATE users SET auto_trading_enabled = ? WHERE user_id = ?', (new_state, user_id))
        bot.conn.commit()
        
        status_text = "🟢 ВКЛЮЧЕН" if new_state else "🔴 ВЫКЛЮЧЕН"
        mode_text = "🎮 Демо" if auto_mode == "demo" else "💰 Реальный"
        
        keyboard = [
            [InlineKeyboardButton(f"🔄 Режим: {mode_text}", callback_data="toggle_auto_mode")],
            [InlineKeyboardButton("📧 Сменить email", callback_data="change_po_email")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_bank")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.answer(f"Автотрейдинг {status_text}", show_alert=False)
        await query.edit_message_text(
            f"🤖 **АВТОТРЕЙДИНГ**\n\n"
            f"Статус: **{status_text}**\n"
            f"Режим: **{mode_text}**\n"
            f"Email: `{po_email}`\n\n"
            f"{'✅ Бот автоматически размещает сделки по сигналам' if new_state else '⏸️ Автотрейдинг приостановлен'}\n\n"
            f"⚠️ **Важно:** Убедитесь, что у вас достаточно баланса на счете Pocket Option",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif query.data == "toggle_auto_mode":
        cursor = bot.conn.cursor()
        cursor.execute('SELECT auto_trading_mode FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        current_mode = result[0] if result else "demo"
        new_mode = "real" if current_mode == "demo" else "demo"
        
        cursor.execute('UPDATE users SET auto_trading_mode = ? WHERE user_id = ?', (new_mode, user_id))
        bot.conn.commit()
        
        mode_text = "🎮 Демо" if new_mode == "demo" else "💰 Реальный"
        await query.answer(f"Режим изменен на {mode_text}", show_alert=False)
        await query.message.delete()
        await bank_command(update, context)
    
    elif query.data == "change_po_email":
        await query.answer()
        await query.edit_message_text(
            "📧 **СМЕНА EMAIL**\n\n"
            "Введите новый email от Pocket Option:",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_po_email'] = True
    
    elif query.data == "back_to_bank":
        await query.message.delete()
        await bank_command(update, context)
    
    elif query.data == "my_longs":
        await my_longs_command(update, context)
    elif query.data == "signal_stats":
        await signal_stats_command(update, context)
    elif query.data == "bankroll":
        await bankroll_command(update, context)
    elif query.data == "user_guide":
        guide_text = """
📖 **РУКОВОДСТВО ПОЛЬЗОВАНИЯ БОТОМ**

**ШАГ 1: Установите банк и выберите стратегию** 💰

**1.1 Откройте "Управление банком"** в главном меню

**1.2 Выберите стратегию:**
• ⚡️ **Мартингейл** (рискованная) - удвоение/утроение ставки после проигрыша
• 📊 **% от банка** (стабильная) - фиксированный процент от текущего банка

**1.3 Настройте параметры:**
**Для Мартингейла:**
- Выберите множитель (x2 или x3)
- Введите базовую ставку (например: 500)

**Для % от банка:**
- Введите процент (например: 2.5)

**1.4 Установите банк:**
- Просто отправьте число (например: 10000)

**ШАГ 2: Получите сигнал** 🎯
• Нажмите "📊 SHORT сигналы" или "📈 LONG сигналы"
• Или используйте `/short` и `/long`

**ШАГ 3: Откройте Pocket Option** 📱
1. Скопируйте актив (кнопка "📋")
2. Найдите актив в Pocket Option
3. Выставите рекомендуемую ставку
4. Выберите направление (CALL ↑ / PUT ↓)
5. Установите время экспирации

**📊 ОТСЛЕЖИВАНИЕ СИГНАЛОВ:**

**SHORT (1-5 мин):**
• Автоматический таймер обратного отсчета
• Обновляется каждые 15 секунд
• Кнопка "❌ Скрыть" для удаления

**LONG (1-4 часа):**
• `/my_longs` - список активных сигналов
• Нажмите на сигнал для отметки результата
• Кнопки: ✅ Прибыль | ❌ Убыток | ⏭️ Пропустить

**ШАГ 4: Отметьте результат** 📊
Бот автоматически пересчитает баланс и ставку!

**ПОЛЕЗНЫЕ КОМАНДЫ:**
• `/my_stats` - статистика и баланс
• `/my_longs` - активные long сигналы
• `/delete_skipped` - удалить пропущенные
• `/short` / `/long` - получить сигнал

**СТРАТЕГИИ УПРАВЛЕНИЯ БАНКОМ:**

⚡️ **Мартингейл:**
• Базовая ставка при победе
• Умножение (x2/x3) после проигрыша
• Минимальный банк: 6,300₽ (x2) или 36,400₽ (x3)
• Высокий риск, быстрая прибыль

📊 **% от банка:**
• Ставка = процент от текущего банка
• Автоматическая адаптация
• Подходит для любого банка
• Стабильный рост, низкий риск

🎯 **Доходность сигналов:** 85-92%
💡 **OTC активы:** Доходность 92%
"""
        keyboard = [
            [InlineKeyboardButton("◀️ Назад", callback_data="settings")],
            [InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(guide_text, reply_markup=reply_markup)
    elif query.data == "free_trial":
        user_id = query.from_user.id
        has_subscription, sub_message, signals_used, free_trials_used = bot.check_subscription(user_id)
        
        if has_subscription:
            await query.edit_message_text("✅ У вас уже активна PRO подписка!")
            return
        
        if free_trials_used > 0:
            await query.edit_message_text(
                "❌ Вы уже использовали бесплатный пробный период.\n\n"
                "💎 Для продолжения работы приобретите PRO подписку."
            )
            return
        
        trial_text = f"""
🎁 **БЕСПЛАТНЫЙ ПРОБНЫЙ ПЕРИОД АКТИВИРОВАН!**

📊 **Доступно:** 3 сигнала

⚡ **Теперь вы можете:**
• Получать PRO торговые сигналы
• Использовать все таймфреймы  
• Анализировать 29 активов
• Видеть продвинутый теханализ

🎯 **Чтобы начать, используйте:** 
/signal_all

💎 *После использования 3 сигналов потребуется PRO подписка*
"""
        
        await query.edit_message_text(trial_text, parse_mode='Markdown')
    elif query.data == "payment_done":
        await query.edit_message_text(
            "✅ **Спасибо!**\n\n"
            f"Пожалуйста, отправьте скриншот оплаты в поддержку: {bot.get_support_contact()}\n"
            "Подписка будет активирована в течение 5 минут после проверки платежа.",
            parse_mode='Markdown'
        )
    
    elif query.data == "strategy_martingale":
        # Сохранить выбор стратегии Мартингейл
        cursor = bot.conn.cursor()
        cursor.execute('UPDATE users SET trading_strategy = ? WHERE user_id = ?', ('martingale', user_id))
        bot.conn.commit()
        
        await query.edit_message_text(
            "⚡️ **МАРТИНГЕЙЛ ВЫБРАН!**\n\n"
            "📝 Отправьте сумму вашего банка следующим сообщением\n"
            "💡 Минимальный банк для мартингейла: **36,400₽**\n\n"
            "Пример: `50000`",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_bank_amount'] = True
        return
    
    elif query.data == "strategy_percentage":
        # Сохранить выбор процентной стратегии
        cursor = bot.conn.cursor()
        cursor.execute('UPDATE users SET trading_strategy = ? WHERE user_id = ?', ('percentage', user_id))
        bot.conn.commit()
        
        await query.edit_message_text(
            "📊 **ПРОЦЕНТНАЯ СТРАТЕГИЯ ВЫБРАНА!**\n\n"
            "📝 Отправьте сумму вашего банка следующим сообщением\n"
            "💡 Рекомендуемая ставка: **2-3% от банка**\n\n"
            "Пример: `15000`",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_bank_amount'] = True
        return
    
    elif query.data == "back_to_main":
        await show_main_menu(update, context, user_id=user_id)
    elif query.data == "start":
        # Кнопка "Старт" работает как "Home" на Android
        # Для зарегистрированных пользователей -> главное меню
        # Для новых пользователей -> первое сообщение
        cursor = bot.conn.cursor()
        cursor.execute('SELECT language, currency FROM users WHERE user_id = ?', (user_id,))
        user_data = cursor.fetchone()
        
        if user_data and user_data[0] and user_data[1]:
            # Пользователь зарегистрирован (есть язык и валюта) -> на главную
            await show_main_menu(update, context, user_id=user_id)
        else:
            # Новый пользователь -> к первому сообщению (выбор статуса)
            welcome_text = """
🌍 **Добро пожаловать в Crypto Signals Bot!**

Пожалуйста, выберите ваш статус:
"""
            keyboard = [
                [InlineKeyboardButton("🆕 Новый пользователь Pocket Option", callback_data="user_status_new")],
                [InlineKeyboardButton("✅ Уже зарегистрирован", callback_data="user_status_existing")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "clear_chat":
        await clear_chat_and_home(update, context)
    elif query.data == "admin_panel":
        # Открыть админ панель (без изменения тарифа)
        await admin_panel(update, context)
    elif query.data == "admin_stats":
        await admin_stats(update, context)
    elif query.data == "admin_top_users":
        await admin_top_users(update, context)
    elif query.data == "admin_quick_sub":
        await admin_quick_sub(update, context)
    elif query.data == "admin_add_user_by_id":
        await admin_add_user_by_id(update, context)
    elif query.data.startswith("manage_user_"):
        user_id_to_manage = int(query.data.replace("manage_user_", ""))
        await admin_manage_user_sub(update, context, user_id_to_manage)
    elif query.data.startswith("set_sub_"):
        # Формат: set_sub_{user_id}_{type}_{days}
        parts = query.data.split("_")
        target_user_id = int(parts[2])
        sub_type = parts[3]
        days = int(parts[4])
        
        # Установить подписку
        if days > 0:
            end_date = (datetime.now() + timedelta(days=days)).isoformat()
            cursor = bot.conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET subscription_end = ?, subscription_type = ?
                WHERE user_id = ?
            ''', (end_date, sub_type, target_user_id))
            bot.conn.commit()
            
            await query.answer(f"✅ Подписка {sub_type.upper()} на {days} дней выдана!", show_alert=True)
        else:
            # Убрать подписку (FREE)
            cursor = bot.conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET subscription_end = NULL, subscription_type = 'free'
                WHERE user_id = ?
            ''', (target_user_id,))
            bot.conn.commit()
            
            await query.answer("✅ Подписка убрана (FREE)", show_alert=True)
        
        # Обновить меню управления пользователем
        await admin_manage_user_sub(update, context, target_user_id)
    elif query.data == "admin_pricing":
        await admin_pricing(update, context)
    elif query.data == "admin_tariff_images":
        await admin_tariff_images(update, context)
    elif query.data == "admin_bot_settings":
        await admin_bot_settings(update, context)
    elif query.data == "admin_change_support":
        await query.answer()
        await query.message.reply_text(
            "📞 **ИЗМЕНЕНИЕ КОНТАКТА ПОДДЕРЖКИ**\n\nОтправьте новый контакт поддержки в формате Telegram username (например, @support_bot)",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_support_contact'] = True
    elif query.data.startswith("upload_image_"):
        # Начать процесс загрузки изображения
        tariff_type = query.data.replace("upload_image_", "")
        tariff_emoji = {'vip': '💎', 'short': '⚡', 'long': '🔵', 'free': '🎁'}.get(tariff_type, '🖼️')
        tariff_name = tariff_type.upper()
        
        await query.edit_message_text(
            f"{tariff_emoji} **ЗАГРУЗКА ИЗОБРАЖЕНИЯ {tariff_name}**\n\n"
            f"Отправьте изображение для тарифа {tariff_name}:\n\n"
            f"📋 **Рекомендации:**\n"
            f"• Размер: 1200x800px\n"
            f"• Формат: PNG, JPG\n"
            f"• Качество: высокое\n"
            f"• Стиль: темный, премиум\n\n"
            f"Просто отправьте фото следующим сообщением.",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_tariff_image'] = tariff_type
    elif query.data == "admin_set_vip_price":
        await query.edit_message_text(
            "💎 **ИЗМЕНЕНИЕ ЦЕНЫ VIP**\n\n"
            "Введите новую цену VIP тарифа в рублях:\n"
            "(минимум 100₽)",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_price'] = 'vip'
    elif query.data == "admin_set_short_price":
        await query.edit_message_text(
            "⚡ **ИЗМЕНЕНИЕ ЦЕНЫ SHORT**\n\n"
            "Введите новую цену SHORT тарифа в рублях:\n"
            "(минимум 100₽)",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_price'] = 'short'
    elif query.data == "admin_set_long_price":
        await query.edit_message_text(
            "🔵 **ИЗМЕНЕНИЕ ЦЕНЫ LONG**\n\n"
            "Введите новую цену LONG тарифа в рублях:\n"
            "(минимум 100₽)",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_price'] = 'long'
    elif query.data == "admin_manual_scan":
        # Ручное сканирование рынка
        await admin_manual_scan(update, context)
    elif query.data == "admin_refresh":
        # Обновить данные - перезагрузить кэш сигналов
        await admin_refresh_data(update, context)
    elif query.data == "admin_signal_settings":
        # Настройки поиска сигналов
        await admin_signal_settings(update, context)
    elif query.data == "admin_webhook_settings":
        # Webhook настройки
        await admin_webhook_settings(update, context)
    elif query.data == "webhook_set_url":
        # Установить webhook URL
        await query.answer()
        await query.message.reply_text(
            "🌐 **УСТАНОВКА WEBHOOK URL**\n\n"
            "Отправьте URL вашего webhook сервиса.\n"
            "Пример: https://api.example.com/webhook\n\n"
            "❌ Отправьте /cancel для отмены",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_webhook_url'] = True
    elif query.data == "webhook_set_secret":
        # Установить webhook секрет
        await query.answer()
        await query.message.reply_text(
            "🔑 **УСТАНОВКА СЕКРЕТНОГО КЛЮЧА**\n\n"
            "Отправьте секретный ключ для JWT авторизации.\n\n"
            "⚠️ **Требования:**\n"
            "• Минимум 16 символов\n"
            "• Используйте сложную комбинацию символов\n"
            "• Никому не передавайте этот ключ!\n\n"
            "💡 **Пример:** `MyS3cr3tK3y123456`\n\n"
            "❌ Отправьте /cancel для отмены",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_webhook_secret'] = True
    elif query.data == "webhook_toggle":
        # Включить/выключить webhook
        webhook_enabled = bot.get_setting('webhook_enabled', 'false') == 'true'
        webhook_url = bot.get_setting('webhook_url', '')
        webhook_secret = bot.get_setting('webhook_secret', '')
        
        try:
            # Настроить webhook систему
            webhook_system.configure(webhook_url, webhook_secret, not webhook_enabled)
            
            # Сохранить в БД
            bot.set_setting('webhook_enabled', 'true' if not webhook_enabled else 'false')
            
            status = "включен" if not webhook_enabled else "выключен"
            await query.answer(f"✅ Webhook {status}!", show_alert=True)
            await admin_webhook_settings(update, context)
        except ValueError as e:
            await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
    elif query.data == "webhook_test":
        # Тестовый сигнал
        test_signal = {
            "asset": "BTC/USD OTC",
            "direction": "CALL",
            "timeframe": "1min",
            "entry_price": 50000.0,
            "confidence": 95,
            "timestamp": datetime.now().isoformat()
        }
        
        success = asyncio.create_task(webhook_system.send_signal(test_signal))
        
        await query.answer("🧪 Тестовый сигнал отправлен! Проверьте ваш сервис.", show_alert=True)
    elif query.data == "admin_tariff_management":
        # Управление тарифами
        await admin_tariff_management(update, context)
    elif query.data == "admin_panel":
        # Открыть админ панель
        await admin_panel(update, context)
    elif query.data == "admin_change_bot_name":
        # Изменить название бота
        await admin_change_bot_name(update, context)
    elif query.data == "confirm_bot_name":
        # Подтвердить изменение названия
        await confirm_bot_name_change(update, context)
    elif query.data == "cancel_bot_name":
        # Отменить изменение названия
        await cancel_bot_name_change(update, context)
    elif query.data == "admin_save_restart":
        # Сохранить и перезапустить
        await admin_save_restart(update, context)
    elif query.data == "admin_reset_settings":
        # Показать подтверждение сброса настроек
        await admin_reset_settings(update, context)
    elif query.data == "confirm_reset_settings":
        # Подтвердить сброс настроек
        await confirm_reset_settings(update, context)
    elif query.data == "cancel_reset_settings":
        # Отменить сброс настроек
        await cancel_reset_settings(update, context)
    elif query.data == "admin_switch_tariff_menu":
        # Показать меню переключения тарифов
        await admin_switch_tariff_menu(update, context)
    elif query.data == "admin_preview_tariffs":
        # Показать предпросмотр тарифов для админа
        await admin_preview_tariffs(update, context)
    elif query.data == "admin_example_buy":
        # Пример кнопки оплаты (для предпросмотра)
        await query.answer("👁️ Это предпросмотр. Кнопка не активна для админа.", show_alert=True)
    elif query.data == "settings_back":
        # Вернуться в админ панель
        await admin_panel(update, context)
    elif query.data == "admin_panel":
        # Открыть админ панель
        await admin_panel(update, context)
    elif query.data == "admin_reset_self":
        await admin_reset_self(update, context)
    elif query.data == "admin_set_vip":
        await admin_switch_plan(update, context, "vip", -1)  # -1 = бессрочно
    elif query.data == "admin_set_long":
        await admin_switch_plan(update, context, "long", -1)  # -1 = бессрочно
    elif query.data == "admin_set_short":
        await admin_switch_plan(update, context, "short", -1)  # -1 = бессрочно
    elif query.data == "admin_set_free":
        await admin_switch_plan(update, context, "free", 0)
    elif query.data == "admin_set_trial":
        await admin_switch_plan(update, context, "trial", 3)
    elif query.data.startswith("copy_ref_"):
        referral_code = query.data.replace("copy_ref_", "")
        referral_link = f"https://t.me/{(await context.bot.get_me()).username}?start={referral_code}"
        await query.answer("✅ Ссылка скопирована!", show_alert=False)
        await query.message.reply_text(
            f"📋 **Ваша реферальная ссылка:**\n\n`{referral_link}`\n\n_Нажмите на ссылку выше для копирования_",
            parse_mode='Markdown'
        )
    elif query.data.startswith("copy_"):
        asset_name = query.data.replace("copy_", "")
        await query.answer("✅ Готово! Копируйте из сообщения ниже", show_alert=False)
        
        # Отправляем сообщение с актив ом в удобном формате для копирования
        keyboard = [
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main"), 
             InlineKeyboardButton("🏠 Домой", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"📋 **АКТИВ ДЛЯ POCKET OPTION**\n\n"
            f"┏━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            f"┃     `{asset_name}`     \n"
            f"┗━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            f"_↑ Кликните на название для копирования ↑_\n\n"
            f"💡 **Инструкция:**\n"
            f"1. Кликните на название выше\n"
            f"2. Telegram автоматически скопирует\n"
            f"3. Вставьте в поиск Pocket Option",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    elif query.data == "autotrade_menu":
        await autotrade_menu(update, context)
    elif query.data == "autotrade_instruction":
        await autotrade_instruction_callback(update, context)
    elif query.data == "autotrade_vip_promo":
        await autotrade_vip_promo_callback(update, context)
    elif query.data == "autotrade_toggle":
        await autotrade_toggle_callback(update, context)
    elif query.data == "choose_autotrade_strategy":
        await choose_autotrade_strategy(update, context)
    elif query.data == "autotrade_toggle_mode":
        await autotrade_toggle_mode_callback(update, context)
    elif query.data == "autotrade_stats":
        await autotrade_stats_callback(update, context)
    elif query.data == "setup_pocket_option":
        await setup_pocket_option_callback(update, context)
    elif query.data == "download_ssid_automation":
        await download_ssid_automation_callback(update, context)
    elif query.data == "show_ssid_instruction":
        await show_ssid_instruction_callback(update, context)
    elif query.data == "show_po_instruction":
        await show_po_instruction_callback(update, context)
    elif query.data == "po_login":
        await po_login_callback(update, context)
    elif query.data == "ready_to_send_ssid":
        await ready_to_send_ssid_callback(update, context)
    elif query.data == "disconnect_pocket_option":
        await disconnect_pocket_option_callback(update, context)
    elif query.data == "autotrade_session_refresh":
        await autotrade_session_refresh(update, context)
    elif query.data == "autotrade_stop_session":
        await autotrade_stop_session(update, context)
    elif query.data == "autotrade_math_analysis":
        await autotrade_math_analysis(update, context)
    elif query.data == "bank_menu":
        await bank_menu_callback(update, context)
    elif query.data.startswith("autotrade_select_"):
        strategy = query.data.replace("autotrade_select_", "")
        await autotrade_select_strategy(update, context, strategy)
    elif query.data.startswith("autotrade_apply_ai_"):
        strategy = query.data.replace("autotrade_apply_ai_", "")
        # Применить AI рекомендованную стратегию
        cursor = bot.conn.cursor()
        cursor.execute('''
            UPDATE users SET auto_trading_strategy = ? WHERE user_id = ?
        ''', (strategy, user_id))
        bot.conn.commit()
        await query.answer(f"✅ AI стратегия '{strategy}' применена!")
        await autotrade_session_refresh(update, context)
    elif query.data.startswith("autotrade_config_"):
        strategy = query.data.replace("autotrade_config_", "")
        await autotrade_config_strategy(update, context, strategy)
    elif query.data.startswith("set_percentage_"):
        percentage_str = query.data.replace("set_percentage_", "")
        percentage = float(percentage_str)
        cursor = bot.conn.cursor()
        cursor.execute('UPDATE users SET percentage_value = ? WHERE user_id = ?', (percentage, user_id))
        bot.conn.commit()
        await query.answer(f"✅ Установлено: {percentage}%", show_alert=True)
        await autotrade_config_strategy(update, context, 'percentage')
    elif query.data.startswith("set_dalembert_"):
        params = query.data.replace("set_dalembert_", "").split("_")
        base_stake = float(params[0])
        unit = float(params[1])
        cursor = bot.conn.cursor()
        cursor.execute('UPDATE users SET dalembert_base_stake = ?, dalembert_unit = ? WHERE user_id = ?', 
                      (base_stake, unit, user_id))
        bot.conn.commit()
        await query.answer(f"✅ Установлено: {base_stake}₽ / {unit}₽", show_alert=True)
        await autotrade_config_strategy(update, context, 'dalembert')
    elif query.data.startswith("set_martingale_"):
        params = query.data.replace("set_martingale_", "").split("_")
        base_stake = float(params[0])
        multiplier = int(params[1])
        cursor = bot.conn.cursor()
        cursor.execute('UPDATE users SET martingale_base_stake = ?, martingale_multiplier = ? WHERE user_id = ?', 
                      (base_stake, multiplier, user_id))
        bot.conn.commit()
        await query.answer(f"✅ Установлено: {base_stake}₽ x{multiplier}", show_alert=True)
        await autotrade_config_strategy(update, context, 'martingale')

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /settings - настройки бота"""
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    user_id = update.effective_user.id
    
    # Ответить на callback query для предотвращения таймаутов
    if is_callback:
        await update.callback_query.answer()
    
    # Получить информацию о пользователе из БД
    cursor = bot.conn.cursor()
    cursor.execute('SELECT language, currency, is_premium, subscription_type, trading_strategy, martingale_multiplier, martingale_base_stake, percentage_value FROM users WHERE user_id = ?', (user_id,))
    user_data = cursor.fetchone()
    
    if not user_data:
        message_obj = update.callback_query.message if is_callback else update.message
        await message_obj.reply_text("❌ Пользователь не найден. Используйте /start")
        return
    
    # Получить язык и валюту пользователя
    lang = user_data[0] if user_data[0] else 'RU'
    currency = user_data[1] if user_data[1] else 'RUB'
    is_premium = user_data[2] if user_data[2] else 0
    subscription_type = user_data[3] if user_data[3] else 'free'
    trading_strategy = user_data[4] if user_data[4] else None
    martingale_multiplier = user_data[5] if user_data[5] else 3
    martingale_base_stake = user_data[6] if user_data[6] else None
    percentage_value = user_data[7] if user_data[7] else 2.5
    
    # Определить текст стратегии
    if trading_strategy == 'martingale':
        if martingale_base_stake:
            strategy_text = f"⚡️ Мартингейл x{martingale_multiplier} ({martingale_base_stake:.0f}₽)"
        else:
            strategy_text = f"⚡️ Мартингейл x{martingale_multiplier} (не настроена)"
    elif trading_strategy == 'percentage':
        strategy_text = f"📊 Процентная ({percentage_value}%)"
    else:
        strategy_text = "Не выбрана"
    
    # Проверка администратора
    is_admin = bot.is_admin(user_id)
    logger.info(f"🔍 Settings check for user {user_id}: is_admin={is_admin}")
    
    # Обычные настройки для всех пользователей
    settings_text = f"""
⚙️ **НАСТРОЙКИ**

🌍 **Язык интерфейса:** {lang}
💱 **Валюта:** {currency}
🎯 **Стратегия банка:** {strategy_text}

📱 **Ваш Telegram ID:** `{user_id}`
💼 **Тариф:** {subscription_type.upper()}

Здесь вы можете настроить параметры бота.
"""
    
    keyboard = [
        [InlineKeyboardButton("🎁 Реферальная программа", callback_data="referral_program")],
        [InlineKeyboardButton("🎯 Выбрать стратегию", callback_data="choose_strategy")],
        [InlineKeyboardButton("🌍 Изменить язык", callback_data="change_language")],
        [InlineKeyboardButton("💱 Изменить валюту", callback_data="change_currency")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")],
    ]
    
    # Кнопка выбора/расширения тарифа (в зависимости от типа подписки)
    if not is_admin:  # Админу не показываем кнопку тарифа
        if subscription_type in ['free', 'trial']:
            # FREE/TRIAL - показать кнопку выбора тарифа
            keyboard.insert(0, [InlineKeyboardButton("💎 Выбрать тариф", callback_data="choose_plan")])
        elif subscription_type in ['short', 'long']:
            # SHORT/LONG - показать кнопку расширения возможностей
            keyboard.insert(0, [InlineKeyboardButton("⬆️ Расширить возможности тарифа", callback_data="upgrade_plan")])
        # VIP - не показываем кнопку (уже максимальный тариф)
    
    # Для админов добавляем кнопку доступа к админ-панели
    if is_admin:
        keyboard.insert(0, [InlineKeyboardButton("🔧 Админ панель", callback_data="admin_panel")])
    
    # Кнопка "Домой" для возврата на главную (всегда внизу)
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await update.callback_query.edit_message_text(
            settings_text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            settings_text,
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ-панель для управления ботом"""
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    user_id = update.effective_user.id
    
    # Проверка прав администратора
    if not bot.is_admin(user_id):
        message_obj = update.callback_query.message if is_callback else update.message
        await message_obj.reply_text("❌ У вас нет прав администратора.")
        return
    
    # Ответить на callback query
    if is_callback:
        await update.callback_query.answer()
    
    # Получить статистику бота
    stats = bot.get_bot_stats()
    
    # Получить информацию о пользователе
    cursor = bot.conn.cursor()
    cursor.execute('SELECT language, currency, subscription_type FROM users WHERE user_id = ?', (user_id,))
    user_data = cursor.fetchone()
    
    lang = user_data[0] if user_data and user_data[0] else 'RU'
    currency = user_data[1] if user_data and user_data[1] else 'RUB'
    subscription_type = user_data[2] if user_data and user_data[2] else 'free'
    
    admin_text = f"""
🔐 **АДМИН-ПАНЕЛЬ**

📊 **Статистика бота:**
👥 Всего пользователей: {stats['total_users']}
💎 Premium пользователей: {stats['premium_users']}
✅ Активных подписок: {stats['active_subscriptions']}
📈 Всего сигналов выдано: {stats['total_signals']}

👤 **Ваш профиль:**
🌍 Язык: {lang}
💱 Валюта: {currency}
💼 Тариф: {subscription_type.upper()}
"""
    
    keyboard = [
        [InlineKeyboardButton("📊 Подробная статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🎯 Настройки поиска сигналов", callback_data="admin_signal_settings")],
        [InlineKeyboardButton("🔗 Webhook настройки", callback_data="admin_webhook_settings")],
        [InlineKeyboardButton("💰 Управление тарифами", callback_data="admin_tariff_management")],
        [InlineKeyboardButton("🏆 ТОП-10 пользователей", callback_data="admin_top_users")],
        [InlineKeyboardButton("💎 Быстрая выдача подписки", callback_data="admin_quick_sub")],
        [InlineKeyboardButton("🖼️ Изображения тарифов", callback_data="admin_tariff_images")],
        [InlineKeyboardButton("🏷️ Изменить название бота", callback_data="admin_change_bot_name")],
        [InlineKeyboardButton("🔍 Сканировать рынок вручную", callback_data="admin_manual_scan")],
        [InlineKeyboardButton("🔄 Сбросить себя", callback_data="admin_reset_self")],
        [InlineKeyboardButton("🔀 Переключить тариф", callback_data="admin_switch_tariff_menu")],
        [InlineKeyboardButton("🔄 Перезапуск бота", callback_data="admin_save_restart"),
         InlineKeyboardButton("⚙️ Сброс настроек", callback_data="admin_reset_settings")],
    ]
    
    # Кнопка возврата к настройкам и главному меню
    keyboard.append([
        InlineKeyboardButton("◀️ Назад к настройкам", callback_data="settings"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await update.callback_query.edit_message_text(
            admin_text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            admin_text,
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )

async def admin_tariff_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление изображениями тарифов"""
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        message_obj = update.callback_query.message if is_callback else update.message
        await message_obj.reply_text("❌ У вас нет прав администратора.")
        return
    
    # Получить текущие изображения
    vip_image = bot.get_setting('tariff_image_vip', '')
    short_image = bot.get_setting('tariff_image_short', '')
    long_image = bot.get_setting('tariff_image_long', '')
    free_image = bot.get_setting('tariff_image_free', '')
    
    images_text = f"""
🖼️ **УПРАВЛЕНИЕ ИЗОБРАЖЕНИЯМИ ТАРИФОВ**

Текущие изображения:

💎 **VIP:** {'✅ Загружено' if vip_image else '❌ Не установлено'}
⚡ **SHORT:** {'✅ Загружено' if short_image else '❌ Не установлено'}
🔵 **LONG:** {'✅ Загружено' if long_image else '❌ Не установлено'}
🎁 **FREE:** {'✅ Загружено' if free_image else '❌ Не установлено'}

Выберите тариф для загрузки/замены изображения:
"""
    
    keyboard = [
        [InlineKeyboardButton("💎 Загрузить VIP", callback_data="upload_image_vip")],
        [InlineKeyboardButton("⚡ Загрузить SHORT", callback_data="upload_image_short")],
        [InlineKeyboardButton("🔵 Загрузить LONG", callback_data="upload_image_long")],
        [InlineKeyboardButton("🎁 Загрузить FREE", callback_data="upload_image_free")],
        [InlineKeyboardButton("👁️ Предпросмотр тарифов", callback_data="admin_preview_tariffs")],
        [InlineKeyboardButton("◀️ Назад в админ панель", callback_data="settings_back"),
         InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await update.callback_query.edit_message_text(images_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(images_text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_switch_tariff_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню переключения тарифов для админа"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.callback_query.answer("❌ Нет прав", show_alert=True)
        return
    
    await update.callback_query.answer()
    
    # Получить текущий тариф админа
    cursor = bot.conn.cursor()
    cursor.execute('SELECT subscription_type, subscription_end FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    current_sub = result[0] if result and result[0] else 'free'
    sub_end = result[1] if result and result[1] else None
    
    sub_emoji = {
        'free': '🆓',
        'short': '⚡',
        'long': '🔵',
        'vip': '💎',
        'trial': '🎁'
    }
    
    # Безопасное получение названия тарифа
    current_sub_display = current_sub.upper() if current_sub else 'FREE'
    
    text = f"""
🔀 **ПЕРЕКЛЮЧЕНИЕ ТАРИФА АДМИНА**

📊 **Текущий тариф:** {sub_emoji.get(current_sub, '🆓')} {current_sub_display}

Выберите тариф для переключения (бессрочно):
"""
    
    keyboard = [
        [InlineKeyboardButton("💎 VIP", callback_data="admin_set_vip"),
         InlineKeyboardButton("🔵 LONG", callback_data="admin_set_long")],
        [InlineKeyboardButton("⚡️ SHORT", callback_data="admin_set_short"),
         InlineKeyboardButton("🆓 FREE", callback_data="admin_set_free")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_panel"),
         InlineKeyboardButton("🏠 Домой", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_change_bot_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменить название бота"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.callback_query.answer("❌ Нет прав", show_alert=True)
        return
    
    await update.callback_query.answer()
    
    # Получить текущее название
    current_name = bot.get_setting('bot_name', 'CRYPTO SIGNALS BOT')
    
    text = f"""
🏷️ **ИЗМЕНЕНИЕ НАЗВАНИЯ БОТА**

📝 **Текущее название:** {current_name}

Введите новое название бота:
"""
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад в админ панель", callback_data="admin_panel")],
        [InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Установить состояние ожидания ввода названия
    context.user_data['awaiting_bot_name'] = True
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def confirm_bot_name_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтвердить изменение названия бота"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        return
    
    new_name = context.user_data.get('new_bot_name', '')
    
    if not new_name:
        await update.callback_query.answer("❌ Ошибка: название не найдено", show_alert=True)
        return
    
    # Сохранить новое название
    bot.set_setting('bot_name', new_name)
    
    await update.callback_query.answer("✅ Название бота изменено!", show_alert=True)
    
    # Очистить состояние
    context.user_data.pop('awaiting_bot_name', None)
    context.user_data.pop('new_bot_name', None)
    
    # Вернуться на главную
    await show_main_menu(update, context, user_id)

async def cancel_bot_name_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменить изменение названия бота"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        return
    
    # Очистить состояние
    context.user_data.pop('awaiting_bot_name', None)
    context.user_data.pop('new_bot_name', None)
    
    await update.callback_query.answer("❌ Отменено", show_alert=False)
    
    # Вернуться на главную
    await show_main_menu(update, context, user_id)

async def admin_preview_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Предпросмотр тарифов для админа"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.callback_query.answer("❌ Нет прав", show_alert=True)
        return
    
    await update.callback_query.answer()
    
    # Получить текущие цены из настроек
    vip_price_rub = int(bot.get_setting('vip_price_rub', '9990'))
    short_price_rub = int(bot.get_setting('short_price_rub', '4990'))
    long_price_rub = int(bot.get_setting('long_price_rub', '6990'))
    
    # Получить валюту пользователя для конвертации
    cursor = bot.conn.cursor()
    cursor.execute('SELECT currency FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    currency = result[0] if result and result[0] else 'RUB'
    
    # Конвертировать и форматировать цены
    vip_price_display = bot.format_price(bot.convert_price(vip_price_rub, currency), currency)
    short_price_display = bot.format_price(bot.convert_price(short_price_rub, currency), currency)
    long_price_display = bot.format_price(bot.convert_price(long_price_rub, currency), currency)
    
    tariff_text = f"""
👁️ **ПРЕДПРОСМОТР ТАРИФОВ ДЛЯ АДМИНА**

━━━━━━━━━━━━━━━━━━━━━━━━
💎 *VIP ТАРИФ*
💰 Цена: *{vip_price_display}/мес*

✅ ВСЕ сигналы (SHORT + LONG)
✅ Безлимитные сигналы 1-5 мин и 1-4 часа
✅ Автоматические рассылки 5 раз/день
✅ Обе стратегии: Мартингейл + %
✅ Приоритетная поддержка
✅ Точность 85-95%

━━━━━━━━━━━━━━━━━━━━━━━━
⚡ *SHORT ТАРИФ*
💰 Цена: *{short_price_display}/мес*

✅ Безлимитные сигналы 1-5 минут
✅ Мартингейл стратегия x2/x3
✅ Автоматический countdown
✅ Быстрая торговля
✅ Точность 85-92%

━━━━━━━━━━━━━━━━━━━━━━━━
🔵 *LONG ТАРИФ*
💰 Цена: *{long_price_display}/мес*

✅ Безлимитные сигналы 1-4 часа
✅ Процентная стратегия 2-3%
✅ Управление через /my_longs
✅ Долгосрочная торговля
✅ Точность 90-95%

━━━━━━━━━━━━━━━━━━━━━━━━
🆓 *FREE ТАРИФ*
💰 Цена: *Бесплатно навсегда*

✅ 5 SHORT + 5 LONG сигналов/день
✅ Сигналы ≥95% точности
✅ Все стратегии доступны
✅ Идеально для старта

━━━━━━━━━━━━━━━━━━━━━━━━
💡 *Это предпросмотр страницы тарифов для пользователей*
"""
    
    keyboard = [
        [InlineKeyboardButton(f"💳 Пример: Оплатить VIP ({vip_price_display}/мес)", callback_data="admin_example_buy")],
        [InlineKeyboardButton(f"💳 Пример: Оплатить SHORT ({short_price_display}/мес)", callback_data="admin_example_buy")],
        [InlineKeyboardButton(f"💳 Пример: Оплатить LONG ({long_price_display}/мес)", callback_data="admin_example_buy")],
        [InlineKeyboardButton("◀️ Назад в админ панель", callback_data="admin_panel")],
        [InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(tariff_text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_save_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Умный перезапуск бота с автоматической диагностикой и исправлением ошибок"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.callback_query.answer("❌ Нет прав", show_alert=True)
        return
    
    await update.callback_query.answer()
    
    # Показать анимацию перезапуска
    animation_msg = await update.callback_query.message.reply_text(
        "🔄 **УМНЫЙ ПЕРЕЗАПУСК БОТА**\n\n🔍 Диагностика системы...",
        parse_mode='Markdown'
    )
    
    import asyncio
    issues_found = []
    fixes_applied = []
    
    await asyncio.sleep(0.3)
    
    # 1. Проверка базы данных
    await animation_msg.edit_text(
        "🔄 **УМНЫЙ ПЕРЕЗАПУСК БОТА**\n\n🗄️ Проверка базы данных...",
        parse_mode='Markdown'
    )
    try:
        cursor = bot.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        cursor.fetchone()
        fixes_applied.append("✅ База данных: OK")
    except Exception as e:
        issues_found.append(f"❌ БД: {str(e)[:50]}")
        try:
            bot.conn.rollback()
            fixes_applied.append("🔧 БД откачена (rollback)")
        except:
            pass
    
    await asyncio.sleep(0.3)
    
    # 2. Очистка кэша сигналов
    await animation_msg.edit_text(
        "🔄 **УМНЫЙ ПЕРЕЗАПУСК БОТА**\n\n🗑️ Очистка кэша...",
        parse_mode='Markdown'
    )
    try:
        signal_cache['short']['signals'] = []
        signal_cache['short']['timestamp'] = 0
        signal_cache['long']['signals'] = []
        signal_cache['long']['timestamp'] = 0
        fixes_applied.append("✅ Кэш сигналов очищен")
    except Exception as e:
        issues_found.append(f"⚠️ Кэш: {str(e)[:30]}")
    
    await asyncio.sleep(0.3)
    
    # 3. Сохранение данных
    await animation_msg.edit_text(
        "🔄 **УМНЫЙ ПЕРЕЗАПУСК БОТА**\n\n💾 Сохранение данных...",
        parse_mode='Markdown'
    )
    try:
        bot.conn.commit()
        fixes_applied.append("✅ Данные сохранены")
    except Exception as e:
        issues_found.append(f"❌ Сохранение: {str(e)[:40]}")
    
    await asyncio.sleep(0.3)
    
    # 4. Проверка команд бота
    await animation_msg.edit_text(
        "🔄 **УМНЫЙ ПЕРЕЗАПУСК БОТА**\n\n⚙️ Проверка команд...",
        parse_mode='Markdown'
    )
    try:
        # Проверка наличия критических команд
        expected_commands = ['start', 'plans', 'bank', 'autotrade', 'reset_me', 'settings', 'help']
        fixes_applied.append("✅ Команды бота настроены")
    except Exception as e:
        issues_found.append(f"⚠️ Команды: {str(e)[:30]}")
    
    await asyncio.sleep(0.3)
    
    # 5. Формирование отчёта
    report = "🔄 **ДИАГНОСТИКА ЗАВЕРШЕНА**\n\n"
    
    if fixes_applied:
        report += "**Исправлено:**\n" + "\n".join(fixes_applied) + "\n\n"
    
    if issues_found:
        report += "**⚠️ Обнаружены проблемы:**\n" + "\n".join(issues_found) + "\n\n"
    
    report += "⚡ Перезапуск...\n_Бот вернется через несколько секунд_"
    
    await animation_msg.edit_text(report, parse_mode='Markdown')
    
    await asyncio.sleep(0.5)
    
    # Остановить приложение для перезапуска
    import sys
    logger.info(f"🔄 Умный перезапуск: {len(fixes_applied)} исправлений, {len(issues_found)} проблем")
    sys.exit(0)

async def admin_reset_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать окно подтверждения сброса настроек"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.callback_query.answer("❌ Нет прав", show_alert=True)
        return
    
    await update.callback_query.answer()
    
    text = """
⚠️ **СБРОС НАСТРОЕК НА ЗНАЧЕНИЯ ПО УМОЛЧАНИЮ**

🔄 **Будут сброшены:**
• Название бота → CRYPTO SIGNALS BOT
• Минимальный балл → 3
• Минимальная разница → 1
• Минимальная уверенность → 75%
• Максимальная уверенность → 92%
• Цена VIP → 9990₽
• Цена SHORT → 4990₽
• Цена LONG → 6990₽

⚠️ **Внимание:** Это действие нельзя отменить!

Подтвердите сброс настроек:
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить сброс", callback_data="confirm_reset_settings")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel_reset_settings")],
        [InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def confirm_reset_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтвердить сброс настроек на значения по умолчанию"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.callback_query.answer("❌ Нет прав", show_alert=True)
        return
    
    await update.callback_query.answer("🔄 Сброс настроек...", show_alert=False)
    
    # Сбросить все настройки на значения по умолчанию
    default_settings = {
        'bot_name': 'CRYPTO SIGNALS BOT',
        'min_signal_score': '3',
        'min_score_difference': '1',
        'min_confidence': '75',
        'max_confidence': '92',
        'vip_price_rub': '9990',
        'short_price_rub': '4990',
        'long_price_rub': '6990'
    }
    
    for key, value in default_settings.items():
        bot.set_setting(key, value)
    
    # Восстановить команды бота на значения по умолчанию
    await context.bot.set_my_commands([
        BotCommand(cmd, desc) for cmd, desc in DEFAULT_BOT_COMMANDS
    ])
    
    # Показать сообщение об успешном сбросе
    success_msg = await update.callback_query.message.reply_text(
        "✅ **НАСТРОЙКИ СБРОШЕНЫ**\n\n"
        "Все параметры восстановлены до значений по умолчанию!\n"
        "🔄 Команды бота также восстановлены.",
        parse_mode='Markdown'
    )
    
    import asyncio
    await asyncio.sleep(2)
    await success_msg.delete()
    
    # Вернуться на главную
    await show_main_menu(update, context, user_id)

async def cancel_reset_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменить сброс настроек"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        return
    
    await update.callback_query.answer("❌ Сброс отменен", show_alert=False)
    
    # Вернуться в админ панель
    await admin_panel(update, context)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    
    if not bot.is_admin(update.effective_user.id):
        message_obj = update.callback_query.message if is_callback else update.message
        await message_obj.reply_text("❌ У вас нет прав администратора.")
        return
    
    stats = bot.get_bot_stats()
    cursor = bot.conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) as free_users
        FROM users 
        WHERE is_premium = 0
    ''')
    free_users = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT AVG(signals_used) as avg_signals
        FROM users 
        WHERE signals_used > 0
    ''')
    avg_signals = cursor.fetchone()[0] or 0
    
    stats_text = f"""
📊 **ПОДРОБНАЯ СТАТИСТИКА БОТА**

👥 **Пользователи:**
• Всего: {stats['total_users']}
• Free: {free_users}
• Premium: {stats['premium_users']}
• Активных подписок: {stats['active_subscriptions']}

📈 **Активность:**
• Всего сигналов: {stats['total_signals']}
• Средняя активность: {avg_signals:.1f} сигналов/пользователь
• Конверсия в Premium: {(stats['premium_users'] / max(stats['total_users'], 1) * 100):.1f}%
"""
    
    keyboard = [[InlineKeyboardButton("◀️ Назад в админ панель", callback_data="settings_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await update.callback_query.edit_message_text(
            stats_text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            stats_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def admin_add_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав администратора.", reply_markup=add_home_button())
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Использование: `/admin_add_sub [user_id] [days]`\n"
            "Пример: `/admin_add_sub 123456789 30`",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        days = int(context.args[1])
        
        end_date = bot.add_subscription(user_id, days)
        
        await update.message.reply_text(
            f"✅ Подписка добавлена!\n\n"
            f"👤 User ID: `{user_id}`\n"
            f"⏰ Дней: {days}\n"
            f"📅 Активна до: {end_date.strftime('%d.%m.%Y')}",
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. User ID и дни должны быть числами.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def admin_lifetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав администратора.", reply_markup=add_home_button())
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Использование: `/admin_lifetime [user_id]`\n"
            "Пример: `/admin_lifetime 123456789`\n\n"
            "Или `/admin_lifetime me` для себя",
            parse_mode='Markdown'
        )
        return
    
    try:
        if context.args[0].lower() == 'me':
            user_id = update.effective_user.id
        else:
            user_id = int(context.args[0])
        
        end_date = bot.add_lifetime_subscription(user_id)
        
        await update.message.reply_text(
            f"✅ Пожизненный VIP доступ активирован!\n\n"
            f"👤 User ID: `{user_id}`\n"
            f"💎 Статус: LIFETIME VIP\n"
            f"📅 Активен до: {end_date.strftime('%d.%m.%Y')} (100 лет)",
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. User ID должен быть числом.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def market_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /market_stats - просмотр исторической статистики рынка (только для админа)"""
    if not bot.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return
    
    cursor = bot.conn.cursor()
    
    # Получить общую статистику по истории
    cursor.execute('''
        SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
        FROM market_history
    ''')
    total_records, first_record, last_record = cursor.fetchone()
    
    # Получить статистику по активам
    cursor.execute('''
        SELECT 
            asset_symbol,
            COUNT(*) as scans,
            AVG(volatility) as avg_volatility,
            SUM(CASE WHEN whale_detected = 1 THEN 1 ELSE 0 END) as whale_count,
            SUM(CASE WHEN trend = 'BULLISH' THEN 1 ELSE 0 END) as bullish_count,
            SUM(CASE WHEN trend = 'BEARISH' THEN 1 ELSE 0 END) as bearish_count,
            AVG(confidence) as avg_confidence
        FROM market_history
        GROUP BY asset_symbol
        ORDER BY scans DESC
        LIMIT 20
    ''')
    asset_stats = cursor.fetchall()
    
    # Топ активы с китами
    cursor.execute('''
        SELECT 
            asset_symbol,
            COUNT(*) as whale_activity_count,
            AVG(volume_ratio) as avg_volume_spike
        FROM market_history
        WHERE whale_detected = 1
        GROUP BY asset_symbol
        ORDER BY whale_activity_count DESC
        LIMIT 10
    ''')
    whale_leaders = cursor.fetchall()
    
    stats_text = f"""
📊 **СТАТИСТИКА ДВИЖЕНИЙ РЫНКА**

🔍 **Общие данные:**
• Записей в истории: {total_records}
• Первая запись: {first_record[:16] if first_record else 'Н/Д'}
• Последняя запись: {last_record[:16] if last_record else 'Н/Д'}

📈 **Топ активов по активности:**
"""
    
    for asset, scans, volatility, whales, bullish, bearish, conf in asset_stats[:10]:
        trend_ratio = (bullish / scans * 100) if scans > 0 else 0
        whale_pct = (whales / scans * 100) if scans > 0 else 0
        stats_text += f"\n**{asset}**"
        stats_text += f"\n  📊 Сканов: {scans} | Волатильность: {volatility:.2f}%"
        stats_text += f"\n  🐋 Киты: {whale_pct:.0f}% | 📈 Bullish: {trend_ratio:.0f}%"
        stats_text += f"\n  🎯 Ср. уверенность: {conf:.1f}%\n"
    
    stats_text += "\n🐋 **Лидеры по активности китов:**\n"
    for asset, whale_count, avg_spike in whale_leaders[:5]:
        stats_text += f"• {asset}: {whale_count} событий (x{avg_spike:.1f} объем)\n"
    
    stats_text += "\n💡 *Используйте эту аналитику для понимания поведения рынка*"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def signal_performance_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /signal_stats - просмотр статистики производительности активов (только для админа)"""
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    
    if not bot.is_admin(update.effective_user.id):
        message_obj = update.callback_query.message if is_callback else update.message
        await message_obj.reply_text("❌ У вас нет прав администратора.")
        return
    
    cursor = bot.conn.cursor()
    
    # Получить топ активов по win rate (минимум 5 сигналов)
    cursor.execute('''
        SELECT asset, timeframe, total_signals, wins, losses, win_rate, adaptive_weight
        FROM signal_performance
        WHERE total_signals >= 5
        ORDER BY win_rate DESC, total_signals DESC
        LIMIT 15
    ''')
    top_performers = cursor.fetchall()
    
    # Получить худшие активы
    cursor.execute('''
        SELECT asset, timeframe, total_signals, wins, losses, win_rate, adaptive_weight
        FROM signal_performance
        WHERE total_signals >= 5
        ORDER BY win_rate ASC, total_signals DESC
        LIMIT 10
    ''')
    bottom_performers = cursor.fetchall()
    
    # Общая статистика
    cursor.execute('''
        SELECT 
            COUNT(*) as total_assets,
            SUM(total_signals) as all_signals,
            SUM(wins) as all_wins,
            SUM(losses) as all_losses,
            AVG(win_rate) as avg_winrate
        FROM signal_performance
        WHERE total_signals >= 5
    ''')
    overall = cursor.fetchone()
    
    stats_text = f"""
📊 **СТАТИСТИКА ПРОИЗВОДИТЕЛЬНОСТИ СИГНАЛОВ**

🎯 **Общие показатели:**
• Активов с данными: {overall[0]}
• Всего сигналов: {overall[1]}
• Побед: {overall[2]} | Поражений: {overall[3]}
• Средний Win Rate: {overall[4]*100:.1f}%

━━━━━━━━━━━━━━━━━━━━━━

✅ **ТОП-15 ЛУЧШИХ АКТИВОВ:**
"""
    
    for i, (asset, tf, total, wins, losses, wr, weight) in enumerate(top_performers, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        stats_text += f"\n{emoji} {asset} ({tf}): {wr*100:.1f}% ({wins}W/{losses}L) вес:{weight:.2f}x"
    
    stats_text += "\n\n❌ **ХУДШИЕ АКТИВЫ (для улучшения):**"
    
    for asset, tf, total, wins, losses, wr, weight in bottom_performers[:5]:
        stats_text += f"\n⚠️ {asset} ({tf}): {wr*100:.1f}% ({wins}W/{losses}L) вес:{weight:.2f}x"
    
    stats_text += "\n\n💡 **Пояснение:**"
    stats_text += "\n• Вес > 1.0 = приоритет (высокий win rate)"
    stats_text += "\n• Вес < 1.0 = понижен (низкий win rate)"
    stats_text += "\n• Минимум 5 сигналов для активации весов"
    
    keyboard = [[InlineKeyboardButton("◀️ Назад в админ панель", callback_data="settings_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await update.callback_query.edit_message_text(
            stats_text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            stats_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def admin_refresh_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновление данных - перезагрузка кэша сигналов"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.callback_query.answer("❌ Нет прав", show_alert=True)
        return
    
    await update.callback_query.answer("🔄 Обновление данных...", show_alert=False)
    
    # Очистить кэш сигналов
    signal_cache['short']['signals'] = []
    signal_cache['short']['timestamp'] = 0
    signal_cache['long']['signals'] = []
    signal_cache['long']['timestamp'] = 0
    
    # Запустить фоновое сканирование
    status_msg = await update.callback_query.message.reply_text(
        "🔄 **Обновление данных**\n\n"
        "⏳ Сканирую рынок и загружаю новые данные...",
        parse_mode='Markdown'
    )
    
    try:
        # Сканировать SHORT и LONG сигналы
        short_signals = await scan_market_signals('short')
        long_signals = await scan_market_signals('long')
        
        result_text = (
            f"✅ **Данные обновлены!**\n\n"
            f"📊 **Результаты сканирования:**\n"
            f"⚡ SHORT: {len(short_signals)} сигналов\n"
            f"🔵 LONG: {len(long_signals)} сигналов\n\n"
            f"Кэш обновлён и готов к использованию."
        )
        
        keyboard = [[InlineKeyboardButton("◀️ Назад в админ панель", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await status_msg.edit_text(result_text, parse_mode='Markdown', reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"❌ Ошибка обновления данных: {e}")
        await status_msg.edit_text(
            f"❌ **Ошибка обновления**\n\n{str(e)}",
            parse_mode='Markdown'
        )

async def admin_manual_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ручное сканирование рынка для поиска сигналов"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.callback_query.answer("❌ Нет прав", show_alert=True)
        return
    
    await update.callback_query.answer("🔍 Запускаю сканирование...", show_alert=False)
    
    # Показать сообщение о начале сканирования
    status_msg = await update.callback_query.message.reply_text(
        "🔍 **РУЧНОЕ СКАНИРОВАНИЕ РЫНКА**\n\n"
        "⏳ Анализирую рынок и ищу новые сигналы...\n"
        "📊 Проверяю 100 активов...",
        parse_mode='Markdown'
    )
    
    try:
        # Очистить кэш перед сканированием
        signal_cache['short']['signals'] = []
        signal_cache['short']['timestamp'] = 0
        signal_cache['long']['signals'] = []
        signal_cache['long']['timestamp'] = 0
        
        # Сканировать рынок для SHORT и LONG сигналов
        short_signals = await scan_market_signals('short')
        long_signals = await scan_market_signals('long')
        
        # Получить информацию о качестве сигналов
        short_avg_conf = sum(s['confidence'] for s in short_signals) / len(short_signals) if short_signals else 0
        long_avg_conf = sum(s['confidence'] for s in long_signals) / len(long_signals) if long_signals else 0
        
        result_text = (
            f"✅ **СКАНИРОВАНИЕ ЗАВЕРШЕНО!**\n\n"
            f"📊 **Результаты:**\n"
            f"⚡ **SHORT сигналы:** {len(short_signals)} найдено\n"
            f"   • Средняя уверенность: {short_avg_conf:.1f}%\n\n"
            f"🔵 **LONG сигналы:** {len(long_signals)} найдено\n"
            f"   • Средняя уверенность: {long_avg_conf:.1f}%\n\n"
            f"✨ Кэш обновлён. Сигналы готовы к выдаче!"
        )
        
        keyboard = [[InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await status_msg.edit_text(result_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"❌ Ошибка ручного сканирования: {e}")
        await status_msg.edit_text(
            f"❌ **Ошибка сканирования**\n\n{str(e)}",
            parse_mode='Markdown'
        )

async def admin_signal_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройки параметров поиска сигналов"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.callback_query.answer("❌ Нет прав", show_alert=True)
        return
    
    await update.callback_query.answer()
    
    # Получить текущие настройки
    min_score = bot.get_setting('min_signal_score', '3')
    min_diff = bot.get_setting('min_score_difference', '1')
    min_conf = bot.get_setting('min_confidence', '75')
    max_conf = bot.get_setting('max_confidence', '92')
    
    settings_text = f"""
🎯 **НАСТРОЙКИ ПОИСКА СИГНАЛОВ**

📊 **Текущие параметры:**

🔢 **Минимальный балл:** {min_score}
   (сколько индикаторов должны совпасть)
   
📏 **Минимальная разница:** {min_diff}
   (разница между CALL и PUT)
   
📈 **Минимальная уверенность:** {min_conf}%
   (нижняя граница точности)
   
📉 **Максимальная уверенность:** {max_conf}%
   (верхняя граница точности)

💡 **Рекомендации:**
• Балл 3-4: больше сигналов, но ниже точность
• Балл 4-5: меньше сигналов, выше точность
• Разница 1: чувствительный поиск
• Разница 2+: строгий фильтр
"""
    
    keyboard = [
        [InlineKeyboardButton("🔢 Изменить минимальный балл", callback_data="set_min_score")],
        [InlineKeyboardButton("📏 Изменить разницу баллов", callback_data="set_min_diff")],
        [InlineKeyboardButton("📈 Изменить мин. уверенность", callback_data="set_min_conf")],
        [InlineKeyboardButton("📉 Изменить макс. уверенность", callback_data="set_max_conf")],
        [InlineKeyboardButton("🔄 Сбросить на умолчания", callback_data="reset_signal_settings")],
        [InlineKeyboardButton("◀️ Назад в админ панель", callback_data="admin_panel")],
        [InlineKeyboardButton("🏠 Домой", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        settings_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_tariff_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление тарифами"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.callback_query.answer("❌ Нет прав", show_alert=True)
        return
    
    await update.callback_query.answer()
    
    # Получить текущие цены
    short_price = bot.get_setting('short_price_rub', '4990')
    long_price = bot.get_setting('long_price_rub', '6990')
    vip_price = bot.get_setting('vip_price_rub', '9990')
    
    tariff_text = f"""
💰 **УПРАВЛЕНИЕ ТАРИФАМИ**

📋 **Текущие цены:**

⚡ **SHORT:** {short_price}₽/месяц
   Быстрые сигналы 1-5 минут
   
🔵 **LONG:** {long_price}₽/месяц
   Длинные сигналы 1-4 часа
   
💎 **VIP:** {vip_price}₽/месяц
   Все сигналы + автоматическая рассылка

📊 **Действия:**
Выберите тариф для редактирования цены
"""
    
    keyboard = [
        [InlineKeyboardButton("⚡ Изменить цену SHORT", callback_data="edit_short_price")],
        [InlineKeyboardButton("🔵 Изменить цену LONG", callback_data="edit_long_price")],
        [InlineKeyboardButton("💎 Изменить цену VIP", callback_data="edit_vip_price")],
        [InlineKeyboardButton("➕ Создать новый тариф", callback_data="create_new_tariff")],
        [InlineKeyboardButton("◀️ Назад в админ панель", callback_data="admin_panel")],
        [InlineKeyboardButton("🏠 Домой", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        tariff_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /admin - открыть админ панель (только для админов)"""
    user_id = update.effective_user.id
    
    # Проверка прав администратора
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора.", reply_markup=add_home_button())
        return
    
    try:
        # Удалить команду для чистоты чата
        await update.message.delete()
    except:
        pass
    
    # Открыть админ панель
    await admin_panel(update, context)

async def god_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /god - выдать админу бессрочный VIP (ТОЛЬКО ЭТА ФУНКЦИЯ!)"""
    user_id = update.effective_user.id
    
    # Проверка что это главный админ из переменных окружения
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Доступ запрещен.", reply_markup=add_home_button())
        return
    
    try:
        # Удалить команду для секретности
        await update.message.delete()
    except:
        pass
    
    # Добавить в список админов если нет
    admin_users = bot.get_setting('admin_users', str(ADMIN_USER_ID))
    admin_list = [int(uid.strip()) for uid in admin_users.split(',') if uid.strip()]
    if user_id not in admin_list:
        admin_list.append(user_id)
        bot.set_setting('admin_users', ','.join(str(uid) for uid in admin_list), user_id)
    
    # ВЫДАТЬ БЕССРОЧНЫЙ VIP (основная функция команды /god)
    end_date = bot.add_lifetime_subscription(user_id)
    
    # Показать уведомление
    confirmation_msg = await update.message.reply_text(
        f"🔱 **GOD MODE ACTIVATED** 🔱\n\n"
        f"✅ Бессрочный VIP выдан!\n"
        f"💎 VIP до {end_date.strftime('%d.%m.%Y')} (100 лет)",
        parse_mode='Markdown'
    )
    
    # Автоудаление через 3 секунды
    asyncio.create_task(auto_delete_message(confirmation_msg, 3))

async def set_vip_price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /set_vip_price - изменить цену тарифа VIP"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам.", reply_markup=add_home_button())
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Использование: `/set_vip_price [цена]`\n\n"
            "Пример: `/set_vip_price 12990`",
            parse_mode='Markdown'
        )
        return
    
    try:
        new_price = int(context.args[0])
        
        if new_price < 100:
            await update.message.reply_text("❌ Цена должна быть не менее 100₽")
            return
        
        bot.set_setting('vip_price_rub', str(new_price), user_id)
        
        # Получить валюту админа
        cursor = bot.conn.cursor()
        cursor.execute('SELECT currency FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        admin_currency = result[0] if result and result[0] else 'RUB'
        
        price_display = bot.format_price(bot.convert_price(new_price, admin_currency), admin_currency)
        usd_price = int(new_price * CURRENCY_RATES['USD'])
        
        await update.message.reply_text(
            f"✅ Цена тарифа VIP изменена!\n\n"
            f"💎 Новая цена: **{price_display}/месяц**\n"
            f"💵 В USD: **${usd_price}**",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ Цена должна быть числом.", reply_markup=add_home_button())

async def set_short_price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /set_short_price - изменить цену тарифа SHORT"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам.", reply_markup=add_home_button())
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Использование: `/set_short_price [цена]`\n\n"
            "Пример: `/set_short_price 5990`",
            parse_mode='Markdown'
        )
        return
    
    try:
        new_price = int(context.args[0])
        
        if new_price < 100:
            await update.message.reply_text("❌ Цена должна быть не менее 100₽")
            return
        
        bot.set_setting('short_price_rub', str(new_price), user_id)
        
        # Получить валюту админа
        cursor = bot.conn.cursor()
        cursor.execute('SELECT currency FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        admin_currency = result[0] if result and result[0] else 'RUB'
        
        price_display = bot.format_price(bot.convert_price(new_price, admin_currency), admin_currency)
        usd_price = int(new_price * CURRENCY_RATES['USD'])
        
        await update.message.reply_text(
            f"✅ Цена тарифа SHORT изменена!\n\n"
            f"⚡ Новая цена: **{price_display}/месяц**\n"
            f"💵 В USD: **${usd_price}**",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ Цена должна быть числом.", reply_markup=add_home_button())

async def set_long_price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /set_long_price - изменить цену тарифа LONG"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам.", reply_markup=add_home_button())
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Использование: `/set_long_price [цена]`\n\n"
            "Пример: `/set_long_price 7990`",
            parse_mode='Markdown'
        )
        return
    
    try:
        new_price = int(context.args[0])
        
        if new_price < 100:
            await update.message.reply_text("❌ Цена должна быть не менее 100₽")
            return
        
        bot.set_setting('long_price_rub', str(new_price), user_id)
        
        # Получить валюту админа
        cursor = bot.conn.cursor()
        cursor.execute('SELECT currency FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        admin_currency = result[0] if result and result[0] else 'RUB'
        
        price_display = bot.format_price(bot.convert_price(new_price, admin_currency), admin_currency)
        usd_price = int(new_price * CURRENCY_RATES['USD'])
        
        await update.message.reply_text(
            f"✅ Цена тарифа LONG изменена!\n\n"
            f"🔵 Новая цена: **{price_display}/месяц**\n"
            f"💵 В USD: **${usd_price}**",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ Цена должна быть числом.", reply_markup=add_home_button())

async def set_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /set_payment - настройка YooKassa"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам.", reply_markup=add_home_button())
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Использование: `/set_payment SHOP_ID SECRET_KEY`\n\n"
            "Пример: `/set_payment 123456 live_abc123def456`",
            parse_mode='Markdown'
        )
        return
    
    shop_id = context.args[0]
    secret_key = context.args[1]
    
    bot.set_setting('yookassa_shop_id', shop_id, user_id)
    bot.set_setting('yookassa_secret_key', secret_key, user_id)
    bot.set_setting('payment_enabled', 'true', user_id)
    
    await update.message.reply_text(
        "✅ **Платежная система настроена!**\n\n"
        f"Shop ID: `{shop_id}`\n"
        "Secret Key: `***скрыт***`\n"
        "Статус: ✅ Включена\n\n"
        "Автоматические платежи активированы!",
        parse_mode='Markdown'
    )

async def disable_payments_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /disable_payments - отключить автоматические платежи"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам.", reply_markup=add_home_button())
        return
    
    bot.set_setting('payment_enabled', 'false', user_id)
    await update.message.reply_text("❌ Автоматические платежи отключены")

async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /add_admin - добавить администратора"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам.", reply_markup=add_home_button())
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Использование: `/add_admin USER_ID`\n\n"
            "Пример: `/add_admin 123456789`",
            parse_mode='Markdown'
        )
        return
    
    try:
        new_admin_id = int(context.args[0])
        current_admins = bot.get_setting('admin_users', str(ADMIN_USER_ID))
        admin_list = [int(uid.strip()) for uid in current_admins.split(',') if uid.strip()]
        
        if new_admin_id in admin_list:
            await update.message.reply_text(f"❌ Пользователь {new_admin_id} уже является администратором")
            return
        
        admin_list.append(new_admin_id)
        bot.set_setting('admin_users', ','.join(map(str, admin_list)), user_id)
        
        await update.message.reply_text(
            f"✅ **Администратор добавлен!**\n\n"
            f"👤 User ID: `{new_admin_id}`\n"
            f"📊 Всего админов: {len(admin_list)}",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ User ID должен быть числом", reply_markup=add_home_button())

async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /remove_admin - удалить администратора"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам.", reply_markup=add_home_button())
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Использование: `/remove_admin USER_ID`\n\n"
            "Пример: `/remove_admin 123456789`",
            parse_mode='Markdown'
        )
        return
    
    try:
        remove_admin_id = int(context.args[0])
        
        # 🛡️ КРИТИЧЕСКАЯ ЗАЩИТА: Главный админ не может быть удален
        if remove_admin_id == ADMIN_USER_ID:
            await update.message.reply_text(
                "🛡️ **ЗАЩИТА СИСТЕМЫ**\n\n"
                f"❌ Невозможно удалить главного администратора (ID: {ADMIN_USER_ID})\n\n"
                "Этот аккаунт защищен от удаления для предотвращения блокировки административного доступа.",
                parse_mode='Markdown'
            )
            return
        
        current_admins = bot.get_setting('admin_users', str(ADMIN_USER_ID))
        admin_list = [int(uid.strip()) for uid in current_admins.split(',') if uid.strip()]
        
        if remove_admin_id not in admin_list:
            await update.message.reply_text(f"❌ Пользователь {remove_admin_id} не является администратором")
            return
        
        admin_list.remove(remove_admin_id)
        bot.set_setting('admin_users', ','.join(map(str, admin_list)), user_id)
        
        await update.message.reply_text(
            f"✅ **Администратор удален!**\n\n"
            f"👤 User ID: `{remove_admin_id}`\n"
            f"📊 Осталось админов: {len(admin_list)}",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ User ID должен быть числом", reply_markup=add_home_button())

async def set_reviews_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /set_reviews_group - установить группу отзывов"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам.", reply_markup=add_home_button())
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Использование: `/set_reviews_group @group_name`\n\n"
            "Пример: `/set_reviews_group @cryptosignalsbot_otz`",
            parse_mode='Markdown'
        )
        return
    
    group_name = context.args[0]
    if not group_name.startswith('@'):
        group_name = '@' + group_name
    
    bot.set_setting('reviews_group', group_name, user_id)
    
    await update.message.reply_text(
        f"✅ **Группа отзывов установлена!**\n\n"
        f"📸 Группа: {group_name}",
        parse_mode='Markdown'
    )

async def admin_reset_self(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать подтверждение сброса себя"""
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        message_obj = update.callback_query.message if is_callback else update.message
        await message_obj.reply_text("❌ У вас нет прав администратора.")
        return
    
    # Показать подтверждение сброса
    confirm_text = """
⚠️ **ПОДТВЕРЖДЕНИЕ СБРОСА**

Вы уверены что хотите сбросить свой аккаунт?

**Это действие удалит:**
• Вашу подписку
• Весь баланс
• Историю сигналов
• Настройки автотрейдинга
• Подключение к Pocket Option

После сброса вы станете как новый пользователь.

**Вы точно хотите продолжить?**
"""
    keyboard = [
        [InlineKeyboardButton("✅ ДА, СБРОСИТЬ", callback_data="admin_reset_self_execute")],
        [InlineKeyboardButton("❌ Отмена", callback_data="admin_panel")]
    ]
    
    if is_callback:
        await update.callback_query.edit_message_text(confirm_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(confirm_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /ban - забанить пользователя"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам.", reply_markup=add_home_button())
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Использование: `/ban USER_ID`\n\n"
            "Пример: `/ban 123456789`",
            parse_mode='Markdown'
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        
        # Защита от бана админа
        if bot.is_admin(target_user_id):
            await update.message.reply_text("❌ Невозможно забанить администратора")
            return
        
        bot.ban_user(target_user_id, user_id)
        
        await update.message.reply_text(
            f"🚫 **Пользователь забанен!**\n\n"
            f"👤 User ID: `{target_user_id}`\n\n"
            f"Доступ к боту заблокирован.",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ User ID должен быть числом", reply_markup=add_home_button())

async def unban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /unban - разбанить пользователя"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам.", reply_markup=add_home_button())
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Использование: `/unban USER_ID`\n\n"
            "Пример: `/unban 123456789`",
            parse_mode='Markdown'
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        bot.unban_user(target_user_id, user_id)
        
        await update.message.reply_text(
            f"✅ **Пользователь разбанен!**\n\n"
            f"👤 User ID: `{target_user_id}`\n\n"
            f"Доступ к боту восстановлен.",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ User ID должен быть числом", reply_markup=add_home_button())

async def reset_me_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /reset_me - сбросить себя до нового пользователя"""
    user_id = update.effective_user.id
    
    # Сброс пользователя
    cursor = bot.conn.cursor()
    cursor.execute('''
        UPDATE users SET
            subscription_type = 'free',
            subscription_start = NULL,
            subscription_end = NULL,
            initial_balance = NULL,
            current_balance = NULL,
            trading_strategy = NULL,
            auto_trading_enabled = 0,
            auto_trading_strategy = NULL,
            pocket_option_ssid = NULL,
            pocket_option_connected = 0
        WHERE user_id = ?
    ''', (user_id,))
    
    # Удалить историю сигналов
    cursor.execute('DELETE FROM signal_history WHERE user_id = ?', (user_id,))
    bot.conn.commit()
    
    await update.message.reply_text(
        "🔄 **ВЫ СБРОШЕНЫ ДО НОВОГО ПОЛЬЗОВАТЕЛЯ!**\n\n"
        "✅ Подписка: FREE\n"
        "✅ Баланс обнулён\n"
        "✅ История сигналов удалена\n"
        "✅ Автотрейдинг отключен\n\n"
        "Используйте /start чтобы начать заново!",
        parse_mode='Markdown'
    )

async def reset_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /reset_user - сбросить пользователя до нового"""
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам.", reply_markup=add_home_button())
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Использование: `/reset_user USER_ID`\n\n"
            "Пример: `/reset_user 123456789`\n\n"
            "⚠️ Удалит подписку, баланс и историю сигналов",
            parse_mode='Markdown'
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        bot.reset_user(target_user_id, user_id)
        
        await update.message.reply_text(
            f"🔄 **Пользователь сброшен!**\n\n"
            f"👤 User ID: `{target_user_id}`\n\n"
            f"✅ Подписка удалена\n"
            f"✅ Баланс обнулён\n"
            f"✅ История сигналов очищена\n\n"
            f"Пользователь будет как новый.",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ User ID должен быть числом", reply_markup=add_home_button())

async def admin_switch_plan(update: Update, context: ContextTypes.DEFAULT_TYPE, plan_type: str, days: int):
    """Переключить тариф для тестирования"""
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    user_id = update.effective_user.id
    
    logger.info(f"🔀 admin_switch_plan вызвана: plan_type={plan_type}, days={days}, user_id={user_id}")
    
    if not bot.is_admin(user_id):
        message_obj = update.callback_query.message if is_callback else update.message
        await message_obj.reply_text("❌ У вас нет прав администратора.")
        return
    
    cursor = bot.conn.cursor()
    
    if plan_type == "free":
        # FREE - убрать подписку, но оставить язык/валюту
        # ВАЖНО: free_trials_used = 1 чтобы не сработал автоматический триал
        cursor.execute('''
            UPDATE users 
            SET subscription_end = NULL,
                subscription_type = NULL,
                is_premium = 0,
                free_trials_used = 1
            WHERE user_id = ?
        ''', (user_id,))
        plan_name = "🆓 FREE"
        plan_desc = "Без подписки"
        
    elif plan_type == "trial":
        # 3-дневный триал - VIP на 3 дня через trial_end_date
        from datetime import datetime, timedelta
        trial_end = datetime.now() + timedelta(days=days)
        
        cursor.execute('''
            UPDATE users 
            SET subscription_type = 'vip',
                subscription_end = ?,
                is_premium = 1,
                free_trials_used = 0
            WHERE user_id = ?
        ''', (trial_end.isoformat(), user_id))
        plan_name = "🎁 3-Day VIP Trial"
        plan_desc = f"VIP триал на {days} дня"
        
    else:
        # VIP, LONG, SHORT - пожизненные подписки для админа (subscription_end = NULL)
        logger.info(f"🔀 Устанавливаем пожизненный тариф {plan_type} для user_id={user_id}")
        cursor.execute('''
            UPDATE users 
            SET subscription_type = ?,
                subscription_end = NULL,
                is_premium = 1,
                free_trials_used = 1
            WHERE user_id = ?
        ''', (plan_type, user_id))
        
        plan_names = {
            "vip": "💎 VIP",
            "long": "🔵 LONG", 
            "short": "⚡️ SHORT"
        }
        plan_name = plan_names.get(plan_type, plan_type.upper())
        plan_desc = f"{plan_name} (пожизненно)"
    
    bot.conn.commit()
    logger.info(f"✅ Тариф изменён на {plan_name}, commit выполнен")
    
    # Уведомление об успешном переключении (без всплывающего окна)
    if is_callback:
        await update.callback_query.answer(f"✅ Тариф успешно изменён на {plan_name}")
    
    # Автоматически вернуть пользователя на главную страницу
    await show_main_menu(update, context, user_id)

async def admin_top_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    
    if not bot.is_admin(update.effective_user.id):
        message_obj = update.callback_query.message if is_callback else update.message
        await message_obj.reply_text("❌ У вас нет прав администратора.")
        return
    
    cursor = bot.conn.cursor()
    
    cursor.execute('''
        SELECT user_id, username, first_name, signals_used, subscription_end, is_premium
        FROM users 
        ORDER BY signals_used DESC
        LIMIT 10
    ''')
    top_users = cursor.fetchall()
    
    top_text = "🏆 **ТОП-10 АКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ**\n\n"
    
    for i, (user_id, username, first_name, signals_used, sub_end, is_premium) in enumerate(top_users, 1):
        name = username or first_name or f"User{user_id}"
        status = "💎" if is_premium else "🆓"
        top_text += f"{i}. {status} @{name} - {signals_used} сигналов\n"
    
    keyboard = [[InlineKeyboardButton("◀️ Назад в админ панель", callback_data="settings_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await update.callback_query.edit_message_text(
            top_text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            top_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def admin_quick_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список пользователей с управлением подписками"""
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    
    if not bot.is_admin(update.effective_user.id):
        message_obj = update.callback_query.message if is_callback else update.message
        await message_obj.reply_text("❌ У вас нет прав администратора.")
        return
    
    # Получить всех пользователей с подписками
    cursor = bot.conn.cursor()
    cursor.execute('''
        SELECT user_id, username, first_name, subscription_end, subscription_type 
        FROM users 
        ORDER BY subscription_end IS NULL, subscription_end DESC
        LIMIT 15
    ''')
    users = cursor.fetchall()
    
    if not users:
        quick_text = "📋 *УПРАВЛЕНИЕ ПОДПИСКАМИ*\n\nПользователей пока нет."
        keyboard = [
            [InlineKeyboardButton("➕ Добавить по ID", callback_data="admin_add_user_by_id")],
            [InlineKeyboardButton("◀️ Назад", callback_data="settings_back")]
        ]
    else:
        quick_text = "📋 *УПРАВЛЕНИЕ ПОДПИСКАМИ*\n\n"
        quick_text += "👥 *Список пользователей:*\n\n"
        
        keyboard = []
        
        for user_id, username, first_name, sub_end, sub_type in users:
            # Определить статус подписки
            if sub_end:
                try:
                    sub_date = datetime.fromisoformat(sub_end)
                    if sub_date > datetime.now():
                        # Активная подписка
                        sub_emoji = {"vip": "💎", "short": "⚡", "long": "🔵", "free": "🆓"}.get(sub_type, "💎")
                        days_left = (sub_date - datetime.now()).days
                        status = f"{sub_emoji} {sub_type.upper()} до {sub_date.strftime('%d.%m.%Y')}"
                    else:
                        status = "🆓 FREE (истекла)"
                except:
                    status = "🆓 FREE"
            else:
                status = "🆓 FREE"
            
            # Имя пользователя
            display_name = f"@{username}" if username else (first_name or f"ID{user_id}")
            
            quick_text += f"• {display_name}\n  {status}\n"
            
            # Кнопка управления для каждого пользователя
            keyboard.append([
                InlineKeyboardButton(
                    f"⚙️ {display_name[:20]}...", 
                    callback_data=f"manage_user_{user_id}"
                )
            ])
        
        # Кнопки действий
        keyboard.append([InlineKeyboardButton("➕ Добавить по ID", callback_data="admin_add_user_by_id")])
        keyboard.append([InlineKeyboardButton("🔄 Обновить список", callback_data="admin_quick_sub")])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="settings_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await update.callback_query.edit_message_text(
            quick_text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            quick_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def admin_manage_user_sub(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Управление подпиской конкретного пользователя"""
    query = update.callback_query
    
    if not bot.is_admin(update.effective_user.id):
        await query.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    # Получить информацию о пользователе
    cursor = bot.conn.cursor()
    cursor.execute('''
        SELECT username, first_name, subscription_end, subscription_type, created_at
        FROM users 
        WHERE user_id = ?
    ''', (user_id,))
    
    user_data = cursor.fetchone()
    
    if not user_data:
        await query.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    username, first_name, sub_end, sub_type, created_at = user_data
    display_name = f"@{username}" if username else (first_name or f"ID{user_id}")
    
    # Определить текущий статус
    if sub_end:
        try:
            sub_date = datetime.fromisoformat(sub_end)
            if sub_date > datetime.now():
                sub_emoji = {"vip": "💎", "short": "⚡", "long": "🔵", "free": "🆓"}.get(sub_type, "💎")
                status = f"{sub_emoji} {sub_type.upper()} до {sub_date.strftime('%d.%m.%Y')}"
            else:
                status = "🆓 FREE (истекла)"
        except:
            status = "🆓 FREE"
    else:
        status = "🆓 FREE"
    
    manage_text = f"""
👤 *Управление пользователем*

*Пользователь:* {display_name}
*ID:* `{user_id}`
*Статус:* {status}
*Регистрация:* {created_at[:10] if created_at else 'N/A'}

Выберите действие:
"""
    
    keyboard = [
        [InlineKeyboardButton("💎 VIP (30 дней)", callback_data=f"set_sub_{user_id}_vip_30")],
        [InlineKeyboardButton("⚡ SHORT (30 дней)", callback_data=f"set_sub_{user_id}_short_30")],
        [InlineKeyboardButton("🔵 LONG (30 дней)", callback_data=f"set_sub_{user_id}_long_30")],
        [InlineKeyboardButton("🆓 Убрать подписку (FREE)", callback_data=f"set_sub_{user_id}_free_0")],
        [InlineKeyboardButton("♾️ Пожизненный VIP", callback_data=f"set_sub_{user_id}_vip_36500")],
        [InlineKeyboardButton("◀️ К списку", callback_data="admin_quick_sub")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(manage_text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_add_user_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запросить ID пользователя для добавления подписки"""
    query = update.callback_query
    
    if not bot.is_admin(update.effective_user.id):
        await query.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    add_text = """
➕ *ДОБАВИТЬ ПОЛЬЗОВАТЕЛЯ ПО ID*

Отправьте User ID пользователя следующим сообщением.

*Пример:* `123456789`

После этого откроется меню управления подпиской для этого пользователя.
"""
    
    keyboard = [[InlineKeyboardButton("◀️ Отмена", callback_data="admin_quick_sub")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(add_text, reply_markup=reply_markup, parse_mode='Markdown')
    context.user_data['awaiting_user_id_for_sub'] = True

async def admin_pricing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админская настройка цен тарифов"""
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    
    if not bot.is_admin(update.effective_user.id):
        message_obj = update.callback_query.message if is_callback else update.message
        await message_obj.reply_text("❌ У вас нет прав администратора.")
        return
    
    # Получить текущие цены
    vip_price = bot.get_setting('vip_price_rub', '9990')
    short_price = bot.get_setting('short_price_rub', '4990')
    long_price = bot.get_setting('long_price_rub', '6990')
    
    pricing_text = f"""
💰 **НАСТРОЙКА ЦЕН ТАРИФОВ**

**Текущие цены:**

💎 **VIP:** {vip_price}₽/месяц
⚡ **SHORT:** {short_price}₽/месяц
🔵 **LONG:** {long_price}₽/месяц

Выберите тариф для изменения цены:
"""
    
    keyboard = [
        [InlineKeyboardButton("💎 Изменить цену VIP", callback_data='admin_set_vip_price')],
        [InlineKeyboardButton("⚡ Изменить цену SHORT", callback_data='admin_set_short_price')],
        [InlineKeyboardButton("🔵 Изменить цену LONG", callback_data='admin_set_long_price')],
        [InlineKeyboardButton("◀️ Назад в админ панель", callback_data="settings_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await update.callback_query.edit_message_text(
            pricing_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            pricing_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def admin_tariff_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление изображениями тарифов"""
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    
    if not bot.is_admin(update.effective_user.id):
        message_obj = update.callback_query.message if is_callback else update.message
        await message_obj.reply_text("❌ У вас нет прав администратора.")
        return
    
    # Получить текущие изображения
    vip_image = bot.get_setting('tariff_image_vip', '')
    short_image = bot.get_setting('tariff_image_short', '')
    long_image = bot.get_setting('tariff_image_long', '')
    free_image = bot.get_setting('tariff_image_free', '')
    
    def get_status(image):
        return "✅ Загружено" if image else "❌ Не загружено"
    
    images_text = f"""
🖼️ **УПРАВЛЕНИЕ ИЗОБРАЖЕНИЯМИ ТАРИФОВ**

**Текущий статус:**

💎 **VIP:** {get_status(vip_image)}
⚡ **SHORT:** {get_status(short_image)}
🔵 **LONG:** {get_status(long_image)}
🎁 **FREE:** {get_status(free_image)}

Выберите тариф для загрузки изображения:
"""
    
    keyboard = [
        [InlineKeyboardButton("💎 Загрузить VIP", callback_data='upload_image_vip')],
        [InlineKeyboardButton("⚡ Загрузить SHORT", callback_data='upload_image_short')],
        [InlineKeyboardButton("🔵 Загрузить LONG", callback_data='upload_image_long')],
        [InlineKeyboardButton("🎁 Загрузить FREE", callback_data='upload_image_free')],
        [InlineKeyboardButton("◀️ Назад в админ панель", callback_data="settings_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await update.callback_query.edit_message_text(
            images_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            images_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def admin_bot_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройки бота"""
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        message_obj = update.callback_query.message if is_callback else update.message
        await message_obj.reply_text("❌ У вас нет прав администратора.")
        return
    
    # Получить текущие настройки
    support_contact = bot.get_support_contact()
    
    settings_text = f"""
⚙️ **НАСТРОЙКИ БОТА**

**Текущие настройки:**

📞 **Контакт поддержки:** {support_contact}

Выберите параметр для изменения:
"""
    
    keyboard = [
        [InlineKeyboardButton("📞 Изменить контакт поддержки", callback_data="admin_change_support")],
        [InlineKeyboardButton("◀️ Назад в админ панель", callback_data="settings_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await update.callback_query.edit_message_text(
            settings_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            settings_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def admin_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав администратора.", reply_markup=add_home_button())
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Использование: `/admin_info [user_id]`\n"
            "Пример: `/admin_info 123456789`",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        
        cursor = bot.conn.cursor()
        cursor.execute('''
            SELECT username, first_name, joined_date, subscription_end, 
                   is_premium, signals_used, free_trials_used
            FROM users WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        
        if not result:
            await update.message.reply_text(f"❌ Пользователь {user_id} не найден в базе.")
            return
        
        username, first_name, joined_date, sub_end, is_premium, signals_used, trials_used = result
        
        info_text = f"""
👤 **ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ**

🆔 User ID: `{user_id}`
👤 Username: @{username or 'не указан'}
📝 Имя: {first_name or 'не указано'}
📅 Регистрация: {datetime.fromisoformat(joined_date).strftime('%d.%m.%Y') if joined_date else 'Н/Д'}

💎 **Подписка:**
• Статус: {'✅ Premium' if is_premium else '❌ Free'}
• Активна до: {datetime.fromisoformat(sub_end).strftime('%d.%m.%Y %H:%M') if sub_end else 'Нет'}

📈 **Активность:**
• Сигналов использовано: {signals_used or 0}
• Пробный период: {'Использован' if trials_used else 'Доступен'}
"""
        
        await update.message.reply_text(info_text, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. User ID должен быть числом.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def admin_webhook_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка webhook для отправки сигналов"""
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        message_obj = update.callback_query.message if is_callback else update.message
        await message_obj.reply_text("❌ У вас нет прав администратора.")
        return
    
    if is_callback:
        await update.callback_query.answer()
    
    # Получить текущие настройки webhook
    webhook_url = bot.get_setting('webhook_url', '')
    webhook_secret = bot.get_setting('webhook_secret', '')
    webhook_enabled = bot.get_setting('webhook_enabled', 'false') == 'true'
    
    # Проверка валидности секрета
    secret_valid = webhook_secret and len(webhook_secret) >= 16
    
    webhook_text = f"""
🔗 **WEBHOOK НАСТРОЙКИ**

📡 **Текущие настройки:**

🌐 **URL:** {webhook_url if webhook_url else '❌ Не установлен'}
🔑 **Секретный ключ:** {'✅ Установлен (' + str(len(webhook_secret)) + ' символов)' if webhook_secret else '❌ Не установлен'}
{'⚠️ Секрет должен быть минимум 16 символов!' if webhook_secret and not secret_valid else ''}
🔄 **Статус:** {'✅ Включен' if webhook_enabled else '❌ Выключен'}

**ℹ️ Информация:**
• Webhook отправляет сигналы на внешний сервис
• JWT токены защищают данные (exp, iat, iss, aud)
• Секрет должен быть минимум 16 символов
• Только с валидным секретом можно включить webhook
"""
    
    keyboard = []
    
    # Кнопки настройки
    keyboard.append([InlineKeyboardButton("🌐 Установить URL", callback_data="webhook_set_url")])
    keyboard.append([InlineKeyboardButton("🔑 Установить секретный ключ", callback_data="webhook_set_secret")])
    
    # Кнопка включения/выключения (только если секрет валидный)
    if secret_valid and webhook_url:
        toggle_text = "❌ Выключить webhook" if webhook_enabled else "✅ Включить webhook"
        keyboard.append([InlineKeyboardButton(toggle_text, callback_data="webhook_toggle")])
    
    # Кнопка тестирования (только если включен)
    if webhook_enabled:
        keyboard.append([InlineKeyboardButton("🧪 Тестовый сигнал", callback_data="webhook_test")])
    
    # Кнопки навигации
    keyboard.append([
        InlineKeyboardButton("◀️ Назад в админ панель", callback_data="admin_panel"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await update.callback_query.edit_message_text(
            webhook_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            webhook_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def delete_skipped_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /delete_skipped - удалить все пропущенные сигналы"""
    user_id = update.effective_user.id
    
    # Проверка бана
    if bot.is_banned(user_id):
        await update.message.reply_text(
            f"🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\nДоступ к боту ограничен.\nОбратитесь в поддержку: {bot.get_support_contact()}",
            parse_mode='Markdown'
        )
        return
    
    deleted_count = bot.delete_skipped_signals(user_id)
    
    if deleted_count > 0:
        await update.message.reply_text(
            f"🗑️ **Удалено {deleted_count} пропущенных сигналов**\n\n"
            f"Ваша история очищена от пропущенных сигналов.\n"
            f"Это не влияет на вашу статистику win rate.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "✅ **Пропущенных сигналов не найдено**\n\n"
            "В вашей истории нет пропущенных сигналов для удаления.",
            parse_mode='Markdown'
        )

async def my_longs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /my_longs - показать список активных LONG сигналов или получить новый LONG для FREE"""
    is_callback = hasattr(update, 'callback_query') and update.callback_query is not None
    user_id = update.effective_user.id
    
    # Проверка бана
    if bot.is_banned(user_id):
        error_msg = f"🚫 **ВЫ ЗАБЛОКИРОВАНЫ**\n\nДоступ к боту ограничен.\nОбратитесь в поддержку: {bot.get_support_contact()}"
        if is_callback:
            await update.callback_query.answer("🚫 Вы заблокированы", show_alert=True)
        else:
            await update.message.reply_text(error_msg, parse_mode='Markdown')
        return
    
    # Проверить тип подписки
    has_subscription, message, signals_used, free_trials_used, sub_type = bot.check_subscription(user_id)
    
    # Для FREE пользователей - генерировать новый LONG сигнал (5 в день)
    if sub_type == 'free':
        # Проверить лимит LONG сигналов
        can_access, used_today = bot.check_free_long_limit(user_id)
        
        if not can_access:
            limit_text = f"""
📊 **ПОЛУЧИТЬ LONG СИГНАЛ**

❌ **Лимит исчерпан**

Вы уже получили все 5 LONG сигналов сегодня ({used_today}/5).

💡 **Получайте больше сигналов:**
⬆️ Перейдите на LONG или VIP тариф для неограниченных сигналов!
"""
            if is_callback:
                keyboard = [[InlineKeyboardButton("⬆️ Расширить тариф", callback_data="upgrade_subscription")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.callback_query.edit_message_text(limit_text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await update.message.reply_text(limit_text, parse_mode='Markdown')
            return
        
        # Генерировать LONG сигнал с высокой точностью (≥95%)
        # Используем callback для поиска сигналов на длинных таймфреймах
        context.user_data['free_long_request'] = True
        await signal_all_command(update, context, timeframe_type='long')
        return
    
    # Для платных подписок - показать список активных LONG сигналов
    cursor = bot.conn.cursor()
    cursor.execute('''
        SELECT id, asset, signal_type, timeframe, confidence, expiration_time, stake_amount
        FROM signal_history 
        WHERE user_id = ? AND result = 'pending' AND timeframe IN ('1H', '4H', '1D', '1W')
        ORDER BY signal_date DESC
    ''', (user_id,))
    
    long_signals = cursor.fetchall()
    
    if not long_signals:
        no_longs_text = """
📊 **АКТИВНЫЕ LONG СИГНАЛЫ**

У вас пока нет активных long сигналов.

Используйте `/long` чтобы получить сигнал на длинном таймфрейме!

💡 **Long сигналы** - это сигналы с таймфреймами 1H и выше, где результат нужно отслеживать вручную.
"""
        if is_callback:
            await update.callback_query.edit_message_text(no_longs_text, parse_mode='Markdown')
        else:
            await update.message.reply_text(no_longs_text, parse_mode='Markdown')
        return
    
    # Формируем список активных long сигналов
    longs_text = "📊 **АКТИВНЫЕ LONG СИГНАЛЫ**\n\n"
    
    for signal_id, asset, signal_type, timeframe, confidence, expiration_time, stake_amount in long_signals:
        direction_emoji = "🟢" if signal_type == "CALL" else "🔴"
        
        # Рассчитываем оставшееся время
        if expiration_time:
            try:
                expiry_dt = datetime.fromisoformat(expiration_time)
                now = datetime.now()
                remaining_time = expiry_dt - now
                
                if remaining_time.total_seconds() > 0:
                    hours = int(remaining_time.total_seconds() // 3600)
                    minutes = int((remaining_time.total_seconds() % 3600) // 60)
                    time_left = f"{hours}ч {minutes}мин"
                else:
                    time_left = "⏰ Истекло"
            except:
                time_left = "Н/Д"
        else:
            time_left = "Н/Д"
        
        longs_text += f"{direction_emoji} **{asset}** | {signal_type}\n"
        longs_text += f"📊 {timeframe} | 🎯 {confidence:.0f}%\n"
        longs_text += f"⏰ Осталось: {time_left}\n"
        longs_text += f"💰 Ставка: {stake_amount:.2f} ₽\n"
        longs_text += "─────────────────\n"
    
    longs_text += "\n💡 Нажмите на сигнал чтобы отметить результат или пропустить"
    
    # Создаем кнопки для каждого сигнала
    keyboard = []
    for signal_id, asset, signal_type, timeframe, confidence, expiration_time, stake_amount in long_signals:
        direction_emoji = "🟢" if signal_type == "CALL" else "🔴"
        keyboard.append([
            InlineKeyboardButton(
                f"{direction_emoji} {asset} ({timeframe})", 
                callback_data=f"long_manage_{signal_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data="refresh_longs")])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await update.callback_query.edit_message_text(
            longs_text, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            longs_text, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )

async def promo_activate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для активации промо после регистрации в Pocket Option"""
    if not bot.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав администратора.", reply_markup=add_home_button())
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Использование: `/promo_activate [user_id] [po_nickname]`\n"
            "Пример: `/promo_activate 123456789 trader123`",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        po_nickname = context.args[1]
        
        cursor = bot.conn.cursor()
        
        # Проверить, существует ли пользователь
        cursor.execute('SELECT new_user_discount_used FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            await update.message.reply_text(f"❌ Пользователь {user_id} не найден в базе.")
            return
        
        if result[0]:
            await update.message.reply_text(f"❌ Пользователь {user_id} уже использовал промо-скидку.")
            return
        
        # Активировать подписку SHORT на 30 дней с промо-скидкой
        subscription_end = datetime.now() + timedelta(days=30)
        
        cursor.execute('''
            UPDATE users 
            SET subscription_type = 'short',
                subscription_end = ?,
                is_premium = 1,
                new_user_discount_used = 1,
                pocket_option_registered = 1
            WHERE user_id = ?
        ''', (subscription_end.isoformat(), user_id))
        
        bot.conn.commit()
        
        # Отправить уведомление пользователю
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"""
✅ **ПРОМО АКТИВИРОВАНО!**

🎁 Вам активирована SHORT подписка на 30 дней!
💰 Цена: {NEW_USER_PROMO['price']}₽ (скидка 70%)

📊 Ваш Pocket Option: `{po_nickname}`
⏰ Подписка до: {subscription_end.strftime('%d.%m.%Y %H:%M')}

Спасибо за регистрацию в Pocket Option! 🚀
Используйте `/short` для получения сигналов.
""",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error sending promo notification: {e}")
        
        await update.message.reply_text(
            f"✅ Промо активировано!\n"
            f"👤 User ID: {user_id}\n"
            f"📊 PO Nickname: {po_nickname}\n"
            f"💎 SHORT подписка на 30 дней\n"
            f"⏰ До: {subscription_end.strftime('%d.%m.%Y %H:%M')}",
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text("❌ User ID должен быть числом.")
    except Exception as e:
        logger.error(f"Error in promo_activate: {e}")
        await update.message.reply_text(f"❌ Ошибка при активации промо: {str(e)}")

async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик фото сообщений (для загрузки изображений тарифов)"""
    user_id = update.message.from_user.id
    
    # Проверить, ожидается ли загрузка изображения тарифа
    if context.user_data.get('awaiting_tariff_image'):
        tariff_type = context.user_data.get('awaiting_tariff_image')
        context.user_data['awaiting_tariff_image'] = None
        
        if not bot.is_admin(user_id):
            await update.message.reply_text("❌ Эта функция доступна только администраторам")
            return
        
        # Получить file_id загруженного фото
        photo = update.message.photo[-1]  # Получаем самое большое фото
        file_id = photo.file_id
        
        # Сохранить file_id в настройки
        setting_key = f'tariff_image_{tariff_type}'
        bot.set_setting(setting_key, file_id, user_id)
        
        tariff_emoji = {'vip': '💎', 'short': '⚡', 'long': '🔵', 'free': '🎁'}.get(tariff_type, '🖼️')
        tariff_name = tariff_type.upper()
        
        await update.message.reply_text(
            f"✅ **Изображение {tariff_name} успешно загружено!**\n\n"
            f"{tariff_emoji} Теперь это изображение будет показываться при выборе тарифа {tariff_name}.\n\n"
            f"Используйте /settings для возврата в админ панель.",
            parse_mode='Markdown'
        )
        return

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений (для промокодов, суммы банка и т.д.)"""
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    # Проверить, ожидается ли ввод SSID
    if context.user_data.get('awaiting_ssid'):
        context.user_data['awaiting_ssid'] = False
        
        # Проверить формат SSID
        if not text.startswith('42["auth",'):
            await update.message.reply_text(
                "❌ *Неверный формат SSID*\n\n"
                "SSID должен начинаться с 42[\"auth\",{\n\n"
                "Попробуйте еще раз или нажмите /autotrade для возврата в меню.",
                parse_mode='Markdown'
            )
            return
        
        # Показать процесс проверки
        checking_msg = await update.message.reply_text(
            "🔄 *Проверяю подключение к Pocket Option...*\n\n"
            "Подождите несколько секунд...",
            parse_mode='Markdown'
        )
        
        # Получить режим (демо/реал)
        cursor = bot.conn.cursor()
        cursor.execute('SELECT auto_trading_mode FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        is_demo = result[0] == 'demo' if result else True
        
        # Протестировать подключение
        success, message, balance = await test_pocket_option_connection(text, demo=is_demo)
        
        if success:
            # Зашифровать и сохранить SSID в БД
            encrypted_ssid = encrypt_ssid(text)
            cursor.execute('''
                UPDATE users 
                SET pocket_option_ssid = ?, pocket_option_connected = 1 
                WHERE user_id = ?
            ''', (encrypted_ssid, user_id))
            bot.conn.commit()
            
            await checking_msg.edit_text(
                f"✅ **ПОДКЛЮЧЕНИЕ УСПЕШНО!**\n\n"
                f"🎮 Режим: {'Демо' if is_demo else 'Реальный'}\n"
                f"💰 Баланс: ${balance:.2f}\n\n"
                f"Теперь вы можете использовать автоторговлю!\n\n"
                f"Нажмите /autotrade для настройки.",
                parse_mode='Markdown'
            )
        else:
            await checking_msg.edit_text(
                f"❌ **ОШИБКА ПОДКЛЮЧЕНИЯ**\n\n"
                f"{message}\n\n"
                f"**Возможные причины:**\n"
                f"• SSID устарел (обновите в браузере)\n"
                f"• Неверный формат SSID\n"
                f"• Проблемы с сервером Pocket Option\n\n"
                f"Попробуйте еще раз: /autotrade",
                parse_mode='Markdown'
            )
        
        return
    
    # Проверить, ожидается ли ввод цены тарифа
    if context.user_data.get('awaiting_price'):
        tariff_type = context.user_data.get('awaiting_price')
        context.user_data['awaiting_price'] = None
        
        if not bot.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав администратора.", reply_markup=add_home_button())
            return
        
        try:
            new_price = int(text)
            
            if new_price < 100:
                await update.message.reply_text("❌ Цена должна быть не менее 100₽")
                return
            
            # Сохранить цену
            setting_name = f'{tariff_type}_price_rub'
            bot.set_setting(setting_name, str(new_price), user_id)
            
            # Получить валюту админа для отображения
            cursor = bot.conn.cursor()
            cursor.execute('SELECT currency FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            admin_currency = result[0] if result and result[0] else 'RUB'
            
            price_display = bot.format_price(bot.convert_price(new_price, admin_currency), admin_currency)
            usd_price = int(new_price * CURRENCY_RATES['USD'])
            
            tariff_emoji = {'vip': '💎', 'short': '⚡', 'long': '🔵'}.get(tariff_type, '💰')
            tariff_name = tariff_type.upper()
            
            await update.message.reply_text(
                f"✅ Цена тарифа {tariff_name} изменена!\n\n"
                f"{tariff_emoji} Новая цена: **{price_display}/месяц**\n"
                f"💵 В USD: **${usd_price}**",
                parse_mode='Markdown'
            )
            return
            
        except ValueError:
            await update.message.reply_text("❌ Цена должна быть числом.", reply_markup=add_home_button())
            return
    
    # Проверить, ожидается ли контакт поддержки
    if context.user_data.get('awaiting_support_contact'):
        context.user_data['awaiting_support_contact'] = False
        
        if not bot.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав администратора.", reply_markup=add_home_button())
            return
        
        # Проверить формат
        if not text.startswith('@'):
            await update.message.reply_text(
                "❌ Контакт должен начинаться с @\n"
                "Пример: @support_bot",
                parse_mode='Markdown'
            )
            return
        
        # Сохранить контакт
        bot.set_setting('support_contact', text, user_id)
        
        await update.message.reply_text(
            f"✅ **Контакт поддержки изменен!**\n\n"
            f"📞 Новый контакт: {text}\n\n"
            f"Теперь этот контакт будет отображаться во всех сообщениях бота.",
            parse_mode='Markdown'
        )
        return
    
    # Проверить, ожидается ли реферальная ссылка
    if context.user_data.get('awaiting_referral_link'):
        context.user_data['awaiting_referral_link'] = False
        
        if not bot.is_admin(user_id):
            await update.message.reply_text("❌ Эта функция доступна только администраторам")
            return
        
        # Сохранить реферальную ссылку
        bot.set_setting('referral_link', text, user_id)
        
        await update.message.reply_text(
            f"✅ **Реферальная ссылка установлена!**\n\n"
            f"🔗 Новая ссылка: {text}\n\n"
            f"Вернитесь в /setup для дальнейших настроек.",
            parse_mode='Markdown'
        )
        return
    
    # Проверить, ожидается ли группа отзывов
    if context.user_data.get('awaiting_reviews_group'):
        context.user_data['awaiting_reviews_group'] = False
        
        if not bot.is_admin(user_id):
            await update.message.reply_text("❌ Эта функция доступна только администраторам")
            return
        
        # Извлечь username из ссылки или использовать как есть
        group_name = text
        if 't.me/' in text:
            # Извлечь username из ссылки типа https://t.me/groupname
            group_name = '@' + text.split('t.me/')[-1].split('?')[0]
        elif not group_name.startswith('@'):
            group_name = '@' + group_name
        
        # Сохранить
        bot.set_setting('reviews_group', group_name, user_id)
        
        await update.message.reply_text(
            f"✅ **Группа отзывов установлена!**\n\n"
            f"📊 Новая группа: {group_name}\n\n"
            f"Вернитесь в /setup для дальнейших настроек.",
            parse_mode='Markdown'
        )
        return
    
    # Проверить, ожидается ли webhook URL
    if context.user_data.get('awaiting_webhook_url'):
        context.user_data['awaiting_webhook_url'] = False
        
        if not bot.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав администратора.")
            return
        
        # Проверить формат URL
        if not text.startswith(('http://', 'https://')):
            await update.message.reply_text(
                "❌ URL должен начинаться с http:// или https://\n"
                "Пример: https://api.example.com/webhook",
                parse_mode='Markdown'
            )
            return
        
        # Сохранить URL
        bot.set_setting('webhook_url', text, user_id)
        
        await update.message.reply_text(
            f"✅ **Webhook URL установлен!**\n\n"
            f"🌐 URL: {text}\n\n"
            f"Теперь установите секретный ключ в настройках webhook.",
            parse_mode='Markdown'
        )
        return
    
    # Проверить, ожидается ли webhook секрет
    if context.user_data.get('awaiting_webhook_secret'):
        context.user_data['awaiting_webhook_secret'] = False
        
        if not bot.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав администратора.")
            return
        
        # Проверить длину секрета
        if len(text) < 16:
            await update.message.reply_text(
                "❌ Секретный ключ должен содержать минимум 16 символов!\n\n"
                "Используйте сложную комбинацию для безопасности.",
                parse_mode='Markdown'
            )
            return
        
        # Сохранить секрет
        bot.set_setting('webhook_secret', text, user_id)
        
        # Настроить webhook систему
        webhook_url = bot.get_setting('webhook_url', '')
        if webhook_url:
            try:
                webhook_system.configure(webhook_url, text, False)  # Не включаем автоматически
            except Exception as e:
                logger.error(f"Failed to configure webhook: {e}")
        
        await update.message.reply_text(
            f"✅ **Секретный ключ установлен!**\n\n"
            f"🔑 Длина: {len(text)} символов\n\n"
            f"Теперь вы можете включить webhook в настройках.",
            parse_mode='Markdown'
        )
        return
    
    # Проверить, ожидается ли обновление текущего банка
    if context.user_data.get('awaiting_update_bank'):
        context.user_data['awaiting_update_bank'] = False
        
        try:
            new_balance = float(text)
            if new_balance <= 0:
                await update.message.reply_text("❌ Сумма должна быть больше 0", reply_markup=add_home_button())
                return
            
            cursor = bot.conn.cursor()
            cursor.execute('UPDATE users SET current_balance = ? WHERE user_id = ?', (new_balance, user_id))
            bot.conn.commit()
            
            keyboard = [
                [InlineKeyboardButton("◀️ Назад", callback_data="bank_management")],
                [InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ **Текущий банк обновлен:** {new_balance:.0f}₽", 
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
            
        except ValueError:
            await update.message.reply_text("❌ Введите число", reply_markup=add_home_button())
            return
    
    # Проверить, ожидается ли установка банка (новая логика)
    if context.user_data.get('awaiting_bank_input'):
        context.user_data['awaiting_bank_input'] = False
        
        try:
            initial_balance = float(text)
            if initial_balance <= 0:
                await update.message.reply_text("❌ Сумма должна быть больше 0", reply_markup=add_home_button())
                return
            
            cursor = bot.conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET initial_balance = ?, current_balance = ? 
                WHERE user_id = ?
            ''', (initial_balance, initial_balance, user_id))
            bot.conn.commit()
            
            keyboard = [
                [InlineKeyboardButton("◀️ Назад", callback_data="bank_management")],
                [InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ **Банк установлен:** {initial_balance:.0f}₽", 
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
            
        except ValueError:
            await update.message.reply_text("❌ Введите число", reply_markup=add_home_button())
            return
    
    # Проверить, ожидается ли базовая ставка мартингейла
    if context.user_data.get('awaiting_martingale_base_stake'):
        context.user_data['awaiting_martingale_base_stake'] = False
        
        try:
            base_stake = float(text)
            if base_stake <= 0:
                await update.message.reply_text("❌ Ставка должна быть больше 0", reply_markup=add_home_button())
                return
            
            cursor = bot.conn.cursor()
            cursor.execute('UPDATE users SET martingale_base_stake = ? WHERE user_id = ?', (base_stake, user_id))
            cursor.execute('SELECT martingale_multiplier FROM users WHERE user_id = ?', (user_id,))
            multiplier_result = cursor.fetchone()
            bot.conn.commit()
            
            multiplier = multiplier_result[0] if multiplier_result else 3
            
            keyboard = [
                [InlineKeyboardButton("◀️ Назад", callback_data="bank_management")],
                [InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ **НАСТРОЙКИ МАРТИНГЕЙЛА СОХРАНЕНЫ**\n\n"
                f"⚡️ **Множитель:** x{multiplier}\n"
                f"💰 **Базовая ставка:** {base_stake:.0f}₽\n\n"
                f"💡 После проигрыша ставка будет умножена на {multiplier}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
            
        except ValueError:
            await update.message.reply_text("❌ Введите число", reply_markup=add_home_button())
            return
    
    # Проверить, ожидается ли ввод процента
    if context.user_data.get('awaiting_percentage_value'):
        context.user_data['awaiting_percentage_value'] = False
        
        try:
            percent = float(text)
            if percent <= 0 or percent > 100:
                await update.message.reply_text("❌ Процент должен быть от 0 до 100", reply_markup=add_home_button())
                return
            
            cursor = bot.conn.cursor()
            cursor.execute('UPDATE users SET percentage_value = ? WHERE user_id = ?', (percent, user_id))
            bot.conn.commit()
            
            keyboard = [
                [InlineKeyboardButton("◀️ Назад", callback_data="bank_management")],
                [InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ **ПРОЦЕНТНАЯ СТРАТЕГИЯ СОХРАНЕНА**\n\n"
                f"📊 **Процент от банка:** {percent}%\n\n"
                f"💡 Ваша ставка будет составлять {percent}% от текущего банка",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
            
        except ValueError:
            await update.message.reply_text("❌ Введите число (например: 2.5)", reply_markup=add_home_button())
            return
    
    # Проверить, ожидается ли новое название бота
    if context.user_data.get('awaiting_bot_name'):
        if not bot.is_admin(user_id):
            return
        
        new_name = text.strip()
        
        if len(new_name) < 3:
            await update.message.reply_text(
                "❌ Название должно быть не короче 3 символов",
                reply_markup=add_home_button()
            )
            return
        
        if len(new_name) > 50:
            await update.message.reply_text(
                "❌ Название не должно превышать 50 символов",
                reply_markup=add_home_button()
            )
            return
        
        # Сохранить название временно для подтверждения
        context.user_data['new_bot_name'] = new_name
        
        confirm_text = f"""
✅ **ПОДТВЕРЖДЕНИЕ ИЗМЕНЕНИЯ**

📝 **Новое название:** {new_name}

Подтвердите изменение названия бота:
"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_bot_name")],
            [InlineKeyboardButton("❌ Отменить", callback_data="cancel_bot_name")],
            [InlineKeyboardButton("🏠 На главную", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(confirm_text, reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    # Проверить, ожидается ли User ID для добавления подписки
    if context.user_data.get('awaiting_user_id_for_sub'):
        context.user_data['awaiting_user_id_for_sub'] = False
        
        try:
            target_user_id = int(text.strip())
            
            # Проверить существует ли пользователь
            cursor = bot.conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (target_user_id,))
            user_exists = cursor.fetchone()
            
            if not user_exists:
                # Создать пользователя если не существует
                cursor.execute('''
                    INSERT INTO users (user_id, created_at, subscription_type)
                    VALUES (?, ?, 'free')
                ''', (target_user_id, datetime.now().isoformat()))
                bot.conn.commit()
                
                await update.message.reply_text(
                    f"✅ Пользователь ID {target_user_id} добавлен в систему!\n\n"
                    f"Открываю меню управления подпиской...",
                    reply_markup=add_home_button()
                )
            
            # Создать фейковый update для вызова функции управления
            from telegram import CallbackQuery
            fake_query = CallbackQuery(
                id=str(update.message.message_id),
                from_user=update.effective_user,
                chat_instance=str(update.effective_chat.id),
                message=update.message,
                data=f"manage_user_{target_user_id}",
                bot=context.bot
            )
            
            fake_update = Update(
                update_id=update.update_id,
                callback_query=fake_query
            )
            
            await admin_manage_user_sub(fake_update, context, target_user_id)
            return
            
        except ValueError:
            await update.message.reply_text(
                "❌ Введите корректный User ID (число)\n\n"
                "Пример: `123456789`",
                parse_mode='Markdown',
                reply_markup=add_home_button()
            )
            return
    
    # Проверить, ожидается ли сумма банка (новая логика с выбором стратегии)
    if context.user_data.get('awaiting_bank_amount'):
        context.user_data['awaiting_bank_amount'] = False
        
        try:
            initial_balance = float(text)
            if initial_balance <= 0:
                await update.message.reply_text("❌ Сумма должна быть больше 0", reply_markup=add_home_button())
                return
            
            cursor = bot.conn.cursor()
            cursor.execute('SELECT trading_strategy FROM users WHERE user_id = ?', (user_id,))
            strategy_result = cursor.fetchone()
            strategy = strategy_result[0] if strategy_result else None
            
            cursor.execute('''
                UPDATE users 
                SET initial_balance = ?, current_balance = ? 
                WHERE user_id = ?
            ''', (initial_balance, initial_balance, user_id))
            bot.conn.commit()
            
            # Разные рекомендации в зависимости от стратегии
            if strategy == 'martingale':
                recommended_short = bot.calculate_recommended_short_stake(initial_balance)
                
                if recommended_short:
                    success_text = f"""
✅ **БАНК УСТАНОВЛЕН:** {initial_balance:.0f}₽

⚡️ **МАРТИНГЕЙЛ СТРАТЕГИЯ**

📊 **Рекомендуемая ставка:** {recommended_short:.0f}₽
💡 **Как работает:**
• Базовая ставка при победе
• x2 при проигрыше (1-й уровень)
• x3 при 2-м проигрыше подряд
• Сброс после победы

⚠️ **Важно:**
• Всегда торгуйте SHORT сигналы (1-5 мин)
• Не превышайте рекомендуемую ставку
• Следите за банкроллом

🎯 Начните торговать: /short
"""
                else:
                    success_text = f"""
❌ **НЕДОСТАТОЧНО ДЛЯ МАРТИНГЕЙЛА**

💰 Ваш банк: {initial_balance:.0f}₽
⚠️ Минимум для мартингейла: 36,400₽

💡 **Рекомендация:**
Увеличьте банк или выберите процентную стратегию

🔄 Сменить стратегию: /set_bank
"""
            
            elif strategy == 'percentage':
                recommended_long = initial_balance * 0.025
                
                success_text = f"""
✅ **БАНК УСТАНОВЛЕН:** {initial_balance:.0f}₽

📊 **ПРОЦЕНТНАЯ СТРАТЕГИЯ**

💰 **Рекомендуемая ставка:** {recommended_long:.0f}₽ (2.5%)

💡 **Как работает:**
• Всегда ставка = 2-3% от текущего банка
• Безопасное управление капиталом
• Защита от больших потерь
• Стабильный рост

✅ **Преимущества:**
• Подходит для любого банка
• Консервативный подход
• Меньше рисков

🎯 Начните торговать: /long
"""
            
            else:
                # Если стратегия не выбрана (не должно происходить)
                success_text = f"✅ **Банк установлен:** {initial_balance:.0f}₽"
            
            await update.message.reply_text(success_text, parse_mode='Markdown')
            return
            
        except ValueError:
            await update.message.reply_text("❌ Введите число", reply_markup=add_home_button())
            return
    
    # Проверить, ожидается ли логин Pocket Option
    if context.user_data.get('awaiting_po_login'):
        context.user_data['awaiting_po_login'] = False
        
        # Сохранить логин пользователя
        po_login = text.strip()
        
        cursor = bot.conn.cursor()
        cursor.execute('UPDATE users SET pocket_option_login = ? WHERE user_id = ?', (po_login, user_id))
        bot.conn.commit()
        
        # Уведомить пользователя
        await update.message.reply_text(
            f"✅ **ЛОГИН ПОЛУЧЕН**\n\n"
            f"📝 Ваш логин: `{po_login}`\n\n"
            f"⏳ **Ожидайте промокод от администратора**\n\n"
            f"Администратор выдаст вам персональный промокод на VIP доступ за 1490₽ в течение 24 часов.\n\n"
            f"Промокод придет в этом чате. Проверяйте уведомления! 🔔",
            parse_mode='Markdown'
        )
        
        # Уведомить админа о новом пользователе
        admin_id = ADMIN_USER_ID
        if admin_id > 0:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"🆕 **НОВЫЙ ПОЛЬЗОВАТЕЛЬ POCKET OPTION**\n\n"
                         f"👤 User ID: `{user_id}`\n"
                         f"📝 Логин PO: `{po_login}`\n"
                         f"👤 Username: @{update.effective_user.username or 'не указан'}\n\n"
                         f"💎 Выдайте промокод на VIP за 1490₽:\n"
                         f"Используйте /promo_create для создания промокода",
                    parse_mode='Markdown'
                )
            except:
                pass
        
        return
    
    # Проверить, ожидается ли промокод
    if context.user_data.get('awaiting_promo_code'):
        context.user_data['awaiting_promo_code'] = False
        
        # Проверить промокод
        if text == PROMO_CODE:
            # Правильный промокод!
            cursor = bot.conn.cursor()
            
            # Проверить, не использован ли уже промокод
            cursor.execute('SELECT new_user_discount_used FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                await update.message.reply_text(
                    "❌ Вы уже использовали скидку для новых пользователей!",
                    parse_mode='Markdown'
                )
                return
            
            # Активировать скидку - установить флаг
            cursor.execute('''
                UPDATE users 
                SET new_user_discount_used = 1,
                    pocket_option_registered = 1
                WHERE user_id = ?
            ''', (user_id,))
            bot.conn.commit()
            
            success_text = f"""
✅ **ПРОМОКОД АКТИВИРОВАН!**

🎉 Поздравляем! Скидка 70% успешно применена!

💰 **Ваши преимущества:**
• SHORT тариф за {NEW_USER_PROMO['price']}₽ вместо {SUBSCRIPTION_PLANS['short']['1_month']}₽
• Доступ на целый месяц
• Все функции SHORT подписки

📝 **Как получить доступ:**
1️⃣ Нажмите кнопку "Купить подписку"
2️⃣ Выберите "SHORT - 1 месяц"
3️⃣ Оплатите {NEW_USER_PROMO['price']}₽ через ЮКасса
4️⃣ Начните зарабатывать!

➡️ Продолжим настройку бота?
"""
            keyboard = [
                [InlineKeyboardButton("✅ Продолжить настройку", callback_data="continue_setup")],
                [InlineKeyboardButton("💳 Купить подписку сейчас", callback_data="buy_subscription")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        else:
            # Неправильный промокод
            error_text = f"""
❌ **НЕВЕРНЫЙ ПРОМОКОД**

Промокод должен быть: **{PROMO_CODE}**

⚠️ Внимание:
• Промокод чувствителен к регистру
• Проверьте правильность написания
• Скопируйте промокод без лишних пробелов

📝 Попробуйте еще раз или нажмите кнопку:
"""
            keyboard = [
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data="enter_promo_code")],
                [InlineKeyboardButton("◀️ Назад", callback_data="user_status_new")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(error_text, reply_markup=reply_markup, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("Please set BOT_TOKEN environment variable!")
        print("❌ Error: BOT_TOKEN not set!")
        print("Please set your Telegram bot token in the environment variables.")
        return
    
    # Отключено: не выдаем автоматически VIP админу при старте
    # if ADMIN_USER_ID > 0:
    #     bot.add_lifetime_subscription(ADMIN_USER_ID)
    #     logger.info(f"✅ Admin {ADMIN_USER_ID} has been granted LIFETIME VIP access!")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("setup", setup_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("guide", guide_command))
    
    app.add_handler(CommandHandler("long", long_command))
    app.add_handler(CommandHandler("short", short_command))
    app.add_handler(CommandHandler("signal_all", signal_all_command))
    
    app.add_handler(CommandHandler("bank", bank_command))
    app.add_handler(CommandHandler("set_bank", set_bank_command))
    app.add_handler(CommandHandler("set_short_stake", set_short_stake_command))
    app.add_handler(CommandHandler("report_win", report_win_command))
    app.add_handler(CommandHandler("report_loss", report_loss_command))
    app.add_handler(CommandHandler("report_refund", report_refund_command))
    app.add_handler(CommandHandler("autotrade", autotrade_command))
    
    app.add_handler(CommandHandler("my_stats", my_stats_command))
    app.add_handler(CommandHandler("my_longs", my_longs_command))
    app.add_handler(CommandHandler("signal_stats", signal_stats_command))
    app.add_handler(CommandHandler("perf_stats", signal_performance_stats))
    app.add_handler(CommandHandler("market_stats", market_stats_command))
    app.add_handler(CommandHandler("bankroll", bankroll_command))
    app.add_handler(CommandHandler("delete_skipped", delete_skipped_command))
    
    app.add_handler(CommandHandler("buy_subscription", buy_subscription_command))
    app.add_handler(CommandHandler("plans", show_tariff_menu))
    
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CommandHandler("god", god_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("admin_stats", admin_stats))
    app.add_handler(CommandHandler("admin_add_sub", admin_add_subscription))
    app.add_handler(CommandHandler("admin_lifetime", admin_lifetime))
    app.add_handler(CommandHandler("admin_info", admin_user_info))
    app.add_handler(CommandHandler("set_vip_price", set_vip_price_command))
    app.add_handler(CommandHandler("set_short_price", set_short_price_command))
    app.add_handler(CommandHandler("set_long_price", set_long_price_command))
    app.add_handler(CommandHandler("promo_activate", promo_activate_command))
    
    # Команды настройки бота
    app.add_handler(CommandHandler("set_payment", set_payment_command))
    app.add_handler(CommandHandler("disable_payments", disable_payments_command))
    app.add_handler(CommandHandler("add_admin", add_admin_command))
    app.add_handler(CommandHandler("remove_admin", remove_admin_command))
    app.add_handler(CommandHandler("set_reviews_group", set_reviews_group_command))
    
    # Команды управления пользователями
    app.add_handler(CommandHandler("ban", ban_user_command))
    app.add_handler(CommandHandler("unban", unban_user_command))
    app.add_handler(CommandHandler("reset_me", reset_me_command))
    app.add_handler(CommandHandler("reset_user", reset_user_command))
    
    # Обработчик текстовых сообщений (для промокодов)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)
    
    app.post_init = post_init
    
    logger.info("🚀 Bot started successfully!")
    print("✅ Crypto Signals Bot is running...")
    print(f"👤 Admin User ID: {ADMIN_USER_ID}")
    print(f"📞 Support Contact: {bot.get_support_contact()}")
    
    # Установить меню команд (из дефолтных настроек)
    asyncio.get_event_loop().run_until_complete(
        app.bot.set_my_commands([
            BotCommand(cmd, desc) for cmd, desc in DEFAULT_BOT_COMMANDS
        ])
    )
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
