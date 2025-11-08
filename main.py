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

# Команды бота
DEFAULT_BOT_COMMANDS = [
    ("start", "📱 Главное меню"),
    ("plans", "💼 Тарифы и подписки"),
    ("bank", "💰 Управление банком"),
    ("autotrade", "🤖 Автоторговля (VIP)"),
    ("signals", "📡 Сигналы Short/Long"),
    ("faq", "❓ Помощь"),
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
        'description': 'Все сигналы SHORT + LONG + аналитика + расширенные настройки',
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
    else:
        logger.error(f"❌ Ошибка сохранения команды: {command} для пользователя {user_id}")
    return success

async def get_bot_status(user_id: int):
    """Получение статуса торговли из Supabase"""
    status_data = supabase_request('bot_status', filters=f'user_id=eq.{user_id}')
    if status_data and len(status_data) > 0:
        return status_data[0]
    return None

async def get_user_deals(user_id: int, limit=5):
    """Получение последних сделок пользователя"""
    deals = supabase_request('trades', filters=f'user_id=eq.{user_id}&order=created_at.desc&limit={limit}')
    return deals if deals else []

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
         InlineKeyboardButton("📊 Статус", callback_data='status')],
        [InlineKeyboardButton("❓ Помощь", callback_data='faq')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '🤖 *Crypto Signals Bot*\n\n'
        'Привет! Я помогу тебе с торговлей на финансовых рынках.\n\n'
        'Выберите действие:',
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
        "• Быстрые сигналы (1-5 мин)\n"
        "• Мартингейл стратегия\n\n"
        "📈 *LONG* - 4,990₽/мес\n" 
        "• Долгосрочные сигналы (1-4 часа)\n"
        "• Процентная ставка 2.5%\n\n"
        "👑 *VIP* - 9,990₽/мес\n"
        "• Все сигналы SHORT + LONG\n"
        "• Расширенные настройки\n"
        "• Автоторговля\n"
        "• Персональная поддержка"
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
        trades_today = status_info.get('trades_today', 0)
        
        message = (
            f"💰 *Управление банком*\n\n"
            f"• Текущий баланс: *{balance}₽*\n"
            f"• Профит сегодня: *{profit}₽*\n"
            f"• Сделок сегодня: *{trades_today}*\n"
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
        "*Часто задаваемые вопросы:*\n"
        "• Как начать торговлю? - Выберите тариф и начните получать сигналы\n"
        "• Как работает автоторговля? - Бот автоматически исполняет сигналы\n"
        "• Нужен ли мне аккаунт Pocket Option? - Да, для автоторговли\n"
        "• Какой минимальный депозит? - От 1000₽\n"
        "• Есть ли гарантия прибыли? - Нет, торговля связана с рисками"
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
            f"• Профит сегодня: {status_info.get('daily_profit', 0)}₽\n"
            f"• Общий баланс: {status_info.get('balance', 0)}₽\n"
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
        await start_command(query, context)
        return
        
    elif data == 'status':
        await status_command(query, context)
        return
        
    elif data == 'autotrade_menu':
        # Показываем меню автоторговли
        keyboard = [
            [InlineKeyboardButton("🚀 Запустить автоторговлю", callback_data='start_autotrade')],
            [InlineKeyboardButton("🛑 Остановить автоторговлю", callback_data='stop_autotrade')],
            [InlineKeyboardButton("⚙️ Настройки автоторговли", callback_data='autotrade_settings')],
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
                "Торговое ядро получило команду и начинает работу...\n\n"
                "Ожидайте уведомлений о сделках!",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Ошибка запуска автоторговли")
        return
        
    elif data == 'stop_autotrade':
        success = await save_user_command(user_id, 'stop_autotrade')
        if success:
            await query.edit_message_text(
                "🛑 *Автоторговля остановлена*\n\n"
                "Все торговые операции приостановлены.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Ошибка остановки автоторговли")
        return
        
    elif data == 'autotrade_settings':
        keyboard = [
            [InlineKeyboardButton("💰 Настройка ставок", callback_data='set_stakes')],
            [InlineKeyboardButton("⚡ Выбор стратегии", callback_data='set_strategy')],
            [InlineKeyboardButton("📈 Выбор активов", callback_data='set_assets')],
            [InlineKeyboardButton("🔙 Назад", callback_data='autotrade_menu')]
        ]
        await query.edit_message_text(
            "⚙️ *Настройки автоторговли*\n\n"
            "Настройте параметры автоматической торговли:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
        
    elif data in ['signals_short', 'signals_long']:
        signal_type = 'short' if data == 'signals_short' else 'long'
        success = await save_user_command(user_id, f'get_signals_{signal_type}')
        if success:
            await query.edit_message_text(
                f"📡 *Запрос {signal_type.upper()} сигналов*\n\n"
                "Сигналы запрошены у торгового ядра...\n\n"
                "Ожидайте поступления сигналов в ближайшее время!",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Ошибка запроса сигналов")
        return
        
    elif data == 'plans':
        await plans_command(query, context)
        return
        
    elif data == 'faq':
        await faq_command(query, context)
        return
        
    elif data.startswith('buy_'):
        plan_type = data.replace('buy_', '')
        success = await save_user_command(user_id, f'buy_subscription', details={'plan': plan_type})
        if success:
            plan_info = SUBSCRIPTION_PLANS.get(plan_type, {})
            plan_name = plan_info.get('name', plan_type.upper())
            price = plan_info.get('1m', 0)
            
            await query.edit_message_text(
                f"🛒 *Оформление подписки {plan_name}*\n\n"
                f"Стоимость: {price}₽/месяц\n\n"
                "Запрос передан в систему оплаты...\n"
                "С вами свяжется менеджер для завершения оплаты.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Ошибка оформления подписки")
        return
        
    elif data == 'my_deals':
        # Получаем историю сделок
        deals = await get_user_deals(user_id, 5)
        
        if deals and len(deals) > 0:
            deals_text = "📊 *Последние сделки:*\n\n"
            for deal in deals:
                asset = deal.get('asset', 'N/A')
                action = deal.get('action', 'N/A')
                result = deal.get('result', 'N/A')
                profit = deal.get('profit_loss', 0)
                
                # Определяем эмодзи для результата
                result_emoji = "🟢" if result == 'win' else "🔴" if result == 'loss' else "⚪"
                
                deals_text += f"{result_emoji} {asset} {action} - {profit}₽\n"
        else:
            deals_text = "📊 *История сделок*\n\nСделок пока нет"
            
        deals_text += "\n💡 Для просмотра полной статистики используйте команду /status"
        
        await query.edit_message_text(deals_text, parse_mode='Markdown')
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
    pending_commands = supabase_request('user_commands', filters='processed=eq.false')
    
    total_users = len(users) if users else 0
    active_count = len(active_traders) if active_traders else 0
    pending_commands_count = len(pending_commands) if pending_commands else 0
    
    message = (
        f"👑 *Админ статистика*\n\n"
        f"• Всего пользователей: {total_users}\n"
        f"• Активных трейдеров: {active_count}\n"
        f"• Ожидающих команд: {pending_commands_count}\n"
        f"• Админ ID: {ADMIN_USER_ID}\n\n"
        f"• Supabase URL: {SUPABASE_URL[:20]}...\n"
        f"• Бот запущен: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')

# ===== ОСНОВНАЯ ФУНКЦИЯ =====

async def post_init(application):
    """Установка команд бота"""
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
    
    # Пользовательские команды
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("plans", plans_command))
    application.add_handler(CommandHandler("autotrade", autotrade_command))
    application.add_handler(CommandHandler("signals", signals_command))
    application.add_handler(CommandHandler("bank", bank_command))
    application.add_handler(CommandHandler("faq", faq_command))
    application.add_handler(CommandHandler("help", faq_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Админ команды
    application.add_handler(CommandHandler("admin", admin_stats_command))
    
    # Обработчики сообщений и кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("🚀 Бот запущен (Интерфейсная версия)")
    print("✅ Crypto Signals Bot is running...")
    print(f"👑 Admin User ID: {ADMIN_USER_ID}")
    print(f"🔗 Supabase URL: {SUPABASE_URL}")
    print(f"⏰ Moscow Time: {datetime.now(MOSCOW_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()