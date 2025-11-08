"""
bot_interface.py - Полный Telegram интерфейс бота
Переносит всю логику интерфейса из исходника с интеграцией Supabase
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import warnings
import requests
import json

warnings.filterwarnings('ignore')
load_dotenv()

# ===== КОНФИГУРАЦИЯ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "7746862973"))
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@banana_pwr")
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

# Проверка обязательных переменных
def check_environment():
    """Проверка наличия всех необходимых переменных окружения"""
    if not all([BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
        raise Exception("Missing required environment variables: BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY")
    return True

MOSCOW_TZ = timezone(timedelta(hours=3))
POCKET_OPTION_REF_LINK = "https://pocket-friends.com/r/ugauihalod"
PROMO_CODE = "FRIENDUGAUIHALOD"

# Команды бота (must be lowercase, alphanumeric and underscores only)
DEFAULT_BOT_COMMANDS = [
    ("start", "📱 Главное меню"),
    ("help", "❓ Помощь"),
    ("plans", "💼 Тарифы и подписки"),
    ("bank", "💰 Управление банком"),
    ("autotrade", "🤖 Автоторговля"),
    ("signals", "📡 Сигналы Short/Long"),
    ("status", "📊 Статус торговли"),
]

# Тарифные планы
SUBSCRIPTION_PLANS = {
    'short': {
        '1m': 4990,
        '6m': 26946,
        '12m': 47904,
        'name': 'SHORT',
        'description': 'Быстрые сигналы (1-5 мин) с мартингейл стратегией',
        'emoji': '🟧'
    },
    'long': {
        '1m': 4990,
        '6m': 26946,
        '12m': 47904,
        'name': 'LONG',
        'description': 'Долгосрочные сигналы (1-4 часа) с процентной ставкой',
        'emoji': '📈'
    },
    'vip': {
        '1m': 9990,
        '6m': 53946,
        '12m': 95904,
        'name': 'VIP',
        'description': 'Все сигналы SHORT + LONG + аналитика + расширенные настройки и статистика',
        'emoji': '👑'
    }
}

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С SUPABASE =====

def supabase_request(table, method='GET', data=None, filters=None):
    """Универсальная функция для работы с Supabase"""
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
    }
    
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    
    if filters:
        url += f"?{filters}"
    
    try:
        if method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'PATCH':
            response = requests.patch(url, headers=headers, json=data)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        
        if response.status_code in [200, 201, 204]:
            return response.json() if response.content else {'status': 'success'}
        else:
            logger.error(f"Supabase error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Supabase request error: {e}")
        return None

async def check_or_create_user(user_id: int, username: str):
    """Создание/проверка пользователя в Supabase"""
    user_data = {
        'telegram_id': user_id,
        'username': username or 'Unknown',
        'subscription_type': 'none',
        'created_at': datetime.now().isoformat()
    }
    
    # Проверяем существующего пользователя
    existing_user = supabase_request('users', filters=f'telegram_id=eq.{user_id}')
    
    if existing_user and len(existing_user) > 0:
        # Обновляем username если изменился
        if existing_user[0].get('username') != username:
            supabase_request('users', 'PATCH', {'username': username}, filters=f'telegram_id=eq.{user_id}')
        return existing_user[0]
    else:
        # Создаем нового пользователя
        result = supabase_request('users', 'POST', user_data)
        if result:
            logger.info(f"Created new user: {user_id}")
            return user_data
        else:
            logger.error(f"Failed to create user: {user_id}")
            return None

async def save_user_command(user_id: int, command: str, asset=None, details=None):
    """Сохранение команды для торгового ядра"""
    command_data = {
        'user_id': user_id,
        'command': command,
        'asset': asset,
        'details': json.dumps(details) if details else None,
        'processed': False,
        'created_at': datetime.now().isoformat()
    }
    
    result = supabase_request('user_commands', 'POST', command_data)
    return result is not None

async def get_bot_status(user_id: int):
    """Получение статуса торговли из Supabase"""
    status_data = supabase_request('bot_status', filters=f'user_id=eq.{user_id}')
    if status_data and len(status_data) > 0:
        return status_data[0]
    return None

async def update_user_subscription(user_id: int, plan_type: str, duration: str):
    """Обновление подписки пользователя"""
    from datetime import datetime, timedelta
    
    duration_days = 30 if duration == '1m' else 180 if duration == '6m' else 365
    
    subscription_data = {
        'subscription_type': plan_type,
        'subscription_end': (datetime.now() + timedelta(days=duration_days)).isoformat(),
        'is_premium': True,
        'updated_at': datetime.now().isoformat()
    }
    
    result = supabase_request('users', 'PATCH', subscription_data, filters=f'telegram_id=eq.{user_id}')
    return result is not None

# ===== ОСНОВНЫЕ КОМАНДЫ БОТА =====

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главное меню"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Создаем/проверяем пользователя
    await check_or_create_user(user_id, username)
    
    keyboard = [
        [InlineKeyboardButton("📡 Сигналы Short", callback_data='signals_short'),
         InlineKeyboardButton("📈 Сигналы Long", callback_data='signals_long')],
        [InlineKeyboardButton("🤖 Автоторговля", callback_data='autotrade_menu'),
         InlineKeyboardButton("💼 Мои сделки", callback_data='my_deals')],
        [InlineKeyboardButton("👑 Тарифы", callback_data='plans'),
         InlineKeyboardButton("❓ Помощь", callback_data='faq')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '🤖 *Crypto Signals Bot*\n\nПривет! Я помогу тебе с торговлей на финансовых рынках.\n\nВыберите действие:',
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Тарифные планы"""
    keyboard = [
        [InlineKeyboardButton("🟧 SHORT Plan", callback_data='buy_short')],
        [InlineKeyboardButton("📈 LONG Plan", callback_data='buy_long')],
        [InlineKeyboardButton("👑 VIP Plan", callback_data='buy_vip')],
        [InlineKeyboardButton("🔙 Назад", callback_data='start')]
    ]
    
    message = (
        "👑 *Тарифные планы*\n\n"
        "🟧 *SHORT* - 4,990₽/мес\n"
        "Быстрые сигналы (1-5 мин)\n\n"
        "📈 *LONG* - 4,990₽/мес\n" 
        "Долгосрочные сигналы (1-4 часа)\n\n"
        "👑 *VIP* - 9,990₽/мес\n"
        "Все сигналы + расширенные функции"
    )
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def autotrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Автоторговля"""
    user_id = update.effective_user.id
    
    # Сохраняем команду для ядра
    success = await save_user_command(user_id, 'start_autotrade')
    
    if success:
        await update.message.reply_text(
            "✅ *Автоторговля запускается*\n\n"
            "Команда передана торговому ядру. Ожидайте начала торговли...",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Ошибка запуска автоторговли")

async def signals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сигналы"""
    keyboard = [
        [InlineKeyboardButton("🟧 Short сигналы", callback_data='signals_short'),
         InlineKeyboardButton("📈 Long сигналы", callback_data='signals_long')],
        [InlineKeyboardButton("🔙 Назад", callback_data='start')]
    ]
    
    await update.message.reply_text(
        "📡 *Сигналы для торговли*\n\n"
        "Выберите тип сигналов:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Управление банком"""
    user_id = update.effective_user.id
    
    # Получаем статус из базы
    status_info = await get_bot_status(user_id)
    
    if status_info:
        balance = status_info.get('balance', 0)
        profit = status_info.get('daily_profit', 0)
        
        message = (
            f"💰 *Управление банком*\n\n"
            f"• Текущий баланс: *{balance}₽*\n"
            f"• Профит сегодня: *{profit}₽*\n"
            f"• Статус: {'🟢 Активен' if status_info.get('is_active') else '🔴 Не активен'}"
        )
    else:
        message = "💰 *Управление банком*\n\nТорговля еще не запущена"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def faq_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Помощь"""
    message = (
        "❓ *Помощь и поддержка*\n\n"
        "📞 Техническая поддержка: @banana_pwr\n\n"
        "🔗 Регистрация в Pocket Option:\n"
        "https://pocket-friends.com/r/ugauihalod\n\n"
        "🎁 Промокод: FRIENDUGAUIHALOD\n\n"
        "Часто задаваемые вопросы:\n"
        "• Как начать торговлю? - Выберите тариф и начните получать сигналы\n"
        "• Как работает автоторговля? - Бот автоматически исполняет сигналы\n"
        "• Нужен ли мне аккаунт Pocket Option? - Да, для автоторговли"
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Статус торговли"""
    user_id = update.effective_user.id
    
    status_info = await get_bot_status(user_id)
    
    if status_info:
        message = (
            f"📊 *Статус торговли*\n\n"
            f"• Активность: {'🟢 ВКЛ' if status_info.get('is_active') else '🔴 ВЫКЛ'}\n"
            f"• Сделок сегодня: {status_info.get('trades_today', 0)}\n"
            f"• Профит: {status_info.get('daily_profit', 0)}₽\n"
            f"• Баланс: {status_info.get('balance', 0)}₽\n"
            f"• Винрейт: {status_info.get('win_rate', 0)}%"
        )
    else:
        message = "📊 *Статус*\n\nТорговля еще не запущена"
    
    await update.message.reply_text(message, parse_mode='Markdown')

# ===== ОБРАБОТЧИКИ КНОПОК =====

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == 'start':
        # Воссоздаем главное меню
        keyboard = [
            [InlineKeyboardButton("📡 Сигналы Short", callback_data='signals_short'),
             InlineKeyboardButton("📈 Сигналы Long", callback_data='signals_long')],
            [InlineKeyboardButton("🤖 Автоторговля", callback_data='autotrade_menu'),
             InlineKeyboardButton("💼 Мои сделки", callback_data='my_deals')],
            [InlineKeyboardButton("👑 Тарифы", callback_data='plans'),
             InlineKeyboardButton("❓ Помощь", callback_data='faq')]
        ]
        await query.edit_message_text(
            '🤖 *Crypto Signals Bot*\n\nВыберите действие:',
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
        
    elif data == 'status':
        status_info = await get_bot_status(user_id)
        if status_info:
            message = (
                f"📊 *Статус торговли*\n\n"
                f"• Активность: {'🟢 ВКЛ' if status_info.get('is_active') else '🔴 ВЫКЛ'}\n"
                f"• Сделок сегодня: {status_info.get('trades_today', 0)}\n"
                f"• Профит: {status_info.get('daily_profit', 0)}₽"
            )
        else:
            message = "📊 *Статус*\n\nТорговля еще не запущена"
        await query.edit_message_text(message, parse_mode='Markdown')
        return
        
    elif data == 'autotrade_menu':
        # Показываем меню автоторговли
        keyboard = [
            [InlineKeyboardButton("🚀 Запустить автоторговлю", callback_data='start_autotrade')],
            [InlineKeyboardButton("🛑 Остановить автоторговлю", callback_data='stop_autotrade')],
            [InlineKeyboardButton("⚙️ Настройки", callback_data='autotrade_settings')],
            [InlineKeyboardButton("🔙 Назад", callback_data='start')]
        ]
        await query.edit_message_text(
            "🤖 *Автоторговля*\n\nУправление автоматической торговлей:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
        
    elif data == 'start_autotrade':
        success = await save_user_command(user_id, 'start_autotrade')
        if success:
            await query.edit_message_text(
                "✅ *Автоторговля запущена*\n\n"
                "Торговое ядро получило команду и начинает работу...",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Ошибка запуска автоторговли")
        return
        
    elif data == 'stop_autotrade':
        success = await save_user_command(user_id, 'stop_autotrade')
        if success:
            await query.edit_message_text("🛑 *Автоторговля остановлена*", parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ Ошибка остановки автоторговли")
        return
        
    elif data in ['signals_short', 'signals_long']:
        signal_type = 'short' if data == 'signals_short' else 'long'
        success = await save_user_command(user_id, f'get_signals_{signal_type}')
        if success:
            await query.edit_message_text(
                f"📡 *Запрос {signal_type.upper()} сигналов*\n\n"
                "Сигналы запрошены у торгового ядра...",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Ошибка запроса сигналов")
        return
        
    elif data == 'plans':
        keyboard = [
            [InlineKeyboardButton("🟧 SHORT Plan", callback_data='buy_short')],
            [InlineKeyboardButton("📈 LONG Plan", callback_data='buy_long')],
            [InlineKeyboardButton("👑 VIP Plan", callback_data='buy_vip')],
            [InlineKeyboardButton("🔙 Назад", callback_data='start')]
        ]
        
        message = (
            "👑 *Тарифные планы*\n\n"
            "🟧 *SHORT* - 4,990₽/мес\n"
            "Быстрые сигналы (1-5 мин)\n\n"
            "📈 *LONG* - 4,990₽/мес\n" 
            "Долгосрочные сигналы (1-4 часа)\n\n"
            "👑 *VIP* - 9,990₽/мес\n"
            "Все сигналы + расширенные функции"
        )
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
        
    elif data == 'faq':
        message = (
            "❓ *Помощь и поддержка*\n\n"
            "📞 Техническая поддержка: @banana_pwr\n\n"
            "🔗 Регистрация в Pocket Option:\n"
            "https://pocket-friends.com/r/ugauihalod\n\n"
            "🎁 Промокод: FRIENDUGAUIHALOD"
        )
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='start')]]
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
        
    elif data.startswith('buy_'):
        plan_type = data.replace('buy_', '')
        success = await save_user_command(user_id, f'buy_subscription', details={'plan': plan_type})
        if success:
            await query.edit_message_text(
                f"🛒 *Оформление подписки {plan_type.upper()}*\n\n"
                "Запрос передан в систему оплаты...",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Ошибка оформления подписки")
        return
        
    elif data == 'my_deals':
        # Получаем историю сделок
        deals = supabase_request('trades', filters=f'user_id=eq.{user_id}&order=created_at.desc&limit=5')
        
        if deals and len(deals) > 0:
            deals_text = "📊 *Последние сделки:*\n\n"
            for deal in deals:
                asset = deal.get('asset', 'N/A')
                action = deal.get('action', 'N/A')
                result = deal.get('result', 'N/A')
                profit = deal.get('profit_loss', 0)
                deals_text += f"• {asset} {action} - {result} ({profit}₽)\n"
        else:
            deals_text = "📊 *История сделок*\n\nСделок пока нет"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='start')]]
        await query.edit_message_text(
            deals_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    # God panel callbacks (только для админа)
    elif data.startswith('god_'):
        if user_id != ADMIN_USER_ID:
            await query.edit_message_text("❌ Доступ запрещен")
            return
            
        if data == 'god_close':
            await query.edit_message_text("⚡️ God панель закрыта")
            return
        elif data == 'god_stats':
            users = supabase_request('users')
            active_traders = supabase_request('bot_status', filters='is_active=eq.true')
            message = (
                f"📊 *Статистика системы*\n\n"
                f"• Всего пользователей: {len(users) if users else 0}\n"
                f"• Активных трейдеров: {len(active_traders) if active_traders else 0}\n"
                f"• Админ ID: {ADMIN_USER_ID}"
            )
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='god_back')]]
            await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return
        elif data == 'god_back':
            # Возвращаем god панель
            keyboard = [
                [InlineKeyboardButton("📊 Статистика", callback_data='god_stats'),
                 InlineKeyboardButton("👥 Пользователи", callback_data='god_users')],
                [InlineKeyboardButton("⚙️ Настройки", callback_data='god_settings'),
                 InlineKeyboardButton("📝 Логи", callback_data='god_logs')],
                [InlineKeyboardButton("🔄 Перезагрузка", callback_data='god_restart'),
                 InlineKeyboardButton("🗑️ Очистка", callback_data='god_cleanup')],
                [InlineKeyboardButton("🔙 Закрыть", callback_data='god_close')]
            ]
            message = (
                f"⚡️ *GOD MODE ПАНЕЛЬ*\n\n"
                f"👑 Админ ID: {ADMIN_USER_ID}\n\n"
                f"Выберите действие:"
            )
            await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return
        else:
            # Для остальных god команд
            await query.edit_message_text(f"⚡️ God функция '{data}' в разработке", parse_mode='Markdown')
            return
    
    # Если действие не распознано
    await query.edit_message_text("⚡ Действие выполнено")

