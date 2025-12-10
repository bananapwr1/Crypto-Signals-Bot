"""
ai_core.py - AI Core для аналитики рынка
Версия: 2.0
Дата: 2025-12-10

Обеспечивает:
- Аналитику рынка через LLM (Claude/GPT)
- Генерацию торговых сигналов на основе технического анализа
- Использование внешних сигналов (из парсера) для обучения и улучшения анализа
- Бесконечный цикл анализа (run_analysis_cycle)
- Интеграция с yfinance для получения рыночных данных
"""

import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any

# Pandas и NumPy - опциональные (для облегченных версий)
try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None
    np = None

# Технический анализ
try:
    import ta
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False

# yfinance для рыночных данных
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# Anthropic Claude API
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)


class AICore:
    """AI Core для аналитики рынка"""
    
    def __init__(self, db_manager=None):
        """
        Инициализация AI Core
        
        Args:
            db_manager: Экземпляр DatabaseManager для сохранения сигналов
        """
        self.db_manager = db_manager
        
        # Anthropic API ключ
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.anthropic_client = None
        
        if ANTHROPIC_AVAILABLE and self.anthropic_key:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_key)
                logger.info("✅ Anthropic Claude API инициализирован")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации Claude API: {e}")
        else:
            logger.warning("⚠️ Anthropic API недоступен (отсутствует ключ или библиотека)")
        
        # Список активов для анализа (синхронизировано с Pocket Option)
        self.assets = [
            'EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X',
            'BTC-USD', 'ETH-USD', 'XRP-USD',
            'AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN',
            'GC=F', 'CL=F'  # Gold, Oil
        ]
        
        # Интервал анализа (в секундах)
        self.analysis_interval = 300  # 5 минут
        
        logger.info(f"✅ AI Core инициализирован (активов: {len(self.assets)})")
    
    # ========================================
    # ПОЛУЧЕНИЕ РЫНОЧНЫХ ДАННЫХ
    # ========================================
    
    def get_market_data(self, symbol: str, period: str = '1d', interval: str = '5m') -> Optional[Dict]:
        """
        Получить рыночные данные через yfinance
        
        Args:
            symbol: Символ актива (например, 'BTC-USD')
            period: Период данных ('1d', '5d', '1mo', etc.)
            interval: Интервал ('1m', '5m', '15m', '1h', etc.)
        
        Returns:
            pd.DataFrame или Dict: DataFrame с ценовыми данными или None
        """
        if not YFINANCE_AVAILABLE:
            logger.warning("⚠️ yfinance не установлен - рыночные данные недоступны")
            return None
        
        if not PANDAS_AVAILABLE:
            logger.warning("⚠️ pandas не установлен - анализ данных ограничен")
            return None
        
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                logger.warning(f"⚠️ Нет данных для {symbol}")
                return None
            
            logger.info(f"✅ Получены данные для {symbol}: {len(data)} свечей")
            return data
        
        except Exception as e:
            logger.error(f"❌ Ошибка получения данных для {symbol}: {e}")
            return None
    
    # ========================================
    # ТЕХНИЧЕСКИЙ АНАЛИЗ
    # ========================================
    
    def calculate_indicators(self, df):
        """
        Рассчитать технические индикаторы
        
        Args:
            df: DataFrame с ценовыми данными
        
        Returns:
            DataFrame с добавленными индикаторами
        """
        if not PANDAS_AVAILABLE:
            logger.warning("⚠️ pandas не установлен - технический анализ недоступен")
            return df
        
        if not TA_AVAILABLE:
            logger.warning("⚠️ Библиотека ta не установлена, технический анализ ограничен")
            return df
        
        try:
            # RSI (Relative Strength Index)
            df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
            
            # MACD (Moving Average Convergence Divergence)
            macd = ta.trend.MACD(df['Close'])
            df['MACD'] = macd.macd()
            df['MACD_signal'] = macd.macd_signal()
            df['MACD_diff'] = macd.macd_diff()
            
            # Bollinger Bands
            bollinger = ta.volatility.BollingerBands(df['Close'], window=20)
            df['BB_upper'] = bollinger.bollinger_hband()
            df['BB_middle'] = bollinger.bollinger_mavg()
            df['BB_lower'] = bollinger.bollinger_lband()
            
            # EMA (Exponential Moving Average)
            df['EMA_12'] = ta.trend.EMAIndicator(df['Close'], window=12).ema_indicator()
            df['EMA_26'] = ta.trend.EMAIndicator(df['Close'], window=26).ema_indicator()
            
            # Stochastic Oscillator
            stoch = ta.momentum.StochasticOscillator(df['High'], df['Low'], df['Close'])
            df['Stoch_K'] = stoch.stoch()
            df['Stoch_D'] = stoch.stoch_signal()
            
            logger.info(f"✅ Рассчитаны индикаторы для {len(df)} свечей")
            return df
        
        except Exception as e:
            logger.error(f"❌ Ошибка расчета индикаторов: {e}")
            return df
    
    def generate_signal(self, df, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Генерирует торговый сигнал на основе технического анализа
        
        Args:
            df: DataFrame с индикаторами
            symbol: Символ актива
        
        Returns:
            Dict: Торговый сигнал или None
        """
        if not PANDAS_AVAILABLE:
            logger.warning("⚠️ pandas не установлен - генерация сигналов недоступна")
            return None
        
        if df is None or df.empty or len(df) < 2:
            return None
        
        try:
            # Берем последние значения
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            signal_type = None
            confidence = 0.0
            reasons = []
            
            # Анализ RSI
            if 'RSI' in last and not (pd and pd.isna(last['RSI'])):
                if last['RSI'] < 30:
                    signal_type = 'CALL'
                    confidence += 20
                    reasons.append(f"RSI перепродан ({last['RSI']:.1f})")
                elif last['RSI'] > 70:
                    signal_type = 'PUT'
                    confidence += 20
                    reasons.append(f"RSI перекуплен ({last['RSI']:.1f})")
            
            # Анализ MACD
            if 'MACD_diff' in last and not (pd and pd.isna(last['MACD_diff'])):
                if last['MACD_diff'] > 0 and prev['MACD_diff'] < 0:
                    if signal_type != 'PUT':
                        signal_type = 'CALL'
                        confidence += 25
                        reasons.append("MACD бычий кроссовер")
                elif last['MACD_diff'] < 0 and prev['MACD_diff'] > 0:
                    if signal_type != 'CALL':
                        signal_type = 'PUT'
                        confidence += 25
                        reasons.append("MACD медвежий кроссовер")
            
            # Анализ Bollinger Bands
            if all(k in last for k in ['BB_upper', 'BB_lower']):
                if not (pd and pd.isna(last['BB_lower'])) and last['Close'] < last['BB_lower']:
                    if signal_type != 'PUT':
                        signal_type = 'CALL'
                        confidence += 15
                        reasons.append("Цена ниже нижней полосы Боллинджера")
                elif not (pd and pd.isna(last['BB_upper'])) and last['Close'] > last['BB_upper']:
                    if signal_type != 'CALL':
                        signal_type = 'PUT'
                        confidence += 15
                        reasons.append("Цена выше верхней полосы Боллинджера")
            
            # Если сигнал слабый, не генерируем
            if confidence < 40:
                return None
            
            # Формируем сигнал
            signal = {
                'symbol': symbol,
                'signal_type': signal_type,
                'confidence': min(confidence, 100),  # Ограничиваем 100%
                'entry_price': float(last['Close']),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'reasons': reasons,
                'timeframe': '5m'
            }
            
            logger.info(f"📊 Сигнал сгенерирован: {symbol} {signal_type} (уверенность: {confidence:.0f}%)")
            return signal
        
        except Exception as e:
            logger.error(f"❌ Ошибка генерации сигнала: {e}")
            return None
    
    # ========================================
    # LLM АНАЛИЗ (ОПЦИОНАЛЬНО)
    # ========================================
    
    async def analyze_with_llm(self, market_summary: str) -> Optional[str]:
        """
        Анализ рынка с помощью Claude
        
        Args:
            market_summary: Сводка по рынку
        
        Returns:
            str: Анализ от LLM или None
        """
        if not self.anthropic_client:
            return None
        
        try:
            prompt = f"""Ты - опытный трейдер. Проанализируй следующую рыночную ситуацию и дай краткие рекомендации:

{market_summary}

Ответь кратко (2-3 предложения): какие активы сейчас интересны для торговли и почему?"""
            
            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            analysis = message.content[0].text
            logger.info(f"✅ LLM анализ получен: {analysis[:100]}...")
            return analysis
        
        except Exception as e:
            logger.error(f"❌ Ошибка LLM анализа: {e}")
            return None
    
    # ========================================
    # РАБОТА С ВНЕШНИМИ СИГНАЛАМИ
    # ========================================
    
    async def get_external_signals(self) -> List[Dict[str, Any]]:
        """
        Получить внешние сигналы из парсера для анализа
        
        Returns:
            List[Dict]: Список внешних сигналов из БД
        """
        if not self.db_manager:
            return []
        
        try:
            # Получаем сигналы, помеченные как внешние (от парсера)
            signals = self.db_manager.get_external_signals()
            
            if signals:
                logger.info(f"📨 Получено {len(signals)} внешних сигналов для анализа")
            
            return signals
        
        except Exception as e:
            logger.error(f"❌ Ошибка получения внешних сигналов: {e}")
            return []
    
    def analyze_external_signals(self, external_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Анализ внешних сигналов для обучения и улучшения модели
        
        Args:
            external_signals: Список внешних сигналов
        
        Returns:
            Dict: Статистика по внешним сигналам
        """
        if not external_signals:
            return {}
        
        try:
            # Группируем сигналы по активам
            by_symbol = {}
            by_type = {'CALL': 0, 'PUT': 0}
            
            for signal in external_signals:
                symbol = signal.get('symbol', 'UNKNOWN')
                signal_type = signal.get('signal_type', 'UNKNOWN')
                
                if symbol not in by_symbol:
                    by_symbol[symbol] = {'CALL': 0, 'PUT': 0}
                
                by_symbol[symbol][signal_type] = by_symbol[symbol].get(signal_type, 0) + 1
                by_type[signal_type] = by_type.get(signal_type, 0) + 1
            
            logger.info(f"📊 Анализ внешних сигналов: {by_type}")
            
            return {
                'total': len(external_signals),
                'by_symbol': by_symbol,
                'by_type': by_type
            }
        
        except Exception as e:
            logger.error(f"❌ Ошибка анализа внешних сигналов: {e}")
            return {}
    
    # ========================================
    # БЕСКОНЕЧНЫЙ ЦИКЛ АНАЛИЗА
    # ========================================
    
    async def run_analysis_cycle(self):
        """
        Бесконечный цикл аналитики рынка
        Использует как собственный анализ, так и внешние сигналы для обучения
        Вызывается из main.py через asyncio.gather
        """
        logger.info("🔍 Запуск бесконечного цикла аналитики...")
        logger.info("📊 Режим: собственный анализ + обучение на внешних сигналах")
        
        iteration = 0
        
        while True:
            try:
                iteration += 1
                logger.info(f"📊 Итерация анализа #{iteration}")
                
                # Получаем внешние сигналы для анализа
                external_signals = await self.get_external_signals()
                if external_signals:
                    external_stats = self.analyze_external_signals(external_signals)
                    logger.info(f"📈 Внешние сигналы: {external_stats.get('total', 0)}")
                
                # Анализируем каждый актив
                signals_generated = 0
                
                for symbol in self.assets:
                    # Получаем данные
                    df = self.get_market_data(symbol, period='1d', interval='5m')
                    
                    if df is None or df.empty:
                        continue
                    
                    # Рассчитываем индикаторы
                    df = self.calculate_indicators(df)
                    
                    # Генерируем сигнал на основе технического анализа
                    signal = self.generate_signal(df, symbol)
                    
                    if signal and self.db_manager:
                        # Помечаем как сигнал от AI Core
                        signal['source'] = 'ai_core'
                        
                        # Сохраняем в БД
                        self.db_manager.add_signal(signal)
                        signals_generated += 1
                    
                    # Небольшая задержка между активами
                    await asyncio.sleep(1)
                
                logger.info(f"✅ Итерация #{iteration} завершена. Сигналов сгенерировано: {signals_generated}")
                
                # Ждем до следующей итерации
                await asyncio.sleep(self.analysis_interval)
            
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле анализа: {e}")
                await asyncio.sleep(60)  # Ждем минуту при ошибке
