"""
admin_manager.py - Админ-панель и LLM-чат
Версия: 1.0
Дата: 2025-12-09

Обеспечивает:
- Админ-панель (/manager)
- Просмотр логов (/logs)
- Статистика бота (/stats)
- LLM-чат с админами (через Anthropic Claude)
- Управление пользователями
"""

import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Anthropic Claude API
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)


class AdminManager:
    """Менеджер админ-панели"""
    
    def __init__(self, db_manager=None, ai_core=None, autotrader=None):
        """
        Инициализация AdminManager
        
        Args:
            db_manager: Экземпляр DatabaseManager
            ai_core: Экземпляр AICore
            autotrader: Экземпляр AutoTrader
        """
        self.db_manager = db_manager
        self.ai_core = ai_core
        self.autotrader = autotrader
        
        # Anthropic API для LLM-чата
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.anthropic_client = None
        
        if ANTHROPIC_AVAILABLE and self.anthropic_key:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_key)
                logger.info("✅ Anthropic Claude API инициализирован (Admin)")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации Claude API: {e}")
        else:
            logger.warning("⚠️ LLM-чат недоступен (отсутствует ANTHROPIC_API_KEY)")
        
        # История чатов с админами (для контекста)
        self.admin_chat_history: Dict[int, List[Dict]] = {}
        
        logger.info("✅ AdminManager инициализирован")
    
    # ========================================
    # КОМАНДА /manager - АДМИН-ПАНЕЛЬ
    # ========================================
    
    async def handle_manager_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /manager - главная админ-панель"""
        keyboard = [
            [
                InlineKeyboardButton("📊 Статистика", callback_data='admin_stats'),
                InlineKeyboardButton("📝 Логи", callback_data='admin_logs')
            ],
            [
                InlineKeyboardButton("👥 Пользователи", callback_data='admin_users'),
                InlineKeyboardButton("🤖 Автоторговля", callback_data='admin_autotrade')
            ],
            [
                InlineKeyboardButton("🔍 AI Аналитика", callback_data='admin_ai'),
                InlineKeyboardButton("💬 LLM Чат", callback_data='admin_llm_chat')
            ],
            [InlineKeyboardButton("🔄 Перезапустить бота", callback_data='admin_restart')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "🛠️ **АДМИН-ПАНЕЛЬ**\n\n"
            "Выберите действие:"
        )
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # ========================================
    # КОМАНДА /stats - СТАТИСТИКА
    # ========================================
    
    async def handle_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /stats - статистика бота"""
        if not self.db_manager:
            await update.message.reply_text("⚠️ База данных недоступна")
            return
        
        # Получаем глобальную статистику
        stats = self.db_manager.get_global_stats()
        
        # Получаем информацию о автоторговле
        users_with_autotrade = len(self.db_manager.get_users_with_auto_trading()) if self.db_manager else 0
        
        text = (
            "📊 **СТАТИСТИКА БОТА**\n\n"
            f"👥 Всего пользователей: {stats.get('total_users', 0)}\n"
            f"💎 Активных подписок: {stats.get('active_subscriptions', 0)}\n"
            f"📈 Всего сигналов: {stats.get('total_signals', 0)}\n"
            f"🤖 Автоторговля включена: {users_with_autotrade} польз.\n\n"
            f"🕐 Обновлено: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='admin_panel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # ========================================
    # КОМАНДА /logs - ЛОГИ
    # ========================================
    
    async def handle_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /logs - просмотр логов"""
        try:
            # Читаем последние 50 строк из лог-файла
            with open('bot.log', 'r', encoding='utf-8') as f:
                lines = f.readlines()
                last_lines = lines[-50:] if len(lines) > 50 else lines
                log_text = ''.join(last_lines)
            
            # Telegram ограничивает длину сообщения 4096 символами
            if len(log_text) > 4000:
                log_text = log_text[-4000:]
            
            text = f"📝 **ЛОГИ (последние 50 строк)**\n\n```\n{log_text}\n```"
            
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='admin_panel')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка чтения логов: {e}")
    
    # ========================================
    # LLM-ЧАТ С АДМИНАМИ
    # ========================================
    
    async def handle_llm_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик LLM-чата с админами"""
        if not self.anthropic_client:
            await update.message.reply_text(
                "⚠️ LLM-чат недоступен.\n"
                "Убедитесь, что ANTHROPIC_API_KEY задан в переменных окружения."
            )
            return
        
        user = update.effective_user
        message_text = update.message.text
        
        # Инициализируем историю чата для пользователя
        if user.id not in self.admin_chat_history:
            self.admin_chat_history[user.id] = []
        
        # Добавляем сообщение пользователя в историю
        self.admin_chat_history[user.id].append({
            'role': 'user',
            'content': message_text
        })
        
        # Ограничиваем историю последними 10 сообщениями
        if len(self.admin_chat_history[user.id]) > 10:
            self.admin_chat_history[user.id] = self.admin_chat_history[user.id][-10:]
        
        try:
            # Формируем системный промпт
            system_prompt = """Ты - AI ассистент для администратора торгового бота.
Ты помогаешь:
- Анализировать статистику и метрики
- Давать рекомендации по улучшению бота
- Отвечать на вопросы о трейдинге и стратегиях
- Помогать с технической поддержкой

Отвечай кратко, по делу, на русском языке."""
            
            # Отправляем запрос к Claude
            typing_task = asyncio.create_task(self._show_typing(update))
            
            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=system_prompt,
                messages=self.admin_chat_history[user.id]
            )
            
            typing_task.cancel()
            
            # Получаем ответ
            assistant_reply = message.content[0].text
            
            # Добавляем ответ в историю
            self.admin_chat_history[user.id].append({
                'role': 'assistant',
                'content': assistant_reply
            })
            
            # Отправляем ответ
            await update.message.reply_text(assistant_reply)
            
            logger.info(f"✅ LLM ответ отправлен админу {user.id}")
        
        except Exception as e:
            logger.error(f"❌ Ошибка LLM-чата: {e}")
            await update.message.reply_text(
                f"⚠️ Ошибка обработки запроса: {e}\n\n"
                "Попробуйте еще раз."
            )
    
    async def _show_typing(self, update: Update):
        """Показывать индикатор печати во время обработки запроса"""
        try:
            while True:
                await update.message.chat.send_action('typing')
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass
    
    # ========================================
    # ОБРАБОТЧИК CALLBACK КНОПОК
    # ========================================
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик callback кнопок админ-панели"""
        query = update.callback_query
        data = query.data
        
        if data == 'admin_stats':
            # Статистика
            stats = self.db_manager.get_global_stats() if self.db_manager else {}
            users_with_autotrade = len(self.db_manager.get_users_with_auto_trading()) if self.db_manager else 0
            
            text = (
                "📊 **СТАТИСТИКА БОТА**\n\n"
                f"👥 Всего пользователей: {stats.get('total_users', 0)}\n"
                f"💎 Активных подписок: {stats.get('active_subscriptions', 0)}\n"
                f"📈 Всего сигналов: {stats.get('total_signals', 0)}\n"
                f"🤖 Автоторговля: {users_with_autotrade} польз.\n\n"
                f"🕐 {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC"
            )
            
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='admin_panel')]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        elif data == 'admin_logs':
            # Логи
            try:
                with open('bot.log', 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    last_lines = lines[-30:] if len(lines) > 30 else lines
                    log_text = ''.join(last_lines)
                
                if len(log_text) > 3500:
                    log_text = log_text[-3500:]
                
                text = f"📝 **ЛОГИ**\n\n```\n{log_text}\n```"
            except Exception as e:
                text = f"❌ Ошибка чтения логов: {e}"
            
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='admin_panel')]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        elif data == 'admin_users':
            # Список пользователей
            users = self.db_manager.get_all_users() if self.db_manager else []
            
            text = f"👥 **ПОЛЬЗОВАТЕЛИ** ({len(users)})\n\n"
            
            for i, user in enumerate(users[:10], 1):  # Показываем первых 10
                username = user.get('username', 'unknown')
                subscription = user.get('subscription_type', 'None')
                text += f"{i}. @{username} - {subscription}\n"
            
            if len(users) > 10:
                text += f"\n... и еще {len(users) - 10} пользователей"
            
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='admin_panel')]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        elif data == 'admin_autotrade':
            # Информация об автоторговле
            users_with_autotrade = self.db_manager.get_users_with_auto_trading() if self.db_manager else []
            
            text = f"🤖 **АВТОТОРГОВЛЯ**\n\n"
            text += f"Активных пользователей: {len(users_with_autotrade)}\n\n"
            
            for user in users_with_autotrade[:5]:
                username = user.get('username', 'unknown')
                strategy = user.get('auto_trading_strategy', 'unknown')
                mode = user.get('auto_trading_mode', 'demo')
                text += f"• @{username} - {strategy} ({mode})\n"
            
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='admin_panel')]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        elif data == 'admin_ai':
            # Информация об AI аналитике
            text = "🔍 **AI АНАЛИТИКА**\n\n"
            
            if self.ai_core:
                text += "✅ AI Core активен\n"
                text += f"📊 Активов в анализе: {len(self.ai_core.assets)}\n"
                text += f"⏱️ Интервал: {self.ai_core.analysis_interval}сек\n"
            else:
                text += "❌ AI Core не инициализирован"
            
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='admin_panel')]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        elif data == 'admin_llm_chat':
            # Инструкции по LLM-чату
            text = (
                "💬 **LLM ЧАТ**\n\n"
                "Для общения с LLM просто напишите сообщение боту.\n\n"
                "LLM может помочь с:\n"
                "• Анализом статистики\n"
                "• Рекомендациями по стратегиям\n"
                "• Технической поддержкой\n\n"
                "Напишите любое сообщение для начала чата."
            )
            
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='admin_panel')]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        elif data == 'admin_panel':
            # Возврат в главное меню
            keyboard = [
                [
                    InlineKeyboardButton("📊 Статистика", callback_data='admin_stats'),
                    InlineKeyboardButton("📝 Логи", callback_data='admin_logs')
                ],
                [
                    InlineKeyboardButton("👥 Пользователи", callback_data='admin_users'),
                    InlineKeyboardButton("🤖 Автоторговля", callback_data='admin_autotrade')
                ],
                [
                    InlineKeyboardButton("🔍 AI Аналитика", callback_data='admin_ai'),
                    InlineKeyboardButton("💬 LLM Чат", callback_data='admin_llm_chat')
                ]
            ]
            
            text = "🛠️ **АДМИН-ПАНЕЛЬ**\n\nВыберите действие:"
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
