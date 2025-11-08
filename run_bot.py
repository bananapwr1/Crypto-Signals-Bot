#!/usr/bin/env python3
"""
run_bot.py - Простая точка запуска для бота
"""

import logging
from bot_interface import BotInterface, main

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Запуск Crypto Signals Bot Interface")
    logger.info("=" * 60)
    
    try:
        # Запуск бота
        main()
    except KeyboardInterrupt:
        logger.info("\n👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
        raise
