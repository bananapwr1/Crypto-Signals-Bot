# main.py: Главный файл чистого интерфейса Telegram бота (Application)
# Использует минимальные зависимости и заглушки для Supabase.

import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, 
    filters, ContextTypes, CallbackContext
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
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "7746862973"))  # Исправлено на ваш ID
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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    user = update.effective_user

    # Инициализация пользователя в БД
    db.check_or_create_user(user.id, user.username or f"user_{user.id}")

    welcome_text = (
        f"🤖 Привет, {user.first_name}! Я твой бот-помощник.\n"
        f"Здесь ты можешь управлять подписками, настройками и сигналами."
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu_keyboard(user.id)
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /admin."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔️ Доступ запрещен. Вы не администратор.")
        return

    keyboard = [
        [InlineKeyboardButton("Статистика", callback_data='admin_stats'),
         InlineKeyboardButton("Сброс (Stats)", callback_data='admin_reset_stats')],
        [InlineKeyboardButton("Управление юзерами", callback_data='admin_user_manage')],
        [InlineKeyboardButton("Назад в меню", callback_data='menu')]
    ]

    await update.message.reply_text(
        "🛠️ **АДМИН ПАНЕЛЬ**\nВыберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def reset_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Админ-команда для сброса данных пользователя."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔️ Доступ запрещен.")
        return

    if not context.args:
        await update.message.reply_text(
            "⚙️ **СБРОС ПОЛЬЗОВАТЕЛЯ**\n"
            "Использование: /reset_user [ID пользователя]"
        )
        return

    try:
        target_user_id = int(context.args[0])
        # STUB: Здесь будет вызов db.reset_user(target_user_id)
        await update.message.reply_text(
            f"✅ **[DB STUB]** Сброс данных пользователя с ID `{target_user_id}` выполнен (пока только заглушка)."
        )
    except ValueError:
        await update.message.reply_text("❌ Неверный ID пользователя. ID должен быть числом.")

async def reset_all_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Админ-команда для сброса всей статистики."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔️ Доступ запрещен.")
        return

    # STUB: Здесь будет вызов db.reset_all_stats()
    await update.message.reply_text(
        "⚠️ **[DB STUB]** Сброс ВСЕЙ статистики пользователей выполнен (пока только заглушка)."
    )

# --- Обработчик кнопок (CallbackQuery) ---

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на инлайн-кнопки."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == 'menu' or data == 'profile':
        user_status = db.get_user_status(user_id) # Получаем статус (или заглушку)

        # Обновляем сообщение с главным меню
        await query.edit_message_text(
            f"🏠 **ГЛАВНОЕ МЕНЮ**\nВаш статус: {user_status['status'] if user_status else 'Неизвестен'}",
            reply_markup=get_main_menu_keyboard(user_id)
        )

    elif data == 'admin_panel':
        # Создаем фейковое сообщение для вызова админ-панели
        fake_update = Update(update.update_id, message=query.message)
        await admin_command(fake_update, context)

    # Обработка других кнопок (STUB)
    elif data in ['plans', 'bank', 'settings', 'admin_stats', 'admin_reset_stats', 'admin_user_manage']:
        await query.edit_message_text(f"🚧 **[STUB]** Вы нажали: {data}. Эта функция пока не реализована (Фаза 3).")

# --- Основная функция запуска ---

async def post_init(application: Application) -> None:
    """Функция, выполняемая после инициализации бота."""
    commands = [
        BotCommand("start", "🏠 Главное меню"),
        BotCommand("plans", "💎 Тарифы"),
        BotCommand("profile", "💼 Профиль")
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ Меню команд установлено.")

def main() -> None:
    """Запускает бота."""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден. Проверьте .env файл или переменные окружения на хостинге.")
        return

    logger.info("✅ Токен считан. Начало токена: %s...", BOT_TOKEN[:5])

    # Создаем Application с современным синтаксисом
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("reset_user", reset_user_command))
    application.add_handler(CommandHandler("reset_all_stats", reset_all_stats_command))
    application.add_handler(CallbackQueryHandler(button_callback))

    logger.info("🚀 Bot started successfully!")

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")