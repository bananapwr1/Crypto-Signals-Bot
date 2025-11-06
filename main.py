# main.py (Чистый интерфейс для Bothost.ru)
# В этом файле оставлены только обработчики команд и кнопок.
# Вся логика, требующая БД (Supabase) или аналитики (pandas, numpy), заменена заглушками (STUB).

import os
import logging
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

# --- Настройка Логирования ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Загрузка переменных окружения ---
load_dotenv()

# Используем переменные, адаптированные под предоставленный .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", 0)) 
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

# --- Константы ---
SUPPORT_CONTACT = "@banana_pwr"
MOSCOW_TZ = timezone(timedelta(hours=3))
POCKET_OPTION_REF_LINK = "https://pocket-friends.com/r/ugauihalod"
PROMO_CODE = "FRIENDUGAUIHALOD"

# Команды бота (для установки меню)
DEFAULT_BOT_COMMANDS = [
    ("start", "🏠 Главное меню"),
    ("status", "📊 Текущий статус"),
    ("signals", "⚡️ Получить сигнал"),
    ("admin", "🔑 Админ-панель (для администратора)")
]

# --- Функции-Заглушки для БД (будут заменены на реальную логику Supabase) ---

def check_or_create_user_stub(user_id, username):
    """
    STUB: Имитация проверки/создания пользователя в базе данных.
    Всегда возвращает True для запуска интерфейса.
    """
    logger.info(f"DB STUB: Проверка/создание пользователя {user_id} - {username}. Успешно.")
    return True 

def get_user_status_stub(user_id):
    """
    STUB: Имитация получения статуса пользователя.
    Возвращает фиктивные данные для отображения.
    """
    logger.info(f"DB STUB: Запрос статуса для {user_id}")
    return {
        'subscription_active': True,
        'subscription_end': datetime.now(MOSCOW_TZ) + timedelta(days=30),
        'signals_today': 5,
        'signals_limit': 10,
        'bank_balance': 1000.00
    }

