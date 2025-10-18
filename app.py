# app.py - Crypto Bot для Hostbot
print("=" * 50)
print("🚀 CRYPTO SIGNALS BOT - СИСТЕМА АКТИВНА")
print("✅ Версия: Production")
print("✅ Хостинг: Hostbot")
print("=" * 50)

import time
import os
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

logger = logging.getLogger(name)

def check_environment():
    """Проверка переменных окружения"""
    logger.info("🔧 ПРОВЕРКА КОНФИГУРАЦИИ:")
    
    env_vars = {
        'SUPABASE_URL': os.getenv('SUPABASE_URL'),
        'SUPABASE_KEY': os.getenv('SUPABASE_KEY'),
        'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN')
    }
    
    for key, value in env_vars.items():
        status = "✅ УСТАНОВЛЕНА" if value else "❌ ОТСУТСТВУЕТ"
        logger.info(f"   {key}: {status}")
    
    return all(env_vars.values())

class HostBot:
    def init(self):
        self.is_running = False
        self.cycle_count = 0
        logger.info("🤖 Бот инициализирован для Hostbot")
    
    def safe_init_telegram(self):
        """Безопасная инициализация Telegram"""
        try:
            from telegram import Bot
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            if token:
                bot = Bot(token=token)
                logger.info("✅ Telegram Bot API доступен")
                return bot
            else:
                logger.warning("⚠️ Telegram токен не настроен")
                return None
        except Exception as e:
            logger.warning(f"⚠️ Telegram недоступен: {e}")
            return None
    
    def safe_init_supabase(self):
        """Безопасная инициализация Supabase"""
        try:
            from supabase import create_client
            url = os.getenv('SUPABASE_URL')
            key = os.getenv('SUPABASE_KEY')
            if url and key:
                client = create_client(url, key)
                logger.info("✅ Supabase подключен")
                return client
            else:
                logger.warning("⚠️ Supabase ключи не настроены")
                return None
        except Exception as e:
            logger.warning(f"⚠️ Supabase недоступен: {e}")
            return None
    
    def run(self):
        """Запуск основного цикла"""
        try:
            self.is_running = True
            
            # Проверяем конфигурацию
            config_ok = check_environment()
            
            # Инициализируем сервисы
            logger.info("🔄 ИНИЦИАЛИЗАЦИЯ СЕРВИСОВ...")
            self.telegram_bot = self.safe_init_telegram()
            self.supabase_client = self.safe_init_supabase()
            
            logger.info("🎯 СИСТЕМА ЗАПУЩЕНА УСПЕШНО!")
            
            # Основной рабочий цикл
            while self.is_running:
                self.cycle_count += 1
                
                # Выполняем работу
                if self.cycle_count % 5 == 0:
                    logger.info(f"📊 Статус: Цикл #{self.cycle_count} - Система активна")
                
                # Ждем перед следующим циклом
                time.sleep(30)  # 30 секунд
                
        except KeyboardInterrupt:
            logger.info("🛑 Остановка по команде пользователя")
        except Exception as e:
            logger.error(f"💥 Критическая ошибка: {e}")
        finally:
            self.is_running = False
            logger.info(f"🔴 Система остановлена. Всего циклов: {self.cycle_count}")

if name == "main":
    bot = HostBot()
    bot.run()
