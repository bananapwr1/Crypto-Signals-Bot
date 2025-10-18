"""
Webhook система для отправки сигналов во внешние сервисы
Поддерживает JWT-авторизацию для безопасности
"""

import asyncio
import aiohttp
import jwt
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class WebhookSystem:
    """Система для отправки сигналов через webhook"""
    
    def __init__(self):
        self.webhook_url: Optional[str] = None
        self.webhook_secret: Optional[str] = None
        self.webhook_enabled: bool = False
        self.session: Optional[aiohttp.ClientSession] = None
        
    def configure(self, url: str, secret: str, enabled: bool = True):
        """Настроить webhook с валидацией безопасности"""
        # Валидация секрета перед включением
        if enabled:
            if not secret or len(secret) < 16:
                raise ValueError("Webhook secret must be at least 16 characters long for security")
            if secret.isspace():
                raise ValueError("Webhook secret cannot be empty or whitespace")
        
        self.webhook_url = url
        self.webhook_secret = secret
        self.webhook_enabled = enabled
        logger.info(f"🔗 Webhook настроен: {url} (включен: {enabled})")
    
    def generate_jwt_token(self, payload: Dict[str, Any]) -> str:
        """Генерация JWT токена для авторизации с полными claims"""
        token_payload = {
            **payload,
            'exp': datetime.utcnow() + timedelta(minutes=5),
            'iat': datetime.utcnow(),
            'iss': 'crypto-signals-bot',  # Issuer
            'aud': self.webhook_url  # Audience - URL получателя
        }
        return jwt.encode(token_payload, self.webhook_secret, algorithm='HS256')
    
    async def send_signal(self, signal_data: Dict[str, Any]) -> bool:
        """
        Отправить сигнал через webhook
        
        Args:
            signal_data: Данные сигнала для отправки
            
        Returns:
            bool: True если отправка успешна, False иначе
        """
        if not self.webhook_enabled or not self.webhook_url:
            return False
        
        try:
            # Генерируем JWT токен для авторизации
            token = self.generate_jwt_token({
                'signal_type': signal_data.get('type', 'unknown'),
                'timestamp': datetime.utcnow().isoformat()
            })
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            
            # Создаем сессию если её нет
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Отправляем POST запрос
            async with self.session.post(
                self.webhook_url,
                json=signal_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    logger.info(f"✅ Webhook отправлен успешно: {signal_data.get('asset', 'unknown')}")
                    return True
                else:
                    logger.error(f"❌ Webhook ошибка {response.status}: {await response.text()}")
                    return False
                    
        except asyncio.TimeoutError:
            logger.error("⏱️ Webhook timeout - превышено время ожидания")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка отправки webhook: {e}")
            return False
    
    async def close(self):
        """Закрыть HTTP сессию"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def format_signal_for_webhook(self, signal: Dict[str, Any], signal_type: str) -> Dict[str, Any]:
        """
        Форматировать сигнал для отправки через webhook
        
        Args:
            signal: Сигнал из системы
            signal_type: Тип сигнала ('short' или 'long')
            
        Returns:
            Dict с форматированными данными сигнала
        """
        return {
            'type': signal_type,
            'asset': signal.get('asset', ''),
            'direction': signal.get('direction', ''),
            'timeframe': signal.get('timeframe', ''),
            'confidence': signal.get('confidence', 0),
            'score': signal.get('score', 0),
            'entry_price': signal.get('entry_price', 0),
            'payout': signal.get('payout', 0),
            'is_otc': signal.get('is_otc', False),
            'timestamp': datetime.utcnow().isoformat(),
            'indicators': {
                'rsi': signal.get('rsi'),
                'ema_trend': signal.get('ema_trend'),
                'macd_signal': signal.get('macd_signal'),
                'support_resistance': signal.get('support_resistance')
            },
            'recommended_stake': signal.get('recommended_stake', 0),
            'strategy': signal.get('strategy', '')
        }

# Глобальный экземпляр webhook системы
webhook_system = WebhookSystem()
