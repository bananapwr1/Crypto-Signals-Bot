"""
autotrader.py - Автоторговля
Версия: 2.0
Дата: 2025-12-10

Обеспечивает:
- Автоматическое выполнение сделок через Pocket Option API
- Получение сигналов из БД (сигналы добавляются внешним парсером)
- Бесконечный цикл автоторговли (run_autotrade_cycle)
- Управление стратегиями (Мартингейл, Процентная ставка, Д'Аламбер)
"""

import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class AutoTrader:
    """Автотрейдер для выполнения сделок на основе сигналов из БД"""
    
    def __init__(self, db_manager=None, pocket_api=None):
        """
        Инициализация AutoTrader
        
        Args:
            db_manager: Экземпляр DatabaseManager
            pocket_api: Экземпляр PocketOptionAPI
        """
        self.db_manager = db_manager
        self.pocket_api = pocket_api
        
        # Интервал проверки автоторговли (в секундах)
        self.autotrade_interval = 60  # 1 минута
        
        logger.info(f"✅ AutoTrader инициализирован")
        logger.info(f"📊 Режим работы: получение сигналов из БД")
    
    # ========================================
    # ПОЛУЧЕНИЕ СИГНАЛОВ ИЗ БД
    # ========================================
    
    async def get_pending_signals(self) -> List[Dict[str, Any]]:
        """
        Получить новые неотработанные сигналы из БД
        
        Returns:
            List[Dict]: Список сигналов из БД
        """
        if not self.db_manager:
            return []
        
        try:
            # Получаем сигналы из БД, которые еще не обработаны
            signals = self.db_manager.get_pending_signals()
            
            if signals:
                logger.info(f"📊 Получено {len(signals)} новых сигналов из БД")
            
            return signals
        
        except Exception as e:
            logger.error(f"❌ Ошибка получения сигналов из БД: {e}")
            return []
    
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
    
    async def run_autotrade_cycle(self):
        """
        Бесконечный цикл автоторговли
        Получает сигналы из БД и выполняет сделки
        Вызывается из main.py через asyncio.gather
        """
        logger.info("🤖 Запуск бесконечного цикла автоторговли...")
        logger.info("📊 Сигналы будут получены из БД (внешний парсер)")
        
        iteration = 0
        
        while True:
            try:
                iteration += 1
                logger.info(f"🤖 Итерация автоторговли #{iteration}")
                
                # Получаем новые сигналы из БД
                signals = await self.get_pending_signals()
                
                # Обрабатываем каждый сигнал
                for signal in signals:
                    try:
                        await self.execute_signal_for_users(signal)
                        
                        # Отмечаем сигнал как обработанный в БД
                        if self.db_manager:
                            self.db_manager.mark_signal_as_processed(signal.get('id'))
                    
                    except Exception as e:
                        logger.error(f"❌ Ошибка обработки сигнала {signal.get('id')}: {e}")
                
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
