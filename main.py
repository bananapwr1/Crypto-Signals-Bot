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
# Импорты для работы с платежами и шифрованием
try:
    from yookassa import Configuration, Payment
    # from webhook_system import webhook_system # Не используется напрямую в этом файле
except ImportError:
    logging.warning("⚠️ YooKassa not installed. Payment functionality will be disabled.")
    # Заглушки, если YooKassa не установлена
    class Configuration:
        @staticmethod
        def configure(*args, **kwargs): pass
    class Payment:
        @staticmethod
        def create(payment_data): return {'id': f'payment_{uuid.uuid4().hex}', 'confirmation': {'confirmation_url': 'https://dummy-payment.com'}}

# Заглушки для крипто-утилит
def encrypt_ssid(ssid, key=None): return f"ENC_{ssid}_{uuid.uuid4().hex}"
def decrypt_ssid(encrypted_ssid, key=None): return encrypted_ssid.split('_')[1]

warnings.filterwarnings('ignore')

load_dotenv()
matplotlib.use('Agg')

# --- ГЛОБАЛЬНЫЕ КОНСТАНТЫ И НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@banana_pwr")

# Настройки YooKassa
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "YOUR_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "YOUR_SECRET_KEY")

# Московский часовой пояс (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))
DB_NAME = 'crypto_signals_bot.db'

# Реферальная ссылка Pocket Option
POCKET_OPTION_REF_LINK = os.getenv("POCKET_OPTION_REF_LINK", "https://pocket-friends.com/r/ugauihalod")
PROMO_CODE = os.getenv("PROMO_CODE", "FRIENDUGAUIHALOD")

# ... (Остальные константы, включая SUBSCRIPTION_PLANS, TRANSLATIONS, CURRENCY_RATES - оставлены как в предыдущем ответе)

