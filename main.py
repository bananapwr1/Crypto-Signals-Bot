"""
main.py - Монолитный сервис для Telegram-бота с автоторговлей
Версия: 1.0 (Модульная архитектура)
Автор: AI Architect
Дата: 2025-12-09

Архитектура:
- UI + Админка + Автоторговля + Аналитика в одном процессе
- Параллельные фоновые задачи через asyncio.gather
- Модульная структура для легкой поддержки
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

# Загрузка переменных окружения в самом начале
from dotenv import load_dotenv
load_dotenv()

# ==============================
# ИМПОРТЫ МОДУЛЕЙ СИСТЕМЫ
# ==============================

# Конфигурация
try:
    from config import config, Config
except ImportError:
    print("❌ ОШИБКА: Не найден модуль config.py")
    sys.exit(1)

# База данных
try:
    from db_manager import DatabaseManager
except ImportError:
    print("⚠️ ПРЕДУПРЕЖДЕНИЕ: Модуль db_manager.py не найден, создайте его")
    DatabaseManager = None

# Криптографические утилиты
try:
    from crypto_utils import encrypt_ssid, decrypt_ssid, generate_key
except ImportError:
    print("⚠️ ПРЕДУПРЕЖДЕНИЕ: Модуль crypto_utils.py не найден, создайте его")
    encrypt_ssid = decrypt_ssid = generate_key = None

# AI Core - Аналитика рынка
try:
    from ai_core import AICore
except ImportError:
    print("⚠️ ПРЕДУПРЕЖДЕНИЕ: Модуль ai_core.py не найден, создайте его")
    AICore = None

# Автоторговля
try:
    from autotrader import AutoTrader
except ImportError:
    print("⚠️ ПРЕДУПРЕЖДЕНИЕ: Модуль autotrader.py не найден, создайте его")
    AutoTrader = None

# Админ-менеджер
try:
    from admin_manager import AdminManager
except ImportError:
    print("⚠️ ПРЕДУПРЕЖДЕНИЕ: Модуль admin_manager.py не найден, создайте его")
    AdminManager = None

# UI-обработчики
try:
    from ui_handlers import UIHandlers
except ImportError:
    print("⚠️ ПРЕДУПРЕЖДЕНИЕ: Модуль ui_handlers.py не найден, создайте его")
    UIHandlers = None

# Pocket Option API
try:
    from pocket_option_api import PocketOptionAPI
except ImportError:
    print("⚠️ ПРЕДУПРЕЖДЕНИЕ: Модуль pocket_option_api.py не найден, создайте его")
    PocketOptionAPI = None

# Telegram API
try:
    from telegram import Update, BotCommand
    from telegram.ext import (
        Application,
        CommandHandler,
        CallbackQueryHandler,
        MessageHandler,
        ContextTypes,
        filters
    )
except ImportError:
    print("❌ ОШИБКА: python-telegram-bot не установлен")
    print("Установите: pip install python-telegram-bot")
    sys.exit(1)

# ==============================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ==============================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ==============================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ==============================

# Инстансы модулей (инициализируются в main_async)
db_manager: Optional[DatabaseManager] = None
ai_core: Optional[AICore] = None
autotrader: Optional[AutoTrader] = None
admin_manager: Optional[AdminManager] = None
ui_handlers: Optional[UIHandlers] = None
pocket_api: Optional[PocketOptionAPI] = None

# Telegram Application
app: Optional[Application] = None

# ==============================
# TELEGRAM HANDLERS - КЛИЕНТСКИЕ
# ==============================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start - Главное меню"""
    user = update.effective_user
    
    if ui_handlers:
        await ui_handlers.handle_start(update, context)
    else:
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            "Бот в процессе инициализации. Попробуйте позже."
        )


async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /plans - Тарифы и подписки"""
    if ui_handlers:
        await ui_handlers.handle_plans(update, context)
    else:
        await update.message.reply_text("⚠️ Модуль UI не загружен")


async def bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /bank - Управление банком"""
    if ui_handlers:
        await ui_handlers.handle_bank(update, context)
    else:
        await update.message.reply_text("⚠️ Модуль UI не загружен")


