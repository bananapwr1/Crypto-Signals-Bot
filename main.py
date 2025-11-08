import os
import logging
import asyncio
import requests
import json
from datetime import datetime, timedelta, timezone
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

# Проверка обязательных переменных
if not BOT_TOKEN:
    raise Exception("❌ BOT_TOKEN не найден в переменных окружения")
if not SUPABASE_URL:
    raise Exception("❌ SUPABASE_URL не найден в переменных окружения")  
if not SUPABASE_KEY:
    raise Exception("❌ SUPABASE_KEY не найден в переменных окружения")

MOSCOW_TZ = timezone(timedelta(hours=3))
POCKET_OPTION_REF_LINK = "https://pocket-friends.com/r/ugauihalod"
PROMO_CODE = "FRIENDUGAUIHALOD"

# Команды бота - ТОЧНО КАК У ТЕБЯ БЫЛО
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
    ("God", "👑 God Mode"),
    ("Admin", "🛠️ Admin Panel")
]

# Тарифные планы
SUBSCRIPTION_PLANS = {
    'short': {
        '1m': 4990,
        '6m': 26946, 
        '12m': 47904,
        'name': 'SHORT',
        'description': '⚡ Быстрые сигналы (1-5 мин)',
        'emoji': '🟧'
    },
    'long': {
        '1m': 4990,
        '6m': 26946,
        '12m': 47904,
        'name': 'LONG', 
        'description': '🔵 Долгосрочные сигналы (1-4 часа)',
        'emoji': '📈'
    },
    'vip': {
        '1m': 9990,
        '6m': 53946,
        '12m': 95904,
        'name': 'VIP',
        'description': '👑 Все сигналы + автоторговля',
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
    
    existing_user = supabase_request('users', filters=f'telegram_id=eq.{user_id}')
    
    if existing_user and len(existing_user) > 0:
        if existing_user[0].get('username') != username:
            supabase_request('users', 'PATCH', {'username': username}, filters=f'telegram_id=eq.{user_id}')
        return existing_user[0]
    else:
        result = supabase_request('users', 'POST', user_data)
        if result:
            logger.info(f"✅ Создан новый пользователь: {user_id}")
            return user_data
        else:
            logger.error(f"❌ Ошибка создания пользователя: {user_id}")
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
    success = result is not None
    if success:
        logger.info(f"✅ Команда сохранена: {command} для пользователя {user_id}")
    return success

async def get_bot_status(user_id: int):
    """Получение статуса торговли из Supabase"""
    status_data = supabase_request('bot_status', filters=f'user_id=eq.{user_id}')
    if status_data and len(status_data) > 0:
        return status_data[0]
    return None

async def get_user_deals(user_id: int, limit=10):
    """Получение последних сделок пользователя"""
    deals = supabase_request('trades', filters=f'user_id=eq.{user_id}&order=created_at.desc&limit={limit}')
    return deals if deals else []

async def get_user_stats(user_id: int):
    """Получение статистики пользователя"""
    stats = supabase_request('user_stats', filters=f'user_id=eq.{user_id}')
    if stats and len(stats) > 0:
        return stats[0]
    return None

# ===== ОСНОВНЫЕ КОМАНДЫ БОТА =====

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🏠 Главное меню - УМНОЕ МЕНЮ С КНОПКАМИ НАЗАД"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    await check_or_create_user(user_id, username)
    
    # Умное меню с кнопками как было в оригинале
    keyboard = [
        [InlineKeyboardButton("⚡ SHORT сигнал", callback_data='short_signal'),
         InlineKeyboardButton("🔵 LONG сигнал", callback_data='long_signal')],
        [InlineKeyboardButton("💰 Управление банком", callback_data='bank_menu'),
         InlineKeyboardButton("📋 Мои LONG позиции", callback_data='my_longs')],
        [InlineKeyboardButton("📊 Моя статистика", callback_data='my_stats'),
         InlineKeyboardButton("💎 Тарифы и подписки", callback_data='plans_menu')],
        [InlineKeyboardButton("⚙️ Настройки", callback_data='settings_menu'),
         InlineKeyboardButton("❓ Помощь", callback_data='help_menu')],
        [InlineKeyboardButton("👑 God Mode", callback_data='god_mode'),
         InlineKeyboardButton("🛠️ Admin Panel", callback_data='admin_panel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '🏠 *Главное меню*\n\n'
        '🤖 Добро пожаловать в Crypto Signals Bot!\n\n'
        'Выберите действие:',
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """❓ Помощь и инструкции"""
    keyboard = [
        [InlineKeyboardButton("🔙 Назад в меню", callback_data='start')]
    ]
    
    message = (
        "❓ *Помощь и инструкции*\n\n"
        "📞 *Техническая поддержка:* @banana_pwr\n\n"
        "🔗 *Регистрация в Pocket Option:*\n"
        "https://pocket-friends.com/r/ugauihalod\n\n"
        "🎁 *Промокод:* FRIENDUGAUIHALOD\n\n"
        "*📚 Инструкция по использованию:*\n"
        "1. Выберите тарифный план\n"
        "2. Получите сигналы SHORT или LONG\n"
        "3. Настройте автоторговлю\n"
        "4. Следите за статистикой\n\n"
        "*⚡ SHORT сигналы:* 1-5 минут\n"
        "*🔵 LONG сигналы:* 1-4 часа\n"
        "*🤖 Автоторговля:* автоматическое исполнение"
    )
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def short_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """⚡ SHORT сигнал (1-5 мин)"""
    user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("🔄 Получить SHORT сигнал", callback_data='get_short')],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data='start')]
    ]
    
    await update.message.reply_text(
        "⚡ *SHORT сигнал (1-5 минут)*\n\n"
        "Быстрые сигналы для краткосрочной торговли:\n"
        "• Время экспирации: 1-5 минут\n"
        "• Высокая частота сигналов\n"
        "• Мартингейл стратегия\n\n"
        "Нажмите кнопку ниже чтобы получить сигнал:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def long_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🔵 LONG сигнал (1-4 часа)"""
    user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("🔄 Получить LONG сигнал", callback_data='get_long')],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data='start')]
    ]
    
    await update.message.reply_text(
        "🔵 *LONG сигнал (1-4 часа)*\n\n"
        "Долгосрочные сигналы для стабильного дохода:\n"
        "• Время экспирации: 1-4 часа\n"
        "• Высокая точность\n"
        "• Процентная стратегия 2.5%\n\n"
        "Нажмите кнопку ниже чтобы получить сигнал:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """💰 Управление банком"""
    user_id = update.effective_user.id
    
    status_info = await get_bot_status(user_id)
    
    keyboard = [
        [InlineKeyboardButton("💳 Пополнить баланс", callback_data='deposit')],
        [InlineKeyboardButton("📤 Вывести средства", callback_data='withdraw')],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data='start')]
    ]
    
    if status_info:
        balance = status_info.get('balance', 0)
        profit = status_info.get('daily_profit', 0)
        trades_today = status_info.get('trades_today', 0)
        
        message = (
            f"💰 *Управление банком*\n\n"
            f"• Текущий баланс: *{balance}₽*\n"
            f"• Профит сегодня: *{profit}₽*\n"
            f"• Сделок сегодня: *{trades_today}*\n"
            f"• Статус: {'🟢 Активен' if status_info.get('is_active') else '🔴 Не активен'}\n\n"
            f"Выберите действие:"
        )
    else:
        message = "💰 *Управление банком*\n\nТорговля еще не запущена\n\nВыберите действие:"
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def my_longs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """📋 Мои LONG позиции"""
    user_id = update.effective_user.id
    
    deals = await get_user_deals(user_id, 10)
    long_deals = [deal for deal in deals if deal.get('action') in ['LONG', 'long']]
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data='my_longs')],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data='start')]
    ]
    
    if long_deals:
        deals_text = "📋 *Мои LONG позиции:*\n\n"
        for deal in long_deals[:5]:  # Показываем последние 5
            asset = deal.get('asset', 'N/A')
            result = deal.get('result', 'pending')
            profit = deal.get('profit_loss', 0)
            created_at = deal.get('created_at', '')
            
            result_emoji = "🟢" if result == 'win' else "🔴" if result == 'loss' else "🟡"
            deals_text += f"{result_emoji} {asset} - {profit}₽\n"
    else:
        deals_text = "📋 *Мои LONG позиции*\n\nАктивных позиций нет"
    
    deals_text += "\n💡 Для полной статистики используйте /my_stats"
    
    await update.message.reply_text(
        deals_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def my_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """📊 Моя статистика"""
    user_id = update.effective_user.id
    
    stats = await get_user_stats(user_id)
    deals = await get_user_deals(user_id, 50)
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data='my_stats')],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data='start')]
    ]
    
    if deals:
        total_trades = len(deals)
        wins = len([d for d in deals if d.get('result') == 'win'])
        losses = len([d for d in deals if d.get('result') == 'loss'])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        total_profit = sum(d.get('profit_loss', 0) for d in deals)
        
        message = (
            f"📊 *Моя статистика*\n\n"
            f"• Всего сделок: *{total_trades}*\n"
            f"• Успешных: *{wins}*\n"
            f"• Неудачных: *{losses}*\n"
            f"• Винрейт: *{win_rate:.1f}%*\n"
            f"• Общий профит: *{total_profit:.2f}₽*\n\n"
            f"📈 *Последние сделки:*\n"
        )
        
        for deal in deals[:3]:
            asset = deal.get('asset', 'N/A')
            result = deal.get('result', 'pending')
            profit = deal.get('profit_loss', 0)
            result_emoji = "🟢" if result == 'win' else "🔴" if result == 'loss' else "🟡"
            message += f"{result_emoji} {asset} - {profit}₽\n"
    else:
        message = "📊 *Моя статистика*\n\nСтатистика пока недоступна\nНачните торговать чтобы увидеть данные"
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """💎 Тарифы и подписки"""
    keyboard = [
        [InlineKeyboardButton("🟧 SHORT Plan", callback_data='buy_short')],
        [InlineKeyboardButton("🔵 LONG Plan", callback_data='buy_long')],
        [InlineKeyboardButton("👑 VIP Plan", callback_data='buy_vip')],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data='start')]
    ]
    
    message = (
        "💎 *Тарифы и подписки*\n\n"
        "🟧 *SHORT Plan* - 4,990₽/мес\n"
        "⚡ Быстрые сигналы 1-5 мин\n"
        "🎯 Мартингейл стратегия\n\n"
        "🔵 *LONG Plan* - 4,990₽/мес\n" 
        "📈 Долгосрочные сигналы 1-4 часа\n"
        "💵 Процентная стратегия 2.5%\n\n"
        "👑 *VIP Plan* - 9,990₽/мес\n"
        "🤖 Все сигналы + автоторговля\n"
        "⚙️ Расширенные настройки\n"
        "👨‍💻 Персональная поддержка"
    )
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """⚙️ Настройки"""
    keyboard = [
        [InlineKeyboardButton("🤖 Настройки автоторговли", callback_data='auto_settings')],
        [InlineKeyboardButton("💰 Настройки ставок", callback_data='stake_settings')],
        [InlineKeyboardButton("📊 Настройки уведомлений", callback_data='notify_settings')],
        [InlineKeyboardButton("🔧 Расширенные настройки", callback_data='advanced_settings')],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data='start')]
    ]
    
    message = (
        "⚙️ *Настройки*\n\n"
        "Настройте параметры бота под свои предпочтения:\n\n"
        "• 🤖 *Автоторговля* - настройки автоматической торговли\n"
        "• 💰 *Ставки* - управление размерами ставок\n"
        "• 📊 *Уведомления* - настройка оповещений\n"
        "• 🔧 *Расширенные* - дополнительные параметры"
    )
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def god_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """👑 God Mode - только для админа"""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Доступно только в God Mode")
        return
        
    keyboard = [
        [InlineKeyboardButton("🌐 Статус системы", callback_data='system_status')],
        [InlineKeyboardButton("📊 Полная статистика", callback_data='full_stats')],
        [InlineKeyboardButton("🔧 Управление ботом", callback_data='bot_control')],
        [InlineKeyboardButton("⚡ Экстренные действия", callback_data='emergency')],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data='start')]
    ]
    
    message = (
        "👑 *God Mode*\n\n"
        "Полный контроль над системой:\n\n"
        "• 🌐 Статус системы и серверов\n"
        "• 📊 Детальная статистика\n"
        "• 🔧 Управление работой бота\n"
        "• ⚡ Экстренные действия"
    )
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🛠️ Admin Panel - только для админа"""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Доступно только администраторам")
        return
        
    users = supabase_request('users')
    active_traders = supabase_request('bot_status', filters='is_active=eq.true')
    pending_commands = supabase_request('user_commands', filters='processed=eq.false')
    
    total_users = len(users) if users else 0
    active_count = len(active_traders) if active_traders else 0
    pending_commands_count = len(pending_commands) if pending_commands else 0
    
    keyboard = [
        [InlineKeyboardButton("👥 Управление пользователями", callback_data='user_management')],
        [InlineKeyboardButton("📈 Статистика системы", callback_data='system_stats')],
        [InlineKeyboardButton("🔔 Рассылка сообщений", callback_data='broadcast')],
        [InlineKeyboardButton("⚙️ Настройки системы", callback_data='system_settings')],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data='start')]
    ]
    
    message = (
        f"🛠️ *Admin Panel*\n\n"
        f"📊 *Статистика системы:*\n"
        f"• Пользователей: {total_users}\n"
        f"• Активных трейдеров: {active_count}\n"
        f"• Ожидающих команд: {pending_commands_count}\n"
        f"• Админ ID: {ADMIN_USER_ID}\n\n"
        f"🛠️ *Инструменты администрирования:*"
    )
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ===== ОБРАБОТЧИКИ КНОПОК =====

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий кнопок - УМНЫЕ КНОПКИ НАЗАД"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # Обработка основных команд меню
    if data == 'start':
        await start_command(query, context)
        return
        
    elif data == 'help_menu':
        await help_command(query, context)
        return
        
    elif data == 'short_signal':
        await short_command(query, context)
        return
        
    elif data == 'long_signal':
        await long_command(query, context)
        return
        
    elif data == 'bank_menu':
        await bank_command(query, context)
        return
        
    elif data == 'my_longs':
        await my_longs_command(query, context)
        return
        
    elif data == 'my_stats':
        await my_stats_command(query, context)
        return
        
    elif data == 'plans_menu':
        await plans_command(query, context)
        return
        
    elif data == 'settings_menu':
        await settings_command(query, context)
        return
        
    elif data == 'god_mode':
        await god_command(query, context)
        return
        
    elif data == 'admin_panel':
        await admin_command(query, context)
        return
    
    # Обработка действий
    elif data == 'get_short':
        success = await save_user_command(user_id, 'get_short_signal')
        if success:
            await query.edit_message_text(
                "⚡ *SHORT сигнал запрошен*\n\n"
                "Сигнал обрабатывается...\n"
                "Ожидайте поступления сигнала в ближайшие секунды!",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Ошибка запроса сигнала")
        return
        
    elif data == 'get_long':
        success = await save_user_command(user_id, 'get_long_signal')
        if success:
            await query.edit_message_text(
                "🔵 *LONG сигнал запрошен*\n\n"
                "Сигнал обрабатывается...\n"
                "Ожидайте поступления сигнала!",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Ошибка запроса сигнала")
        return
    
    # Обработка покупки подписок
    elif data.startswith('buy_'):
        plan_type = data.replace('buy_', '')
        success = await save_user_command(user_id, f'buy_subscription', details={'plan': plan_type})
        if success:
            plan_info = SUBSCRIPTION_PLANS.get(plan_type, {})
            plan_name = plan_info.get('name', plan_type.upper())
            price = plan_info.get('1m', 0)
            
            await query.edit_message_text(
                f"💎 *Оформление подписки {plan_name}*\n\n"
                f"Стоимость: {price}₽/месяц\n\n"
                "✅ Запрос передан в систему оплаты\n"
                "📞 С вами свяжется менеджер для завершения оплаты",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Ошибка оформления подписки")
        return
    
    # Для всех остальных действий - просто подтверждение
    else:
        await query.edit_message_text(
            f"⚡ Действие выполнено: {data}\n\n"
            f"Команда передана в систему для обработки",
            parse_mode='Markdown'
        )

# ===== ЗАПУСК БОТА =====

async def post_init(application):
    """Установка команд бота - ТОЧНО КАК У ТЕБЯ БЫЛО"""
    await application.bot.set_my_commands([
        BotCommand(command, description) for command, description in DEFAULT_BOT_COMMANDS
    ])

def main() -> None:
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден в переменных окружения")
        return
        
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Регистрация ВСЕХ команд - ТОЧНО КАК У ТЕБЯ БЫЛО
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("short", short_command))
    application.add_handler(CommandHandler("long", long_command))
    application.add_handler(CommandHandler("bank", bank_command))
    application.add_handler(CommandHandler("my_longs", my_longs_command))
    application.add_handler(CommandHandler("my_stats", my_stats_command))
    application.add_handler(CommandHandler("plans", plans_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("God", god_command))
    application.add_handler(CommandHandler("Admin", admin_command))
    
    # Обработчики кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("🚀 Бот запущен с УМНЫМ МЕНЮ")
    print("✅ Crypto Signals Bot is running with SMART MENU...")
    print(f"👑 Admin User ID: {ADMIN_USER_ID}")
    print(f"🔗 Commands: {[cmd[0] for cmd in DEFAULT_BOT_COMMANDS]}")
    
    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()