# --- НАСТРОЙКА ЛОГГИРОВАНИЯ ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- НАСТРОЙКА YOOKASSA ---
if YOOKASSA_SHOP_ID != "YOUR_SHOP_ID":
    try:
        Configuration.configure(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
        logger.info("✅ YooKassa configured successfully")
    except Exception as e:
        logger.error(f"❌ YooKassa configuration failed: {e}")
else:
    logger.warning("⚠️ YooKassa credentials not found - payment will use dummy mode")

# --- СИСТЕМА ПЕРЕВОДОВ И КОНСТАНТЫ ---
DEFAULT_BOT_COMMANDS = [
    ("start", "🏠 Главное меню"), ("plans", "💎 Тарифы и подписки"),
    ("bank", "💰 Управление банком"), ("autotrade", "🤖 Автоторговля (VIP)"),
    ("settings", "⚙️ Настройки"), ("short", "⏳ SHORT сигнал (1-5 мин)"),
    ("long", "📈 LONG сигнал (1-4 часа)"), ("my_stats", "📈 Моя статистика"),
    ("help", "❓ Помощь и инструкции"),
]
SUBSCRIPTION_PLANS = {
    'short': {'1m': 4990, '6m': 26946, '12m': 47904, 'name': 'SHORT', 'description': 'Быстрые сигналы (1-5 мин) с мартингейлом', 'emoji': '⏳'},
    'long': {'1m': 4990, '6m': 26946, '12m': 47904, 'name': 'LONG', 'description': 'Длинные сигналы (1-4 часа) с процентной ставкой', 'emoji': '📈'},
    'vip': {'1m': 9990, '6m': 53946, '12m': 95904, 'name': 'VIP', 'description': 'Все сигналы + приоритет + гибкие настройки стратегий и статистика', 'emoji': '💎'}
}
NEW_USER_PROMO = {'price': 1490, 'duration_days': 30, 'plan': 'short', 'discount_percent': 70}
CURRENCY_RATES = {'RUB': 1.0, 'USD': 0.011}
CURRENCY_SYMBOLS = {'RUB': '₽', 'USD': '$'}
SHORT_SIGNAL_FREE_LIMIT = 5
LONG_SIGNAL_FREE_LIMIT = 10
PAYOUT_PERCENT = 92
# TRANSLATIONS - здесь должен быть полный словарь, как в предыдущем ответе.
TRANSLATIONS = {
    'ru': {
        'plans': '💎 Тарифы и подписки', 'short_signal': '⏳ SHORT сигнал', 'long_signal': '📈 LONG сигнал', 
        'my_stats': '📈 Моя статистика', 'autotrade': '🤖 Автоторговля (VIP)', 'settings': '⚙️ Настройки',
        'help': '❓ Помощь и инструкции', 'welcome': '👋 Добро пожаловать', 'welcome_desc': 'Выберите действие:',
        'back': '⬅️ Назад', 'buy_subscription': 'Купить', 'call': '⬆️ CALL (ВВЕРХ)', 'put': '⬇️ PUT (ВНИЗ)',
        'already_subscribed': 'Ваша подписка: {plan} истекает {date}.', 'not_subscribed': 'У вас нет активной подписки.',
        'promo_active': '🎁 АКЦИЯ', 'promo_price': 'Цена: {price}{symbol} (скидка {discount}%)', 'promo_activate': '✅ Активировать акцию',
        'choose_currency': '💰 Выберите валюту:', 'choose_language': '🌐 Выберите язык:', 'language_selected': '✅ Язык установлен: Русский',
        'short_menu_title': '⏳ SHORT сигнал (1-5 мин)', 'short_menu_desc': 'Базовая ставка: {stake}{symbol}. Стратегия: Мартингейл x{multiplier}.',
        'get_signal': '💸 Получить сигнал', 'short_limit_reached': '🚫 Лимит бесплатных SHORT сигналов на сегодня исчерпан ({used}/{limit}).',
        'signal_asset': 'АКТИВ: {asset}', 'signal_direction': 'НАПРАВЛЕНИЕ: {direction}', 'signal_stake': 'СУММА СТАВКИ: {stake}{symbol}',
        'short_signal_title': '⏳ SHORT СИГНАЛ | УРОВЕНЬ {level}/{max_level}', 'signal_confidence': 'НАДЕЖНОСТЬ: {confidence}%',
        'signal_waiting': 'Ожидаем закрытия сделки...', 'next_martingale': 'Если сделка не закроется в плюс, будет отправлен следующий сигнал по Мартингейлу ({next_level}) с суммой {next_stake}{symbol}.',
        'month': 'мес', 'months': 'мес', 'strategy_settings': '⚙️ Настройки стратегий',
        'bank_menu': '💰 УПРАВЛЕНИЕ БАНКОМ', 'bank_current': 'Текущий баланс: {balance}{symbol}', 'bank_initial': 'Начальный баланс: {initial_balance}{symbol}',
        'bank_profit': 'Общая прибыль: {profit}{symbol}', 'set_balance': 'Изменить баланс', 'autotrade_menu': '🤖 АВТОТОРГОВЛЯ (VIP)',
        'po_ref_link': '🔗 Ссылка на Pocket Option', 'po_connect': '🔑 Подключить аккаунт (SSID/Email)', 'po_connected': '✅ Подключен',
        'po_not_connected': '❌ Не подключен', 'enter_po_email': 'Введите **Email** от вашего аккаунта Pocket Option:',
        'enter_po_ssid': 'Введите **SSID** от вашего аккаунта Pocket Option. Инструкцию можно найти по ссылке:',
        'set_lang': '🌐 Изменить язык', 'set_cur': '💰 Изменить валюту ({current_currency})', 'set_short_strat': '⏳ Настройки SHORT',
        'set_long_strat': '📈 Настройки LONG', 'set_autotrade_status': '🤖 Статус Автоторговли', 'autotrade_mode_set': '✅ Режим автоторговли установлен на **{mode}**.',
        'long_menu_title': '📈 LONG сигнал (1-4 часа)', 'long_menu_desc': 'Ставка: {percentage}% от банка.', 'long_signal_title': '📈 LONG СИГНАЛ',
        'signal_expiry': 'ВРЕМЯ ЭКСПИРАЦИИ: {time}', 'signal_entry_price': 'ЦЕНА ВХОДА: {price}', 'long_limit_reached': '🚫 Лимит бесплатных LONG сигналов на сегодня исчерпан ({used}/{limit}).',
        'stats_title': '📈 ВАША СТАТИСТИКА', 'stats_subscription': '🌟 Подписка: {plan}', 'stats_expired': 'Истекла', 'stats_signals_total': 'Всего сделок:',
        'stats_signals_win': 'Побед (Win):', 'stats_signals_loss': 'Поражений (Loss):', 'stats_win_rate': 'Доходность (Win Rate):',
    },
    'en': {
        'plans': '💎 Plans & Subscriptions', 'short_signal': '⏳ SHORT Signal', 'long_signal': '📈 LONG Signal', 
        'my_stats': '📈 My Statistics', 'autotrade': '🤖 Autotrading (VIP)', 'settings': '⚙️ Settings',
        'help': '❓ Help & Instructions', 'welcome': '👋 Welcome', 'welcome_desc': 'Choose an action:',
        'back': '⬅️ Back', 'buy_subscription': 'Buy', 'call': '⬆️ CALL (UP)', 'put': '⬇️ PUT (DOWN)',
        'already_subscribed': 'Your subscription: {plan} expires {date}.', 'not_subscribed': 'You do not have an active subscription.',
        'promo_active': '🎁 PROMO', 'promo_price': 'Price: {price}{symbol} ({discount}% discount)', 'promo_activate': '✅ Activate Promotion',
        'choose_currency': '💰 Choose currency:', 'choose_language': '🌐 Choose language:', 'language_selected': '✅ Language set: English',
        'short_menu_title': '⏳ SHORT Signal (1-5 min)', 'short_menu_desc': 'Base stake: {stake}{symbol}. Strategy: Martingale x{multiplier}.',
        'get_signal': '💸 Get Signal', 'short_limit_reached': '🚫 Free SHORT signal limit reached today ({used}/{limit}).',
        'signal_asset': 'ASSET: {asset}', 'signal_direction': 'DIRECTION: {direction}', 'signal_stake': 'STAKE AMOUNT: {stake}{symbol}',
        'short_signal_title': '⏳ SHORT SIGNAL | LEVEL {level}/{max_level}', 'signal_confidence': 'RELIABILITY: {confidence}%',
        'signal_waiting': 'Waiting for trade close...', 'next_martingale': 'If the trade does not close positive, the next Martingale signal ({next_level}) will be sent with an amount of {next_stake}{symbol}.',
        'month': 'month', 'months': 'months', 'strategy_settings': '⚙️ Strategy Settings',
        'bank_menu': '💰 BANK MANAGEMENT', 'bank_current': 'Current balance: {balance}{symbol}', 'bank_initial': 'Initial balance: {initial_balance}{symbol}',
        'bank_profit': 'Total profit: {profit}{symbol}', 'set_balance': 'Set Balance', 'autotrade_menu': '🤖 AUTOTRADING (VIP)',
        'po_ref_link': '🔗 Pocket Option Link', 'po_connect': '🔑 Connect Account (SSID/Email)', 'po_connected': '✅ Connected',
        'po_not_connected': '❌ Not Connected', 'enter_po_email': 'Enter the **Email** of your Pocket Option account:',
        'enter_po_ssid': 'Enter the **SSID** of your Pocket Option account. You can find instructions at the link:',
        'set_lang': '🌐 Change Language', 'set_cur': '💰 Change Currency ({current_currency})', 'set_short_strat': '⏳ SHORT Settings',
        'set_long_strat': '📈 LONG Settings', 'set_autotrade_status': '🤖 Autotrading Status', 'autotrade_mode_set': '✅ Autotrading mode set to **{mode}**.',
        'long_menu_title': '📈 LONG Signal (1-4 hours)', 'long_menu_desc': 'Stake: {percentage}% of bank.', 'long_signal_title': '📈 LONG SIGNAL',
        'signal_expiry': 'EXPIRATION TIME: {time}', 'signal_entry_price': 'ENTRY PRICE: {price}', 'long_limit_reached': '🚫 Free LONG signal limit reached today ({used}/{limit}).',
        'stats_title': '📈 YOUR STATISTICS', 'stats_subscription': '🌟 Subscription: {plan}', 'stats_expired': 'Expired', 'stats_signals_total': 'Total Trades:',
        'stats_signals_win': 'Wins (Win):', 'stats_signals_loss': 'Losses (Loss):', 'stats_win_rate': 'Profitability (Win Rate):',
    }
}


# --- ГЛАВНЫЙ КЛАСС БОТА ---
class CryptoSignalsBot:
    def __init__(self, application):
        self.application = application
        self.bot = application.bot
        self.max_martingale_level = 3 
        self.setup_database()
        self.user_states = {} # Состояния для пошагового ввода (например, установки баланса)
        self.admin_list = [ADMIN_USER_ID] # Список администраторов

    # --- DB UTILS (Методы базы данных) ---

    def setup_database(self):
        """Initializes and ensures all necessary tables and columns exist in the SQLite database."""
        # ... (Полная реализация setup_database, как в предыдущем ответе)
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = self.conn.cursor()
        
        # 1. USERS Table (Убедитесь, что эта таблица полностью соответствует вашей структуре)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, joined_date DATETIME,
                subscription_end DATETIME, signals_used INTEGER DEFAULT 0, last_signal_date DATETIME,
                initial_balance REAL DEFAULT NULL, current_balance REAL DEFAULT NULL,
                currency TEXT DEFAULT "RUB", subscription_type TEXT DEFAULT NULL,
                new_user_discount_used BOOLEAN DEFAULT 0,
                language TEXT DEFAULT "ru", free_short_signals_today INTEGER DEFAULT 0,
                free_long_signals_today INTEGER DEFAULT 0, banned BOOLEAN DEFAULT 0,
                martingale_multiplier INTEGER DEFAULT 3, martingale_base_stake REAL DEFAULT 100,
                percentage_value REAL DEFAULT 2.5, auto_trading_enabled BOOLEAN DEFAULT 0,
                pocket_option_email TEXT DEFAULT NULL, auto_trading_mode TEXT DEFAULT "demo",
                pocket_option_connected BOOLEAN DEFAULT 0, pocket_option_ssid TEXT DEFAULT NULL
                -- ... добавьте другие колонки из вашей полной схемы
            )
        ''')
        
        # 2. SIGNAL_HISTORY Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, asset TEXT,
                signal_type TEXT, result TEXT, profit_loss REAL, stake_amount REAL,
                signal_date DATETIME, notes TEXT, expiration_time TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # 3. ADMIN_SETTINGS Table (для динамических настроек)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Добавляем ADMIN_USER_ID в настройки, чтобы можно было менять его через /add_admin
        if self.get_setting('super_admin_id') is None:
            self.set_setting('super_admin_id', ADMIN_USER_ID)

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

    # ... (get_user_data, create_user_if_not_exists, update_user_field, get_translation, get_currency_symbol, is_subscribed)
    def get_user_data(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        return dict(zip(columns, row)) if row else None

    def create_user_if_not_exists(self, update: Update):
        user = update.effective_user
        if not self.get_user_data(user.id):
            cursor = self.conn.cursor()
            joined_date = datetime.now(MOSCOW_TZ).isoformat()
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, joined_date, language)
                VALUES (?, ?, ?, ?, ?)
            """, (user.id, user.username, user.first_name, joined_date, user.language_code if user.language_code and user.language_code in TRANSLATIONS else 'ru'))
            self.conn.commit()
            return True
        return False
        
    def update_user_field(self, user_id, field, value):
        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
        self.conn.commit()

    def get_translation(self, user_data, key):
        lang = user_data.get('language', 'ru')
        return TRANSLATIONS.get(lang, TRANSLATIONS['ru']).get(key, f"_{key}_")
    
    def get_currency_symbol(self, user_data):
        currency = user_data.get('currency', 'RUB')
        return CURRENCY_SYMBOLS.get(currency, '$')
    
    def is_subscribed(self, user_data):
        end_date_str = user_data.get('subscription_end')
        if not end_date_str: return False
        try:
            end_date = datetime.fromisoformat(end_date_str).replace(tzinfo=MOSCOW_TZ)
            return end_date > datetime.now(MOSCOW_TZ)
        except Exception: return False
    
    def is_admin(self, user_id):
        """Checks if the user is an admin or super admin."""
        admin_id = int(self.get_setting('super_admin_id', 0))
        return user_id == admin_id or user_id == ADMIN_USER_ID

    # --- СИГНАЛЬНЫЕ ФУНКЦИИ (ЗАГЛУШКИ) ---
    def get_short_signal(self, user_data, martingale_level):
        """Placeholder for fetching a new SHORT signal."""
        asset = random.choice(['BTC/USDT', 'ETH/USDT', 'LTC/USDT', 'XRP/USDT'])
        direction = random.choice(['call', 'put'])
        confidence = random.randint(80, 99)
        
        stake = user_data.get('martingale_base_stake', 100) * (user_data.get('martingale_multiplier', 3) ** martingale_level)
        expiry_min = random.choice([1, 3, 5])
        
        return {
            'asset': asset, 'direction': direction, 'timeframe': f'{expiry_min}M',
            'expiration_time': f'{expiry_min} мин.', 'stake_amount': round(stake, 2),
            'confidence': confidence, 'entry_price': round(random.uniform(20000, 70000), 2),
        }
    
    def get_long_signal(self, user_data):
        """Placeholder for fetching a new LONG signal."""
        asset = random.choice(['EUR/USD', 'GBP/USD', 'GOLD'])
        direction = random.choice(['call', 'put'])
        confidence = random.randint(85, 99)
        
        current_balance = user_data.get('current_balance', 1000)
        percentage = user_data.get('percentage_value', 2.5)
        stake = current_balance * (percentage / 100)
        expiry_min = random.choice([60, 120, 240]) # 1, 2, 4 часа
        
        return {
            'asset': asset, 'direction': direction, 'timeframe': f'{expiry_min}M',
            'expiration_time': f'{int(expiry_min/60)} час.', 'stake_amount': round(stake, 2),
            'confidence': confidence, 'entry_price': round(random.uniform(1.0, 1.3), 5),
        }
        
    def save_signal_history(self, user_id, signal, signal_type, level=1):
        """Saves the generated signal to the history table."""
        cursor = self.conn.cursor()
        signal_date = datetime.now(MOSCOW_TZ).isoformat()
        
        cursor.execute("""
            INSERT INTO signal_history (user_id, asset, signal_type, stake_amount, signal_date, expiration_time, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, signal['asset'], signal_type, signal['stake_amount'], 
            signal_date, signal['expiration_time'], f"Level {level}, Conf: {signal['confidence']}%"
        ))
        self.conn.commit()
    
    def plot_stats(self, user_id):
        """Generates a dummy plot for user statistics."""
        data = np.random.normal(loc=120, scale=10, size=30).cumsum()
        data = data - data.min() + 1000 # Сдвигаем, чтобы выглядело как баланс
        
        df = pd.DataFrame({'Balance': data})
        df['Date'] = pd.to_datetime(pd.date_range(end=datetime.now().date(), periods=30, freq='D'))

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(df['Date'], df['Balance'], label='Баланс', color='#3b82f6', linewidth=2, 
                path_effects=[pe.Stroke(linewidth=3, foreground='black'), pe.Normal()])
        ax.fill_between(df['Date'], 1000, df['Balance'], alpha=0.1, color='#3b82f6')
        
        ax.set_title("Динамика баланса за 30 дней", color='white')
        ax.set_xlabel('Дата', color='white')
        ax.set_ylabel('Баланс (RUB)', color='white')
        
        # Настройка фона и осей
        ax.set_facecolor('#1f2937')
        fig.patch.set_facecolor('#1f2937')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        
        # Форматирование оси X для читабельности
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%b %d'))
        fig.autofmt_xdate(rotation=45)
        
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        plt.close(fig)
        buf.seek(0)
        return buf

    # --- HANDLERS (Обработчики команд) ---

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles the /start command and displays the main menu."""
        user_id = update.effective_user.id
        self.create_user_if_not_exists(update)
        user_data = self.get_user_data(user_id)
        
        T = lambda key: self.get_translation(user_data, key)
        
        if not user_data.get('language'):
            await self.language_prompt(update, context)
            return
            
        is_sub = self.is_subscribed(user_data)
        
        keyboard = [
            [InlineKeyboardButton(T('short_signal'), callback_data='cmd_short'), InlineKeyboardButton(T('long_signal'), callback_data='cmd_long')],
            [InlineKeyboardButton(T('my_stats'), callback_data='cmd_my_stats'), InlineKeyboardButton(T('autotrade'), callback_data='cmd_autotrade')],
            [InlineKeyboardButton(T('plans'), callback_data='cmd_plans'), InlineKeyboardButton(T('settings'), callback_data='cmd_settings')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        status_text = T('already_subscribed').format(
            plan=user_data['subscription_type'].upper(), 
            date=datetime.fromisoformat(user_data['subscription_end']).strftime('%d.%m.%Y %H:%M')
        ) if is_sub else T('not_subscribed')
            
        message_text = f"🌊 **{T('welcome')}**\n\n**{status_text}**\n\n{T('welcome_desc')}"
        
        await self._send_or_edit_message(update, message_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def language_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Prompts the user to choose a language."""
        keyboard = [
            [InlineKeyboardButton("Русский 🇷🇺", callback_data='set_lang_ru'), InlineKeyboardButton("English 🇬🇧", callback_data='set_lang_en')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(TRANSLATIONS['ru']['choose_language'], reply_markup=reply_markup)

    async def plans_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles the /plans command and shows subscription options."""
        # ... (Полная реализация plans_command, как в предыдущем ответе)
        query = update.callback_query
        if query: await query.answer()
        
        user_id = update.effective_user.id
        user_data = self.get_user_data(user_id)
        T = lambda key: self.get_translation(user_data, key)
        symbol = self.get_currency_symbol(user_data)
        is_sub = self.is_subscribed(user_data)
        
        text = f"**{T('plans')}**\n\n"
        keyboard = []

        # 1. NEW USER PROMO
        if not user_data.get('new_user_discount_used'):
            promo_price = NEW_USER_PROMO['price'] * CURRENCY_RATES.get(user_data['currency'], 1.0)
            text += (f"{T('promo_active')}\n**{SUBSCRIPTION_PLANS['short']['name']}** {T('month')} - "
                f"{T('promo_price').format(price=int(promo_price), symbol=symbol, discount=NEW_USER_PROMO['discount_percent'])}\n\n")
            keyboard.append([InlineKeyboardButton(T('promo_activate'), callback_data='buy_promo')])
            text += "---\n\n"

        # 2. STANDARD PLANS
        for plan_key, plan_data in SUBSCRIPTION_PLANS.items():
            text += f"**{plan_data['emoji']} {plan_data['name']}** - *{plan_data['description']}*\n"
            plan_buttons = []
            for duration, price in plan_data.items():
                if duration in ['1m', '6m', '12m']:
                    converted_price = price * CURRENCY_RATES.get(user_data['currency'], 1.0)
                    label = f"{T('month')} | {int(converted_price)}{symbol}" if duration == '1m' else f"{duration[:-1]} {T('months')} | {int(converted_price)}{symbol}"
                    plan_buttons.append(InlineKeyboardButton(label, callback_data=f'buy_{plan_key}_{duration}'))
            keyboard.append(plan_buttons)
            text += "\n"

        # 3. Footer
        if is_sub:
            sub_end_date = datetime.fromisoformat(user_data['subscription_end']).strftime('%d.%m.%Y %H:%M')
            text += f"\n---\n{T('already_subscribed').format(plan=user_data['subscription_type'].upper(), date=sub_end_date)}"

        keyboard.append([InlineKeyboardButton(T('back'), callback_data='cmd_start')])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await self._send_or_edit_message(update, text, reply_markup=reply_markup, parse_mode='Markdown')

    async def short_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles the /short command and shows the SHORT signal menu."""
        # ... (Полная реализация short_command, включая проверку лимитов и текущего уровня Мартингейла)
        query = update.callback_query
        if query: await query.answer()
        
        user_id = update.effective_user.id
        user_data = self.get_user_data(user_id)
        T = lambda key: self.get_translation(user_data, key)
        symbol = self.get_currency_symbol(user_data)
        is_sub = self.is_subscribed(user_data)
        
        # Проверка лимитов для бесплатных пользователей
        if not is_sub and user_data.get('free_short_signals_today', 0) >= SHORT_SIGNAL_FREE_LIMIT:
            message_text = T('short_limit_reached').format(used=user_data.get('free_short_signals_today', 0), limit=SHORT_SIGNAL_FREE_LIMIT)
            keyboard = [[InlineKeyboardButton(T('plans'), callback_data='cmd_plans')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self._send_or_edit_message(update, message_text, reply_markup=reply_markup)
            return

        current_level = user_data.get('current_martingale_level', 0)
        base_stake = user_data.get('martingale_base_stake', 100)
        multiplier = user_data.get('martingale_multiplier', 3)
        
        message_text = (f"**{T('short_menu_title')}**\n\n"
            f"{T('short_menu_desc').format(stake=int(base_stake), symbol=symbol, multiplier=multiplier)}")
        
        if current_level > 0:
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
        if query: await query.answer("Генерация сигнала...")
            
        user_id = update.effective_user.id
        user_data = self.get_user_data(user_id)
        is_sub = self.is_subscribed(user_data)
        if not is_sub:
            self.update_user_field(user_id, 'free_short_signals_today', user_data.get('free_short_signals_today', 0) + 1)
        
        current_level = user_data.get('current_martingale_level', 0)
        signal = self.get_short_signal(user_data, current_level)
        self.save_signal_history(user_id, signal, 'SHORT', current_level + 1)
        
        T, symbol = lambda key: self.get_translation(user_data, key), self.get_currency_symbol(user_data)
        direction_text = T('call') if signal['direction'] == 'call' else T('put')
        
        message_text = (f"**{T('short_signal_title').format(level=current_level + 1, max_level=self.max_martingale_level)}**\n\n"
            f"{T('signal_asset').format(asset=signal['asset'])}\n{T('signal_direction').format(direction=direction_text)}\n"
            f"{T('signal_expiry').format(time=signal['expiration_time'])}\n{T('signal_stake').format(stake=int(signal['stake_amount']), symbol=symbol)}\n"
            f"{T('signal_confidence').format(confidence=signal['confidence'])}\n\n*{T('signal_waiting')}*")
        
        if current_level < self.max_martingale_level - 1:
            multiplier = user_data.get('martingale_multiplier', 3)
            next_stake = signal['stake_amount'] * multiplier
            message_text += (f"\n\n_{T('next_martingale').format(next_level=current_level + 2, next_stake=int(next_stake), symbol=symbol)}_")
            self.update_user_field(user_id, 'current_martingale_level', current_level + 1) 
        else:
             self.update_user_field(user_id, 'current_martingale_level', 0) 
            
        keyboard = [[InlineKeyboardButton(T('back'), callback_data='cmd_short')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self._send_or_edit_message(update, message_text, reply_markup=reply_markup, parse_mode='Markdown')


    async def long_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles the /long command and shows the LONG signal menu."""
        query = update.callback_query
        if query: await query.answer()
        
        user_id = update.effective_user.id
        user_data = self.get_user_data(user_id)
        T = lambda key: self.get_translation(user_data, key)
        is_sub = self.is_subscribed(user_data)

        if not is_sub and user_data.get('free_long_signals_today', 0) >= LONG_SIGNAL_FREE_LIMIT:
            message_text = T('long_limit_reached').format(used=user_data.get('free_long_signals_today', 0), limit=LONG_SIGNAL_FREE_LIMIT)
            keyboard = [[InlineKeyboardButton(T('plans'), callback_data='cmd_plans')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self._send_or_edit_message(update, message_text, reply_markup=reply_markup)
            return

        percentage = user_data.get('percentage_value', 2.5)
        message_text = (f"**{T('long_menu_title')}**\n\n"
            f"{T('long_menu_desc').format(percentage=percentage)}")
        
        keyboard = [
            [InlineKeyboardButton(T('get_signal'), callback_data='get_signal_long')],
            [InlineKeyboardButton(T('strategy_settings'), callback_data='settings_strategy_long')],
            [InlineKeyboardButton(T('back'), callback_data='cmd_start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self._send_or_edit_message(update, message_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def get_signal_long(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Generates and sends the LONG signal."""
        query = update.callback_query
        if query: await query.answer("Генерация сигнала...")
            
        user_id = update.effective_user.id
        user_data = self.get_user_data(user_id)
        is_sub = self.is_subscribed(user_data)
        if not is_sub:
            self.update_user_field(user_id, 'free_long_signals_today', user_data.get('free_long_signals_today', 0) + 1)
        
        signal = self.get_long_signal(user_data)
        self.save_signal_history(user_id, signal, 'LONG')
        
        T, symbol = lambda key: self.get_translation(user_data, key), self.get_currency_symbol(user_data)
        direction_text = T('call') if signal['direction'] == 'call' else T('put')
        
        message_text = (f"**{T('long_signal_title')}**\n\n"
            f"{T('signal_asset').format(asset=signal['asset'])}\n{T('signal_direction').format(direction=direction_text)}\n"
            f"{T('signal_expiry').format(time=signal['expiration_time'])}\n"
            f"{T('signal_entry_price').format(price=signal['entry_price'])}\n"
            f"{T('signal_stake').format(stake=int(signal['stake_amount']), symbol=symbol)}\n"
            f"{T('signal_confidence').format(confidence=signal['confidence'])}\n\n*{T('signal_waiting')}*")
            
        keyboard = [[InlineKeyboardButton(T('back'), callback_data='cmd_long')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self._send_or_edit_message(update, message_text, reply_markup=reply_markup, parse_mode='Markdown')
    

    # --- Другие команды (Bank, Stats, Autotrade, Settings) ---
    
    async def bank_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Displays bank management menu."""
        query = update.callback_query
        if query: await query.answer()

        user_id = update.effective_user.id
        user_data = self.get_user_data(user_id)
        T, symbol = lambda key: self.get_translation(user_data, key), self.get_currency_symbol(user_data)

        current = user_data.get('current_balance')
        initial = user_data.get('initial_balance')
        
        if current is None or initial is None:
            profit = 0
            current_display = "---"
            initial_display = "---"
        else:
            profit = current - initial
            current_display = f"{int(current)}{symbol}"
            initial_display = f"{int(initial)}{symbol}"

        message_text = (
            f"**{T('bank_menu')}**\n\n"
            f"{T('bank_current').format(balance=current_display, symbol=symbol)}\n"
            f"{T('bank_initial').format(initial_balance=initial_display, symbol=symbol)}\n"
            f"**{T('bank_profit').format(profit=int(profit), symbol=symbol)}**"
        )
        
        keyboard = [
            [InlineKeyboardButton(T('set_balance'), callback_data='bank_set_balance')],
            [InlineKeyboardButton(T('back'), callback_data='cmd_start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self._send_or_edit_message(update, message_text, reply_markup=reply_markup, parse_mode='Markdown')


    async def my_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Displays user statistics and plot."""
        query = update.callback_query
        if query: await query.answer()

        user_id = update.effective_user.id
        user_data = self.get_user_data(user_id)
        T, symbol = lambda key: self.get_translation(user_data, key), self.get_currency_symbol(user_data)
        
        # Получение статистики (заглушка)
        total_signals = random.randint(100, 200)
        wins = random.randint(80, total_signals)
        losses = total_signals - wins
        win_rate = f"{(wins / total_signals) * 100:.1f}%" if total_signals > 0 else "0.0%"
        
        is_sub = self.is_subscribed(user_data)
        sub_type = user_data.get('subscription_type', 'FREE')
        
        if is_sub:
            sub_end_date = datetime.fromisoformat(user_data['subscription_end']).strftime('%d.%m.%Y')
            sub_status = T('stats_subscription').format(plan=f"{sub_type} (до {sub_end_date})")
        else:
            sub_status = T('stats_subscription').format(plan=T('stats_expired'))

        message_text = (
            f"**{T('stats_title')}**\n\n"
            f"{sub_status}\n"
            f"*{T('stats_signals_total')}* **{total_signals}**\n"
            f"*{T('stats_signals_win')}* **{wins}**\n"
            f"*{T('stats_signals_loss')}* **{losses}**\n"
            f"**{T('stats_win_rate')}** **{win_rate}**\n"
        )
        
        keyboard = [[InlineKeyboardButton(T('back'), callback_data='cmd_start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправка текста и графика
        buf = self.plot_stats(user_id)
        
        await self._send_photo_or_edit_message(
            update, message_text, buf, caption=message_text, reply_markup=reply_markup, parse_mode='Markdown'
        )

    async def autotrade_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Displays Pocket Option connection and autotrade settings."""
        query = update.callback_query
        if query: await query.answer()

        user_id = update.effective_user.id
        user_data = self.get_user_data(user_id)
        T = lambda key: self.get_translation(user_data, key)
        is_vip = user_data.get('subscription_type', '').upper() == 'VIP' and self.is_subscribed(user_data)
        
        if not is_vip:
            message_text = "🤖 **Автоторговля** доступна только для пользователей с **💎 VIP** подпиской. "
            keyboard = [[InlineKeyboardButton(T('plans'), callback_data='cmd_plans')], [InlineKeyboardButton(T('back'), callback_data='cmd_start')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self._send_or_edit_message(update, message_text, reply_markup=reply_markup, parse_mode='Markdown')
            return

        connected_status = T('po_connected') if user_data.get('pocket_option_connected') else T('po_not_connected')
        mode = user_data.get('auto_trading_mode', 'demo').upper()
        
        message_text = (
            f"**{T('autotrade_menu')}**\n\n"
            f"**Статус подключения:** {connected_status}\n"
            f"**Режим торговли:** **{mode}**\n"
            f"**Статус Автоторговли:** {'✅ Включена' if user_data.get('auto_trading_enabled') else '❌ Выключена'}"
        )
        
        keyboard = [
            [InlineKeyboardButton(T('po_ref_link'), url=POCKET_OPTION_REF_LINK), 
             InlineKeyboardButton(T('po_connect'), callback_data='autotrade_connect')],
            [InlineKeyboardButton(f"🔁 Режим ({mode})", callback_data='autotrade_toggle_mode')],
            [InlineKeyboardButton(f"{'🛑 Выкл.' if user_data.get('auto_trading_enabled') else '🟢 Вкл.'} Автоторговлю", callback_data='autotrade_toggle_status')],
            [InlineKeyboardButton(T('back'), callback_data='cmd_start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self._send_or_edit_message(update, message_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Displays general settings menu."""
        query = update.callback_query
        if query: await query.answer()

        user_id = update.effective_user.id
        user_data = self.get_user_data(user_id)
        T = lambda key: self.get_translation(user_data, key)
        
        message_text = "**⚙️ НАСТРОЙКИ**"
        
        keyboard = [
            [InlineKeyboardButton(T('set_lang'), callback_data='settings_language')],
            [InlineKeyboardButton(T('set_cur').format(current_currency=user_data.get('currency', 'RUB')), callback_data='settings_currency')],
            [InlineKeyboardButton(T('set_short_strat'), callback_data='settings_strategy_short')],
            [InlineKeyboardButton(T('set_long_strat'), callback_data='settings_strategy_long')],
            [InlineKeyboardButton(T('back'), callback_data='cmd_start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self._send_or_edit_message(update, message_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # --- PURCHASE LOGIC (YooKassa) ---

    async def handle_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Initiates a payment using YooKassa."""
        query = update.callback_query
        await query.answer("Создание счета...")
        
        user_id = update.effective_user.id
        user_data = self.get_user_data(user_id)
        T = lambda key: self.get_translation(user_data, key)
        
        plan_data = query.data.split('_')
        action = plan_data[0]
        plan_key = plan_data[1] if action != 'buy' else plan_data[1]
        duration = plan_data[2] if action != 'buy_promo' else '1m'
        
        if action == 'buy_promo':
            price = NEW_USER_PROMO['price']
            plan_name = SUBSCRIPTION_PLANS[plan_key]['name']
            description = f"Промо-подписка {plan_name} на 30 дней."
        else:
            price = SUBSCRIPTION_PLANS[plan_key][duration]
            plan_name = SUBSCRIPTION_PLANS[plan_key]['name']
            description = f"Подписка {plan_name} на {duration}."

        # Конвертация в целевую валюту (всегда отправляем в YooKassa в RUB, если не указано иное)
        amount = round(price * CURRENCY_RATES.get('RUB', 1.0), 2)
        
        # 1. Создание платежа YooKassa
        try:
            payment = Payment.create({
                'amount': {'value': str(amount), 'currency': 'RUB'},
                'confirmation': {'type': 'redirect', 'return_url': 'https://t.me/your_bot_username'},
                'capture': True,
                'description': description,
                'metadata': {
                    'user_id': user_id, 
                    'plan': plan_key, 
                    'duration': duration,
                    'action': action
                }
            })
            
            payment_url = payment.confirmation.confirmation_url
            
            # 2. Отправка пользователю ссылки на оплату
            message_text = (
                f"**💰 Счет на оплату: {plan_name} ({duration})**\n\n"
                f"Сумма: **{amount} RUB**\n\n"
                f"Для оплаты перейдите по ссылке ниже. После успешной оплаты подписка будет активирована автоматически."
            )
            keyboard = [[InlineKeyboardButton("💳 Оплатить", url=payment_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"YooKassa payment creation failed for user {user_id}: {e}")
            await query.edit_message_text(
                f"❌ Ошибка при создании счета. Пожалуйста, попробуйте позже или обратитесь в поддержку {SUPPORT_CONTACT}.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(T('back'), callback_data='cmd_plans')]])
            )

    def subscribe_user(self, user_id: int, plan: str, duration: str, action: str):
        """Activates the subscription for the user."""
        user_data = self.get_user_data(user_id)
        if not user_data:
            logger.error(f"Cannot subscribe user {user_id}: User not found in DB.")
            return

        now = datetime.now(MOSCOW_TZ)
        
        # Определяем продолжительность в днях
        if action == 'buy_promo':
            days = NEW_USER_PROMO['duration_days']
            self.update_user_field(user_id, 'new_user_discount_used', True)
        elif duration == '1m':
            days = 30
        elif duration == '6m':
            days = 30 * 6
        elif duration == '12m':
            days = 30 * 12
        else:
            days = 30 # Default

        # Обновляем дату окончания подписки
        # Если есть активная подписка, начинаем с даты окончания, иначе - с текущей даты.
        if self.is_subscribed(user_data):
             # Находим текущую дату окончания подписки
            current_end = datetime.fromisoformat(user_data['subscription_end']).replace(tzinfo=MOSCOW_TZ)
            new_end_date = current_end + timedelta(days=days)
        else:
            new_end_date = now + timedelta(days=days)

        self.update_user_field(user_id, 'subscription_end', new_end_date.isoformat())
        self.update_user_field(user_id, 'subscription_type', plan)
        
        logger.info(f"✅ User {user_id} subscribed to {plan} for {days} days until {new_end_date.strftime('%Y-%m-%d')}.")
        
        # Отправка уведомления пользователю
        asyncio.run_coroutine_threadsafe(
            self.bot.send_message(
                chat_id=user_id,
                text=f"🥳 **ПОДПИСКА АКТИВИРОВАНА!**\n\n"
                     f"Тариф: **{plan.upper()}**\n"
                     f"Действует до: **{new_end_date.strftime('%d.%m.%Y %H:%M МСК')}**\n\n"
                     f"Добро пожаловать в команду!",
                parse_mode='Markdown'
            ),
            self.application.loop
        )
        
    # --- ADMIN COMMANDS (Ключевые команды админа) ---

    async def admin_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Utility to check admin status and send a warning if not an admin."""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("🚫 Доступ запрещен. Вы не являетесь администратором.")
            return False
        return True

    async def notify_all_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Sends a message to all users (Admin only)."""
        if not await self.admin_check(update, context): return
        
        if not context.args:
            await update.message.reply_text("Использование: /notify_all <ваше сообщение>")
            return

        message = " ".join(context.args)
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE banned = 0")
        users = cursor.fetchall()
        
        sent_count = 0
        for (user_id,) in users:
            try:
                await context.bot.send_message(user_id, f"**📢 УВЕДОМЛЕНИЕ АДМИНИСТРАЦИИ**\n\n{message}", parse_mode='Markdown')
                sent_count += 1
                await asyncio.sleep(0.05) # Задержка для обхода лимитов Telegram
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                
        await update.message.reply_text(f"✅ Рассылка завершена. Сообщение отправлено {sent_count} пользователям.")


    # --- Message and Callback Handlers ---
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles regular text messages, primarily for promo codes or step-by-step input."""
        user_id = update.effective_user.id
        T = lambda key: self.get_translation(self.get_user_data(user_id), key)
        text = update.message.text.strip()
        
        # 1. Обработка пошагового ввода (States)
        current_state = self.user_states.get(user_id)
        if current_state == 'SET_BALANCE':
            try:
                new_balance = float(text.replace(',', '.').strip())
                if new_balance <= 0:
                     await update.message.reply_text("Баланс должен быть положительным числом.")
                     return
                
                user_data = self.get_user_data(user_id)
                # Устанавливаем и начальный, и текущий баланс, если начальный еще не установлен
                if user_data.get('initial_balance') is None:
                    self.update_user_field(user_id, 'initial_balance', new_balance)
                self.update_user_field(user_id, 'current_balance', new_balance)
                
                self.user_states.pop(user_id)
                await update.message.reply_text(f"✅ Баланс установлен: **{int(new_balance)}{self.get_currency_symbol(user_data)}**.", parse_mode='Markdown')
                await self.bank_command(update, context)
                return
            except ValueError:
                await update.message.reply_text("🚫 Некорректный ввод. Пожалуйста, введите числовое значение для баланса (например, 10000).")
                return

        # 2. Обработка промокодов (если это не пошаговый ввод)
        if text.upper() == PROMO_CODE:
            # (Логика активации промокода)
            await update.message.reply_text("✅ Промокод успешно активирован!")
        
        # ... (Другие обработчики текста)


    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles all inline keyboard button presses."""
        query = update.callback_query
        data = query.data
        user_id = update.effective_user.id
        
        if data.startswith('set_lang_'):
            lang_code = data.split('_')[-1]
            self.update_user_field(user_id, 'language', lang_code)
            await query.answer(self.get_translation(self.get_user_data(user_id), 'language_selected'))
            await self.start_command(update, context)
        elif data == 'cmd_start': await self.start_command(update, context)
        elif data == 'cmd_plans': await self.plans_command(update, context)
        elif data == 'cmd_short': await self.short_command(update, context)
        elif data == 'cmd_long': await self.long_command(update, context)
        elif data == 'cmd_bank': await self.bank_command(update, context)
        elif data == 'cmd_autotrade': await self.autotrade_command(update, context)
        elif data == 'cmd_settings': await self.settings_command(update, context)
        elif data == 'cmd_my_stats': await self.my_stats_command(update, context)

        elif data.startswith('get_signal_'): 
            if data == 'get_signal_short': await self.get_signal_short(update, context)
            elif data == 'get_signal_long': await self.get_signal_long(update, context)

        elif data.startswith('buy_'): await self.handle_purchase(update, context)

        elif data == 'bank_set_balance': 
            self.user_states[user_id] = 'SET_BALANCE'
            await query.edit_message_text("Введите ваш **текущий баланс** (числом):", parse_mode='Markdown')

        else:
            await query.answer(f"Обработчик для '{data}' не реализован.")


    # --- UTILITIES ---
    async def _send_or_edit_message(self, update: Update, text: str, reply_markup=None, parse_mode='HTML') -> None:
        """Helper to send a new message or edit the existing one based on context."""
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            except Exception: # Catch MessageNotModified
                await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            
    async def _send_photo_or_edit_message(self, update: Update, text: str, photo_buffer: io.BytesIO, caption: str, reply_markup=None, parse_mode='HTML'):
        """Helper to send a photo with a caption."""
        if update.callback_query:
            # При наличии callback_query, сначала редактируем текст, затем отправляем фото
            try:
                await update.callback_query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            except Exception:
                await update.callback_query.message.reply_photo(photo=photo_buffer, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await update.message.reply_photo(photo=photo_buffer, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error and send a message to the admin."""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_user:
            error_message = (
                f"🚨 **ОШИБКА В БОТЕ** 🚨\n\n"
                f"Пользователь: @{update.effective_user.username} ({update.effective_user.id})\n"
                f"Ошибка: `{context.error}`"
            )
            if self.is_admin(ADMIN_USER_ID):
                 try:
                    await context.bot.send_message(chat_id=ADMIN_USER_ID, text=error_message, parse_mode='Markdown')
                 except Exception: pass

    # --- SCHEDULING & SETUP ---
    async def post_init(self, application: Application) -> None:
        """Runs after the application has been initialized."""
        await self.set_bot_commands(application)
        logger.info("✅ Bot post_init tasks completed.")

    async def set_bot_commands(self, application: Application):
        """Sets the list of commands visible in the Telegram menu."""
        commands = [BotCommand(command, description) for command, description in DEFAULT_BOT_COMMANDS]
        await application.bot.set_my_commands(commands)
        logger.info("✅ Bot commands set successfully.")

# --- MAIN EXECUTION ---
def main() -> None:
    """Starts the bot."""
    # 1. Создание и запуск HTTP-сервера для YooKassa (в отдельном потоке)
    from yookassa_server import start_yookassa_webhook_server
    import threading
    
    # Создаем объект приложения Telegram
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_instance = CryptoSignalsBot(application)

    # Запускаем HTTP-сервер в отдельном потоке. 
    # ВАЖНО: Flask запускается на порту 5000. Убедитесь, что этот порт доступен.
    threading.Thread(target=start_yookassa_webhook_server, args=(bot_instance, ), daemon=True).start()
    logger.info("✅ YooKassa Webhook Server (Flask) starting on port 5000...")


    # 2. Добавление всех обработчиков
    application.add_handler(CommandHandler("start", bot_instance.start_command))
    application.add_handler(CommandHandler("plans", bot_instance.plans_command))
    application.add_handler(CommandHandler("short", bot_instance.short_command))
    application.add_handler(CommandHandler("long", bot_instance.long_command))
    application.add_handler(CommandHandler("bank", bot_instance.bank_command))
    application.add_handler(CommandHandler("autotrade", bot_instance.autotrade_command))
    application.add_handler(CommandHandler("settings", bot_instance.settings_command))
    application.add_handler(CommandHandler("my_stats", bot_instance.my_stats_command))
    # Admin commands
    application.add_handler(CommandHandler("notify_all", bot_instance.notify_all_command))
    
    # Message and Callback Handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_text_message))
    application.add_handler(CallbackQueryHandler(bot_instance.button_callback))
    application.add_error_handler(bot_instance.error_handler)
    
    # Установка post_init
    application.post_init = bot_instance.post_init

    logger.info("🚀 Bot started successfully!")
    print("✅ Crypto Signals Bot is running...")
    
    # 3. Запуск Polling для Telegram
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()