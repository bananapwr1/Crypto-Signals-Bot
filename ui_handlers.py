"""
ui_handlers.py - UI обработчики для клиентов
Версия: 1.0
Дата: 2025-12-09

Обеспечивает:
- Обработчики клиентских команд (/start, /plans, /bank, etc.)
- Клиентские callback кнопки
- Генерация торговых сигналов
- Управление подписками
- Настройки пользователя
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Константы тарифов
SUBSCRIPTION_PLANS = {
    'short': {
        '1m': 4990,
        '6m': 26946,
        '12m': 47904,
        'name': 'SHORT',
        'description': 'Быстрые сигналы (1-5 мин)',
        'emoji': '⚡'
    },
    'long': {
        '1m': 4990,
        '6m': 26946,
        '12m': 47904,
        'name': 'LONG',
        'description': 'Длинные сигналы (1-4 часа)',
        'emoji': '🔵'
    },
    'vip': {
        '1m': 9990,
        '6m': 53946,
        '12m': 95904,
        'name': 'VIP',
        'description': 'Все функции + автоторговля',
        'emoji': '💎'
    }
}


class UIHandlers:
    """Обработчики UI для клиентов"""
    
    def __init__(self, db_manager=None, pocket_api=None):
        """
        Инициализация UIHandlers
        
        Args:
            db_manager: Экземпляр DatabaseManager
            pocket_api: Экземпляр PocketOptionAPI
        """
        self.db_manager = db_manager
        self.pocket_api = pocket_api
        
        logger.info("✅ UIHandlers инициализирован")
    
    # ========================================
    # КОМАНДА /start
    # ========================================
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        
        # Создаем или получаем пользователя
        if self.db_manager:
            self.db_manager.get_or_create_user(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
            self.db_manager.log_command(user.id, 'start')
        
        keyboard = [
            [InlineKeyboardButton("💎 Тарифы и подписки", callback_data='plans')],
            [
                InlineKeyboardButton("⚡ SHORT сигнал", callback_data='short_signal'),
                InlineKeyboardButton("🔵 LONG сигнал", callback_data='long_signal')
            ],
            [
                InlineKeyboardButton("💰 Банк", callback_data='bank'),
                InlineKeyboardButton("📊 Статистика", callback_data='my_stats')
            ],
            [
                InlineKeyboardButton("🤖 Автоторговля", callback_data='autotrade'),
                InlineKeyboardButton("⚙️ Настройки", callback_data='settings')
            ],
            [InlineKeyboardButton("❓ Помощь", callback_data='help')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            f"👋 Привет, {user.first_name}!\n\n"
            "🤖 Добро пожаловать в торговый бот с AI-аналитикой!\n\n"
            "Что умеет бот:\n"
            "⚡ **SHORT сигналы** (1-5 мин)\n"
            "🔵 **LONG сигналы** (1-4 часа)\n"
            "🤖 **Автоторговля** (VIP)\n"
            "📊 **Статистика** и аналитика\n\n"
            "Выберите действие:"
        )
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # ========================================
    # КОМАНДА /plans - ТАРИФЫ
    # ========================================
    
    async def handle_plans(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /plans"""
        user = update.effective_user
        
        if self.db_manager:
            self.db_manager.log_command(user.id, 'plans')
        
        keyboard = []
        
        for plan_id, plan in SUBSCRIPTION_PLANS.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"{plan['emoji']} {plan['name']} - {plan['description']}",
                    callback_data=f'plan_{plan_id}'
                )
            ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='menu')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "💎 **ТАРИФЫ И ПОДПИСКИ**\n\n"
            "Выберите подходящий тариф:\n\n"
            "⚡ **SHORT** - быстрые сигналы (1-5 мин)\n"
            "🔵 **LONG** - долгосрочные сигналы (1-4 часа)\n"
            "💎 **VIP** - все функции + автоторговля"
        )
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # ========================================
    # КОМАНДА /bank - БАНК
    # ========================================
    
    async def handle_bank(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /bank"""
        user = update.effective_user
        
        if self.db_manager:
            self.db_manager.log_command(user.id, 'bank')
            user_data = self.db_manager.get_user(user.id)
        else:
            user_data = None
        
        initial_balance = user_data.get('initial_balance') if user_data else None
        current_balance = user_data.get('current_balance') if user_data else None
        
        if initial_balance and current_balance:
            profit = current_balance - initial_balance
            profit_percent = (profit / initial_balance * 100) if initial_balance > 0 else 0
            
            text = (
                "💰 **ВАШ БАНК**\n\n"
                f"💵 Начальный баланс: ${initial_balance:.2f}\n"
                f"💰 Текущий баланс: ${current_balance:.2f}\n"
                f"📈 Прибыль: ${profit:.2f} ({profit_percent:+.2f}%)\n"
            )
        else:
            text = (
                "💰 **ВАШ БАНК**\n\n"
                "Банк еще не настроен.\n"
                "Укажите начальный баланс для отслеживания прибыли."
            )
        
        keyboard = [
            [InlineKeyboardButton("💵 Установить баланс", callback_data='set_balance')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # ========================================
    # КОМАНДА /autotrade - АВТОТОРГОВЛЯ
    # ========================================
    
    async def handle_autotrade(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /autotrade"""
        user = update.effective_user
        
        if self.db_manager:
            self.db_manager.log_command(user.id, 'autotrade')
            
            # Проверяем VIP подписку
            has_vip = self.db_manager.check_subscription(user.id, 'vip')
            
            if not has_vip:
                text = (
                    "🤖 **АВТОТОРГОВЛЯ**\n\n"
                    "⚠️ Автоторговля доступна только на VIP тарифе.\n\n"
                    "Оформите VIP подписку для доступа к автоматической торговле."
                )
                
                keyboard = [
                    [InlineKeyboardButton("💎 Купить VIP", callback_data='plan_vip')],
                    [InlineKeyboardButton("⬅️ Назад", callback_data='menu')]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                return
            
            # Проверяем статус автоторговли
            user_data = self.db_manager.get_user(user.id)
            auto_trading_enabled = user_data.get('auto_trading_enabled', False) if user_data else False
            
            status_text = "✅ Включена" if auto_trading_enabled else "❌ Отключена"
            
            text = (
                "🤖 **АВТОТОРГОВЛЯ**\n\n"
                f"Статус: {status_text}\n\n"
                "Автоторговля позволяет боту автоматически выполнять сделки "
                "на основе сигналов и выбранной стратегии."
            )
            
            keyboard = [
                [InlineKeyboardButton(
                    "✅ Включить" if not auto_trading_enabled else "❌ Отключить",
                    callback_data='toggle_autotrade'
                )],
                [InlineKeyboardButton("⚙️ Настройки стратегии", callback_data='autotrade_strategy')],
                [InlineKeyboardButton("⬅️ Назад", callback_data='menu')]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text("⚠️ База данных недоступна")
    
    # ========================================
    # КОМАНДА /settings - НАСТРОЙКИ
    # ========================================
    
    async def handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /settings"""
        user = update.effective_user
        
        if self.db_manager:
            self.db_manager.log_command(user.id, 'settings')
        
        keyboard = [
            [InlineKeyboardButton("🌍 Язык", callback_data='settings_language')],
            [InlineKeyboardButton("💱 Валюта", callback_data='settings_currency')],
            [InlineKeyboardButton("🔔 Уведомления", callback_data='settings_notifications')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='menu')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "⚙️ **НАСТРОЙКИ**\n\nВыберите параметр для изменения:"
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # ========================================
    # ТОРГОВЫЕ СИГНАЛЫ
    # ========================================
    
    async def handle_short_signal(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /short - SHORT сигнал"""
        user = update.effective_user
        
        if self.db_manager:
            self.db_manager.log_command(user.id, 'short')
            
            # Проверяем подписку
            has_subscription = self.db_manager.check_subscription(user.id, 'short') or \
                              self.db_manager.check_subscription(user.id, 'vip')
            
            if not has_subscription:
                text = (
                    "⚡ **SHORT СИГНАЛ**\n\n"
                    "⚠️ Для получения SHORT сигналов необходима подписка.\n\n"
                    "Оформите подписку SHORT или VIP."
                )
                
                keyboard = [
                    [InlineKeyboardButton("💎 Купить подписку", callback_data='plans')],
                    [InlineKeyboardButton("⬅️ Назад", callback_data='menu')]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                return
        
        # Генерируем сигнал (заглушка)
        text = (
            "⚡ **SHORT СИГНАЛ**\n\n"
            "📊 Актив: BTC/USD\n"
            "📈 Направление: 🟢 CALL\n"
            "⏱️ Время: 5 минут\n"
            "💰 Ставка: $100\n"
            "🎯 Уверенность: 75%\n\n"
            "⚠️ Не является финансовой рекомендацией."
        )
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_long_signal(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /long - LONG сигнал"""
        user = update.effective_user
        
        if self.db_manager:
            self.db_manager.log_command(user.id, 'long')
            
            # LONG сигналы доступны всем (FREE)
            pass
        
        # Генерируем сигнал (заглушка)
        text = (
            "🔵 **LONG СИГНАЛ**\n\n"
            "📊 Актив: ETH/USD\n"
            "📈 Направление: 🔴 PUT\n"
            "⏱️ Время: 1 час\n"
            "💰 Ставка: 2.5% от банка\n"
            "🎯 Уверенность: 68%\n\n"
            "⚠️ Не является финансовой рекомендацией."
        )
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_my_longs(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /my_longs - Мои LONG позиции"""
        user = update.effective_user
        
        if self.db_manager:
            self.db_manager.log_command(user.id, 'my_longs')
            signals = self.db_manager.get_user_signals(user.id, limit=10)
        else:
            signals = []
        
        if not signals:
            text = "📋 **МОИ LONG ПОЗИЦИИ**\n\nУ вас пока нет открытых позиций."
        else:
            text = f"📋 **МОИ LONG ПОЗИЦИИ** ({len(signals)})\n\n"
            
            for i, signal in enumerate(signals[:5], 1):
                symbol = signal.get('symbol', 'N/A')
                signal_type = signal.get('signal_type', 'N/A')
                result = signal.get('result', 'pending')
                
                emoji = "⏳" if result == 'pending' else ("✅" if result == 'win' else "❌")
                
                text += f"{i}. {emoji} {symbol} {signal_type}\n"
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_my_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /my_stats - Моя статистика"""
        user = update.effective_user
        
        if self.db_manager:
            self.db_manager.log_command(user.id, 'my_stats')
            stats = self.db_manager.get_user_stats(user.id)
        else:
            stats = {}
        
        text = (
            "📊 **МОЯ СТАТИСТИКА**\n\n"
            f"📈 Всего сигналов: {stats.get('total_signals', 0)}\n"
            f"✅ Выигрышей: {stats.get('wins', 0)}\n"
            f"❌ Проигрышей: {stats.get('losses', 0)}\n"
            f"📊 Винрейт: {stats.get('win_rate', 0):.1f}%\n"
            f"💰 Прибыль: ${stats.get('total_profit', 0):.2f}"
        )
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help - Помощь"""
        text = (
            "❓ **ПОМОЩЬ**\n\n"
            "**Команды:**\n"
            "/start - Главное меню\n"
            "/plans - Тарифы и подписки\n"
            "/bank - Управление банком\n"
            "/autotrade - Автоторговля (VIP)\n"
            "/short - SHORT сигнал (1-5 мин)\n"
            "/long - LONG сигнал (1-4 часа)\n"
            "/my_stats - Моя статистика\n\n"
            "**Поддержка:** @banana_pwr"
        )
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # ========================================
    # ОБРАБОТЧИК CALLBACK КНОПОК
    # ========================================
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик callback кнопок"""
        query = update.callback_query
        data = query.data
        
        # Главное меню
        if data == 'menu':
            keyboard = [
                [InlineKeyboardButton("💎 Тарифы и подписки", callback_data='plans')],
                [
                    InlineKeyboardButton("⚡ SHORT сигнал", callback_data='short_signal'),
                    InlineKeyboardButton("🔵 LONG сигнал", callback_data='long_signal')
                ],
                [
                    InlineKeyboardButton("💰 Банк", callback_data='bank'),
                    InlineKeyboardButton("📊 Статистика", callback_data='my_stats')
                ],
                [
                    InlineKeyboardButton("🤖 Автоторговля", callback_data='autotrade'),
                    InlineKeyboardButton("⚙️ Настройки", callback_data='settings')
                ]
            ]
            
            text = "🏠 **ГЛАВНОЕ МЕНЮ**\n\nВыберите действие:"
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        # Остальные callback обрабатываются аналогично
        else:
            await query.edit_message_text(f"🚧 Функция '{data}' в разработке")
