#!/usr/bin/env python3
"""
main.py - Точка входа монолитного сервиса
Версия: 2.0
Дата: 2025-12-10

Координирует:
- Telegram Bot UI (polling)
- AI Core (аналитика рынка)
- AutoTrader (торговля на основе сигналов из БД)
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timezone

# Python-telegram-bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Импорт модулей проекта
from config import Config, config
from db_manager import DatabaseManager  # Используем расширенный DatabaseManager
from ai_core import AICore
from autotrader import AutoTrader
from ui_handlers import UIHandlers
from admin_manager import AdminManager
from pocket_option_api import PocketOptionAPI

# ============================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ============================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


# ============================================
# ПРОВЕРКА АДМИНИСТРАТОРА
# ============================================

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in config.ADMIN_IDS


# ============================================
# ИНИЦИАЛИЗАЦИЯ КОМПОНЕНТОВ
# ============================================

def init_components():
    """
    Инициализация всех компонентов системы
    
    Returns:
        Tuple: (db_manager, pocket_api, ai_core, autotrader, ui_handlers, admin_manager)
    """
    logger.info("=" * 60)
    logger.info("🚀 ИНИЦИАЛИЗАЦИЯ КОМПОНЕНТОВ")
    logger.info("=" * 60)
    
    # 1. Database Manager (Supabase)
    logger.info("📊 Инициализация Database Manager...")
    db_manager = DatabaseManager()
    
    # 2. Pocket Option API
    logger.info("💰 Инициализация Pocket Option API...")
    pocket_api = PocketOptionAPI()
    
    # 3. AI Core (аналитика рынка)
    logger.info("🤖 Инициализация AI Core...")
    ai_core = AICore(db_manager=db_manager)
    
    # 4. AutoTrader (торговля на основе сигналов из БД)
    logger.info("🔄 Инициализация AutoTrader...")
    autotrader = AutoTrader(db_manager=db_manager, pocket_api=pocket_api)
    
    # 5. UI Handlers (клиентский интерфейс)
    logger.info("📱 Инициализация UI Handlers...")
    ui_handlers = UIHandlers(db_manager=db_manager, pocket_api=pocket_api)
    
    # 6. Admin Manager (админ-панель + LLM-чат)
    logger.info("👨‍💼 Инициализация Admin Manager...")
    admin_manager = AdminManager(
        db_manager=db_manager,
        ai_core=ai_core,
        autotrader=autotrader
    )
    
    logger.info("✅ Все компоненты инициализированы")
    logger.info("=" * 60)
    
    return db_manager, pocket_api, ai_core, autotrader, ui_handlers, admin_manager


# ============================================
# РЕГИСТРАЦИЯ ХЭНДЛЕРОВ
# ============================================

def register_handlers(app: Application, ui_handlers: UIHandlers, admin_manager: AdminManager):
    """
    Регистрация всех обработчиков команд и callback'ов
    
    Args:
        app: Telegram Application
        ui_handlers: Экземпляр UIHandlers
        admin_manager: Экземпляр AdminManager
    """
    logger.info("📋 Регистрация хэндлеров...")
    
    # ========================================
    # КЛИЕНТСКИЕ КОМАНДЫ
    # ========================================
    
    app.add_handler(CommandHandler("start", ui_handlers.handle_start))
    app.add_handler(CommandHandler("plans", ui_handlers.handle_plans))
    app.add_handler(CommandHandler("bank", ui_handlers.handle_bank))
    app.add_handler(CommandHandler("autotrade", ui_handlers.handle_autotrade))
    app.add_handler(CommandHandler("settings", ui_handlers.handle_settings))
    app.add_handler(CommandHandler("short", ui_handlers.handle_short_signal))
    app.add_handler(CommandHandler("long", ui_handlers.handle_long_signal))
    app.add_handler(CommandHandler("my_longs", ui_handlers.handle_my_longs))
    app.add_handler(CommandHandler("my_stats", ui_handlers.handle_my_stats))
    app.add_handler(CommandHandler("help", ui_handlers.handle_help))
    
    # ========================================
    # АДМИНСКИЕ КОМАНДЫ
    # ========================================
    
    async def admin_manager_wrapper(update, context):
        """Обертка для проверки прав админа"""
        if is_admin(update.effective_user.id):
            await admin_manager.handle_manager_panel(update, context)
        else:
            await update.message.reply_text("⛔ Доступ запрещен. Эта команда только для администраторов.")
    
    async def admin_stats_wrapper(update, context):
        """Обертка для /stats"""
        if is_admin(update.effective_user.id):
            await admin_manager.handle_stats(update, context)
        else:
            await update.message.reply_text("⛔ Доступ запрещен.")
    
    async def admin_logs_wrapper(update, context):
        """Обертка для /logs"""
        if is_admin(update.effective_user.id):
            await admin_manager.handle_logs(update, context)
        else:
            await update.message.reply_text("⛔ Доступ запрещен.")
    
    app.add_handler(CommandHandler("manager", admin_manager_wrapper))
    app.add_handler(CommandHandler("stats", admin_stats_wrapper))
    app.add_handler(CommandHandler("logs", admin_logs_wrapper))
    
    # ========================================
    # CALLBACK HANDLERS
    # ========================================
    
    app.add_handler(CallbackQueryHandler(ui_handlers.handle_callback))
    app.add_handler(CallbackQueryHandler(admin_manager.handle_callback))
    
    # ========================================
    # LLM-ЧАТ ДЛЯ АДМИНОВ
    # ========================================
    
    async def llm_chat_wrapper(update, context):
        """Обработчик текстовых сообщений для LLM-чата (только для админов)"""
        if is_admin(update.effective_user.id):
            await admin_manager.handle_llm_chat(update, context)
        # Обычные пользователи получают стандартное меню
        else:
            await update.message.reply_text(
                "💬 Для управления ботом используйте команды:\n"
                "/start - Главное меню\n"
                "/help - Помощь"
            )
    
    # MessageHandler для обычных текстовых сообщений (LLM-чат)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, llm_chat_wrapper))
    
    logger.info("✅ Все хэндлеры зарегистрированы")


# ============================================
# ОСНОВНАЯ АСИНХРОННАЯ ФУНКЦИЯ
# ============================================

async def main_async():
    """
    Главная асинхронная функция
    Запускает три параллельных потока:
    1. Telegram Bot UI (polling)
    2. AI Core (аналитика рынка)
    3. AutoTrader (торговля на основе сигналов из БД)
    """
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК МОНОЛИТНОГО СЕРВИСА")
    logger.info("=" * 60)
    logger.info(f"🕐 Время запуска: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    logger.info("=" * 60)
    
    # Валидация конфигурации
    try:
        config.validate()
        logger.info("✅ Конфигурация валидна")
    except ValueError as e:
        logger.error(f"❌ Ошибка конфигурации: {e}")
        sys.exit(1)
    
    # Инициализация компонентов
    db_manager, pocket_api, ai_core, autotrader, ui_handlers, admin_manager = init_components()
    
    # Создание Telegram Application
    logger.info("📱 Создание Telegram Application...")
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    # Регистрация хэндлеров
    register_handlers(app, ui_handlers, admin_manager)
    
    # ========================================
    # ЗАПУСК ПАРАЛЛЕЛЬНЫХ ПОТОКОВ
    # ========================================
    
    logger.info("=" * 60)
    logger.info("🔄 ЗАПУСК ПАРАЛЛЕЛЬНЫХ ПОТОКОВ")
    logger.info("=" * 60)
    
    try:
        # Запускаем три потока параллельно через asyncio.gather
        await asyncio.gather(
            # Поток 1: Telegram Bot UI (polling)
            app.run_polling(
                allowed_updates=['message', 'callback_query'],
                drop_pending_updates=True
            ),
            
            # Поток 2: AI Core (аналитика рынка)
            ai_core.run_analysis_cycle(),
            
            # Поток 3: AutoTrader (торговля на основе сигналов из БД)
            autotrader.run_autotrade_cycle(),
            
            return_exceptions=True
        )
    
    except KeyboardInterrupt:
        logger.info("\n👋 Получен сигнал остановки (Ctrl+C)")
    
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в main_async: {e}", exc_info=True)
    
    finally:
        logger.info("🛑 Остановка сервиса...")
        logger.info("=" * 60)
        logger.info("👋 СЕРВИС ОСТАНОВЛЕН")
        logger.info("=" * 60)


# ============================================
# ТОЧКА ВХОДА
# ============================================

def main():
    """Точка входа приложения"""
    try:
        # Запуск асинхронного main
        asyncio.run(main_async())
    
    except KeyboardInterrupt:
        logger.info("\n👋 Бот остановлен пользователем")
    
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
