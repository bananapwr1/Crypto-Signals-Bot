import os
import logging
import asyncio
import requests
import json
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, WebhookHandler
from dotenv import load_dotenv
import warnings
import sys

# Добавляем путь к корневой директории бота, чтобы импортировать bot_config
# path_to_bot_app = os.path.dirname(os.path.abspath(__file__))
# if path_to_bot_app not in sys.path:
#     sys.path.append(path_to_bot_app)
    
warnings.filterwarnings('ignore')
load_dotenv()

# ===== КОНФИГУРАЦИЯ И ПЕРЕМЕННЫЕ =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "7746862973"))
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@banana_pwr")
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

# Укажите здесь ваш реальный URL на PythonAnywhere!
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "YOUR_PYTHONANYWHERE_WEBAPP_URL")

# Порт для работы Webhook на локальной машине (игнорируется на PythonAnywhere)
PORT = int(os.environ.get('PORT', '8443'))

# Проверка обязательных переменных
if not BOT_TOKEN:
    raise Exception("❌ BOT_TOKEN не найден в переменных окружения")
if not SUPABASE_URL:
    raise Exception("❌ SUPABASE_URL не найден в переменных окружения")  
if not SUPABASE_KEY:
    raise Exception("❌ SUPABASE_KEY не найден в переменных окружения")
if WEBHOOK_URL == "YOUR_PYTHONANYWHERE_WEBAPP_URL":
     print("🚨 ВНИМАНИЕ: WEBHOOK_URL не настроен. Бот будет использовать заглушку.")


MOSCOW_TZ = timezone(timedelta(hours=3))
POCKET_OPTION_REF_LINK = "https://pocket-friends.com/r/ugauihalod"
PROMO_CODE = "FRIENDUGAUIHALOD"

# Команды бота (для setMyCommands - ОБЯЗАТЕЛЬНО нижний регистр)
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
    ("god", "👑 God Mode"), # Исправлено на нижний регистр
    ("admin", "🛠️ Admin Panel") # Исправлено на нижний регистр
]

