# main.py: Главный файл чистого интерфейса Telegram бота (Updater)
# Использует минимальные зависимости и заглушки для Supabase.

import os
import logging
import time
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, error
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext
)

# Импорт менеджера Supabase (должен быть в файле supabase_manager.py)
try:
    from supabase_manager import SupabaseManager
except ImportError:
    # Если файл не найден, используем заглушку, чтобы код не падал
    class SupabaseManager:
        def __init__(self):
            logging.error("❌ Файл 'supabase_manager.py' не найден. Supabase не инициализирован.")
            pass
        def check_or_create_user(self, user_id: int, username: str) -> bool:
            logging.info(f"DB STUB: Проверка/создание пользователя {user_id} - {username}")
            return True
        def get_user_status(self, user_id: int):
            return {"status": "STUB: No DB Connection"}
    
    
# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Ключи и настройки (читаем имена, которые вы используете в .env)
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@support_user")

# Инициализация Supabase клиента
db = SupabaseManager()

# --- Вспомогательные функции ---

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    return user_id == ADMIN_USER_ID

def get_main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Формирует основное меню с кнопками."""
    keyboard = [
        [InlineKeyboardButton("💎 Тарифы и подписки", callback_data='plans')],
        [
            InlineKeyboardButton("💰 Банк", callback_data='bank'),
            InlineKeyboardButton("💼 Профиль", callback_data='profile')
        ],
        [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')]
    ]
    
    # Добавляем кнопку админа, если пользователь - админ
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ АДМИН ПАНЕЛЬ ⚙️", callback_data='admin_panel')])

    return InlineKeyboardMarkup(keyboard)

# --- Обработчики команд ---

def start_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start."""
    user = update.effective_user
    
    # Инициализация пользователя в БД
    db.check_or_create_user(user.id, user.username or f"user_{user.id}")
    
    welcome_text = (
        f"🤖 Привет, {user.first_name}! Я твой бот-помощник.\n"
        f"Здесь ты можешь управлять подписками, настройками и сигналами."
    )
    
    update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu_keyboard(user.id)
    )

def admin_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /admin."""
    if not is_admin(update.effective_user.id):
        update.message.reply_text("⛔️ Доступ запрещен. Вы не администратор.")
        return

    keyboard = [
        [InlineKeyboardButton("Статистика", callback_data='admin_stats'),
         InlineKeyboardButton("Сброс (Stats)", callback_data='admin_reset_stats')],
        [InlineKeyboardButton("Управление юзерами", callback_data='admin_user_manage')],
        [InlineKeyboardButton("Назад в меню", callback_data='menu')]
    ]

    update.message.reply_text(
        "🛠️ **АДМИН ПАНЕЛЬ**\nВыберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def reset_user_command(update: Update, context: CallbackContext) -> None:
    """Админ-команда для сброса данных пользователя."""
    if not is_admin(update.effective_user.id):
        update.message.reply_text("⛔️ Доступ запрещен.")
        return

    if not context.args:
        update.message.reply_text(
            "⚙️ **СБРОС ПОЛЬЗОВАТЕЛЯ**\n"
            "Использование: /reset_user [ID пользователя]"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        # STUB: Здесь будет вызов db.reset_user(target_user_id)
        update.message.reply_text(
            f"✅ **[DB STUB]** Сброс данных пользователя с ID `{target_user_id}` выполнен (пока только заглушка)."
        )
    except ValueError:
        update.message.reply_text("❌ Неверный ID пользователя. ID должен быть числом.")

def reset_all_stats_command(update: Update, context: CallbackContext) -> None:
    """Админ-команда для сброса всей статистики."""
    if not is_admin(update.effective_user.id):
        update.message.reply_text("⛔️ Доступ запрещен.")
        return

    # STUB: Здесь будет вызов db.reset_all_stats()
    update.message.reply_text(
        "⚠️ **[DB STUB]** Сброс ВСЕЙ статистики пользователей выполнен (пока только заглушка)."
    )

# --- Обработчик кнопок (CallbackQuery) ---

def button_callback(update: Update, context: CallbackContext) -> None:
    """Обработчик нажатий на инлайн-кнопки."""
    query = update.callback_query
    query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data == 'menu' or data == 'profile':
        user_status = db.get_user_status(user_id) # Получаем статус (или заглушку)
        
        # Обновляем сообщение с главным меню
        query.edit_message_text(
            f"🏠 **ГЛАВНОЕ МЕНЮ**\nВаш статус: {user_status['status'] if user_status else 'Неизвестен'}",
            reply_markup=get_main_menu_keyboard(user_id)
        )
    
    elif data == 'admin_panel':
        admin_command(query, context) # Вызываем команду /admin для обновления

    # Обработка других кнопок (STUB)
    elif data in ['plans', 'bank', 'settings', 'admin_stats', 'admin_reset_stats', 'admin_user_manage']:
        query.edit_message_text(f"🚧 **[STUB]** Вы нажали: {data}. Эта функция пока не реализована (Фаза 3).")
    
    # Добавьте здесь все остальные обработчики кнопок...

# --- Основная функция запуска ---

def main() -> None:
    """Запускает бота."""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден. Проверьте .env файл или переменные окружения на хостинге.")
        return

    logger.info("✅ Токен считан. Начало токена: %s...", BOT_TOKEN[:5])
    
    # Используем проверенный класс Updater
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Регистрируем основные команды
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("admin", admin_command))
    
    # Регистрируем админ-команды для сброса статистики
    dispatcher.add_handler(CommandHandler("reset_user", reset_user_command))
    dispatcher.add_handler(CommandHandler("reset_all_stats", reset_all_stats_command))
    
    # Обработчик кнопок
    dispatcher.add_handler(CallbackQueryHandler(button_callback))

    # Устанавливаем меню команд (это синхронная операция, но Updater ее обрабатывает)
    commands = [
        BotCommand("start", "🏠 Главное меню"),
        BotCommand("plans", "💎 Тарифы"),
        BotCommand("profile", "💼 Профиль")
    ]
    
    try:
        # Установка списка команд (синхронно)
        updater.bot.set_my_commands(commands)
        logger.info("✅ Меню команд установлено.")
    except error.TelegramError as e:
        logger.error(f"❌ Ошибка установки меню команд: {e}")
        
    logger.info("🚀 Bot started successfully!")
    
    # Начинаем Polling
    updater.start_polling()
    # Блокируем главный поток, пока бот не будет остановлен
    updater.idle()


if __name__ == '__main__':
    # Обернем запуск в try/except для отлова критических ошибок
    try:
        main()
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")