async def autotrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /autotrade - Автоторговля (VIP)"""
    if ui_handlers:
        await ui_handlers.handle_autotrade(update, context)
    else:
        await update.message.reply_text("⚠️ Модуль UI не загружен")


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /settings - Настройки"""
    if ui_handlers:
        await ui_handlers.handle_settings(update, context)
    else:
        await update.message.reply_text("⚠️ Модуль UI не загружен")


async def short_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /short - SHORT сигнал"""
    if ui_handlers:
        await ui_handlers.handle_short_signal(update, context)
    else:
        await update.message.reply_text("⚠️ Модуль UI не загружен")


async def long_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /long - LONG сигнал"""
    if ui_handlers:
        await ui_handlers.handle_long_signal(update, context)
    else:
        await update.message.reply_text("⚠️ Модуль UI не загружен")


async def my_longs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /my_longs - Мои LONG позиции"""
    if ui_handlers:
        await ui_handlers.handle_my_longs(update, context)
    else:
        await update.message.reply_text("⚠️ Модуль UI не загружен")


async def my_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /my_stats - Моя статистика"""
    if ui_handlers:
        await ui_handlers.handle_my_stats(update, context)
    else:
        await update.message.reply_text("⚠️ Модуль UI не загружен")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /help - Помощь"""
    if ui_handlers:
        await ui_handlers.handle_help(update, context)
    else:
        await update.message.reply_text("⚠️ Модуль UI не загружен")


# ==============================
# TELEGRAM HANDLERS - АДМИНСКИЕ
# ==============================

async def manager_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /manager - Админ-панель"""
    user = update.effective_user
    
    # Проверка прав администратора
    if user.id not in config.ADMIN_IDS:
        await update.message.reply_text("⛔️ Доступ запрещен. Эта команда только для администраторов.")
        return
    
    if admin_manager:
        await admin_manager.handle_manager_panel(update, context)
    else:
        await update.message.reply_text("⚠️ Модуль админки не загружен")


async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /logs - Просмотр логов"""
    user = update.effective_user
    
    if user.id not in config.ADMIN_IDS:
        await update.message.reply_text("⛔️ Доступ запрещен.")
        return
    
    if admin_manager:
        await admin_manager.handle_logs(update, context)
    else:
        await update.message.reply_text("⚠️ Модуль админки не загружен")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /stats - Статистика бота"""
    user = update.effective_user
    
    if user.id not in config.ADMIN_IDS:
        await update.message.reply_text("⛔️ Доступ запрещен.")
        return
    
    if admin_manager:
        await admin_manager.handle_stats(update, context)
    else:
        await update.message.reply_text("⚠️ Модуль админки не загружен")


async def llm_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик LLM-чата (для админов)"""
    user = update.effective_user
    
    if user.id not in config.ADMIN_IDS:
        return  # Игнорируем сообщения не от админов
    
    if admin_manager:
        await admin_manager.handle_llm_chat(update, context)
    else:
        await update.message.reply_text("⚠️ Модуль LLM не загружен")


# ==============================
# CALLBACK QUERY HANDLER
# ==============================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик inline кнопок"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    # Проверяем, является ли это админским callback
    if data.startswith('admin_'):
        if user.id not in config.ADMIN_IDS:
            await query.edit_message_text("⛔️ Доступ запрещен.")
            return
        
        if admin_manager:
            await admin_manager.handle_callback(update, context)
        else:
            await query.edit_message_text("⚠️ Модуль админки не загружен")
    else:
        # Клиентские callback
        if ui_handlers:
            await ui_handlers.handle_callback(update, context)
        else:
            await query.edit_message_text("⚠️ Модуль UI не загружен")


# ==============================
# ОБРАБОТЧИК ОШИБОК
# ==============================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик ошибок"""
    logger.error(f"Update {update} caused error: {context.error}")
    
    # Уведомляем пользователя
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Произошла ошибка при обработке вашего запроса.\n"
                "Попробуйте позже или обратитесь в поддержку."
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке: {e}")


