"""
db_manager.py - Менеджер базы данных (Supabase)
Версия: 1.0
Дата: 2025-12-09

Обеспечивает:
- Подключение к Supabase
- CRUD операции для пользователей
- Хранение и получение торговых сигналов
- Статистика и аналитика
- Управление подписками
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

load_dotenv()

# Безопасный импорт Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер базы данных через Supabase"""
    
    def __init__(self):
        """Инициализация подключения к Supabase"""
        self.client: Optional[Client] = None
        
        if not SUPABASE_AVAILABLE:
            logger.warning("⚠️ Supabase библиотека не установлена. Работа в режиме заглушки.")
            return
        
        supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        supabase_key = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            logger.warning("⚠️ Supabase credentials не найдены. Работа в режиме заглушки.")
            return
        
        try:
            self.client = create_client(supabase_url, supabase_key)
            logger.info("✅ Supabase клиент успешно инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Supabase: {e}")
            self.client = None
    
    # ========================================
    # ПОЛЬЗОВАТЕЛИ
    # ========================================
    
    def get_or_create_user(self, user_id: int, username: str = None, first_name: str = None) -> Optional[Dict]:
        """Получить или создать пользователя"""
        if not self.client:
            logger.info(f"DB STUB: get_or_create_user({user_id})")
            return {'user_id': str(user_id), 'username': username, 'subscription_type': None}
        
        try:
            # Проверяем существование
            existing = self.client.table('users').select('*').eq('user_id', str(user_id)).execute()
            
            if existing.data:
                return existing.data[0]
            
            # Создаем нового пользователя
            new_user = {
                'user_id': str(user_id),
                'username': username or f'user_{user_id}',
                'first_name': first_name,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'subscription_type': None,
                'subscription_end': None,
                'initial_balance': None,
                'current_balance': None,
                'auto_trading_enabled': False,
                'trading_strategy': 'percentage',
                'percentage_value': 2.5,
                'martingale_multiplier': 3,
                'language': 'ru'
            }
            
            result = self.client.table('users').insert(new_user).execute()
            logger.info(f"✅ Пользователь {user_id} создан")
            return result.data[0] if result.data else None
        
        except Exception as e:
            logger.error(f"❌ Ошибка get_or_create_user: {e}")
            return None
    
    def update_user(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Обновить данные пользователя"""
        if not self.client:
            logger.info(f"DB STUB: update_user({user_id}, {updates})")
            return True
        
        try:
            updates['updated_at'] = datetime.now(timezone.utc).isoformat()
            self.client.table('users').update(updates).eq('user_id', str(user_id)).execute()
            logger.info(f"✅ Пользователь {user_id} обновлен")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка update_user: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получить данные пользователя"""
        if not self.client:
            logger.info(f"DB STUB: get_user({user_id})")
            return None
        
        try:
            response = self.client.table('users').select('*').eq('user_id', str(user_id)).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"❌ Ошибка get_user: {e}")
            return None
    
    def get_all_users(self) -> List[Dict]:
        """Получить всех пользователей"""
        if not self.client:
            logger.info("DB STUB: get_all_users()")
            return []
        
        try:
            response = self.client.table('users').select('*').execute()
            return response.data or []
        except Exception as e:
            logger.error(f"❌ Ошибка get_all_users: {e}")
            return []
    
    def get_users_with_auto_trading(self) -> List[Dict]:
        """Получить пользователей с включенной автоторговлей"""
        if not self.client:
            return []
        
        try:
            response = self.client.table('users').select('*').eq('auto_trading_enabled', True).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"❌ Ошибка get_users_with_auto_trading: {e}")
            return []
    
    # ========================================
    # ПОДПИСКИ
    # ========================================
    
    def check_subscription(self, user_id: int, subscription_type: str = None) -> bool:
        """Проверить активность подписки"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        # Если не указан тип, проверяем любую активную подписку
        if subscription_type is None:
            if not user.get('subscription_end'):
                return False
            
            end_date = datetime.fromisoformat(user['subscription_end'].replace('Z', '+00:00'))
            return end_date > datetime.now(timezone.utc)
        
        # Проверяем конкретный тип подписки
        if user.get('subscription_type') != subscription_type:
            return False
        
        if not user.get('subscription_end'):
            return False
        
        end_date = datetime.fromisoformat(user['subscription_end'].replace('Z', '+00:00'))
        return end_date > datetime.now(timezone.utc)
    
    def add_subscription(self, user_id: int, subscription_type: str, duration_days: int) -> bool:
        """Добавить или продлить подписку"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        current_end = None
        if user.get('subscription_end'):
            try:
                current_end = datetime.fromisoformat(user['subscription_end'].replace('Z', '+00:00'))
            except:
                pass
        
        # Если подписка еще активна, продлеваем от текущей даты окончания
        if current_end and current_end > datetime.now(timezone.utc):
            new_end = current_end + timedelta(days=duration_days)
        else:
            new_end = datetime.now(timezone.utc) + timedelta(days=duration_days)
        
        return self.update_user(user_id, {
            'subscription_type': subscription_type,
            'subscription_end': new_end.isoformat()
        })
    
    # ========================================
    # ТОРГОВЫЕ СИГНАЛЫ
    # ========================================
    
    def add_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Добавить торговый сигнал в историю"""
        if not self.client:
            logger.info(f"DB STUB: add_signal({signal_data.get('asset', 'unknown')})")
            return True
        
        try:
            signal_data['created_at'] = datetime.now(timezone.utc).isoformat()
            self.client.table('signals').insert(signal_data).execute()
            logger.info(f"✅ Сигнал {signal_data.get('asset')} добавлен")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка add_signal: {e}")
            return False
    
    def get_user_signals(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Получить сигналы пользователя"""
        if not self.client:
            return []
        
        try:
            response = self.client.table('signals') \
                .select('*') \
                .eq('user_id', str(user_id)) \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            return response.data or []
        except Exception as e:
            logger.error(f"❌ Ошибка get_user_signals: {e}")
            return []
    
    def update_signal_result(self, signal_id: int, result: str, profit_loss: float = None) -> bool:
        """Обновить результат сигнала"""
        if not self.client:
            return True
        
        try:
            updates = {
                'result': result,
                'close_date': datetime.now(timezone.utc).isoformat()
            }
            if profit_loss is not None:
                updates['profit_loss'] = profit_loss
            
            self.client.table('signals').update(updates).eq('id', signal_id).execute()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка update_signal_result: {e}")
            return False
    
    # ========================================
    # СТАТИСТИКА
    # ========================================
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получить статистику пользователя"""
        signals = self.get_user_signals(user_id, limit=1000)
        
        if not signals:
            return {
                'total_signals': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'total_profit': 0.0
            }
        
        wins = sum(1 for s in signals if s.get('result') == 'win')
        losses = sum(1 for s in signals if s.get('result') == 'loss')
        total_profit = sum(s.get('profit_loss', 0) for s in signals)
        
        return {
            'total_signals': len(signals),
            'wins': wins,
            'losses': losses,
            'win_rate': (wins / len(signals) * 100) if signals else 0.0,
            'total_profit': total_profit
        }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Получить глобальную статистику"""
        if not self.client:
            return {
                'total_users': 0,
                'active_subscriptions': 0,
                'total_signals': 0
            }
        
        try:
            users = self.get_all_users()
            active_subs = sum(1 for u in users if self.check_subscription(int(u.get('user_id', 0))))
            
            signals_response = self.client.table('signals').select('*', count='exact').execute()
            total_signals = signals_response.count if hasattr(signals_response, 'count') else 0
            
            return {
                'total_users': len(users),
                'active_subscriptions': active_subs,
                'total_signals': total_signals
            }
        except Exception as e:
            logger.error(f"❌ Ошибка get_global_stats: {e}")
            return {'error': str(e)}
    
    # ========================================
    # КОМАНДЫ
    # ========================================
    
    def log_command(self, user_id: int, command: str, data: Dict = None) -> bool:
        """Логировать выполненную команду"""
        if not self.client:
            return True
        
        try:
            self.client.table('commands').insert({
                'user_id': str(user_id),
                'command': command,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': data or {}
            }).execute()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка log_command: {e}")
            return False
