# main.py: Telegram Bot с современным API (Application)
import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = 7746862973  # Ваш Telegram ID

# Заглушка базы данных (замените на реальную реализацию)
class DatabaseManager:
    def check_or_create_user(self, user_id: int, username: str) -> bool:
        logger.info(f"DB: Создание/проверка пользователя {user_id}")
        return True
    
    def get_user_status(self, user_id: int) -> dict:
        return {"status": "Active", "plan": "Basic"}

db = DatabaseManager()

# Вспомогательные функции
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_USER_ID

def get_main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("💎 Тарифы и подписки", callback_data='plans')],
        [
            InlineKeyboardButton("💰 Банк", callback_data='bank'),
            InlineKeyboardButton("💼 Профиль", callback_data='profile')
        ],
        [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')]
    ]
    
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ АДМИН ПАНЕЛЬ", callback_data='admin_panel')])
    
    return InlineKeyboardMarkup(keyboard)

# Обработчики команд
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.check_or_create_user(user.id, user.username or f"user_{user.id}")
    
    welcome_text = f"🤖 Привет, {user.first_name}! Я твой бот-помощник."
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu_keyboard(user.id)
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔️ Доступ запрещен.")
        return
    
    keyboard = [
        [InlineKeyboardButton("Статистика", callback_data='admin_stats'),
         InlineKeyboardButton("Сброс статистики", callback_data='admin_reset_stats')],
        [InlineKeyboardButton("Управление пользователями", callback_data='admin_user_manage')],
        [InlineKeyboardButton("Назад в меню", callback_data='menu')]
    ]
    
    await update.message.reply_text(
        "🛠️ **АДМИН ПАНЕЛЬ**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Обработчик кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == 'menu':
        user_status = db.get_user_status(user_id)
        await query.edit_message_text(
            f"🏠 **ГЛАВНОЕ МЕНЮ**\nСтатус: {user_status['status']}",
            reply_markup=get_main_menu_keyboard(user_id)
        )
    
    elif data == 'admin_panel':
        # Отправляем админ-панель как новое сообщение
        keyboard = [
            [InlineKeyboardButton("Статистика", callback_data='admin_stats'),
             InlineKeyboardButton("Сброс статистики", callback_data='admin_reset_stats')],
            [InlineKeyboardButton("Управление пользователями", callback_data='admin_user_manage')],
            [InlineKeyboardButton("Назад в меню", callback_data='menu')]
        ]
        await query.edit_message_text(
            "🛠️ **АДМИН ПАНЕЛЬ**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == 'profile':
        user_status = db.get_user_status(user_id)
        await query.edit_message_text(
            f"💼 **ПРОФИЛЬ**\n"
            f"ID: {user_id}\n"
            f"Статус: {user_status['status']}\n"
            f"Тариф: {user_status['plan']}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data='menu')]
            ])
        )
    
    else:
        await query.edit_message_text(
            f"🚧 Функция '{data}' в разработке",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад в меню", callback_data='menu')]
            ])
        )

# Настройка команд бота
async def setup_commands(application):
    commands = [
        BotCommand("start", "🏠 Главное меню"),
        BotCommand("admin", "🛠️ Админ панель")
    ]
    await application.bot.set_my_commands(commands)

# Основная функция
def main():
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден!")
        return
    
    # Создаем Application (без use_context!)
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Настраиваем команды при запуске
    application.post_init(setup_commands)
    
    logger.info("🚀 Бот запускается...")
    
    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()