# ==============================
# НАСТРОЙКА КОМАНД БОТА
# ==============================

async def setup_bot_commands(application: Application) -> None:
    """Настройка меню команд бота"""
    commands = [
        BotCommand("start", "🏠 Главное меню"),
        BotCommand("plans", "💎 Тарифы и подписки"),
        BotCommand("bank", "💰 Управление банком"),
        BotCommand("autotrade", "🤖 Автоторговля (VIP)"),
        BotCommand("settings", "⚙️ Настройки"),
        BotCommand("short", "⚡ SHORT сигнал (1-5 мин)"),
        BotCommand("long", "🔵 LONG сигнал (1-4 часа)"),
        BotCommand("my_longs", "📋 Мои LONG позиции"),
        BotCommand("my_stats", "📊 Моя статистика"),
        BotCommand("help", "❓ Помощь и инструкции"),
    ]
    
    await application.bot.set_my_commands(commands)
    logger.info("✅ Команды бота настроены")


# ==============================
# ФОНОВЫЕ ЦИКЛЫ
# ==============================

async def run_analysis_cycle():
    """
    Бесконечный цикл аналитики рынка
    Вызывает ai_core.run_analysis_cycle()
    """
    if not ai_core:
        logger.warning("⚠️ AI Core не инициализирован, аналитика отключена")
        return
    
    logger.info("🔍 Запуск цикла аналитики рынка...")
    
    try:
        await ai_core.run_analysis_cycle()
    except Exception as e:
        logger.error(f"❌ Ошибка в цикле аналитики: {e}")


async def run_autotrade_cycle():
    """
    Бесконечный цикл автоторговли + парсинга TG
    Вызывает autotrader.run_autotrade_and_parser()
    """
    if not autotrader:
        logger.warning("⚠️ AutoTrader не инициализирован, автоторговля отключена")
        return
    
    logger.info("🤖 Запуск цикла автоторговли и парсинга...")
    
    try:
        await autotrader.run_autotrade_and_parser()
    except Exception as e:
        logger.error(f"❌ Ошибка в цикле автоторговли: {e}")


# ==============================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЕЙ
# ==============================

async def initialize_modules():
    """Инициализация всех модулей системы"""
    global db_manager, ai_core, autotrader, admin_manager, ui_handlers, pocket_api
    
    logger.info("=" * 60)
    logger.info("🚀 Инициализация модулей...")
    logger.info("=" * 60)
    
    # 1. База данных
    if DatabaseManager:
        try:
            db_manager = DatabaseManager()
            logger.info("✅ DatabaseManager инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации DatabaseManager: {e}")
    
    # 2. Pocket Option API
    if PocketOptionAPI:
        try:
            pocket_api = PocketOptionAPI()
            logger.info("✅ PocketOptionAPI инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации PocketOptionAPI: {e}")
    
    # 3. AI Core
    if AICore:
        try:
            ai_core = AICore(db_manager=db_manager)
            logger.info("✅ AICore инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации AICore: {e}")
    
    # 4. AutoTrader
    if AutoTrader:
        try:
            autotrader = AutoTrader(
                db_manager=db_manager,
                pocket_api=pocket_api
            )
            logger.info("✅ AutoTrader инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации AutoTrader: {e}")
    
    # 5. Admin Manager
    if AdminManager:
        try:
            admin_manager = AdminManager(
                db_manager=db_manager,
                ai_core=ai_core,
                autotrader=autotrader
            )
            logger.info("✅ AdminManager инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации AdminManager: {e}")
    
    # 6. UI Handlers
    if UIHandlers:
        try:
            ui_handlers = UIHandlers(
                db_manager=db_manager,
                pocket_api=pocket_api
            )
            logger.info("✅ UIHandlers инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации UIHandlers: {e}")
    
    logger.info("=" * 60)
    logger.info("✅ Инициализация модулей завершена")
    logger.info("=" * 60)


