import os
import logging
import pandas as pd
import numpy as np
import yfinance as yf
import asyncio
import sqlite3
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.patheffects as pe
import io
import time
import random
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import warnings
import uuid
from yookassa import Configuration, Payment
from webhook_system import webhook_system
from crypto_utils import encrypt_ssid, decrypt_ssid
warnings.filterwarnings('ignore')

load_dotenv()
matplotlib.use('Agg')

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Константы ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@banana_pwr") # Используем переменную окружения
# Московский часовой пояс (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))
# Реферальная ссылка Pocket Option
POCKET_OPTION_REF_LINK = "https://pocket-friends.com/r/ugauihalod"
# Промокод для новых пользователей
PROMO_CODE = "FRIENDUGAUIHALOD"
# Команды бота по умолчанию (для сброса настроек)
DEFAULT_BOT_COMMANDS = [
    ("start", "🏠 Главное меню"),
    ("plans", "💎 Тарифы и подписки"),
    ("bank", "💰 Управление банком"),
    ("autotrade", "🤖 Автоторговля (...")
]
# ID магазина и Секретный ключ YooKassa
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

# --- Настройка YooKassa (если ключи доступны) ---
if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
    Configuration.configure(
        account_id=YOOKASSA_SHOP_ID,
        secret_key=YOOKASSA_SECRET_KEY
    )
    logger.info("YooKassa configured successfully.")
else:
    logger.warning("YooKassa configuration skipped: SHOP_ID or SECRET_KEY is missing.")

# --- Вспомогательные функции (заглушки) ---

# Функция для получения текущего статуса подписки пользователя (заглушка)
def get_user_subscription_status(user_id):
    """Возвращает статус подписки для демонстрации интерфейса."""
    if user_id % 2 == 0:
         return {"is_active": True, "end_date": (datetime.now(MOSCOW_TZ) + timedelta(days=7)).strftime("%d.%m.%Y")}
    return {"is_active": False}

# Функция для получения текущего баланса (заглушка)
def get_user_balance(user_id):
    """Возвращает текущий баланс пользователя."""
    return random.randint(100, 500) / 100 * 1000 # Например, от 10000 до 50000