# --- Обработчики Команд ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    
    # Заглушка: имитируем проверку пользователя
    if not check_or_create_user_stub(user.id, user.username):
        await update.message.reply_text("Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.")
        return

    keyboard = [
        [InlineKeyboardButton("⚡️ Получить сигнал (STUB)", callback_data='get_signal')],
        [InlineKeyboardButton("📊 Статус и баланс (STUB)", callback_data='status')],
        [InlineKeyboardButton("💰 Пополнить / Тарифы (STUB)", callback_data='plans')],
        [InlineKeyboardButton("🔑 Админ-панель (STUB)", callback_data='admin')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_html(
        f"👋 Добро пожаловать, {user.mention_html()}!\n\n"
        "Ваш интерфейс Crypto Signals Bot запущен.\n"
        "⚠️ Текущая версия - **ЧИСТЫЙ ИНТЕРФЕЙС**. "
        "Для работы с реальными данными необходима **Фаза 3: Интеграция с Supabase**.",
        reply_markup=reply_markup
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    status_data = get_user_status_stub(user_id)
    
    status_text = (
        "📊 **ВАШ СТАТУС (STUB)**\n"
        "-------------------------------------\n"
        f"💳 Подписка: {'✅ Активна' if status_data['subscription_active'] else '❌ Не активна'}\n"
        f"📅 Срок истечения: {status_data['subscription_end'].strftime('%d.%m.%Y %H:%M MSK')}\n"
        f"📈 Сигналов сегодня: {status_data['signals_today']} из {status_data['signals_limit']}\n"
        f"💰 Баланс банка: {status_data['bank_balance']:.2f} USDT (STUB)\n"
    )
    await update.message.reply_markdown(status_text)

async def signals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⚡️ **Получить сигнал:** Эта функция требует интеграции с ядром аналитики. Пока это заглушка (STUB).")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return

    keyboard = [
        [InlineKeyboardButton("Сброс статистики пользователя (STUB)", callback_data='admin_reset_user')],
        [InlineKeyboardButton("Сброс всех пользователей (STUB)", callback_data='admin_reset_all')],
        [InlineKeyboardButton("Статистика DB (STUB)", callback_data='admin_stats')],
        [InlineKeyboardButton("Назад в меню", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("🔑 **Админ-панель (STUB)**\nЗдесь вы можете управлять пользователями и статистикой.", reply_markup=reply_markup)


# --- Обработчик Кнопок (CallbackQuery) ---

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id

    if data == 'start':
        # Перезапуск команды start для обновления меню
        await start_command(query, context)
        
    elif data == 'status':
        # Перезапуск команды status
        await status_command(query, context)
        
    elif data == 'admin':
        # Перезапуск команды admin
        await admin_command(query, context)

    # --- Обработка Админ-кнопок ---
    elif data == 'admin_reset_user':
        if user_id == ADMIN_USER_ID:
            await query.edit_message_text(
                "❗️ **Сброс пользователя (STUB)**: "
                "Введите ID пользователя, которого нужно сбросить (например, /reset_user 123456789)."
            )
        else:
            await query.edit_message_text("❌ Нет прав.")

    elif data == 'admin_reset_all':
        if user_id == ADMIN_USER_ID:
            # Здесь должна быть логика из reset_all_stats.py
            await query.edit_message_text("✅ **ВСЯ СТАТИСТИКА СБРОШЕНА (STUB)**.\n"
                                          "Это действие требует реализации Supabase.")
        else:
            await query.edit_message_text("❌ Нет прав.")
            
    # --- Общие кнопки ---
    else:
        await query.edit_message_text(f"Кнопка '{data}' нажата. Это заглушка (STUB). Требуется реализация логики.")

# --- Обработчик Сброса Пользователя (Админ-команда) ---

async def reset_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Только администратор может использовать эту команду.")
        return

    try:
        # Ожидаем ID после команды, например: /reset_user 123456789
        target_id = int(context.args[0])
        # Здесь должна быть логика из reset_user.py
        await update.message.reply_text(f"✅ Пользователь с ID {target_id} **сброшен (STUB)**. "
                                        "Для реальной работы замените эту заглушку логикой Supabase.")
    except (IndexError, ValueError):
        await update.message.reply_text("❗️ Неверный формат. Используйте: /reset_user <ID_пользователя>")


# --- Главная функция запуска ---

def main() -> None:
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден. Проверьте .env файл или переменные окружения на хостинге.")
        return

    # Проверка, считался ли ADMIN_USER_ID
    if not ADMIN_USER_ID or ADMIN_USER_ID == 0:
        logger.warning("❗️ ADMIN_USER_ID не установлен или равен 0. Админ-команды могут быть недоступны.")

    logger.info(f"✅ Токен считан. Начало токена: {BOT_TOKEN[:5]}...")

    # Использование старого, стабильного метода Updater/run_polling
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Добавление обработчиков
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("status", status_command))
    dispatcher.add_handler(CommandHandler("signals", signals_command))
    dispatcher.add_handler(CommandHandler("admin", admin_command))
    dispatcher.add_handler(CommandHandler("reset_user", reset_user_command)) # Админ-команда

    # Обработчик кнопок
    dispatcher.add_handler(CallbackQueryHandler(button_callback))

    # Установка меню команд (синхронно, так как run_polling блокирующий)
    try:
        dispatcher.bot.set_my_commands(
            [BotCommand(command, description) for command, description in DEFAULT_BOT_COMMANDS]
        )
        logger.info("✅ Меню команд установлено.")
    except Exception as e:
        logger.error(f"❌ Ошибка установки меню команд: {e}")

    logger.info("🚀 Bot started successfully!")
    print("✅ Crypto Signals Bot is running...")
    
    # Запуск бота (блокирующая функция)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()


