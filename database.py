"""
database.py - Минимальный интерфейс для работы с Supabase
Простые функции для управления пользователями, командами и статусом.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

# Загрузка переменных окружения
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
    """Простой менеджер базы данных через Supabase"""
    
    def __init__(self):
        """Инициализация подключения к Supabase"""
        self.client: Optional[Client] = None
        
        if not SUPABASE_AVAILABLE:
            logger.warning("⚠️ Supabase библиотека не установлена. Работа в режиме заглушки.")
            return
        
        # ИСПРАВЛЕНО: используем правильные ключи переменных окружения
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
    
    def add_user(self, user_dict: Dict[str, Any]) -> bool:
        """
        Добавить или обновить пользователя
        
        Args:
            user_dict: Словарь с данными пользователя (user_id, username, etc.)
        
        Returns:
            bool: True если успешно, False если ошибка
        """
        if not self.client:
            logger.info(f"DB STUB: add_user({user_dict.get('user_id', 'unknown')})")
            return True
        
        try:
            user_id = str(user_dict.get('user_id'))
            username = user_dict.get('username', f'user_{user_id}')
            
            # Проверяем существование пользователя
            existing = self.client.table('users').select('*').eq('user_id', user_id).execute()
            
            if existing.data:
                # Обновляем
                self.client.table('users').update({
                    'username': username,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }).eq('user_id', user_id).execute()
                logger.info(f"✅ Пользователь {user_id} обновлен")
            else:
                # Создаем
                self.client.table('users').insert({
                    'user_id': user_id,
                    'username': username,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }).execute()
                logger.info(f"✅ Пользователь {user_id} создан")
            
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка add_user: {e}")
            return False
    
    def add_command(self, command_dict: Dict[str, Any]) -> bool:
        """
        Добавить команду в лог
        
        Args:
            command_dict: Словарь с данными команды (user_id, command, timestamp, etc.)
        
        Returns:
            bool: True если успешно, False если ошибка
        """
        if not self.client:
            logger.info(f"DB STUB: add_command({command_dict.get('command', 'unknown')})")
            return True
        
        try:
            self.client.table('commands').insert({
                'user_id': str(command_dict.get('user_id')),
                'command': command_dict.get('command'),
                'timestamp': command_dict.get('timestamp', datetime.now(timezone.utc).isoformat()),
                'data': command_dict.get('data', {})
            }).execute()
            logger.info(f"✅ Команда {command_dict.get('command')} записана")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка add_command: {e}")
            return False
    
    def get_users(self) -> List[Dict[str, Any]]:
        """
        Получить список всех пользователей
        
        Returns:
            List[Dict]: Список пользователей или пустой список
        """
        if not self.client:
            logger.info("DB STUB: get_users()")
            return []
        
        try:
            response = self.client.table('users').select('*').execute()
            return response.data or []
        except Exception as e:
            logger.error(f"❌ Ошибка get_users: {e}")
            return []
    
    def get_commands(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Получить список последних команд
        
        Args:
            limit: Максимальное количество команд
        
        Returns:
            List[Dict]: Список команд или пустой список
        """
        if not self.client:
            logger.info(f"DB STUB: get_commands(limit={limit})")
            return []
        
        try:
            response = self.client.table('commands').select('*').order('timestamp', desc=True).limit(limit).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"❌ Ошибка get_commands: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получить общий статус бота
        
        Returns:
            Dict: Статус или пустой словарь
        """
        if not self.client:
            logger.info("DB STUB: get_status()")
            return {
                'total_users': 0,
                'total_commands': 0,
                'status': 'stub_mode'
            }
        
        try:
            # Efficient count queries using Supabase
            users_response = self.client.table('users').select('*', count='exact').execute()
            users_count = users_response.count if hasattr(users_response, 'count') else len(users_response.data)
            
            commands_response = self.client.table('commands').select('*', count='exact').execute()
            commands_count = commands_response.count if hasattr(commands_response, 'count') else len(commands_response.data)
            
            return {
                'total_users': users_count,
                'total_commands': commands_count,
                'status': 'active',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Ошибка get_status: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def update_status(self, key: str, value: Any) -> bool:
        """
        Обновить значение в таблице статуса
        
        Args:
            key: Ключ статуса
            value: Новое значение
        
        Returns:
            bool: True если успешно, False если ошибка
        """
        if not self.client:
            logger.info(f"DB STUB: update_status({key}={value})")
            return True
        
        try:
            # Проверяем существование записи
            existing = self.client.table('bot_status').select('*').eq('key', key).execute()
            
            if existing.data:
                # Обновляем
                self.client.table('bot_status').update({
                    'value': str(value),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }).eq('key', key).execute()
            else:
                # Создаем
                self.client.table('bot_status').insert({
                    'key': key,
                    'value': str(value),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }).execute()
            
            logger.info(f"✅ Статус {key} обновлен")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка update_status: {e}")
            return False


# Глобальный экземпляр для удобного импорта
database = DatabaseManager()