# --- Основные команды ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /start, отображая главное меню бота."""
    user = update.effective_user
    user_id = user.id
    status = get_user_subscription_status(user_id)
    balance = get_user_balance(user_id)
    
    # 1. Формирование Текста Сообщения
    text_lines = []
    text_lines.append(f"👋 Добро пожаловать, *{user.first_name}*! (ID: `{user_id}`)\n")
    text_lines.append("-------------------------------------------------")
    
    # Статус подписки
    if status.get("is_active"):
        text_lines.append(f"🟢 *ПОДПИСКА:* Активна до {status['end_date']}")
    else:
        text_lines.append("🔴 *ПОДПИСКА:* Не активна. ➡️ /plans")

    # Баланс
    text_lines.append(f"💰 *БАЛАНС:* {balance:,.2f} USD (Учетная запись)")
    text_lines.append("-------------------------------------------------\n")
    text_lines.append("Выберите нужный раздел для управления ботом:")

    text = "\n".join(text_lines)
    
    # 2. Формирование Кнопок
    keyboard = [
        # Первый ряд: Функциональные разделы
        [InlineKeyboardButton("💎 Тарифы и подписки", callback_data="plans_menu")],
        [InlineKeyboardButton("💰 Управление банком", callback_data="bank_menu")],
        [InlineKeyboardButton("🤖 Автоторговля", callback_data="autotrade_menu")],
        # Второй ряд: Сервисная информация (например, контакты)
        [InlineKeyboardButton("📞 Поддержка", url=f"https://t.me/{SUPPORT_CONTACT.lstrip('@')}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправка/редактирование
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Создает и отправляет пользователю интерфейс с тарифными планами.
    """
    # Этот код уже был создан в предыдущем шаге и остался без изменений
    user_id = update.effective_user.id
    status = get_user_subscription_status(user_id)
    
    # 1. Формирование Текста Сообщения
    text_lines = []
    text_lines.append("💎 *Ваши Тарифы и Подписки* 💎\n")
    
    if status.get("is_active"):
        text_lines.append(f"✅ *СТАТУС:* Активная подписка")
        text_lines.append(f"📅 *Действует до:* {status['end_date']}")
        text_lines.append("-------------------------------------------------\n")
        text_lines.append("Вы можете продлить подписку, выбрав новый план ниже:")
    else:
        text_lines.append("❌ *СТАТУС:* Подписка не активна.")
        text_lines.append("Выберите подходящий тариф для доступа к сигналам:")
        
    text_lines.append("\n*ДОСТУПНЫЕ ПЛАНЫ:*")
    
    
    # 2. Формирование Кнопок (Inline Keyboard)
    keyboard = []
    
    PLANS_DATA = {
        "1m": {"name": "Базовый", "duration_days": 30, "price": 1500},
        "3m": {"name": "Премиум", "duration_days": 90, "price": 4000, "discount": "Скидка 11%"},
        "12m": {"name": "VIP", "duration_days": 365, "price": 15000, "discount": "Скидка 17%", "best_deal": True},
    }

    for key, plan in PLANS_DATA.items():
        button_text = f"{plan['name']} - {plan['price']:,} ₽"
        if plan.get("discount"):
            button_text += f" ({plan['discount']})"
        if plan.get("best_deal"):
            button_text = "⭐️ " + button_text + " (Лучшая цена!)"
        
        # Добавляем описание плана в текст
        text_lines.append(f"• *{plan['name']} ({plan['duration_days']} дн.):* {plan['price']:,} ₽")
        
        # Создаем кнопку для покупки
        keyboard.append([
            InlineKeyboardButton(
                button_text, 
                callback_data=f"buy_plan_{key}" # Например, buy_plan_1m
            )
        ])
    
    # Добавляем сервисные кнопки
    keyboard.append([
        InlineKeyboardButton("💳 Промокод / Оплата YooKassa", callback_data="show_yookassa_info")
    ])
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад в Главное меню", callback_data="start")
    ])

    text = "\n".join(text_lines)
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправка или редактирование сообщения
    if update.callback_query:
        await update.callback_query.answer()
        # Редактируем, если это был CallbackQuery (например, из start_command)
        await update.callback_query.edit_message_text(
            text=text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        # Отправляем новое сообщение, если это была команда /plans
        await update.message.reply_text(
            text=text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
# Функция для заглушки, которая будет вызвана при нажатии кнопки.
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # Логика навигации и оплаты
    if data == 'start' or data == 'main_menu':
        await start_command(update, context)
        return
    elif data == 'plans_menu':
        await plans_command(update, context)
        return
    
    # Заглушки для других разделов
    elif data == 'bank_menu' or data == 'autotrade_menu':
        section_name = "Управление банком" if data == 'bank_menu' else "Автоторговля"
        await query.edit_message_text(
            text=f"🚧 Раздел *{section_name}* находится в разработке.\n\n"
                 f"Возвращаемся в главное меню.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ В Главное меню", callback_data="start")]])
        )
        return
        
    # Обработка покупки (пока заглушка)
    elif data.startswith("buy_plan_"):
        plan_key = data.split("_")[-1]
        plan_name = PLANS_DATA.get(plan_key, {}).get("name", "Выбранный")
        plan_price = PLANS_DATA.get(plan_key, {}).get("price", "???")
        
        # В этом месте будет вызов функции создания платежа YooKassa
        
        await query.edit_message_text(
            text=f"✅ Вы выбрали план *{plan_name}* за {plan_price:,} ₽.\n"
                 f"Сейчас мы перейдем к оплате через YooKassa...",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад в Тарифы", callback_data="plans_menu")]],),
            parse_mode='Markdown'
        )
        return
    
    elif data == 'show_yookassa_info':
        await query.edit_message_text(
            text=f"ℹ️ *Информация об оплате:*\n\n"
                 f"Мы используем платежную систему YooKassa для безопасных и быстрых платежей.\n"
                 f"Доступные способы: Карта, SberPay, ЮMoney и др.\n\n"
                 f"🎁 Ваш промокод для новых пользователей: `{PROMO_CODE}`\n\n"
                 f"Нажмите на кнопку ниже, чтобы вернуться к выбору тарифа.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Выбрать тариф", callback_data="plans_menu")]],),
            parse_mode='Markdown'
        )
        return
        
    # Если callback_data не распознан
    else:
        logger.warning(f"Неизвестный callback_data: {data}")
        await start_command(update, context)


# --- Main function setup ---
def main() -> None:
    """Запуск бота."""
    try:
        # 1. Создание приложения
        application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
        app = application # Переименовываем для краткости

        # 2. Обработчики команд
        app.add_handler(CommandHandler("start", start_command))
        # Добавляем новую команду для тарифов
        app.add_handler(CommandHandler("plans", plans_command)) 
        
        # Заглушки для других команд
        app.add_handler(CommandHandler("bank", start_command)) 
        app.add_handler(CommandHandler("autotrade", start_command)) 
        
        # Обработчик Callback Query (для кнопок)
        app.add_handler(CallbackQueryHandler(button_callback))
        # app.add_error_handler(error_handler)
        
        # Установка меню команд
        # (Оставлю как есть, предполагая что set_my_commands будет реализован в post_init)
        
        logger.info("🚀 Bot started successfully!")
        print("✅ Crypto Signals Bot is running...")
        print(f"👤 Admin User ID: {ADMIN_USER_ID}")
        print(f"📞 Support Contact: {SUPPORT_CONTACT}")
        
        # Запуск бота (Polling)
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Critical error in main: {e}")
        
async def post_init(application: Application) -> None:
    """Выполняется сразу после инициализации бота."""
    # Установка меню команд
    await application.bot.set_my_commands([BotCommand(command, description) for command, description in DEFAULT_BOT_COMMANDS])


if __name__ == '__main__':
    # Определяем PLANS_DATA, чтобы она была доступна вне main()
    PLANS_DATA = {
        "1m": {"name": "Базовый", "duration_days": 30, "price": 1500},
        "3m": {"name": "Премиум", "duration_days": 90, "price": 4000, "discount": "Скидка 11%"},
        "12m": {"name": "VIP", "duration_days": 365, "price": 15000, "discount": "Скидка 17%", "best_deal": True},
    }
    main()