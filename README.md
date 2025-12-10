# 🤖 Crypto Trading Bot

Автоматизированный торговый бот для бинарных опционов с AI-анализом рынка и интеграцией с Pocket Option.

## 📋 Основные возможности

- **AI Core** - Собственный анализ рынка на основе технического анализа
- **AutoTrader** - Автоматическое выполнение сделок
- **Telegram Bot UI** - Удобный интерфейс для пользователей
- **Admin Panel** - Веб-панель для администрирования
- **Multi-strategy** - Поддержка различных торговых стратегий

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────┐
│           TELEGRAM BOT UI                    │
│  - Команды для пользователей                │
│  - Управление подписками                    │
│  - Настройки автоторговли                   │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┴───────────┐
        │                      │
        ↓                      ↓
┌───────────────┐      ┌───────────────┐
│   AI CORE     │      │  AUTOTRADER   │
│               │      │               │
│ - Технический │──────→ - Выполнение  │
│   анализ      │        сделок        │
│ - Генерация   │      │ - Стратегии   │
│   сигналов    │      │ - Мани-       │
│ - Обучение    │      │   менеджмент  │
└───────┬───────┘      └───────┬───────┘
        │                      │
        └──────────┬───────────┘
                   ↓
        ┌──────────────────────┐
        │   SUPABASE БД        │
        │  - Пользователи      │
        │  - Сигналы           │
        │  - Сделки            │
        │  - Статистика        │
        └──────────────────────┘
```

## 📦 Основные компоненты

### Core Files
- `main.py` - Точка входа приложения
- `config.py` - Конфигурация и настройки
- `db_manager.py` - Менеджер базы данных (Supabase)

### Trading Modules
- `ai_core.py` - AI анализ рынка и генерация сигналов
- `autotrader.py` - Автоматическое выполнение сделок
- `pocket_option_api.py` - API для Pocket Option

### User Interface
- `ui_handlers.py` - Обработчики команд пользователей
- `admin_manager.py` - Админ-панель с LLM-чатом
- `app.py` - Flask веб-панель

### Utilities
- `crypto_utils.py` - Шифрование и безопасность
- `webhook_system.py` - Система вебхуков

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

Заполните необходимые переменные:

```env
# Telegram Bot
TELEGRAM_TOKEN=your_telegram_bot_token

# Supabase Database
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# Pocket Option
POCKET_OPTION_SSID=your_pocket_option_ssid

# AI (Optional)
ANTHROPIC_API_KEY=your_anthropic_api_key

# Admin
ADMIN_IDS=123456789,987654321

# Flask
FLASK_SECRET_KEY=your_secret_key
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

### 3. Запуск бота

```bash
python main.py
```

Бот запустит три параллельных потока:
1. **Telegram Bot UI** - Обработка команд пользователей
2. **AI Core** - Анализ рынка и генерация сигналов
3. **AutoTrader** - Выполнение сделок

## 🐳 Docker

### Сборка образа

```bash
docker build -t crypto-bot .
```

### Запуск через Docker Compose

```bash
docker-compose up -d
```

## 📊 Структура БД (Supabase)

### Таблица `users`
```sql
- user_id (text, PK)
- username (text)
- subscription_type (text)
- subscription_end (timestamp)
- auto_trading_enabled (boolean)
- trading_strategy (text)
- current_balance (numeric)
```

### Таблица `signals`
```sql
- id (bigint, PK)
- symbol (text)
- signal_type (text) -- CALL/PUT
- source (text) -- ai_core/parser/external
- confidence (numeric)
- entry_price (numeric)
- created_at (timestamp)
```

### Таблица `trades`
```sql
- id (bigint, PK)
- user_id (text, FK)
- signal_id (bigint, FK)
- amount (numeric)
- result (text) -- win/loss/pending
- profit_loss (numeric)
- created_at (timestamp)
```

## 🎯 Использование

### Команды для пользователей

- `/start` - Главное меню
- `/plans` - Тарифы и подписки
- `/bank` - Управление балансом
- `/autotrade` - Настройки автоторговли
- `/settings` - Настройки профиля
- `/my_stats` - Статистика сделок

### Команды для администраторов

- `/manager` - Админ-панель
- `/stats` - Глобальная статистика
- `/logs` - Просмотр логов

## 🧠 AI Core

AI Core использует технический анализ для генерации торговых сигналов:

### Индикаторы
- **RSI** (Relative Strength Index)
- **MACD** (Moving Average Convergence Divergence)
- **Bollinger Bands**
- **EMA** (Exponential Moving Average)
- **Stochastic Oscillator**

### Источники данных
- **yfinance** - Рыночные данные
- **Внешние сигналы** - Для обучения и улучшения модели

## 💼 Торговые стратегии

### 1. Процентная ставка (Percentage)
Ставка = Баланс × Процент

### 2. Мартингейл (Martingale)
Ставка = Базовая ставка × (Множитель ^ Уровень)

### 3. Д'Аламбер (D'Alembert)
Ставка = Базовая ставка + (Единица × Уровень)

## 🔐 Безопасность

- Шифрование SSID через Fernet
- Безопасное хранение credentials
- Проверка прав администратора
- Rate limiting для API запросов

## 📈 Мониторинг

### Flask Web Panel
Доступна по адресу: `http://localhost:5000`

- Статистика пользователей
- История команд
- Системные метрики

### Логи
Все события записываются в `bot.log`

## 🔧 Конфигурация

### Trading Parameters
```python
# config.py
INITIAL_BALANCE = 1000.0
MIN_TRADE_AMOUNT = 1.0
MAX_TRADE_AMOUNT = 10000.0
DEFAULT_PERCENTAGE = 2.5
MARTINGALE_MULTIPLIER = 3
```

### AI Parameters
```python
# ai_core.py
ANALYSIS_INTERVAL = 300  # 5 минут
MIN_CONFIDENCE = 40  # Минимальная уверенность для сигнала
```

## 🔄 Обновление

```bash
git pull origin main
pip install -r requirements.txt --upgrade
python main.py
```

## 📝 Логирование

Логи сохраняются в `bot.log` с ротацией:

```python
logger.info("✅ Успешная операция")
logger.warning("⚠️ Предупреждение")
logger.error("❌ Ошибка")
```

## 🐛 Troubleshooting

### Проблема: Бот не запускается
**Решение:** Проверьте переменные окружения в `.env`

### Проблема: Ошибка подключения к БД
**Решение:** Убедитесь, что Supabase credentials корректны

### Проблема: Сделки не выполняются
**Решение:** Проверьте валидность Pocket Option SSID

## 🤝 Contributing

Pull requests приветствуются. Для крупных изменений сначала откройте issue.

## 📜 License

MIT License

## 📧 Контакты

Для вопросов и поддержки создавайте issues в репозитории.

---

**Версия:** 2.0  
**Дата:** 2025-12-10  
**Статус:** Production Ready ✅
