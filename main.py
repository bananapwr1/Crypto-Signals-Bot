import os
import logging
import asyncio
import requests
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import warnings

warnings.filterwarnings('ignore')
load_dotenv()

# ===== КОНФИГУРАЦИЯ =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "7746862973"))
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@banana_pwr")
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

# Проверка переменных
if not all([BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    raise Exception("❌ Missing required environment variables")

MOSCOW_TZ = timedelta(hours=3)
POCKET_OPTION_REF_LINK = "https://pocket-friends.com/r/ugauihalod"
PROMO_CODE = "FRIENDUGAUIHALOD"

# ===== СТРУКТУРА ДАННЫХ =====
DEFAULT_BOT_COMMANDS = [
    ("start", "🏠 Главное меню"),
    ("help", "❓ Помощь и инструкции"), 
    ("short", "⚡ SHORT сигнал (1-5 мин)"),
    ("long", "🔵 LONG сигнал (1-4 часа)"),
    ("bank", "💰 Управление банком"),
    ("my_longs", "📋 Мои LONG позиции"),
    ("my_stats", "📊 Моя статистика"),
    ("plans", "💎 Тарифы и подписки"),
    ("settings", "⚙️ Настройки"),
    ("god", "👑 God Mode"),
    ("admin", "🛠️ Admin Panel")
]

SUBSCRIPTION_PLANS = {
    'none': {
        'name': 'БЕСПЛАТНЫЙ',
        'emoji': '🆓',
        'price': 0,
        'features': ['🔸 3 сигнала в день', '🔸 Базовые функции'],
        'restrictions': ['❌ Без автоторговли', '❌ Ограниченные сигналы']
    },
    'short': {
        'name': 'SHORT',
        'emoji': '🟧',
        'price': 4990,
        'features': ['✅ Неограниченные SHORT сигналы', '✅ Мартингейл стратегия'],
        'restrictions': ['❌ LONG сигналы ограничены']
    },
    'long': {
        'name': 'LONG', 
        'emoji': '📈',
        'price': 4990,
        'features': ['✅ Неограниченные LONG сигналы', '✅ Процентная стратегия 2.5%'],
        'restrictions': ['❌ SHORT сигналы ограничены']
    },
    'vip': {
        'name': 'VIP',
        'emoji': '👑',
        'price': 9990,
        'features': ['✅ Все сигналы', '✅ Автоторговля', '✅ Расширенные настройки'],
        'restrictions': []
    }
}

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== SUPABASE ФУНКЦИИ =====
class SupabaseManager:
    def __init__(self):
        self.url = SUPABASE_URL
        self.key = SUPABASE_KEY
        self.headers = {
            'apikey': self.key,
            'Authorization': f'Bearer {self.key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        }

    def request(self, table, method='GET', data=None, filters=None):
        """Универсальный запрос к Supabase"""
        url = f"{self.url}/rest/v1/{table}"
        if filters:
            url += f"?{filters}"
        
        try:
            if method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method == 'GET':
                response = requests.get(url, headers=self.headers)
            elif method == 'PATCH':
                response = requests.patch(url, headers=self.headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers)
            
            if response.status_code in [200, 201, 204]:
                return response.json() if response.content else {'status': 'success'}
            return None
        except Exception as e:
            logger.error(f"Supabase error: {e}")
            return None

    # Пользователи
    async def get_user(self, user_id):
        user = self.request('users', filters=f'telegram_id=eq.{user_id}')
        return user[0] if user and len(user) > 0 else None

    async def create_user(self, user_id, username):
        user_data = {
            'telegram_id': user_id,
            'username': username or 'Unknown',
            'subscription_type': 'none',
            'created_at': datetime.now().isoformat()
        }
        return self.request('users', 'POST', user_data)

    async def update_user(self, user_id, data):
        return self.request('users', 'PATCH', data, filters=f'telegram_id=eq.{user_id}')

    # Команды
    async def save_command(self, user_id, command, details=None):
        command_data = {
            'user_id': user_id,
            'command': command,
            'details': json.dumps(details) if details else None,
            'processed': False,
            'created_at': datetime.now().isoformat()
        }
        return self.request('user_commands', 'POST', command_data)

    async def get_user_commands(self, user_id, limit=10):
        return self.request('user_commands', filters=f'user_id=eq.{user_id}&order=created_at.desc&limit={limit}')

    # Статус и статистика
    async def get_bot_status(self, user_id):
        status = self.request('bot_status', filters=f'user_id=eq.{user_id}')
        return status[0] if status and len(status) > 0 else None

    async def update_bot_status(self, user_id, data):
        existing = await self.get_bot_status(user_id)
        if existing:
            return self.request('bot_status', 'PATCH', data, filters=f'user_id=eq.{user_id}')
        else:
            data['user_id'] = user_id
            data['created_at'] = datetime.now().isoformat()
            return self.request('bot_status', 'POST', data)

    # Сделки
    async def get_user_trades(self, user_id, limit=20):
        return self.request('trades', filters=f'user_id=eq.{user_id}&order=created_at.desc&limit={limit}')

    async def save_trade(self, trade_data):
        return self.request('trades', 'POST', trade_data)

    # Админ-функции
    async def get_all_users(self):
        return self.request('users')

    async def get_all_trades(self, limit=100):
        return self.request('trades', filters=f'order=created_at.desc&limit={limit}')

    async def get_system_stats(self):
        users = await self.get_all_users()
        trades = await self.get_all_trades(1000)
        
        stats = {
            'total_users': len(users) if users else 0,
            'total_trades': len(trades) if trades else 0,
            'active_today': 0,
            'total_profit': 0
        }
        
        if trades:
            today = datetime.now().date()
            stats['active_today'] = len([t for t in trades if datetime.fromisoformat(t['created_at']).date() == today])
            stats['total_profit'] = sum(t.get('profit_loss', 0) for t in trades)
            
        return stats

# Инициализация менеджера базы
db = SupabaseManager()

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ =====
async def ensure_user(user_id, username):
    """Создание/проверка пользователя"""
    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, username)
    return user

async def get_user_subscription(user_id):
    """Получение подписки пользователя"""
    user = await db.get_user(user_id)
    return user.get('subscription_type', 'none') if user else 'none'

async def can_user_use_signal(user_id, signal_type):
    """Проверка лимитов сигналов"""
    user = await db.get_user(user_id)
    if not user:
        return False
        
    subscription = user.get('subscription_type', 'none')
    
    # VIP могут всё
    if subscription == 'vip':
        return True
        
    # Бесплатные: 3 сигнала в день
    if subscription == 'none':
        today = datetime.now().strftime('%Y-%m-%d')
        last_signal_date = user.get('last_signal_date', '')
        signals_today = user.get('signals_today', 0)
        
        if last_signal_date != today:
            # Новый день - сбрасываем счетчик
            await db.update_user(user_id, {'signals_today': 1, 'last_signal_date': today})
            return True
        else:
            if signals_today < 3:
                await db.update_user(user_id, {'signals_today': signals_today + 1})
                return True
            return False
    
    # Платные подписки
    if subscription == 'short' and signal_type == 'short':
        return True
    if subscription == 'long' and signal_type == 'long':
        return True
        
    return False

# ===== УМНОЕ МЕНЮ =====
def create_main_menu(user_id, subscription):
    """Создание умного меню по подписке"""
    keyboard = []
    sub_info = SUBSCRIPTION_PLANS.get(subscription, SUBSCRIPTION_PLANS['none'])
    
    # Первый ряд: сигналы
    if subscription in ['short', 'vip']:
        short_btn = InlineKeyboardButton("⚡ SHORT сигнал", callback_data='get_short')
    else:
        short_btn = InlineKeyboardButton("⚡ SHORT (🔒)", callback_data='upgrade_short')
    
    if subscription in ['long', 'vip']:
        long_btn = InlineKeyboardButton("🔵 LONG сигнал", callback_data='get_long')
    else:
        long_btn = InlineKeyboardButton("🔵 LONG (🔒)", callback_data='upgrade_long')
    
    keyboard.append([short_btn, long_btn])
    
    # Второй ряд: банк и статистика
    keyboard.append([
        InlineKeyboardButton("💰 Управление банком", callback_data='bank'),
        InlineKeyboardButton("📊 Моя статистика", callback_data='my_stats')
    ])
    
    # Третий ряд: сделки и автоторговля
    if subscription == 'vip':
        auto_btn = InlineKeyboardButton("🤖 Автоторговля", callback_data='autotrade')
    else:
        auto_btn = InlineKeyboardButton("🤖 Автоторговля (🔒)", callback_data='upgrade_vip')
    
    keyboard.append([
        InlineKeyboardButton("📋 Мои сделки", callback_data='my_trades'),
        auto_btn
    ])
    
    # Четвертый ряд: настройки и тарифы
    keyboard.append([
        InlineKeyboardButton("💎 Тарифы", callback_data='plans'),
        InlineKeyboardButton("⚙️ Настройки", callback_data='settings')
    ])
    
    # Пятый ряд: помощь
    keyboard.append([InlineKeyboardButton("❓ Помощь", callback_data='help')])
    
    # Админ-кнопки
    if user_id == ADMIN_USER_ID:
        keyboard.append([
            InlineKeyboardButton("👑 God Mode", callback_data='god_mode'),
            InlineKeyboardButton("🛠️ Admin Panel", callback_data='admin_panel')
        ])
    
    return InlineKeyboardMarkup(keyboard), sub_info

# ===== ОСНОВНЫЕ КОМАНДЫ =====
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🏠 Главное меню"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    await ensure_user(user_id, username)
    subscription = await get_user_subscription(user_id)
    
    keyboard, sub_info = create_main_menu(user_id, subscription)
    
    message = (
        f"🏠 *Главное меню*\n\n"
        f"🤖 Добро пожаловать в Crypto Signals Bot!\n\n"
        f"📋 *Ваш тариф:* {sub_info['emoji']} {sub_info['name']}\n\n"
    )
    
    # Особенности тарифа
    if sub_info.get('features'):
        message += "*✅ Доступно:*\n"
        for feature in sub_info['features']:
            message += f"• {feature}\n"
        message += "\n"
    
    # Ограничения
    if sub_info.get('restrictions'):
        message += "*❌ Ограничения:*\n"
        for restriction in sub_info['restrictions']:
            message += f"• {restriction}\n"
        message += "\n"
    
    message += "Выберите действие:"
    
    await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """❓ Помощь"""
    user_id = update.effective_user.id
    subscription = await get_user_subscription(user_id)
    sub_info = SUBSCRIPTION_PLANS.get(subscription, SUBSCRIPTION_PLANS['none'])
    
    keyboard = [[InlineKeyboardButton("🔙 Назад в меню", callback_data='start')]]
    
    message = (
        f"❓ *Помощь и инструкции*\n\n"
        f"📞 *Поддержка:* {SUPPORT_CONTACT}\n\n"
        f"🔗 *Регистрация:* {POCKET_OPTION_REF_LINK}\n"
        f"🎁 *Промокод:* {PROMO_CODE}\n\n"
        f"*📚 Как пользоваться:*\n"
        f"1. Выберите тариф (/plans)\n"
        f"2. Получайте сигналы (/short /long)\n"
        f"3. Следите за статистикой (/my_stats)\n"
        f"4. Для VIP: настройте автоторговлю\n\n"
        f"*⚡ SHORT сигналы:* 1-5 минут\n"
        f"*🔵 LONG сигналы:* 1-4 часа\n"
        f"*🤖 Автоторговля:* только для VIP\n\n"
        f"*📋 Ваш тариф:* {sub_info['emoji']} {sub_info['name']}"
    )
    
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def short_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚡ SHORT сигнал"""
    user_id = update.effective_user.id
    
    if not await can_user_use_signal(user_id, 'short'):
        keyboard = [
            [InlineKeyboardButton("💎 Обновить тариф", callback_data='plans')],
            [InlineKeyboardButton("🔙 Назад", callback_data='start')]
        ]
        await update.message.reply_text(
            "❌ *Лимит исчерпан или недоступно*\n\n"
            "⚡ SHORT сигналы:\n"
            "• Бесплатно: 3 сигнала в день\n"
            "• SHORT тариф: неограниченно\n"
            "• VIP: все сигналы\n\n"
            "Обновите тариф:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
    
    # Отправляем команду в ядро
    success = await db.save_command(user_id, 'get_short_signal')
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='start')]]
    
    if success:
        await update.message.reply_text(
            "⚡ *SHORT сигнал запрошен*\n\n"
            "Сигнал отправлен в торговое ядро...\n"
            "Ожидайте уведомления в ближайшие секунды!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ *Ошибка отправки команды*\n\n"
            "Попробуйте позже или обратитесь в поддержку",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def long_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔵 LONG сигнал"""
    user_id = update.effective_user.id
    
    if not await can_user_use_signal(user_id, 'long'):
        keyboard = [
            [InlineKeyboardButton("💎 Обновить тариф", callback_data='plans')],
            [InlineKeyboardButton("🔙 Назад", callback_data='start')]
        ]
        await update.message.reply_text(
            "❌ *Лимит исчерпан или недоступно*\n\n"
            "🔵 LONG сигналы:\n"
            "• Бесплатно: 3 сигнала в день\n"
            "• LONG тариф: неограниченно\n"
            "• VIP: все сигналы\n\n"
            "Обновите тариф:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
    
    success = await db.save_command(user_id, 'get_long_signal')
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='start')]]
    
    if success:
        await update.message.reply_text(
            "🔵 *LONG сигнал запрошен*\n\n"
            "Сигнал отправлен в торговое ядро...\n"
            "Ожидайте уведомления!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ *Ошибка отправки команды*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💰 Управление банком"""
    user_id = update.effective_user.id
    status = await db.get_bot_status(user_id)
    
    keyboard = [
        [InlineKeyboardButton("💳 Пополнить", callback_data='deposit')],
        [InlineKeyboardButton("📤 Вывести", callback_data='withdraw')],
        [InlineKeyboardButton("🔄 Обновить", callback_data='bank')],
        [InlineKeyboardButton("🔙 Назад", callback_data='start')]
    ]
    
    if status:
        message = (
            f"💰 *Управление банком*\n\n"
            f"• Баланс: *{status.get('balance', 0)}₽*\n"
            f"• Профит сегодня: *{status.get('daily_profit', 0)}₽*\n"
            f"• Сделок сегодня: *{status.get('trades_today', 0)}*\n"
            f"• Винрейт: *{status.get('win_rate', 0)}%*\n"
            f"• Статус: {'🟢 Активен' if status.get('is_active') else '🔴 Не активен'}"
        )
    else:
        message = "💰 *Управление банком*\n\nСтатистика пока недоступна"
    
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def my_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📊 Моя статистика"""
    user_id = update.effective_user.id
    trades = await db.get_user_trades(user_id, 50)
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data='my_stats')],
        [InlineKeyboardButton("🔙 Назад", callback_data='start')]
    ]
    
    if trades:
        total = len(trades)
        wins = len([t for t in trades if t.get('result') == 'win'])
        losses = len([t for t in trades if t.get('result') == 'loss'])
        win_rate = (wins / total * 100) if total > 0 else 0
        total_profit = sum(t.get('profit_loss', 0) for t in trades)
        
        message = (
            f"📊 *Моя статистика*\n\n"
            f"• Всего сделок: *{total}*\n"
            f"• Успешных: *{wins}*\n"
            f"• Неудачных: *{losses}*\n"
            f"• Винрейт: *{win_rate:.1f}%*\n"
            f"• Общий профит: *{total_profit:.2f}₽*\n\n"
            f"📈 *Последние сделки:*\n"
        )
        
        for trade in trades[:5]:
            asset = trade.get('asset', 'N/A')
            result = trade.get('result', 'pending')
            profit = trade.get('profit_loss', 0)
            emoji = "🟢" if result == 'win' else "🔴" if result == 'loss' else "🟡"
            message += f"{emoji} {asset} - {profit}₽\n"
    else:
        message = "📊 *Моя статистика*\n\nСделок пока нет"
    
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💎 Тарифы"""
    user_id = update.effective_user.id
    current_sub = await get_user_subscription(user_id)
    current_info = SUBSCRIPTION_PLANS.get(current_sub, SUBSCRIPTION_PLANS['none'])
    
    keyboard = [
        [InlineKeyboardButton("🟧 SHORT тариф", callback_data='buy_short')],
        [InlineKeyboardButton("🔵 LONG тариф", callback_data='buy_long')],
        [InlineKeyboardButton("👑 VIP тариф", callback_data='buy_vip')],
        [InlineKeyboardButton("🔙 Назад", callback_data='start')]
    ]
    
    message = (
        f"💎 *Тарифные планы*\n\n"
        f"🟧 *SHORT* - {SUBSCRIPTION_PLANS['short']['price']}₽/мес\n"
        f"⚡ Неограниченные SHORT сигналы\n"
        f"🎯 Мартингейл стратегия\n\n"
        f"🔵 *LONG* - {SUBSCRIPTION_PLANS['long']['price']}₽/мес\n"
        f"📈 Неограниченные LONG сигналы\n"
        f"💵 Процентная стратегия\n\n"
        f"👑 *VIP* - {SUBSCRIPTION_PLANS['vip']['price']}₽/мес\n"
        f"🤖 Все сигналы + автоторговля\n"
        f"⚙️ Расширенные настройки\n\n"
        f"*Ваш тариф:* {current_info['emoji']} {current_info['name']}"
    )
    
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚙️ Настройки"""
    user_id = update.effective_user.id
    subscription = await get_user_subscription(user_id)
    
    keyboard = [
        [InlineKeyboardButton("💰 Настройки ставок", callback_data='stake_settings')],
        [InlineKeyboardButton("📊 Настройки уведомлений", callback_data='notification_settings')],
    ]
    
    if subscription == 'vip':
        keyboard.append([InlineKeyboardButton("🤖 Настройки автоторговли", callback_data='autotrade_settings')])
    
    keyboard.extend([
        [InlineKeyboardButton("🔧 Расширенные настройки", callback_data='advanced_settings')],
        [InlineKeyboardButton("🔙 Назад", callback_data='start')]
    ])
    
    message = (
        "⚙️ *Настройки*\n\n"
        "Настройте параметры бота:\n\n"
        "• 💰 *Ставки* - размеры ставок\n"
        "• 📊 *Уведомления* - оповещения\n"
    )
    
    if subscription == 'vip':
        message += "• 🤖 *Автоторговля* - настройки Pocket Option\n"
    
    message += "• 🔧 *Расширенные* - дополнительные параметры"
    
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ===== АДМИН-ПАНЕЛЬ =====
async def god_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """👑 God Mode"""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Доступно только в God Mode")
        return
    
    keyboard = [
        [InlineKeyboardButton("🌐 Статус системы", callback_data='system_status')],
        [InlineKeyboardButton("📊 Полная статистика", callback_data='full_stats')],
        [InlineKeyboardButton("🔧 Управление ботом", callback_data='bot_control')],
        [InlineKeyboardButton("⚡ Экстренные действия", callback_data='emergency_actions')],
        [InlineKeyboardButton("🔙 Назад", callback_data='start')]
    ]
    
    message = (
        "👑 *God Mode*\n\n"
        "Полный контроль над системой:\n\n"
        "• 🌐 Статус системы и серверов\n"
        "• 📊 Детальная статистика\n"
        "• 🔧 Управление работой бота\n"
        "• ⚡ Экстренные действия"
    )
    
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🛠️ Admin Panel"""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Доступно только администраторам")
        return
    
    stats = await db.get_system_stats()
    
    keyboard = [
        [InlineKeyboardButton("👥 Управление пользователями", callback_data='user_management')],
        [InlineKeyboardButton("📈 Статистика системы", callback_data='system_stats')],
        [InlineKeyboardButton("🔔 Рассылка сообщений", callback_data='broadcast')],
        [InlineKeyboardButton("⚙️ Настройки системы", callback_data='system_settings')],
        [InlineKeyboardButton("🔙 Назад", callback_data='start')]
    ]
    
    message = (
        f"🛠️ *Admin Panel*\n\n"
        f"📊 *Статистика системы:*\n"
        f"• Пользователей: {stats['total_users']}\n"
        f"• Сделок всего: {stats['total_trades']}\n"
        f"• Активных сегодня: {stats['active_today']}\n"
        f"• Общий профит: {stats['total_profit']:.2f}₽\n"
        f"• Админ ID: {ADMIN_USER_ID}\n\n"
        f"🛠️ *Инструменты администрирования:*"
    )
    
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ===== ОБРАБОТЧИК КНОПОК =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # Основные команды меню
    if data == 'start':
        await start_command(query, context)
    elif data == 'help':
        await help_command(query, context)
    elif data == 'bank':
        await bank_command(query, context)
    elif data == 'my_stats':
        await my_stats_command(query, context)
    elif data == 'plans':
        await plans_command(query, context)
    elif data == 'settings':
        await settings_command(query, context)
    elif data == 'god_mode':
        await god_command(query, context)
    elif data == 'admin_panel':
        await admin_command(query, context)
    
    # Сигналы
    elif data == 'get_short':
        await short_command(query, context)
    elif data == 'get_long':
        await long_command(query, context)
    
    # Апгрейд тарифов
    elif data.startswith('upgrade_'):
        plan = data.replace('upgrade_', '')
        plan_info = SUBSCRIPTION_PLANS.get(plan, {})
        
        keyboard = [
            [InlineKeyboardButton(f"💎 Купить {plan_info.get('name', '')}", callback_data=f'buy_{plan}')],
            [InlineKeyboardButton("🔙 Назад", callback_data='plans')]
        ]
        
        await query.edit_message_text(
            f"💎 *Обновление до {plan_info.get('name', '')}*\n\n"
            f"Стоимость: {plan_info.get('price', 0)}₽/месяц\n\n"
            f"*Преимущества:*\n" + "\n".join([f"• {f}" for f in plan_info.get('features', [])]) + "\n\n"
            f"Для покупки свяжитесь с поддержкой: {SUPPORT_CONTACT}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # Покупка подписок
    elif data.startswith('buy_'):
        plan = data.replace('buy_', '')
        success = await db.save_command(user_id, 'buy_subscription', {'plan': plan})
        
        if success:
            await query.edit_message_text(
                f"💎 *Запрос на подписку {plan.upper()}*\n\n"
                f"✅ Запрос отправлен в систему\n"
                f"📞 С вами свяжется менеджер для оформления оплаты\n\n"
                f"Свяжитесь с поддержкой: {SUPPORT_CONTACT}",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Ошибка оформления заявки")
    
    # Просмотр сделок
    elif data == 'my_trades':
        trades = await db.get_user_trades(user_id, 10)
        
        if trades:
            message = "📋 *Последние сделки:*\n\n"
            for trade in trades:
                asset = trade.get('asset', 'N/A')
                action = trade.get('action', 'N/A')
                result = trade.get('result', 'pending')
                profit = trade.get('profit_loss', 0)
                emoji = "🟢" if result == 'win' else "🔴" if result == 'loss' else "🟡"
                message += f"{emoji} {asset} {action} - {profit}₽\n"
        else:
            message = "📋 *Мои сделки*\n\nСделок пока нет"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data='my_trades')],
            [InlineKeyboardButton("🔙 Назад", callback_data='start')]
        ]
        
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    # Автоторговля
    elif data == 'autotrade':
        subscription = await get_user_subscription(user_id)
        if subscription != 'vip':
            await query.edit_message_text(
                "❌ *Премиум функция*\n\n"
                "🤖 Автоторговля доступна только для тарифа VIP\n\n"
                "Обновите тариф для доступа:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💎 Обновить до VIP", callback_data='buy_vip')],
                    [InlineKeyboardButton("🔙 Назад", callback_data='start')]
                ]),
                parse_mode='Markdown'
            )
            return
        
        keyboard = [
            [InlineKeyboardButton("🚀 Запустить автоторговлю", callback_data='start_autotrade')],
            [InlineKeyboardButton("🛑 Остановить автоторговлю", callback_data='stop_autotrade')],
            [InlineKeyboardButton("⚙️ Настройки автоторговли", callback_data='autotrade_settings')],
            [InlineKeyboardButton("🔙 Назад", callback_data='start')]
        ]
        
        await query.edit_message_text(
            "🤖 *Автоторговля*\n\n"
            "Автоматическая торговля на основе сигналов:\n\n"
            "• 🤖 Полностью автоматическая работа\n"
            "• ⚡ Мгновенное исполнение сигналов\n"
            "• 📊 Автоматическое управление рисками\n"
            "• 💰 Оптимизация размера ставок\n\n"
            "Для настройки укажите логин и пароль от Pocket Option",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # Запуск/остановка автоторговли
    elif data in ['start_autotrade', 'stop_autotrade']:
        action = 'start' if data == 'start_autotrade' else 'stop'
        success = await db.save_command(user_id, f'{action}_autotrade')
        
        if success:
            status = "запущена" if action == 'start' else "остановлена"
            await query.edit_message_text(f"✅ Автоторговля {status}", parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ Ошибка команды", parse_mode='Markdown')
    
    # Настройки автоторговли
    elif data == 'autotrade_settings':
        await query.edit_message_text(
            "⚙️ *Настройки автоторговли*\n\n"
            "Для настройки автоторговли необходимо:\n\n"
            "1. Указать логин от Pocket Option\n"
            "2. Указать пароль от аккаунта\n"
            "3. Выбрать режим (демо/реальный)\n\n"
            "Отправьте логин в формате:\n"
            "`/set_login ваш_логин`\n\n"
            "Отправьте пароль в формате:\n"
            "`/set_password ваш_пароль`\n\n"
            "Режим работы:\n"
            "`/set_mode demo` - демо-режим\n"
            "`/set_mode real` - реальный режим",
            parse_mode='Markdown'
        )
    
    # Админ-функции
    elif data == 'system_stats':
        if user_id != ADMIN_USER_ID:
            return
        
        stats = await db.get_system_stats()
        users = await db.get_all_users()
        
        # Статистика по тарифам
        tariff_stats = {}
        for user in users:
            tariff = user.get('subscription_type', 'none')
            tariff_stats[tariff] = tariff_stats.get(tariff, 0) + 1
        
        message = f"📈 *Статистика системы*\n\n"
        message += f"👥 Пользователей: {stats['total_users']}\n"
        message += f"💼 Сделок всего: {stats['total_trades']}\n"
        message += f"📊 Активных сегодня: {stats['active_today']}\n"
        message += f"💰 Общий профит: {stats['total_profit']:.2f}₽\n\n"
        message += "*Распределение по тарифам:*\n"
        
        for tariff, count in tariff_stats.items():
            tariff_info = SUBSCRIPTION_PLANS.get(tariff, SUBSCRIPTION_PLANS['none'])
            message += f"• {tariff_info['emoji']} {tariff_info['name']}: {count}\n"
        
        await query.edit_message_text(message, parse_mode='Markdown')

# ===== ОБРАБОТЧИКИ СООБЩЕНИЙ =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Обработка команд настройки автоторговли
    if text.startswith('/set_login'):
        login = text.replace('/set_login', '').strip()
        if login:
            await db.update_user(user_id, {'pocket_option_email': login})
            await update.message.reply_text(f"✅ Логин сохранен: {login}")
    
    elif text.startswith('/set_password'):
        password = text.replace('/set_password', '').strip()
        if password:
            await db.update_user(user_id, {'pocket_option_password': password})
            await update.message.reply_text("✅ Пароль сохранен")
    
    elif text.startswith('/set_mode'):
        mode = text.replace('/set_mode', '').strip()
        if mode in ['demo', 'real']:
            await db.update_user(user_id, {'auto_trading_mode': mode})
            await update.message.reply_text(f"✅ Режим установлен: {mode}")
    
    else:
        await update.message.reply_text(
            "🤖 Для работы с ботом используйте команды из меню\n"
            "Нажмите /start для открытия главного меню"
        )

# ===== ЗАПУСК БОТА =====
async def post_init(application):
    """Установка команд бота"""
    await application.bot.set_my_commands([
        BotCommand(command, description) for command, description in DEFAULT_BOT_COMMANDS
    ])

def main():
    """Запуск бота"""
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("short", short_command))
    application.add_handler(CommandHandler("long", long_command))
    application.add_handler(CommandHandler("bank", bank_command))
    application.add_handler(CommandHandler("my_longs", my_stats_command))  # Алиас
    application.add_handler(CommandHandler("my_stats", my_stats_command))
    application.add_handler(CommandHandler("plans", plans_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("God", god_command))
    application.add_handler(CommandHandler("Admin", admin_command))
    
    # Обработчики кнопок и сообщений
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🚀 Бот запущен с полным функционалом")
    print("✅ Crypto Signals Bot запущен!")
    print(f"👑 Admin ID: {ADMIN_USER_ID}")
    print(f"📊 Команды: {[cmd[0] for cmd in DEFAULT_BOT_COMMANDS]}")
    
    application.run_polling()

if __name__ == '__main__':
    main()