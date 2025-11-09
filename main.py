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
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, MessageHandler, filters, ApplicationBuilder
)
from dotenv import load_dotenv
import warnings
import uuid
# from yookassa import Configuration, Payment # Uncomment if actual YooKassa is used
# from webhook_system import webhook_system # Uncomment if actual webhook system is used
# from crypto_utils import encrypt_ssid, decrypt_ssid # Uncomment if actual crypto utils are used

# --- External Module Placeholders (Remove if you have actual implementations) ---
class DummyPayment:
    @staticmethod
    def create(payment_data):
        return {'id': f'payment_{uuid.uuid4().hex}', 'confirmation': {'confirmation_url': 'https://dummy-payment.com'}}

class DummyYooKassaConfig:
    def configure(self, shop_id, secret_key):
        pass
Configuration = DummyYooKassaConfig
Payment = DummyPayment
def encrypt_ssid(ssid, key=None): return f"ENC_{ssid}_KEY"
def decrypt_ssid(encrypted_ssid, key=None): return encrypted_ssid.replace('ENC_', '').replace('_KEY', '')
def webhook_system(*args, **kwargs): pass
# --- End Placeholders ---

warnings.filterwarnings('ignore')

load_dotenv()
matplotlib.use('Agg')

# --- ГЛОБАЛЬНЫЕ КОНСТАНТЫ ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@banana_pwr")

# Московский часовой пояс (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))

POCKET_OPTION_REF_LINK = os.getenv("POCKET_OPTION_REF_LINK", "https://pocket-friends.com/r/ugauihalod")
PROMO_CODE = os.getenv("PROMO_CODE", "FRIENDUGAUIHALOD")

DEFAULT_BOT_COMMANDS = [
    ("start", "🏠 Главное меню"),
    ("plans", "💎 Тарифы и подписки"),
    ("bank", "💰 Управление банком"),
    ("autotrade", "🤖 Автоторговля (VIP)"),
    ("settings", "⚙️ Настройки"),
    ("short", "⏳ SHORT сигнал (1-5 мин)"),
    ("long", "📈 LONG сигнал (1-4 часа)"),
    ("my_longs", "📊 Мои LONG позиции"),
    ("my_stats", "📈 Моя статистика"),
    ("help", "❓ Помощь и инструкции"),
]

# Система тарифов
SUBSCRIPTION_PLANS = {
    'short': {
        '1m': 4990, '6m': 26946, '12m': 47904,
        'name': 'SHORT', 'description': 'Быстрые сигналы (1-5 мин) с мартингейлом', 'emoji': '⏳'
    },
    'long': {
        '1m': 4990, '6m': 26946, '12m': 47904,
        'name': 'LONG', 'description': 'Длинные сигналы (1-4 часа) с процентной ставкой', 'emoji': '📈'
    },
    'vip': {
        '1m': 9990, '6m': 53946, '12m': 95904,
        'name': 'VIP', 'description': 'Все сигналы SHORT + LONG + приоритет + гибкие настройки стратегий и статистика', 'emoji': '💎'
    }
}

# Акция для новых пользователей
NEW_USER_PROMO = {
    'price': 1490, 'duration_days': 30, 'plan': 'short', 'discount_percent': 70
}

PAYOUT_PERCENT = 92
SHORT_SIGNAL_FREE_LIMIT = 5
LONG_SIGNAL_FREE_LIMIT = 10

