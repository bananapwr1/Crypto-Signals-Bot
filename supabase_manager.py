# supabase_manager.py: Класс для управления подключением к Supabase

import os
import logging
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client # Предполагается, что 'supabase-py' установлен

logger = logging.getLogger(__name__)

class SupabaseManager:
    """
    Класс для управления подключением к базе данных Supabase и выполнения
    основных операций с пользователями.
    """
    
    def __init__(self):
        # Переменные окружения должны быть доступны через load_dotenv() в main.py
        self.url: str = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        self.key: str = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        
        if not self.url or not self.key:
            logger.error("❌ Ключи Supabase не найдены (NEXT_PUBLIC_SUPABASE_URL или KEY).")
            self.client = None
        else:
            try:
                # Инициализация клиента Supabase
                self.client: Client = create_client(self.url, self.key)
                logger.info("✅ Supabase клиент успешно инициализирован.")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации Supabase клиента: {e}")
                self.client = None

    def check_or_create_user(self, user_id: int, username: str) -> bool:
        """
        Проверяет наличие пользователя. Если не найден, создает новую запись.
        """
        if not self.client:
            logger.warning(f"DB STUB (Supabase): Клиент недоступен. Пользователь {user_id} не проверен.")
            return True # Возвращаем True, чтобы не блокировать интерфейс

        try:
            # 1. Поиск пользователя
            response = self.client.table('users').select('*').eq('id', str(user_id)).execute()
            
            # Проверяем, есть ли данные
            if response.data:
                logger.info(f"DB: Пользователь {user_id} найден.")
                return True
            
            # 2. Если не найден, создаем
            # Московский часовой пояс для корректной записи
            moscow_tz = timezone(timedelta(hours=3))
            now_moscow = datetime.now(moscow_tz).isoformat()
            
            data_to_insert = {
                'id': str(user_id),
                'username': username,
                'is_admin': False,
                'created_at': now_moscow,
                'is_banned': False,
                'signals_today': 0,
                'signals_limit': 10,
                'subscription_end': (datetime.now(moscow_tz) - timedelta(days=1)).isoformat() # По умолчанию не активна
            }
            
            insert_response = self.client.table('users').insert(data_to_insert).execute()
            logger.info(f"DB: Пользователь {user_id} создан. Ответ: {insert_response.data}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка проверки/создания пользователя {user_id}: {e}")
            return False

    def get_user_status(self, user_id: int):
        """
        Получает статус пользователя из БД.
        """
        if not self.client:
            return None
        
        try:
            response = self.client.table('users').select('*').eq('id', str(user_id)).single().execute()
            return response.data
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса пользователя {user_id}: {e}")
            return None


# Добавьте другие методы здесь (get_admin_stats, reset_user, reset_all_stats и т.д.)
# Эти методы будут реализованы позже в Фазе 3

