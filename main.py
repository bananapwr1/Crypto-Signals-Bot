```python
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Состояния пользователя
class UserState:
    def __init__(self):
        self.initial_bank = 0
        self.current_bank = 0
        self.strategy = "martingale_x3"
        self.base_bet = 0
        self.subscription = "FREE"
        self.subscription_end = "14.11.2025"

# Хранилище состояний пользователей
user_states = {}

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states:
        user_states[user_id] = UserState()
        user_states[user_id].initial_bank = 60000
        user_states[user_id].current_bank = 60000
    
    keyboard = [
        [InlineKeyboardButton("SHORT", callback_data="short"),
         InlineKeyboardButton("LONG", callback_data="long")],
        [InlineKeyboardButton("📊 Управление банком", callback_data="bank_management")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "# Crypto Signals Bot\n## 6от\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

# Главное меню
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("SHORT", callback_data="short"),
         InlineKeyboardButton("LONG", callback_data="long")],
        [InlineKeyboardButton("📊 Управление банком", callback_data="bank_management")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "# Crypto Signals Bot\n## 6от\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

# Раздел SHORT
async def short_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = user_states[user_id]
    
    # Расчет ставки для мартингейла
    if user.strategy == "martingale_x2":
        bet = user.current_bank * 0.01  # 1% для x2
    elif user.strategy == "martingale_x3":
        bet = user.current_bank * 0.005  # 0.5% для x3
    else:  # x5
        bet = user.current_bank * 0.002  # 0.2% для x5
    
    keyboard = [
        [InlineKeyboardButton("📊 Получить сигнал", callback_data="get_short_signal")],
        [InlineKeyboardButton("⚙️ Настройки стратегии", callback_data="strategy_settings")],
        [InlineKeyboardButton("📈 Мои SHORT сделки", callback_data="my_short_trades")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🤖 **SHORT СТРАТЕГИЯ**\n\n"
        f"• Действует до: {user.subscription_end}\n\n"
        f"**БАНК:**\n"
        f"• Начальный: {user.initial_bank:,.0f}₽\n"
        f"• Текущий: {user.current_bank:,.0f}₽\n"
        f"• Прибыль: {'+' if user.current_bank >= user.initial_bank else ''}{user.current_bank - user.initial_bank:,.0f}₽ "
        f"({(user.current_bank/user.initial_bank-1)*100:+.1f}%)\n\n"
        f"**СТРАТЕГИЯ: МАРТИНГЕЙЛ {user.strategy.split('_')[1].upper()}**\n"
        f"• Текущая ставка: {bet:,.0f}₽\n"
        f"• Быстрая торговля (1-5 мин)\n"
        f"• Агрессивный рост\n\n"
        f"Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Раздел LONG
async def long_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = user_states[user_id]
    
    bet = user.current_bank * 0.025  # 2.5% для LONG
    
    keyboard = [
        [InlineKeyboardButton("📊 Получить сигнал", callback_data="get_long_signal")],
        [InlineKeyboardButton("⚙️ Настройки стратегии", callback_data="long_strategy_settings")],
        [InlineKeyboardButton("📈 Мои LONG сделки", callback_data="my_long_trades")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🤖 **LONG СТРАТЕГИЯ**\n\n"
        f"• Действует до: {user.subscription_end}\n\n"
        f"**БАНК:**\n"
        f"• Начальный: {user.initial_bank:,.0f}₽\n"
        f"• Текущий: {user.current_bank:,.0f}₽\n"
        f"• Прибыль: {'+' if user.current_bank >= user.initial_bank else ''}{user.current_bank - user.initial_bank:,.0f}₽ "
        f"({(user.current_bank/user.initial_bank-1)*100:+.1f}%)\n\n"
        f"**СТРАТЕГИЯ: ПРОЦЕНТНАЯ 2.5%**\n"
        f"• Текущая ставка: {bet:,.0f}₽\n"
        f"• Длинные сделки (1-4 часа)\n"
        f"• Стабильный доход\n\n"
        f"Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Управление банком
async def bank_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = user_states[user_id]
    
    # Расчет уровней мартингейла
    levels = calculate_martingale_levels(user)
    
    keyboard = [
        [InlineKeyboardButton("💳 Изменить текущий банк", callback_data="change_bank")],
        [InlineKeyboardButton("🔄 Сбросить и начать заново", callback_data="reset_bank")],
        [InlineKeyboardButton("📊 Настройки стратегии", callback_data="strategy_settings")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💰 **УПРАВЛЕНИЕ БАНКОМ**\n\n"
        f"**БАНК:**\n"
        f"• Начальный: {user.initial_bank:,.0f}₽\n"
        f"• Текущий: {user.current_bank:,.0f}₽\n"
        f"• Прибыль: {'+' if user.current_bank >= user.initial_bank else ''}{user.current_bank - user.initial_bank:,.0f}₽ "
        f"({(user.current_bank/user.initial_bank-1)*100:+.1f}%)\n\n"
        f"**СТРАТЕГИЯ: МАРТИНГЕЙЛ {user.strategy.split('_')[1].upper()}**\n\n"
        f"Множитель после проигрыша: {user.strategy.split('_')[1]}\n\n"
        f"**Уровни ставок:**\n{levels}\n\n"
        f"Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Расчет уровней мартингейла
def calculate_martingale_levels(user):
    base_bet = user.base_bet if user.base_bet > 0 else user.current_bank * 0.005
    multiplier = int(user.strategy.split('_')[1])
    
    levels = []
    current_bet = base_bet
    for i in range(6):
        levels.append(f"{i+1}. {current_bet:,.0f}₽")
        current_bet *= multiplier
    
    return " → ".join(levels)

# Настройки стратегии
async def strategy_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = user_states[user_id]
    
    keyboard = [
        [InlineKeyboardButton("2️⃣ Мартингейл x2", callback_data="set_martingale_x2"),
         InlineKeyboardButton("3️⃣ Мартингейл x3", callback_data="set_martingale_x3")],
        [InlineKeyboardButton("5️⃣ Мартингейл x5", callback_data="set_martingale_x5")],
        [InlineKeyboardButton("💰 Установить базовую ставку", callback_data="set_base_bet")],
        [InlineKeyboardButton("🔙 Назад", callback_data="bank_management")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚙️ **НАСТРОЙКИ СТРАТЕГИИ**\n\n"
        f"Текущая стратегия: **МАРТИНГЕЙЛ {user.strategy.split('_')[1].upper()}**\n"
        f"Базовая ставка: {user.base_bet if user.base_bet > 0 else 'не установлена'}\n\n"
        f"Выберите множитель мартингейла:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Установка стратегии
async def set_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = user_states[user_id]
    
    strategy_map = {
        "set_martingale_x2": "martingale_x2",
        "set_martingale_x3": "martingale_x3", 
        "set_martingale_x5": "martingale_x5"
    }
    
    user.strategy = strategy_map[query.data]
    
    await query.edit_message_text(
        f"✅ Стратегия изменена на: **МАРТИНГЕЙЛ {user.strategy.split('_')[1].upper()}**",
        parse_mode='Markdown'
    )
    await strategy_settings(update, context)

# Получение SHORT сигнала
async def get_short_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = user_states[user_id]
    
    # Здесь должна быть логика генерации сигнала
    signal = generate_signal("SHORT", user)
    
    keyboard = [
        [InlineKeyboardButton("🔄 Новый сигнал", callback_data="get_short_signal")],
        [InlineKeyboardButton("📊 Управление банком", callback_data="bank_management")],
        [InlineKeyboardButton("🔙 Назад", callback_data="short")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        signal,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Генерация сигнала (заглушка)
def generate_signal(strategy_type, user):
    import random
    import datetime
    
    assets = ["EUR/USD OTC", "BTC/USD OTC", "ETH/USD OTC", "AAPL OTC", "INTEL OTC"]
    directions = ["ВВЕРХ", "ВНИЗ"]
    
    asset = random.choice(assets)
    direction = random.choice(directions)
    confidence = random.randint(85, 95)
    expiration = "5 минут" if strategy_type == "SHORT" else "1 час"
    bet = user.current_bank * 0.02 if strategy_type == "SHORT" else user.current_bank * 0.025
    
    current_time = datetime.datetime.now().strftime("%H:%M")
    
    return (
        f"🎯 **СИГНАЛ ДЛЯ POCKET OPTION**\n\n"
        f"**АКТИВ:** {asset}\n"
        f"⬆️ Кликните на название для копирования ⬆️\n\n"
        f"✅ **НАПРАВЛЕНИЕ:** {direction}\n"
        f"✅ **Уверенность:** {confidence}%\n"
        f"✅ **Экспирация:** {expiration}\n"
        f"✅ **Время входа:** {current_time}\n\n"
        f"💰 **Рекомендуемая ставка:** {bet:,.2f}₽\n\n"
        f"📊 **Статистика актива:**\n"
        f"• История: новый актив (менее 5 сигналов)\n"
        f"• Win Rate: анализируется...\n"
        f"• Ожидаемая доходность: расчет после 5+ сделок\n\n"
        f"📊 **Анализ рынка:**\n"
        f"• Волатильность: Очень низкая (стабильный)\n"
        f"• Активность: Обычная активность"
    )

# Тарифы
async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🆓 FREE", callback_data="tariff_free")],
        [InlineKeyboardButton("⚡ SHORT", callback_data="tariff_short")],
        [InlineKeyboardButton("📈 LONG", callback_data="tariff_long")],
        [InlineKeyboardButton("💎 VIP", callback_data="tariff_vip")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💎 **ВЫБЕРИТЕ ТАРИФ И ЗАРАБАТЫВАЙТЕ!**\n\n"
        "Доступные тарифные планы:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Обработка неизвестных команд
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Неизвестная команда. Используйте /start для начала работы.")

# Основная функция
def main():
    # Замените 'YOUR_BOT_TOKEN' на реальный токен вашего бота
    application = Application.builder().token('YOUR_BOT_TOKEN').build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    
    # Обработчики callback'ов
    application.add_handler(CallbackQueryHandler(main_menu, pattern="main_menu"))
    application.add_handler(CallbackQueryHandler(short_strategy, pattern="short"))
    application.add_handler(CallbackQueryHandler(long_strategy, pattern="long"))
    application.add_handler(CallbackQueryHandler(bank_management, pattern="bank_management"))
    application.add_handler(CallbackQueryHandler(strategy_settings, pattern="strategy_settings"))
    application.add_handler(CallbackQueryHandler(set_strategy, pattern="^set_martingale_"))
    application.add_handler(CallbackQueryHandler(get_short_signal, pattern="get_short_signal"))
    application.add_handler(CallbackQueryHandler(show_tariffs, pattern="tariffs"))
    
    # Обработчик неизвестных команд
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    
    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
```

Это полный интерфейс бота с:

· Главным меню
· Разделами SHORT/LONG стратегий
· Управлением банком
· Настройками мартингейла
· Генерацией сигналов
· Системой тарифов

Замени YOUR_BOT_TOKEN на реальный токен от @BotFather и добавь недостающие функции по мере необходимости.