# Система мультиязычности
TRANSLATIONS = {
    'ru': {
        'choose_language': '🌐 Выберите язык / Choose language:',
        'language_selected': '✅ Язык установлен: Русский',
        'choose_currency': '💰 Выберите валюту для отображения цен:',
        'currency_selected': '✅ Валюта установлена',
        'welcome': '👋 Добро пожаловать в бот торговых сигналов!',
        'welcome_desc': 'Выберите тариф для начала работы:',
        'short_plan': '⏳ SHORT',
        'short_desc': 'Быстрые сигналы (1-5 мин)\nМартингейл x3 стратегия',
        'long_plan': '📈 LONG',
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
        'get_signal': '💸 Получить сигнал',
        'back': '⬅️ Назад',
        'call': '⬆️ CALL (ВВЕРХ)',
        'put': '⬇️ PUT (ВНИЗ)',
        'price': 'Цена',
        'subscription': 'Подписка',
        'expires': 'Истекает',
        'balance': 'Баланс',
        'win_rate': 'Доходность сигналов',
        'profit': 'Прибыль',
        'month': 'мес',
        'months': 'мес',
        'promo_active': '🎁 Акция для новых пользователей:',
        'promo_price': 'Цена: {price}{symbol} (скидка {discount}%)',
        'promo_activate': '✅ Активировать акцию',
        'already_subscribed': 'Ваша подписка: {plan} истекает {date}.',
        'not_subscribed': 'У вас нет активной подписки.',
        'short_menu_title': '⏳ SHORT сигнал (1-5 мин)',
        'short_menu_desc': 'Базовая ставка: {stake}{symbol}. Стратегия: Мартингейл x{multiplier}.',
        'short_limit_reached': '🚫 Лимит бесплатных SHORT сигналов на сегодня исчерпан ({used}/{limit}).',
        'short_signal_title': '⏳ SHORT СИГНАЛ | УРОВЕНЬ {level}/{max_level}',
        'signal_asset': 'АКТИВ: {asset}',
        'signal_direction': 'НАПРАВЛЕНИЕ: {direction}',
        'signal_expiry': 'ВРЕМЯ ЭКСПИРАЦИИ: {time}',
        'signal_stake': 'СУММА СТАВКИ: {stake}{symbol}',
        'signal_confidence': 'НАДЕЖНОСТЬ: {confidence}%',
        'signal_waiting': 'Ожидаем закрытия сделки...',
        'next_martingale': 'Если сделка не закроется в плюс, будет отправлен следующий сигнал по Мартингейлу ({next_level}) с суммой {next_stake}{symbol}.',
        'long_limit_reached': '🚫 Лимит бесплатных LONG сигналов на сегодня исчерпан ({used}/{limit}).',
        'lang_currency_settings': '🌐 Язык/Валюта',
        'strategy_settings': '⚙️ Настройки стратегий',
    },
    'en': {
        'choose_language': '🌐 Choose language:',
        'language_selected': '✅ Language set: English',
        'choose_currency': '💰 Choose currency for price display:',
        'currency_selected': '✅ Currency set',
        'welcome': '👋 Welcome to Trading Signals Bot!',
        'welcome_desc': 'Choose a plan to get started:',
        'short_plan': '⏳ SHORT',
        'short_desc': 'Fast signals (1-5 min)\nMartingale x3 strategy',
        'long_plan': '📈 LONG',
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
        'get_signal': '💸 Get Signal',
        'back': '⬅️ Back',
        'call': '⬆️ CALL (UP)',
        'put': '⬇️ PUT (DOWN)',
        'price': 'Price',
        'subscription': 'Subscription',
        'expires': 'Expires',
        'balance': 'Balance',
        'win_rate': 'Signal Profitability',
        'profit': 'Profit',
        'month': 'month',
        'months': 'months',
        'promo_active': '🎁 New user promotion:',
        'promo_price': 'Price: {price}{symbol} ({discount}% discount)',
        'promo_activate': '✅ Activate Promotion',
        'already_subscribed': 'Your subscription: {plan} expires {date}.',
        'not_subscribed': 'You do not have an active subscription.',
        'short_menu_title': '⏳ SHORT Signal (1-5 min)',
        'short_menu_desc': 'Base stake: {stake}{symbol}. Strategy: Martingale x{multiplier}.',
        'short_limit_reached': '🚫 Free SHORT signal limit reached today ({used}/{limit}).',
        'short_signal_title': '⏳ SHORT SIGNAL | LEVEL {level}/{max_level}',
        'signal_asset': 'ASSET: {asset}',
        'signal_direction': 'DIRECTION: {direction}',
        'signal_expiry': 'EXPIRATION TIME: {time}',
        'signal_stake': 'STAKE AMOUNT: {stake}{symbol}',
        'signal_confidence': 'RELIABILITY: {confidence}%',
        'signal_waiting': 'Waiting for trade close...',
        'next_martingale': 'If the trade does not close positive, the next Martingale signal ({next_level}) will be sent with an amount of {next_stake}{symbol}.',
        'long_limit_reached': '🚫 Free LONG signal limit reached today ({used}/{limit}).',
        'lang_currency_settings': '🌐 Language/Currency',
        'strategy_settings': '⚙️ Strategy Settings',
    },
    # ... Add other languages (es, pt) if needed
}

# Курсы валют
CURRENCY_RATES = {
    'RUB': 1.0,
    'USD': 0.011,
}

