# 🤖 Pocket Option Pro Bot

A professional Telegram trading bot for Pocket Option with AI-powered signals, technical analysis, and subscription management.

## ✨ Features

- 📊 **Real-time Market Data**: Fetches live data from Yahoo Finance for 8+ trading assets
- 📈 **Technical Analysis**: RSI, SMA indicators with intelligent signal generation
- 💎 **Subscription System**: Free trial (3 signals) + PRO subscription management
- 📉 **Fast Timeframe Analysis**: 1M, 5M (max 5 minutes for quick signals)
- 📱 **Interactive UI**: Inline keyboards with callback query handling
- 📊 **Professional Charts**: Beautiful trading charts with matplotlib
- 💾 **SQLite Database**: User management and subscription tracking

## 🚀 Quick Start

### 1. Get Your Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token

### 2. Set Environment Variables

Create a `.env` file in the project root:

```env
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_CHAT_ID=your_admin_chat_id_here
```

### 3. Run the Bot

The bot will start automatically. You can also run it manually:

```bash
python main.py
```

## 📋 Bot Commands

- `/start` - Start the bot and view main menu
- `/signal_all` - Scan market and get top 3 trading signals
- `/buy_subscription` - View subscription options
- `/my_stats` - View your statistics and subscription status

## 🎯 Trading Assets

The bot analyzes these popular trading instruments:

- EUR/USD, GBP/USD, USD/JPY, AUD/USD (Forex)
- BTC/USD, ETH/USD (Crypto)
- XAU/USD (Gold)
- US30 (Dow Jones)

## 💰 Subscription Plans

- **Free Trial**: 3 signals (24 hours)
- **PRO**: 4990 RUB/month - Unlimited signals

## 🛠️ Tech Stack

- **Python 3.11+**
- **python-telegram-bot** - Telegram Bot API
- **yfinance** - Market data
- **pandas & numpy** - Data analysis
- **matplotlib** - Chart generation
- **sqlite3** - Database

## 📝 Project Structure

```
.
├── main.py              # Main bot application
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create this)
├── .env.example         # Environment template
├── pocket_option_pro.db # SQLite database (auto-created)
└── README.md            # This file
```

## 🔧 Development

Install dependencies:

```bash
pip install -r requirements.txt
```

## ⚠️ Disclaimer

This bot is for educational purposes only. Trading involves risk. Always do your own research before making trading decisions.

## 📞 Support

For subscription support or issues, contact: @pocket_option_support