# ===== АДМИН КОМАНДЫ =====

async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Статистика для админа"""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Доступно только администраторам")
        return
        
    # Получаем статистику пользователей
    users = supabase_request('users')
    active_traders = supabase_request('bot_status', filters='is_active=eq.true')
    
    message = (
        f"👑 *Админ статистика*\n\n"
        f"• Всего пользователей: {len(users) if users else 0}\n"
        f"• Активных трейдеров: {len(active_traders) if active_traders else 0}\n"
        f"• Админ ID: {ADMIN_USER_ID}"
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def god_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """God команда (только для админа) - полная панель управления"""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data='god_stats'),
         InlineKeyboardButton("👥 Пользователи", callback_data='god_users')],
        [InlineKeyboardButton("⚙️ Настройки", callback_data='god_settings'),
         InlineKeyboardButton("📝 Логи", callback_data='god_logs')],
        [InlineKeyboardButton("🔄 Перезагрузка", callback_data='god_restart'),
         InlineKeyboardButton("🗑️ Очистка", callback_data='god_cleanup')],
        [InlineKeyboardButton("🔙 Закрыть", callback_data='god_close')]
    ]
    
    message = (
        f"⚡️ *GOD MODE ПАНЕЛЬ*\n\n"
        f"👑 Админ: {update.effective_user.first_name}\n"
        f"🆔 ID: {ADMIN_USER_ID}\n\n"
        f"Выберите действие:"
    )
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ===== ОСНОВНАЯ ФУНКЦИЯ =====

async def setup_commands(application):
    """Установка команд бота"""
    await application.bot.set_my_commands([
        BotCommand(command, description) for command, description in DEFAULT_BOT_COMMANDS
    ])
    logger.info("✅ Команды бота настроены")

def main() -> None:
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден в переменных окружения")
        return
        
    # Проверяем окружение
    try:
        check_environment()
    except Exception as e:
        logger.error(f"❌ {e}")
        return
        
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).post_init(setup_commands).build()
    
    # Пользовательские команды
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("plans", plans_command))
    application.add_handler(CommandHandler("autotrade", autotrade_command))
    application.add_handler(CommandHandler("signals", signals_command))
    application.add_handler(CommandHandler("bank", bank_command))
    application.add_handler(CommandHandler("faq", faq_command))
    application.add_handler(CommandHandler("help", faq_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Админ команды (СКРЫТЫЕ - не отображаются в списке команд)
    application.add_handler(CommandHandler("admin", admin_stats_command))
    application.add_handler(CommandHandler("god", god_command))
    
    # Обработчики сообщений и кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("🚀 Бот запущен (Интерфейсная версия)")
    print("✅ Crypto Signals Bot is running...")
    print(f"👑 Admin User ID: {ADMIN_USER_ID}")
    
    # Запуск бота
    application.run_polling()

# Экспорт для обратной совместимости
class BotInterface:
    """Класс для запуска бота из других модулей"""
    
    def __init__(self, token: str = None):
        self.token = token or BOT_TOKEN
        
        if not self.token:
            raise ValueError("BOT_TOKEN не предоставлен")
    
    def run(self):
        """Запустить бота"""
        global BOT_TOKEN
        BOT_TOKEN = self.token
        main()

if __name__ == '__main__':
    main()