CURRENCY_SYMBOLS = {
    'RUB': '₽',
    'USD': '$',
}

# --- НАСТРОЙКА ЛОГГИРОВАНИЯ ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- НАСТРОЙКА YOOKASSA (Если используется) ---
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
    try:
        Configuration.configure(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
        logger.info("✅ YooKassa configured successfully")
    except Exception as e:
        logger.error(f"❌ YooKassa configuration failed: {e}")
else:
    logger.warning("⚠️ YooKassa credentials not found - payment will use manual mode")


# --- ГЛАВНЫЙ КЛАСС БОТА ---
class CryptoSignalsBot:
    def __init__(self):
        self.assets = {} # Placeholder for actual Pocket Option assets
        self.timeframes = {
            "1M": "1m", "3M": "3m", "5M": "5m", "15M": "15m", 
            "30M": "30m", "1H": "1h", "4H": "4h", 
            "1D": "1d", "1W": "1wk"
        }
        self.max_martingale_level = 3 # Max Martingale steps (G1, G2, G3)
        self.setup_database()

    def setup_database(self):
        """Initializes and ensures all necessary tables and columns exist in the SQLite database."""
        self.conn = sqlite3.connect('crypto_signals_bot.db', check_same_thread=False)
        cursor = self.conn.cursor()
        
        # 1. USERS Table (Main user settings and status)
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
                current_balance REAL DEFAULT NULL,
                short_base_stake REAL DEFAULT 100,
                current_martingale_level INTEGER DEFAULT 0,
                consecutive_losses INTEGER DEFAULT 0,
                currency TEXT DEFAULT "RUB",
                martingale_type INTEGER DEFAULT 3,
                long_percentage REAL DEFAULT 2.5,
                subscription_type TEXT DEFAULT NULL,
                referral_code TEXT DEFAULT NULL,
                referred_by INTEGER DEFAULT NULL,
                new_user_discount_used BOOLEAN DEFAULT 0,
                referral_earnings REAL DEFAULT 0,
                pocket_option_registered BOOLEAN DEFAULT 0,
                pocket_option_login TEXT DEFAULT NULL,
                last_upgrade_offer TEXT DEFAULT NULL,
                language TEXT DEFAULT "ru",
                free_short_signals_today INTEGER DEFAULT 0,
                free_short_signals_date TEXT DEFAULT NULL,
                free_long_signals_today INTEGER DEFAULT 0,
                free_long_signals_date TEXT DEFAULT NULL,
                banned BOOLEAN DEFAULT 0,
                trading_strategy TEXT DEFAULT NULL,
                martingale_multiplier INTEGER DEFAULT 3,
                martingale_base_stake REAL DEFAULT 100,
                percentage_value REAL DEFAULT 2.5,
                auto_trading_enabled BOOLEAN DEFAULT 0,
                pocket_option_email TEXT DEFAULT NULL,
                auto_trading_mode TEXT DEFAULT "demo",
                dalembert_base_stake REAL DEFAULT 100,
                dalembert_unit REAL DEFAULT 50,
                current_dalembert_level INTEGER DEFAULT 0,
                auto_trading_strategy TEXT DEFAULT "percentage",
                pocket_option_ssid TEXT DEFAULT NULL,
                pocket_option_connected BOOLEAN DEFAULT 0,
                ssid_automation_purchased BOOLEAN DEFAULT 0,
                ssid_automation_purchase_date DATETIME DEFAULT NULL
            )
        ''')
        
        # 2. SIGNAL_HISTORY Table
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
                expiration_time TEXT,
                signal_tier TEXT DEFAULT "vip",
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')

        # 3. SIGNAL_PERFORMANCE Table
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
        
        # 4. PENDING_NOTIFICATIONS Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                message TEXT,
                data TEXT,
                send_time DATETIME,
                is_sent BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # 5. ADMIN_SETTINGS Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        self.conn.commit()
        logger.info("✅ Database schema initialized/updated.")

    def get_setting(self, key, default=None):
        """Retrieves an admin setting from the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM admin_settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        return result[0] if result else default

    def set_setting(self, key, value):
        """Sets or updates an admin setting in the database."""
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO admin_settings (key, value) VALUES (?, ?)", (key, str(value)))
        self.conn.commit()

    def get_user_data(self, user_id):
        """Retrieves all data for a specific user."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        # Helper to convert row to dict
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        return dict(zip(columns, row)) if row else None

    def create_user_if_not_exists(self, update: Update):
        """Creates a user record if it doesn't exist."""
        user = update.effective_user
        if not self.get_user_data(user.id):
            cursor = self.conn.cursor()
            joined_date = datetime.now(MOSCOW_TZ).isoformat()
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, joined_date, language)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user.id, 
                user.username, 
                user.first_name, 
                joined_date,
                user.language_code if user.language_code in TRANSLATIONS else 'ru'
            ))
            self.conn.commit()
            logger.info(f"👤 New user registered: {user.id} ({user.username})")
            return True
        return False

    def update_user_field(self, user_id, field, value):
        """Updates a single field for a user."""
        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
        self.conn.commit()

    def get_translation(self, user_data, key):
        """Gets translated string based on user's language."""
        lang = user_data.get('language', 'ru')
        return TRANSLATIONS.get(lang, TRANSLATIONS['ru']).get(key, f"_{key}_")

    def get_currency_symbol(self, user_data):
        """Gets currency symbol based on user's currency setting."""
        currency = user_data.get('currency', 'RUB')
        return CURRENCY_SYMBOLS.get(currency, '$')
    
    def is_subscribed(self, user_data):
        """Checks if the user has an active subscription."""
        end_date_str = user_data.get('subscription_end')
        if not end_date_str:
            return False
        
        try:
            # Assumes ISO format for datetime stored in DB
            end_date = datetime.fromisoformat(end_date_str).replace(tzinfo=MOSCOW_TZ)
            return end_date > datetime.now(MOSCOW_TZ)
        except Exception:
            return False

    def is_admin(self, user_id):
        """Checks if the user is an admin."""
        return user_id == ADMIN_USER_ID or user_id == int(self.get_setting('super_admin_id', 0))

    # --- СИГНАЛЬНЫЕ ФУНКЦИИ (ЗАГЛУШКИ) ---
    def get_short_signal(self, user_data, martingale_level):
        """
        Placeholder for fetching a new SHORT signal.
        In a real application, this would involve complex technical analysis.
        """
        asset = random.choice(['BTC/USDT', 'ETH/USDT', 'LTC/USDT', 'XRP/USDT'])
        direction = random.choice(['call', 'put'])
        confidence = random.randint(80, 99)
        
        stake = user_data['short_base_stake'] * (user_data['martingale_multiplier'] ** martingale_level)
        expiry_min = random.choice([1, 3, 5])
        
        return {
            'asset': asset,
            'direction': direction,
            'timeframe': f'{expiry_min}M',
            'expiration_time': f'{expiry_min} {user_data.get("language", "ru")}',
            'stake_amount': round(stake, 2),
            'confidence': confidence,
            'entry_price': random.uniform(20000, 70000), # Dummy price
        }

    # --- HANDLERS (Обработчики команд) ---

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles the /start command and displays the main menu."""
        user_id = update.effective_user.id
        self.create_user_if_not_exists(update)
        user_data = self.get_user_data(user_id)
        
        T = lambda key: self.get_translation(user_data, key)
        
        if not user_data.get('language'):
            # Prompt for language selection on first start
            await self.language_prompt(update, context)
            return
            
        is_sub = self.is_subscribed(user_data)
        
        # Main Menu Buttons
        keyboard = [
            [
                InlineKeyboardButton(T('short_signal'), callback_data='cmd_short'),
                InlineKeyboardButton(T('long_signal'), callback_data='cmd_long')
            ],
            [
                InlineKeyboardButton(T('my_stats'), callback_data='cmd_my_stats'),
                InlineKeyboardButton(T('my_longs'), callback_data='cmd_my_longs')
            ],
            [
                InlineKeyboardButton(T('plans'), callback_data='cmd_plans'),
                InlineKeyboardButton(T('autotrade'), callback_data='cmd_autotrade')
            ],
            [
                InlineKeyboardButton(T('settings'), callback_data='cmd_settings'),
                InlineKeyboardButton(T('help'), callback_data='cmd_help')
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if is_sub:
            sub_end_date = datetime.fromisoformat(user_data['subscription_end']).strftime('%d.%m.%Y %H:%M')
            status_text = T('already_subscribed').format(
                plan=user_data['subscription_type'].upper(), 
                date=sub_end_date
            )
        else:
            status_text = T('not_subscribed')
            
        message_text = (
            f"{T('welcome')}\n\n"
            f"**{status_text}**\n\n"
            f"{T('welcome_desc')}"
        )
        
        await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def language_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Prompts the user to choose a language."""
        keyboard = [
            [
                InlineKeyboardButton("Русский 🇷🇺", callback_data='set_lang_ru'),
                InlineKeyboardButton("English 🇬🇧", callback_data='set_lang_en')
            ],
            [
                InlineKeyboardButton("Español 🇪🇸", callback_data='set_lang_es'),
                InlineKeyboardButton("Português 🇵🇹", callback_data='set_lang_pt')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🌐 Выберите язык / Choose language:", reply_markup=reply_markup)

    async def plans_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles the /plans command and shows subscription options."""
        query = update.callback_query
        if query:
            await query.answer()
            
        user_id = update.effective_user.id
        user_data = self.get_user_data(user_id)
        T = lambda key: self.get_translation(user_data, key)
        symbol = self.get_currency_symbol(user_data)
        is_sub = self.is_subscribed(user_data)
        
        text = "**💎 Выберите свой тариф**\n\n"
        keyboard = []

        # 1. NEW USER PROMO
        if not user_data.get('new_user_discount_used'):
            promo_price = NEW_USER_PROMO['price'] * CURRENCY_RATES.get(user_data['currency'], 1.0)
            text += (
                f"{T('promo_active')}\n"
                f"**{SUBSCRIPTION_PLANS['short']['name']}** {T('month')} - "
                f"{T('promo_price').format(price=int(promo_price), symbol=symbol, discount=NEW_USER_PROMO['discount_percent'])}\n\n"
            )
            keyboard.append([
                InlineKeyboardButton(T('promo_activate'), callback_data='buy_promo')
            ])
            text += "---\n\n"

        # 2. STANDARD PLANS
        for plan_key, plan_data in SUBSCRIPTION_PLANS.items():
            text += f"**{plan_data['emoji']} {plan_data['name']}** - *{plan_data['description']}*\n"
            
            plan_buttons = []
            for duration, price in plan_data.items():
                if duration in ['1m', '6m', '12m']:
                    # Simple currency conversion (assuming all base prices are in RUB)
                    converted_price = price * CURRENCY_RATES.get(user_data['currency'], 1.0)
                    
                    if duration == '1m': 
                        label = f"{T('month')} | {int(converted_price)}{symbol}"
                    else:
                        label = f"{duration[:-1]} {T('months')} | {int(converted_price)}{symbol}"
                        
                    plan_buttons.append(
                        InlineKeyboardButton(label, callback_data=f'buy_{plan_key}_{duration}')
                    )
            keyboard.append(plan_buttons)
            text += "\n"

        # 3. Footer
        if is_sub:
            sub_end_date = datetime.fromisoformat(user_data['subscription_end']).strftime('%d.%m.%Y %H:%M')
            text += f"\n---\n{T('already_subscribed').format(plan=user_data['subscription_type'].upper(), date=sub_end_date)}"

        keyboard.append([InlineKeyboardButton(T('back'), callback_data='cmd_start')])
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Use edit_message_text if called from a query, otherwise reply_text
        if query:
            try:
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            except Exception: # Catch MessageNotModified
                pass
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def short_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles the /short command and shows the SHORT signal menu."""
        query = update.callback_query
        if query:
            await query.answer()
            
        user_id = update.effective_user.id
        user_data = self.get_user_data(user_id)
        T = lambda key: self.get_translation(user_data, key)
        symbol = self.get_currency_symbol(user_data)
        
        is_sub = self.is_subscribed(user_data)
        
        # Check free signal limits for non-subscribers
        if not is_sub:
            today = datetime.now(MOSCOW_TZ).date().isoformat()
            if user_data.get('free_short_signals_date') != today:
                self.update_user_field(user_id, 'free_short_signals_today', 0)
                self.update_user_field(user_id, 'free_short_signals_date', today)
            
            used_signals = user_data.get('free_short_signals_today', 0)
            if used_signals >= SHORT_SIGNAL_FREE_LIMIT:
                message_text = T('short_limit_reached').format(used=used_signals, limit=SHORT_SIGNAL_FREE_LIMIT)
                keyboard = [[InlineKeyboardButton(T('plans'), callback_data='cmd_plans')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await self._send_or_edit_message(update, message_text, reply_markup=reply_markup)
                return

        # Current Martingale Level
        current_level = user_data.get('current_martingale_level', 0)
        base_stake = user_data.get('martingale_base_stake', 100)
        multiplier = user_data.get('martingale_multiplier', 3)
        
        message_text = (
            f"**{T('short_menu_title')}**\n\n"
            f"{T('short_menu_desc').format(stake=int(base_stake), symbol=symbol, multiplier=multiplier)}"
        )
        
        if current_level > 0:
            # If a Martingale series is active
            current_stake = base_stake * (multiplier ** current_level)
            message_text += f"\n\n🚨 **Серия активна:** Уровень **{current_level + 1}/{self.max_martingale_level}**\nСумма для следующей сделки: **{int(current_stake)}{symbol}**"
        
        keyboard = [
            [InlineKeyboardButton(T('get_signal'), callback_data='get_signal_short')],
            [InlineKeyboardButton(T('strategy_settings'), callback_data='settings_strategy_short')],
            [InlineKeyboardButton(T('back'), callback_data='cmd_start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await self._send_or_edit_message(update, message_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def get_signal_short(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Generates and sends the SHORT signal."""
        query = update.callback_query
        if query:
            await query.answer("Генерация сигнала...")
            
        user_id = update.effective_user.id
        user_data = self.get_user_data(user_id)
        T = lambda key: self.get_translation(user_data, key)
        symbol = self.get_currency_symbol(user_data)
        
        is_sub = self.is_subscribed(user_data)
        
        # Check and decrement free signals if not subscribed
        if not is_sub:
            used_signals = user_data.get('free_short_signals_today', 0)
            if used_signals >= SHORT_SIGNAL_FREE_LIMIT:
                # Should have been caught in short_command, but safety check
                return
            self.update_user_field(user_id, 'free_short_signals_today', used_signals + 1)
        
        # Determine current Martingale level (0 is base, 1 is G1, 2 is G2...)
        current_level = user_data.get('current_martingale_level', 0)
        
        # Generate the signal
        signal = self.get_short_signal(user_data, current_level)
        
        # Prepare message
        direction_text = T('call') if signal['direction'] == 'call' else T('put')
        
        message_text = (
            f"**{T('short_signal_title').format(level=current_level + 1, max_level=self.max_martingale_level)}**\n\n"
            f"{T('signal_asset').format(asset=signal['asset'])}\n"
            f"{T('signal_direction').format(direction=direction_text)}\n"
            f"{T('signal_expiry').format(time=signal['expiration_time'])}\n"
            f"{T('signal_stake').format(stake=signal['stake_amount'], symbol=symbol)}\n"
            f"{T('signal_confidence').format(confidence=signal['confidence'])}\n\n"
            f"*{T('signal_waiting')}*"
        )
        
        # Add Martingale follow-up if not the final level
        if current_level < self.max_martingale_level - 1:
            multiplier = user_data.get('martingale_multiplier', 3)
            next_stake = signal['stake_amount'] * multiplier
            message_text += (
                f"\n\n_{T('next_martingale').format(next_level=current_level + 2, next_stake=int(next_stake), symbol=symbol)}_"
            )
            
        keyboard = [
            [InlineKeyboardButton(T('back'), callback_data='cmd_short')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self._send_or_edit_message(update, message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # In a real bot, schedule a task to check the result after the expiry time
        # context.job_queue.run_once(self.check_short_signal_result, ...) 
        
        # Update Martingale state (reset if current_level == 0 and win, increment if loss, etc.)
        # This is typically done after the result is known. Here we just set the level for the *next* possible signal.
        if current_level < self.max_martingale_level - 1:
             self.update_user_field(user_id, 'current_martingale_level', current_level + 1) # Assume loss for simplicity
        else:
             self.update_user_field(user_id, 'current_martingale_level', 0) # Reset series

    # --- ADMIN COMMANDS (Заглушки) ---
    async def admin_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Utility to check admin status and send a warning if not an admin."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("🚫 Доступ запрещен. Вы не являетесь администратором.")
            return False
        return True

    async def stat_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.admin_check(update, context): return
        await update.message.reply_text("📈 [ADMIN] Заглушка для статистики бота.")

    # ... other admin commands placeholders

    # --- UTILITIES ---
    async def _send_or_edit_message(self, update: Update, text: str, reply_markup=None, parse_mode='HTML') -> None:
        """Helper to send a new message or edit the existing one based on context."""
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    text, 
                    reply_markup=reply_markup, 
                    parse_mode=parse_mode
                )
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                await update.callback_query.message.reply_text(
                    text, 
                    reply_markup=reply_markup, 
                    parse_mode=parse_mode
                )
        else:
            await update.message.reply_text(
                text, 
                reply_markup=reply_markup, 
                parse_mode=parse_mode
            )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles all inline keyboard button presses."""
        query = update.callback_query
        data = query.data
        
        # Handle language selection first
        if data.startswith('set_lang_'):
            lang_code = data.split('_')[-1]
            user_id = update.effective_user.id
            self.update_user_field(user_id, 'language', lang_code)
            
            user_data = self.get_user_data(user_id)
            T = lambda key: self.get_translation(user_data, key)
            
            await query.answer(T('language_selected'))
            # Go to start menu after language selection
            await self.start_command(update, context) 
            return

        # Map callback data to commands
        if data == 'cmd_start':
            await self.start_command(update, context)
        elif data == 'cmd_plans':
            await self.plans_command(update, context)
        elif data == 'cmd_short':
            await self.short_command(update, context)
        elif data == 'get_signal_short':
            await self.get_signal_short(update, context)
        # Add handlers for other commands here:
        # elif data == 'cmd_long':
        #     await self.long_command(update, context)
        # elif data == 'cmd_settings':
        #     await self.settings_command(update, context)
        # elif data.startswith('buy_'):
        #     await self.handle_purchase(update, context)
        else:
            await query.answer(f"Обработчик для '{data}' не реализован.")


    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error and send a message to the admin."""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_user:
            error_message = (
                f"🚨 **ОШИБКА В БОТЕ** 🚨\n\n"
                f"Пользователь: @{update.effective_user.username} ({update.effective_user.id})\n"
                f"Ошибка: `{context.error}`\n"
                f"Update: `{update.effective_chat.type if update.effective_chat else 'N/A'}`"
            )
            # Notify admin
            if self.is_admin(ADMIN_USER_ID):
                 try:
                    await context.bot.send_message(
                        chat_id=ADMIN_USER_ID, 
                        text=error_message, 
                        parse_mode='Markdown'
                    )
                 except Exception:
                     pass # Prevent recursive error loop

    # --- SCHEDULING & SETUP ---
    async def post_init(self, application: Application) -> None:
        """Runs after the application has been initialized."""
        await self.set_bot_commands(application)
        # application.job_queue.run_daily(self.run_daily_tasks, time=datetime.strptime('03:00', '%H:%M').time(), tzinfo=MOSCOW_TZ, name='daily_reset')
        logger.info("✅ Bot post_init tasks completed.")

    async def set_bot_commands(self, application: Application):
        """Sets the list of commands visible in the Telegram menu."""
        commands = [BotCommand(command, description) for command, description in DEFAULT_BOT_COMMANDS]
        await application.bot.set_my_commands(commands)
        logger.info("✅ Bot commands set successfully.")

# --- MAIN EXECUTION ---
def main() -> None:
    """Starts the bot."""
    bot_instance = CryptoSignalsBot()

    application = ApplicationBuilder().token(BOT_TOKEN).post_init(bot_instance.post_init).build()

    # --- USER COMMAND HANDLERS ---
    application.add_handler(CommandHandler("start", bot_instance.start_command))
    application.add_handler(CommandHandler("plans", bot_instance.plans_command))
    application.add_handler(CommandHandler("short", bot_instance.short_command))
    # application.add_handler(CommandHandler("long", bot_instance.long_command))
    # application.add_handler(CommandHandler("my_stats", bot_instance.my_stats_command))
    # application.add_handler(CommandHandler("settings", bot_instance.settings_command))
    # application.add_handler(CommandHandler("help", bot_instance.help_command))

    # --- ADMIN COMMAND HANDLERS (Placeholders) ---
    application.add_handler(CommandHandler("stat_admin", bot_instance.stat_admin_command))
    # application.add_handler(CommandHandler("notify_all", bot_instance.notify_all_command))
    # ... other admin command handlers

    # --- CALLBACK AND ERROR HANDLERS ---
    application.add_handler(CallbackQueryHandler(bot_instance.button_callback))
    application.add_error_handler(bot_instance.error_handler)

    logger.info("🚀 Bot started successfully!")
    print("✅ Crypto Signals Bot is running...")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()