# Тарифные планы
SUBSCRIPTION_PLANS = {
    'none': {
        'name': 'БЕСПЛАТНЫЙ',
        'emoji': '🆓',
        'features': ['🔸 1 SHORT сигнал в день', '🔸 1 LONG сигнал в день'],
        'restrictions': ['❌ Без автоторговли', '❌ Ограниченные сигналы']
    },
    'short': {
        '1m': 4990,
        '6m': 26946, 
        '12m': 47904,
        'name': 'SHORT',
        'description': '⚡ Быстрые сигналы (1-5 мин)',
        'emoji': '🟧',
        'features': ['✅ Неограниченные SHORT сигналы', '✅ Мартингейл стратегия', '✅ Поддержка 24/7'],
        'restrictions': ['❌ LONG сигналы ограничены', '❌ Без автоторговли']
    },
    'long': {
        '1m': 4990,
        '6m': 26946,
        '12m': 47904,
        'name': 'LONG', 
        'description': '🔵 Долгосрочные сигналы (1-4 часа)',
        'emoji': '📈',
        'features': ['✅ Неограниченные LONG сигналы', '✅ Процентная стратегия 2.5%', '✅ Поддержка 24/7'],
        'restrictions': ['❌ SHORT сигналы ограничены', '❌ Без автоторговли']
    },
    'vip': {
        '1m': 9990,
        '6m': 53946,
        '12m': 95904,
        'name': 'VIP',
        'description': '👑 Все сигналы + автоторговля',
        'emoji': '👑',
        'features': ['✅ Все SHORT и LONG сигналы', '✅ Автоторговля', '✅ Расширенные настройки', '✅ Персональная поддержка'],
        'restrictions': []
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
        # Для GET-запроса, если ожидаем результат
        if method == 'GET':
            response = requests.get(url, headers=headers)
        
        # Для POST/PATCH/DELETE, где не ожидаем JSON-тела в ответ
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'PATCH':
            response = requests.patch(url, headers=headers, json=data)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            logger.error(f"Неподдерживаемый метод HTTP: {method}")
            return None
        
        if response.status_code in [200, 201]:
            # GET запросы возвращают JSON
            return response.json() if method == 'GET' and response.content else response.json()
        elif response.status_code == 204:
            # POST/PATCH/DELETE часто возвращают 204 No Content
            return {'status': 'success'}
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
        # Обновляем username, если он изменился
        if existing_user[0].get('username') != username:
            supabase_request('users', 'PATCH', {'username': username}, filters=f'telegram_id=eq.{user_id}')
        return existing_user[0]
    else:
        # Создаем нового пользователя
        result = supabase_request('users', 'POST', user_data)
        if result or result == {'status': 'success'}:
            logger.info(f"✅ Создан новый пользователь: {user_id}")
            return user_data
        else:
            logger.error(f"❌ Ошибка создания пользователя: {user_id}")
            return None

async def get_user_subscription(user_id: int):
    """Получение информации о подписке пользователя"""
    user_data = supabase_request('users', filters=f'telegram_id=eq.{user_id}')
    if user_data and len(user_data) > 0:
        return user_data[0].get('subscription_type', 'none')
    return 'none'

async def save_user_command(user_id: int, command: str, asset=None, action=None, details=None):
    """Сохранение команды для торгового ядра"""
    command_data = {
        'user_id': user_id,
        'command': command, # 'GET_SHORT_SIGNAL', 'START_AUTOTRADE' и т.п.
        'asset': asset,
        'action': action, # 'LONG' или 'SHORT'
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

# ===== УМНОЕ МЕНЮ ПО ТАРИФУ =====

def get_main_menu_keyboard(subscription_type: str, user_id: int):
    """Генерация умного меню в зависимости от тарифа пользователя"""
    subscription_info = SUBSCRIPTION_PLANS.get(subscription_type, SUBSCRIPTION_PLANS['none'])
    subscription_name = subscription_info['name']
    subscription_emoji = subscription_info['emoji']
    
    keyboard = []
    
    # Первый ряд: сигналы (зависит от тарифа)
    # Кнопки для SHORT-сигнала
    if subscription_type in ['short', 'vip']:
        short_button = InlineKeyboardButton("⚡ SHORT сигнал", callback_data='request_short_signal')
    else:
        short_button = InlineKeyboardButton("⚡ SHORT (🔒)", callback_data='plans_menu')
    
    # Кнопки для LONG-сигнала
    if subscription_type in ['long', 'vip']:
        long_button = InlineKeyboardButton("🔵 LONG сигнал", callback_data='request_long_signal')
    else:
        long_button = InlineKeyboardButton("🔵 LONG (🔒)", callback_data='plans_menu')
    
    keyboard.append([short_button, long_button])
    
    # Второй ряд: банк и позиции
    keyboard.append([
        InlineKeyboardButton("💰 Управление банком", callback_data='bank_menu'),
        InlineKeyboardButton("📋 Мои позиции", callback_data='my_longs')
    ])
    
    # Третий ряд: статистика и автоторговля
    if subscription_type == 'vip':
        auto_button = InlineKeyboardButton("🤖 Автоторговля", callback_data='autotrade_menu')
    else:
        auto_button = InlineKeyboardButton("🤖 Автоторговля (🔒)", callback_data='plans_menu')
    
    keyboard.append([
        InlineKeyboardButton("📊 Моя статистика", callback_data='my_stats'),
        auto_button
    ])
    
    # Четвертый ряд: тарифы и настройки
    keyboard.append([
        InlineKeyboardButton("💎 Тарифы", callback_data='plans_menu'),
        InlineKeyboardButton("⚙️ Настройки", callback_data='settings_menu')
    ])
    
    # Пятый ряд: помощь
    keyboard.append([InlineKeyboardButton("❓ Помощь", callback_data='help_menu')])
    
    # Админские кнопки (только для админа)
    if user_id == ADMIN_USER_ID:
        keyboard.append([
            InlineKeyboardButton("👑 God Mode", callback_data='god_mode'),
            InlineKeyboardButton("🛠️ Admin Panel", callback_data='admin_panel')
        ])
    
    return keyboard, subscription_name, subscription_emoji

# ===== ОСНОВНЫЕ КОМАНДЫ БОТА (ХЭНДЛЕРЫ) =====

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🏠 Главное меню - УМНОЕ МЕНЮ ПО ТАРИФУ"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    await check_or_create_user(user_id, username)
    subscription_type = await get_user_subscription(user_id)
    
    keyboard, sub_name, sub_emoji = get_main_menu_keyboard(subscription_type, user_id)
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    sub_info = SUBSCRIPTION_PLANS.get(subscription_type, SUBSCRIPTION_PLANS['none'])
    
    message = (
        f'🏠 *Главное меню*\n\n'
        f'🤖 Добро пожаловать в Crypto Signals Bot!\n\n'
        f'📋 *Ваш тариф:* {sub_emoji} {sub_name}\n\n'
    )
    
    if sub_info.get('features'):
        message += "*✅ Доступно:*\n"
        for feature in sub_info['features']:
            message += f"• {feature}\n"
        message += "\n"
    
    if sub_info.get('restrictions'):
        message += "*❌ Ограничения:*\n"
        for restriction in sub_info['restrictions']:
            message += f"• {restriction}\n"
        message += "\n"
    
    message += "Выберите действие:"
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """❓ Помощь и инструкции"""
    user_id = update.effective_user.id
    subscription_type = await get_user_subscription(user_id)
    sub_info = SUBSCRIPTION_PLANS.get(subscription_type, SUBSCRIPTION_PLANS['none'])
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад в меню", callback_data='start')]
    ]
    
    message = (
        f"❓ *Помощь и инструкции*\n\n"
        f"📞 *Техническая поддержка:* {SUPPORT_CONTACT}\n\n"
        f"🔗 *Регистрация в Pocket Option:*\n"
        f"{POCKET_OPTION_REF_LINK}\n\n"
        f"🎁 *Промокод:* `{PROMO_CODE}`\n\n"
        f"*📚 Инструкция по использованию:*\n"
        f"1. Выберите тарифный план\n"
        f"2. Получите сигналы SHORT или LONG\n"
        f"3. Настройте автоторговлю (VIP)\n"
        f"4. Следите за статистикой\n\n"
        f"*⚡ SHORT сигналы:* 1-5 минут\n"
        f"*🔵 LONG сигналы:* 1-4 часа\n"
        f"*🤖 Автоторговля:* автоматическое исполнение (только VIP)\n\n"
        f"*📋 Ваш тариф:* {sub_info['emoji']} {sub_info['name']}"
    )
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def short_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """⚡ SHORT сигнал (1-5 мин) - Прямой вызов"""
    await button_callback_handler(update, context, 'request_short_signal')

async def long_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🔵 LONG сигнал (1-4 часа) - Прямой вызов"""
    await button_callback_handler(update, context, 'request_long_signal')

async def bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """💰 Управление банком - Прямой вызов"""
    await button_callback_handler(update, context, 'bank_menu')

async def my_longs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """📋 Мои LONG позиции - Прямой вызов"""
    await button_callback_handler(update, context, 'my_longs')

async def my_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """📊 Моя статистика - Прямой вызов"""
    await button_callback_handler(update, context, 'my_stats')

async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """💎 Тарифы и подписки - Прямой вызов"""
    await button_callback_handler(update, context, 'plans_menu')

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """⚙️ Настройки - Прямой вызов"""
    await button_callback_handler(update, context, 'settings_menu')

# ===== АДМИНИСТРАТОРСКИЕ КОМАНДЫ =====

async def god_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """👑 God Mode (Только для ADMIN_USER_ID)"""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ *Доступ запрещен*.", parse_mode='Markdown')
        return
    await update.message.reply_text("👑 *God Mode:*\n\nВам доступно управление всеми аспектами системы.", parse_mode='Markdown')

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🛠️ Admin Panel (Только для ADMIN_USER_ID)"""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ *Доступ запрещен*.", parse_mode='Markdown')
        return
    await update.message.reply_text("🛠️ *Admin Panel:*\n\nЗдесь будут инструменты для модерации и статистики.", parse_mode='Markdown')

# ===== ОБРАБОТЧИК КНОПОК =====

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str = None) -> None:
    """Обработчик колбэков и универсальный роутер для команд"""
    query = update.callback_query
    
    if query:
        await query.answer()
        data = query.data
        user_id = query.from_user.id
        edit_func = query.edit_message_text
        
    elif data:
        user_id = update.effective_user.id
        edit_func = update.message.reply_text # Если это прямой вызов, используем reply_text
    else:
        # Не должно случиться, но на всякий случай
        return
    
    # Общая информация о пользователе
    subscription_type = await get_user_subscription(user_id)
    keyboard, sub_name, sub_emoji = get_main_menu_keyboard(subscription_type, user_id)
    
    # --- Роутинг ---
    
    # 1. Запрос сигнала (SHORT/LONG)
    if data in ['request_short_signal', 'request_long_signal']:
        
        # Проверка подписки (повторная, для надежности)
        if data == 'request_short_signal' and subscription_type not in ['short', 'vip']:
            await edit_func("❌ Для SHORT сигналов нужна подписка. Перейдите в '💎 Тарифы'.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Тарифы", callback_data='plans_menu')]]))
            return
        if data == 'request_long_signal' and subscription_type not in ['long', 'vip']:
            await edit_func("❌ Для LONG сигналов нужна подписка. Перейдите в '💎 Тарифы'.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Тарифы", callback_data='plans_menu')]]))
            return
            
        signal_type = "SHORT" if data == 'request_short_signal' else "LONG"
        
        # Сохранение команды для ядра
        success = await save_user_command(user_id, f'GET_{signal_type}_SIGNAL', action=signal_type)
        
        if success:
            message = (
                f"✅ *Запрос отправлен!*\n\n"
                f"Торговое ядро получило команду на генерацию *{signal_type}* сигнала.\n"
                f"⏳ Ожидайте уведомление о сделке в ближайшее время (обычно до 60 секунд)."
            )
        else:
            message = "❌ *Ошибка сохранения команды*.\n\nПовторите попытку позже или обратитесь в поддержку."
            
        await edit_func(message, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В меню", callback_data='start')]]), parse_mode='Markdown')
        return
        
    # 2. Меню Навигации
    elif data == 'start':
        # Возвращение в главное меню
        message = (
            f'🏠 *Главное меню*\n\n'
            f'🤖 Добро пожаловать в Crypto Signals Bot!\n\n'
            f'📋 *Ваш тариф:* {sub_emoji} {sub_name}\n\n'
            f'Выберите действие:'
        )
        await edit_func(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    # 3. Меню Банка (заглушка)
    elif data == 'bank_menu':
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
        
        await edit_func(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return
    
    # 4. Меню Тарифов
    elif data == 'plans_menu':
        # Этот код повторяет логику plans_command
        current_subscription = await get_user_subscription(user_id)
        
        keyboard_plans = [
            [InlineKeyboardButton("🟧 SHORT Plan", callback_data='buy_shor