# ==============================
# ГЛАВНАЯ ФУНКЦИЯ
# ==============================

async def main_async():
    """
    Главная асинхронная функция
    Запускает Telegram UI + 2 фоновых цикла параллельно
    """
    global app
    
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК МОНОЛИТНОГО СЕРВИСА")
    logger.info("=" * 60)
    
    # Проверка конфигурации
    try:
        Config.validate()
        logger.info("✅ Конфигурация валидна")
    except ValueError as e:
        logger.error(f"❌ Ошибка конфигурации: {e}")
        sys.exit(1)
    
    # Логирование переменных окружения
    logger.info(f"📝 BOT_TOKEN: {config.TELEGRAM_TOKEN[:10]}...")
    logger.info(f"📝 SUPABASE_URL: {config.SUPABASE_URL[:30]}..." if config.SUPABASE_URL else "❌ SUPABASE_URL не задан")
    logger.info(f"📝 ADMIN_IDS: {config.ADMIN_IDS}")
    
    # Проверка наличия ANTHROPIC_API_KEY для LLM
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if anthropic_key:
        logger.info(f"✅ ANTHROPIC_API_KEY найден: {anthropic_key[:10]}...")
    else:
        logger.warning("⚠️ ANTHROPIC_API_KEY не найден, LLM-чат будет недоступен")
    
    # Инициализация модулей
    await initialize_modules()
    
    # Создание Telegram приложения
    logger.info("📱 Создание Telegram Application...")
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    # Регистрация обработчиков команд - КЛИЕНТСКИЕ
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("plans", plans_command))
    app.add_handler(CommandHandler("bank", bank_command))
    app.add_handler(CommandHandler("autotrade", autotrade_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("short", short_command))
    app.add_handler(CommandHandler("long", long_command))
    app.add_handler(CommandHandler("my_longs", my_longs_command))
    app.add_handler(CommandHandler("my_stats", my_stats_command))
    app.add_handler(CommandHandler("help", help_command))
    
    # Регистрация обработчиков команд - АДМИНСКИЕ
    app.add_handler(CommandHandler("manager", manager_command))
    app.add_handler(CommandHandler("logs", logs_command))
    app.add_handler(CommandHandler("stats", stats_command))
    
    # Обработчик LLM-чата (текстовые сообщения от админов)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, llm_chat_handler))
    
    # Обработчик кнопок
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик ошибок
    app.add_error_handler(error_handler)
    
    # Настройка команд бота
    await setup_bot_commands(app)
    
    logger.info("✅ Telegram Application готов")
    logger.info("=" * 60)
    
    # Инициализация приложения
    await app.initialize()
    await app.start()
    
    logger.info("🎯 СИСТЕМА ЗАПУЩЕНА!")
    logger.info("=" * 60)
    logger.info("📱 Telegram Bot: ACTIVE")
    logger.info("🔍 Аналитика: STARTING")
    logger.info("🤖 Автоторговля: STARTING")
    logger.info("=" * 60)
    
    # Запуск параллельных задач через asyncio.gather
    try:
        await asyncio.gather(
            # 1. Telegram Polling (Блокирующий)
            app.updater.start_polling(allowed_updates=Update.ALL_TYPES),
            
            # 2. Цикл аналитики рынка (Бесконечный)
            run_analysis_cycle(),
            
            # 3. Цикл автоторговли + парсинга TG (Бесконечный)
            run_autotrade_cycle(),
            
            return_exceptions=True
        )
    except KeyboardInterrupt:
        logger.info("⚠️ Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        # Graceful shutdown
        logger.info("🛑 Остановка сервиса...")
        await app.stop()
        await app.shutdown()
        logger.info("✅ Сервис остановлен")


# ==============================
# ТОЧКА ВХОДА
# ==============================

def main():
    """Синхронная точка входа"""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("⚠️ Программа прервана пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка запуска: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
