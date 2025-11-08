"""
bot_interface.py - ИСПРАВЛЕННЫЙ Telegram интерфейс бота
С реальной работой с Supabase и проверкой окружения.
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Импорт config
try:
    from config import config, Config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    logger.error("❌ config.py не найден")
    config = None

# Импорт Telegram API (v20+)
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.error("❌ python-telegram-bot не установлен")

# Импорт database
try:
    from database import database
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    database = None
    logger.warning("⚠️ database.py не найден, работа в режиме без БД")


def check_environment():
    """Проверка наличия всех необходимых переменных окружения"""
    required_vars = ['BOT_TOKEN', 'NEXT_PUBLIC_SUPABASE_URL', 'NEXT_PUBLIC_SUPABASE_ANON_KEY']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        error_msg = f"❌ Отсутствуют обязательные переменные окружения: {', '.join(missing)}"
        logger.error(error_msg)
        logger.error("Проверьте файл .env или настройки BotHost.ru!")
        raise Exception(error_msg)
    
    logger.info("✅ Все необходимые переменные окружения найдены")
    return True


# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')


# --- Обработчики команд ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start - Приветствие и главное меню"""
    user = update.effective_user
    
    # Добавляем пользователя в базу данных
    if DATABASE_AVAILABLE and database:
        database.add_user({
            'user_id': user.id,
            'username': user.username or f'user_{user.id}',
            'first_name': user.first_name,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Логируем команду
        database.add_command({
            'user_id': user.id,
            'command': 'start',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # Проверяем является ли пользователь админом
    is_admin = config and user.id in config.ADMIN_IDS
    
    keyboard = [
        [InlineKeyboardButton("💎 Тарифы и подписки", callback_data='plans')],
        [
            InlineKeyboardButton("💰 Банк", callback_data='bank'),
            InlineKeyboardButton("💼 Профиль", callback_data='profile')
        ],
        [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')]
    ]
    
    if is_admin:
        keyboard.append([InlineKeyboardButton("🛠️ АДМИН ПАНЕЛЬ", callback_data='admin_panel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f'👋 Привет, {user.first_name}!\n\n'
    welcome_text += '🤖 Я бот-интерфейс для управления.\n'
    welcome_text += 'Выберите действие:'
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /status - Показать текущий статус"""
    user = update.effective_user
    
    # Логируем команду
    if DATABASE_AVAILABLE and database:
        database.add_command({
            'user_id': user.id,
            'command': 'status',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Получаем статус из базы
        status = database.get_status()
        status_text = (
            f"📊 **Статус системы**\n\n"
            f"👥 Пользователей: {status.get('total_users', 0)}\n"
            f"📝 Команд выполнено: {status.get('total_commands', 0)}\n"
            f"⚡ Статус: {status.get('status', 'unknown')}\n"
        )
    else:
        status_text = "📊 **Статус системы**\n\nРабота в режиме без БД"
    
    await update.message.reply_text(status_text, parse_mode='Markdown')


async def trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /trade - Записать намерение торговли"""
    user = update.effective_user
    
    # Записываем команду в базу данных
    if DATABASE_AVAILABLE and database:
        database.add_command({
            'user_id': user.id,
            'command': 'trade',
            'timestamp': datetime.utcnow().isoformat(),
            'data': {'intent': 'trade_request'}
        })
    
    await update.message.reply_text(
        "💰 **Trade команда**\n\n"
        "Ваше намерение торговли записано.\n"
        "Эта команда сохраняет информацию в базе данных.\n\n"
        "⚠️ Примечание: Торговая логика удалена из системы."
    )


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /stop - Остановить операции"""
    user = update.effective_user
    
    # Записываем команду
    if DATABASE_AVAILABLE and database:
        database.add_command({
            'user_id': user.id,
            'command': 'stop',
            'timestamp': datetime.utcnow().isoformat(),
            'data': {'intent': 'stop_request'}
        })
    
    await update.message.reply_text(
        "🛑 **Stop команда**\n\n"
        "Команда остановки записана в систему."
    )


# --- Обработчик кнопок ---

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /admin - Админ панель"""
    user = update.effective_user
    
    # Проверяем права администратора
    if not config or user.id not in config.ADMIN_IDS:
        await update.message.reply_text("⛔️ Доступ запрещен. Эта команда только для администраторов.")
        return
    
    # Логируем команду
    if DATABASE_AVAILABLE and database:
        database.add_command({
            'user_id': user.id,
            'command': 'admin',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats'),
         InlineKeyboardButton("🔄 Сброс статистики", callback_data='admin_reset_stats')],
        [InlineKeyboardButton("👥 Пользователи", callback_data='admin_users')],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data='menu')]
    ]
    
    await update.message.reply_text(
        "🛠️ **АДМИН ПАНЕЛЬ**\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик inline кнопок"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    # Логируем взаимодействие
    if DATABASE_AVAILABLE and database:
        database.add_command({
            'user_id': user.id,
            'command': f'button_{data}',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # Главное меню
    if data == 'menu':
        is_admin = config and user.id in config.ADMIN_IDS
        
        keyboard = [
            [InlineKeyboardButton("💎 Тарифы и подписки", callback_data='plans')],
            [
                InlineKeyboardButton("💰 Банк", callback_data='bank'),
                InlineKeyboardButton("💼 Профиль", callback_data='profile')
            ],
            [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')]
        ]
        
        if is_admin:
            keyboard.append([InlineKeyboardButton("🛠️ АДМИН ПАНЕЛЬ", callback_data='admin_panel')])
        
        await query.edit_message_text(
            "🏠 **ГЛАВНОЕ МЕНЮ**\n\nВыберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # Админ панель
    elif data == 'admin_panel':
        if not config or user.id not in config.ADMIN_IDS:
            await query.edit_message_text("⛔️ Доступ запрещен.")
            return
        
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats'),
             InlineKeyboardButton("🔄 Сброс", callback_data='admin_reset_stats')],
            [InlineKeyboardButton("👥 Пользователи", callback_data='admin_users')],
            [InlineKeyboardButton("⬅️ Назад в меню", callback_data='menu')]
        ]
        
        await query.edit_message_text(
            "🛠️ **АДМИН ПАНЕЛЬ**\n\nВыберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # Админ статистика
    elif data == 'admin_stats':
        if not config or user.id not in config.ADMIN_IDS:
            await query.edit_message_text("⛔️ Доступ запрещен.")
            return
        
        if DATABASE_AVAILABLE and database:
            status = database.get_status()
            users = database.get_users()
            commands = database.get_commands(limit=1000)
            
            text = (
                "📊 **СТАТИСТИКА БОТА**\n\n"
                f"👥 Всего пользователей: {len(users)}\n"
                f"📝 Всего команд: {len(commands)}\n"
                f"⚡ Статус: {status.get('status', 'unknown')}\n"
                f"🕐 Обновлено: {datetime.utcnow().strftime('%H:%M:%S')}"
            )
        else:
            text = "📊 **СТАТИСТИКА**\n\nБаза данных недоступна"
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='admin_panel')]]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # Профиль
    elif data == 'profile':
        if DATABASE_AVAILABLE and database:
            text = (
                f"💼 **ПРОФИЛЬ**\n\n"
                f"👤 ID: {user.id}\n"
                f"📝 Username: @{user.username or 'не указан'}\n"
                f"👋 Имя: {user.first_name}"
            )
        else:
            text = "💼 **ПРОФИЛЬ**\n\nБаза данных недоступна"
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='menu')]]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # Статус
    elif data == 'status':
        if DATABASE_AVAILABLE and database:
            status = database.get_status()
            text = (
                f"📊 **Статус системы**\n\n"
                f"👥 Пользователей: {status.get('total_users', 0)}\n"
                f"📝 Команд: {status.get('total_commands', 0)}\n"
                f"⚡ Статус: {status.get('status', 'unknown')}"
            )
        else:
            text = "📊 **Статус**\n\nРабота без БД"
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='menu')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    # Trade
    elif data == 'trade':
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='menu')]]
        await query.edit_message_text(
            "💰 **Trade**\n\n"
            "Ваше намерение торговли записано в систему.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # Stop
    elif data == 'stop':
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='menu')]]
        await query.edit_message_text(
            "🛑 **Stop**\n\n"
            "Команда остановки выполнена.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # Прочие кнопки
    else:
        keyboard = [[InlineKeyboardButton("⬅️ Назад в меню", callback_data='menu')]]
        await query.edit_message_text(
            f"🚧 Функция '{data}' в разработке",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# --- Обработчик неизвестных команд ---

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик неизвестных команд"""
    await update.message.reply_text(
        "❓ Неизвестная команда.\n\n"
        "Доступные команды:\n"
        "/start - Начать работу\n"
        "/status - Статус системы\n"
        "/trade - Записать намерение торговли\n"
        "/stop - Остановить операции"
    )


# --- Обработчик ошибок ---

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")


# --- Основная функция ---

async def setup_commands(application):
    """Настройка команд бота для меню"""
    commands = [
        BotCommand("start", "🏠 Главное меню"),
        BotCommand("status", "📊 Статус системы"),
        BotCommand("trade", "💰 Записать намерение торговли"),
        BotCommand("stop", "🛑 Остановить операции"),
        BotCommand("admin", "🛠️ Админ панель")
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ Команды бота настроены")


def main():
    """Запуск бота"""
    logger.info("=" * 60)
    logger.info("🚀 Запуск Crypto Signals Bot Interface")
    logger.info("=" * 60)
    
    # Проверка наличия необходимых библиотек
    if not TELEGRAM_AVAILABLE:
        logger.error("❌ python-telegram-bot не установлен. Установите: pip install python-telegram-bot")
        return
    
    # Проверка переменных окружения
    try:
        check_environment()
    except Exception as e:
        logger.error(f"❌ Ошибка проверки окружения: {e}")
        return
    
    # Валидация конфигурации
    if CONFIG_AVAILABLE and config:
        try:
            Config.validate()
            logger.info("✅ Конфигурация валидна")
        except ValueError as e:
            logger.error(f"❌ Ошибка конфигурации: {e}")
            return
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден в переменных окружения")
        return
    
    logger.info(f"🤖 BOT_TOKEN: {BOT_TOKEN[:10]}...")
    logger.info(f"💾 Database: {'Available' if DATABASE_AVAILABLE else 'Unavailable'}")
    logger.info(f"⚙️ Config: {'Available' if CONFIG_AVAILABLE else 'Unavailable'}")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("trade", trade_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("admin", admin_command))
    
    # Регистрируем обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик неизвестных команд
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Настраиваем команды бота
    application.post_init = setup_commands
    
    logger.info("✅ Bot Interface готов к запуску")
    logger.info("=" * 60)
    
    # Запускаем polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)


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
