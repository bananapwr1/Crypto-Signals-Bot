"""
autotrader.py - Автоторговля + Парсинг Telegram
Версия: 1.0
Дата: 2025-12-09

Обеспечивает:
- Автоматическое выполнение сделок через Pocket Option API
- Парсинг сигналов из Telegram каналов (через Telethon)
- Бесконечный цикл автоторговли (run_autotrade_and_parser)
- Управление стратегиями (Мартингейл, Процентная ставка, Д'Аламбер)
"""

import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

# Telethon для парсинга Telegram
try:
    from telethon import TelegramClient, events
    from telethon.tl.types import Message
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False

logger = logging.getLogger(__name__)


class AutoTrader:
    """Автотрейдер с парсингом Telegram"""
    
    def __init__(self, db_manager=None, pocket_api=None):
        """
        Инициализация AutoTrader
        
        Args:
            db_manager: Экземпляр DatabaseManager
            pocket_api: Экземпляр PocketOptionAPI
        """
        self.db_manager = db_manager
        self.pocket_api = pocket_api
        
        # Telegram Client настройки
        self.tg_api_id = os.getenv('TG_API_ID')
        self.tg_api_hash = os.getenv('TG_API_HASH')
        self.tg_client: Optional[TelegramClient] = None
        
        # Список целевых каналов для парсинга
        target_chat_id_str = os.getenv('TARGET_CHAT_ID', '')
        self.target_chat_ids = [
            int(cid.strip()) for cid in target_chat_id_str.split(',') 
            if cid.strip().isdigit() or (cid.strip().startswith('-') and cid.strip()[1:].isdigit())
        ]
        
        # Интервал проверки автоторговли (в секундах)
        self.autotrade_interval = 60  # 1 минута
        
        logger.info(f"✅ AutoTrader инициализирован")
        logger.info(f"📱 TG API ID: {self.tg_api_id}")
        logger.info(f"📱 Целевых каналов: {len(self.target_chat_ids)}")
    
    # ========================================
    # TELEGRAM ПАРСИНГ
    # ========================================
    
    async def init_telegram_client(self):
        """Инициализация Telegram Client"""
        if not TELETHON_AVAILABLE:
            logger.warning("⚠️ Telethon не установлен, парсинг Telegram недоступен")
            return False
        
        if not self.tg_api_id or not self.tg_api_hash:
            logger.warning("⚠️ TG_API_ID или TG_API_HASH не заданы")
            return False
        
        try:
            self.tg_client = TelegramClient(
                'autotrader_session',
                int(self.tg_api_id),
                self.tg_api_hash
            )
            
            await self.tg_client.start()
            logger.info("✅ Telegram Client инициализирован")
            
            # Регистрируем обработчик новых сообщений
            @self.tg_client.on(events.NewMessage(chats=self.target_chat_ids))
            async def handle_new_message(event):
                await self.parse_signal_message(event.message)
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Telegram Client: {e}")
            return False
    
    async def parse_signal_message(self, message: Any):
        """
        Парсинг сигнала из сообщения Telegram
        
        Args:
            message: Telegram сообщение
        """
        try:
            text = message.text or message.message
            
            if not text:
                return
            
            logger.info(f"📨 Новое сообщение в канале: {text[:100]}...")
            
            # Простой парсинг сигналов (примерный формат)
            # Пример: "BTC/USD CALL 5min"
            
            signal = self.extract_signal_from_text(text)
            
            if signal:
                logger.info(f"✅ Сигнал распознан: {signal}")
                
                # Сохраняем в БД
                if self.db_manager:
                    self.db_manager.add_signal({
                        'symbol': signal['symbol'],
                        'signal_type': signal['type'],
                        'timeframe': signal['timeframe'],
                        'source': 'telegram',
                        'confidence': 70.0
                    })
                
                # Выполняем сделку (если есть пользователи с автоторговлей)
                await self.execute_signal_for_users(signal)
        
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга сообщения: {e}")
    
    def extract_signal_from_text(self, text: str) -> Optional[Dict[str, str]]:
        """
        Извлечь сигнал из текста
        
        Args:
            text: Текст сообщения
        
        Returns:
            Dict: Распознанный сигнал или None
        """
        text = text.upper()
        
        # Поиск типа сигнала
        signal_type = None
        if 'CALL' in text or '🟢' in text or '↗' in text:
            signal_type = 'CALL'
        elif 'PUT' in text or '🔴' in text or '↘' in text:
            signal_type = 'PUT'
        
        if not signal_type:
            return None
        
        # Поиск актива (примерные варианты)
        assets_map = {
            'BTC': 'BTC-USD',
            'ETH': 'ETH-USD',
            'EUR': 'EURUSD',
            'GBP': 'GBPUSD',
            'GOLD': 'XAUUSD'
        }
        
        symbol = None
        for key, value in assets_map.items():
            if key in text:
                symbol = value
                break
        
        if not symbol:
            symbol = 'UNKNOWN'
        
        # Поиск таймфрейма
        timeframe = '5m'
        if '1MIN' in text or '1 MIN' in text:
            timeframe = '1m'
        elif '5MIN' in text or '5 MIN' in text:
            timeframe = '5m'
        elif '15MIN' in text or '15 MIN' in text:
            timeframe = '15m'
        
        return {
            'symbol': symbol,
            'type': signal_type,
            'timeframe': timeframe
        }
    
    # ========================================
    # ВЫПОЛНЕНИЕ СДЕЛОК
    # ========================================
    
    async def execute_signal_for_users(self, signal: Dict[str, str]):
        """
        Выполнить сделку для пользователей с автоторговлей
        
        Args:
            signal: Торговый сигнал
        """
        if not self.db_manager:
            return
        
        # Получаем пользователей с включенной автоторговлей
        users = self.db_manager.get_users_with_auto_trading()
        
        logger.info(f"🤖 Выполняем сигнал для {len(users)} пользователей")
        
        for user in users:
            try:
                await self.execute_trade_for_user(user, signal)
            except Exception as e:
                logger.error(f"❌ Ошибка выполнения сделки для {user['user_id']}: {e}")
    
    async def execute_trade_for_user(self, user: Dict, signal: Dict[str, str]):
        """
        Выполнить сделку для конкретного пользователя
        
        Args:
            user: Данные пользователя из БД
            signal: Торговый сигнал
        """
        if not self.pocket_api:
            logger.warning("⚠️ Pocket Option API не инициализирован")
            return
        
        user_id = int(user['user_id'])
        
        # Получаем стратегию пользователя
        strategy = user.get('auto_trading_strategy', 'percentage')
        
        # Рассчитываем сумму сделки
        if strategy == 'martingale':
            stake = self.calculate_martingale_stake(user)
        elif strategy == 'dalembert':
            stake = self.calculate_dalembert_stake(user)
        else:  # percentage
            stake = self.calculate_percentage_stake(user)
        
        # Режим торговли (demo/real)
        mode = user.get('auto_trading_mode', 'demo')
        
        logger.info(f"💰 Открываем сделку для user {user_id}: {signal['type']} {signal['symbol']} (${stake}, {mode})")
        
        # Выполняем сделку через Pocket Option API
        result = await self.pocket_api.place_trade(
            user_id=user_id,
            symbol=signal['symbol'],
            direction=signal['type'],
            amount=stake,
            duration=signal.get('timeframe', '5m'),
            mode=mode
        )
        
        if result:
            logger.info(f"✅ Сделка открыта для user {user_id}")
        else:
            logger.error(f"❌ Не удалось открыть сделку для user {user_id}")
    
    # ========================================
    # РАСЧЕТ СТАВОК
    # ========================================
    
    def calculate_martingale_stake(self, user: Dict) -> float:
        """Рассчитать ставку по стратегии Мартингейл"""
        base_stake = user.get('martingale_base_stake', 100.0)
        multiplier = user.get('martingale_multiplier', 3)
        current_level = user.get('current_martingale_level', 0)
        
        stake = base_stake * (multiplier ** current_level)
        return min(stake, 10000.0)  # Ограничение максимальной ставки
    
    def calculate_dalembert_stake(self, user: Dict) -> float:
        """Рассчитать ставку по стратегии Д'Аламбер"""
        base_stake = user.get('dalembert_base_stake', 100.0)
        unit = user.get('dalembert_unit', 50.0)
        current_level = user.get('current_dalembert_level', 0)
        
        stake = base_stake + (unit * current_level)
        return min(stake, 10000.0)
    
    def calculate_percentage_stake(self, user: Dict) -> float:
        """Рассчитать ставку по процентной стратегии"""
        balance = user.get('current_balance', 1000.0)
        percentage = user.get('percentage_value', 2.5)
        
        stake = balance * (percentage / 100.0)
        return min(stake, 10000.0)
    
    # ========================================
    # БЕСКОНЕЧНЫЙ ЦИКЛ АВТОТОРГОВЛИ
    # ========================================
    
    async def run_autotrade_and_parser(self):
        """
        Бесконечный цикл автоторговли + парсинга TG
        Вызывается из main.py через asyncio.gather
        """
        logger.info("🤖 Запуск бесконечного цикла автоторговли и парсинга...")
        
        # Инициализируем Telegram Client
        tg_initialized = await self.init_telegram_client()
        
        if tg_initialized:
            logger.info("✅ Telegram парсинг включен")
        else:
            logger.warning("⚠️ Telegram парсинг отключен")
        
        iteration = 0
        
        while True:
            try:
                iteration += 1
                logger.info(f"🤖 Итерация автоторговли #{iteration}")
                
                # Если Telegram Client инициализирован, он работает через events
                # Здесь можно добавить дополнительную логику автоторговли
                
                # Проверяем открытые сделки и обновляем их статус
                if self.db_manager and self.pocket_api:
                    await self.check_open_trades()
                
                logger.info(f"✅ Итерация автоторговли #{iteration} завершена")
                
                # Ждем до следующей итерации
                await asyncio.sleep(self.autotrade_interval)
            
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле автоторговли: {e}")
                await asyncio.sleep(60)
    
    async def check_open_trades(self):
        """Проверить открытые сделки и обновить их статус"""
        # TODO: Реализовать проверку открытых сделок через Pocket Option API
        pass
