
## 🔧 Конкретные инструкции для выполнения:

**1. Создайте файл `bot_interface.py` с таким содержимым:**

```python
import os
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import warnings
import uuid
import requests
import json

warnings.filterwarnings('ignore')
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@banana_pwr")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Команды бота
DEFAULT_BOT_COMMANDS = [
    ("start", "Главное меню"),
    ("plans", "Тарифы и подписки"),
    ("bank", "Управление банком"),
    ("autotrade", "Автоторговля"),
    ("signals", "Сигналы Short/Long"),
    ("faq", "Помощь"),
]

# ===== РЕАЛЬНЫЕ ФУНКЦИИ SUPABASE =====

def supabase_request(table, method='GET', data=None, filters=None):
    """Реальные запросы к Supabase"""
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
        
        if response.status_code in [200, 201, 204]:
            return response.json() if response.content else {'status': 'success'}
        else:
            logger.error(f"Supabase error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Supabase request error: {e}")
        return None

async def real_check_or_create_user(user_id: int, username: str):
    """Реальная проверка/создание пользователя в Supabase"""
    user_data = {
        'telegram_id': user_id,
        'username': username or 'Unknown',
        'subscription_type': 'none',
        'created_at': datetime.now().isoformat()
    }
    
    result = supabase_request('users', 'POST', user_data)
    if result:
        logger.info(f"User {user_id} checked/created in Supabase")
    else:
        logger.error(f"Failed to create user {user_id} in Supabase")

async def save_user_command(user_id: int, command: str, asset=None, details=None):
    """Сохранение команды для торгового ядра"""
    command_data = {
        'user_id': user_id,
        'command': command,
        'asset': asset,
        'details': details,
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

# ===== СУЩЕСТВУЮЩИЕ ФУНКЦИИ ИЗ main.py (с небольшими улучшениями) =====

async def check_user_access(update: Update, context: ContextTypes.DEFAULT_TYPE, required_level="any") -> bool:
    """Проверка прав доступа пользователя"""
    if update.effective_user.id == ADMIN_USER_ID:
        return True
    if required_level == "admin":
        await update.message.reply_text("📅 Доступно только администраторам.")
        return False
    return True

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главное меню"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Реальная проверка пользователя
    await real_check_or_create_user(user_id, username)
    
    keyboard = [
        [InlineKeyboardButton("📊 Статус торговли", callback_data='status'),
         InlineKeyboardButton("📈 Автоторговля", callback_data='autotrade_menu')],
        [InlineKeyboardButton("🟧 Сигналы Short", callback_data='signals_short'),
         InlineKeyboardButton("🟦 Сигналы Long", callback_data='signals_long')],
        [InlineKeyboardButton("💼 Тарифы", callback_data='plans'),
         InlineKeyboardButton("❓ Помощь", callback_data='faq')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '🤖 *Crypto Signals Bot*\\n\\nВыберите действие:',
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

# ... (остальные функции из main.py остаются практически без изменений)

async def autotrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Автоторговля - теперь с реальной записью в базу"""
    user_id = update.effective_user.id
    
    # Сохраняем команду для торгового ядра
    success = await save_user_command(user_id, 'start_autotrade')
    
    if success:
        await update.message.reply_text(
            "✅ *Команда на автоторговлю передана ядру*\\n\\n"
            "Торговое ядро получило команду и начинает анализ рынка...",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("❌ Ошибка передачи команды")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопок с реальной логикой"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == 'start':
        await start_command(query, context)
        return
        
    if data == 'status':
        # Показываем реальный статус из базы
        status_info = await get_bot_status(user_id)
        if status_info:
            message = (
                f"📊 *Статус торговли*\\n\\n"
                f"• Активность: {'🟢 ВКЛ' if status_info.get('is_active') else '🔴 ВЫКЛ'}\\n"
                f"• Сделок сегодня: {status_info.get('trades_today', 0)}\\n"
                f"• Профит: {status_info.get('daily_profit', 0)}€\\n"
                f"• Баланс: {status_info.get('balance', 0)}€"
            )
        else:
            message = "📊 *Статус*\\n\\nТорговля еще не запущена"
        
        await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
        return
        
    if data == 'autotrade_menu':
        success = await save_user_command(user_id, 'start_autotrade')
        if success:
            await query.edit_message_text(
                "✅ *Автоторговля запускается*\\n\\n"
                "Команда передана торговому ядру. Ожидайте сигналов...",
                parse_mode=ParseMode.MARKDOWN
            )
        return
        
    if data in ['signals_short', 'signals_long']:
        signal_type = 'short' if data == 'signals_short' else 'long'
        success = await save_user_command(user_id, f'get_signals_{signal_type}')
        if success:
            await query.edit_message_text(
                f"📡 *Запрос {signal_type.upper()} сигналов*\\n\\n"
                "Сигналы запрошены у торгового ядра...",
                parse_mode=ParseMode.MARKDOWN
            )
        return
    
    # Остальная логика кнопок остается как в main.py
    # ...

# ... (остальной код из main.py)

def main() -> None:
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не найден.")
        return
        
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация обработчиков (как в main.py)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("autotrade", autotrade_command))
    # ... остальные обработчики
    
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("🚀 Интерфейсный бот запущен (BotHost.ru)")
    application.run_polling()

if __name__ == '__main__':
    main()