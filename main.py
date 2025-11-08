"""
main.py - Точка входа для запуска Telegram бота
Импортирует и запускает бот из bot_interface.py для избежания дублирования кода.
"""

import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Импорт всей функциональности из bot_interface
from bot_interface import (
    main,
    check_environment,
    BotInterface,
    # Экспорт основных компонентов для совместимости
    start_command,
    status_command,
    plans_command,
    autotrade_command,
    signals_command,
    bank_command,
    faq_command,
    admin_stats_command,
    god_command,
    button_callback,
    setup_commands
)

# Экспорт для обратной совместимости
__all__ = [
    'main',
    'check_environment',
    'BotInterface',
    'start_command',
    'status_command',
    'plans_command',
    'autotrade_command',
    'signals_command',
    'bank_command',
    'faq_command',
    'admin_stats_command',
    'god_command',
    'button_callback',
    'setup_commands'
]


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🚀 Запуск Crypto Signals Bot через main.py")
    logger.info("=" * 60)
    
    try:
        # Запускаем бот из bot_interface
        main()
    except KeyboardInterrupt:
        logger.info("\n👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
        raise
