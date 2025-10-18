# Crypto Signals Bot - Telegram Trading Bot

## Overview
This project is a professional Telegram trading bot for Pocket Option, delivering AI-powered trading signals. It uses advanced technical analysis and real-time market data across over 37 trading assets. The bot offers high-confidence signals, comprehensive bankroll management, adaptive signal weighting, and automated stake calculation to enhance user decision-making. It also includes a robust subscription management system.

## User Preferences
- Signal-only bot approach (no auto-trading, no credentials)
- Maximum 5-minute timeframe preference noted (expanded to 8 timeframes available)
- Professional appearance with dark-themed charts
- Three-tier subscription system:
  - SHORT: 4990₽/month (1-5 min fast signals)
  - LONG: 6990₽/month (1-4 hour long signals)
  - VIP: 9990₽/month (all signals on-demand)
  - FREE: 5 SHORT signals/day + 5 LONG signals/day (≥95% accuracy, on-demand, strict daily limits enforced)
- New user promo: SHORT for 1490₽ (70% discount, one-time)
- Separate notification systems for SHORT (automatic countdown) and LONG (manual list management) signals
- Multilingual Support: Russian (RU), English (EN), Spanish (ES), Portuguese (PT)
- Multi-Currency Support: Russian Ruble (RUB), US Dollar (USD) with automatic price conversion

## System Architecture
The bot is developed in Python 3.11, utilizing `python-telegram-bot` for interactions, `pandas`/`numpy` for data processing, `matplotlib` for dark-themed charts, and `sqlite3` as the embedded database.

**UI/UX Decisions:**
- Intuitive navigation via inline keyboard buttons and professional dark-themed charts.
- Compact signal format with clear instructions and emojis, including a "📋 Скопировать актив" button.
- Dynamic scanning animation and multilingual onboarding flow.
- Subscription-aware UI adapts menus based on user's tier.
- VIP Dashboard provides exclusive analytics and quick actions for VIP users.
- Distinct notification systems for SHORT (automatic countdown) and LONG (manual list management) signals.
- Smart "Start" button for seamless navigation for both new and registered users.
- **Tariff Card System:** Beautiful tariff cards displaying all plans (VIP, SHORT, LONG, FREE) with descriptions, prices from admin panel, and "Оплатить" buttons.

**Technical Implementations & Feature Specifications:**
- **Market Coverage:** Supports 100 verified Pocket Option assets across Crypto, Forex, Stocks, and Commodities/Indices.
- **OTC Priority System:** Prioritizes OTC assets with higher payouts.
- **Advanced Technical Analysis:** Employs EMA, RSI, MACD, Stochastic Oscillator, Support/Resistance, and market sentiment for an 8-point signal scoring system.
- **Optimized Signal Parameters:** Flexible search with dynamic confidence and score requirements.
- **Guaranteed Signal Delivery:** Fallback system ensures a quality OTC signal is always provided.
- **Professional Charts (Enhanced):** Premium-quality visualization system with GitHub Dark theme, 4-panel layout (Price, RSI, MACD, Volume), advanced indicators (EMA, Bollinger Bands, RSI, MACD), enhanced signal markers, information panel, and "🤖 Crypto Signals Pro" watermark.
- **Intelligent Signal Generation:** Provides CALL/PUT signals with high confidence based on minimum score difference.
- **Adaptive Self-Learning:** Tracks signal performance, dynamically adjusts asset weighting, and filters low-performing assets.
- **Historical Market Data Collection:** Records comprehensive market snapshots for pattern recognition and predictive analysis.
- **Four-Tier Subscription System:** FREE, SHORT, LONG, and VIP tiers offering varying access to signals and strategies.
- **VIP Exclusive Auto-Trading:** Comprehensive auto-trading system with secure SSID-based authentication and four advanced strategies: Fixed Percentage, D'Alembert, Martingale, and AI Trading. Includes demo/real mode, real-time session monitoring, profitability analysis, and automatic statistics collection from Pocket Option API.
- **Background Signal Testing & Self-Learning:** Automated system for continuous signal testing, performance collection, strategy optimization, and asset weight adjustment.
- **Webhook System:** JWT-authenticated webhook integration for sending signals to external services, with Flask-based server.
- **Referral Program:** Unique referral codes for user discounts.
- **Priority Queue System:** Hierarchical request processing based on subscription tier.
- **Smart FREE Signal Selection:** Filters for signals with ≥95% win rate and sufficient historical data.
- **ON-DEMAND Architecture:** Signals delivered instantly from TOP-3 pool, updated every minute (доходность 85-92%).
- **No Signal Repeats:** Deduplication system ensures unique signals.
- **Asset Diversity System:** Tracks recently used assets to ensure variety.
- **Unstable Asset Blocking:** Automatically blocks assets after consecutive losses.
- **Enhanced Stability Prioritization:** Strong preference for low-volatility assets.
- **Admin Panel:** Comprehensive `/settings` menu for all users, with an "Админ панель" for administrators offering bot statistics, signal search settings, tariff management, manual market scanning, smart restart, and data refresh functions. Includes user and admin self-reset features.
- **Bankroll Management:** Centralized `/bank` menu with quick actions, strategy selection (Martingale or Percentage), automatic stake calculation, and balance updates.
- **Main Menu Auto-Trading Button:** Large adaptive button on main menu visible to all users, linking to VIP auto-trading features or promo.
- **Automatic Signal Tracking:** Signals are 'pending' until outcome is reported.
- **Repeat Search Feature:** Allows immediate new signal requests after reporting results.
- **Pocket Option Adaptation:** Automatic conversion of asset names and display of OTC indicator.
- **Moscow Timezone:** All timestamps display in Moscow time (UTC+3).
- **Category-by-Category Scanning Animation:** Detailed progress display during signal search.
- **Bot Commands Management:** `DEFAULT_BOT_COMMANDS` constant defines 10 default commands, including `/autotrade`.
- **Enhanced Settings Navigation:** All admin panel pages include "🏠 Главное меню" button.
- **Subscription-Aware Settings UI:** Settings menu adapts based on user subscription tier.

**System Design Choices:**
- **Database Schema:** Tables for `users`, `signal_history`, `signal_performance`, `market_history`, and `bot_settings`.
- **Dynamic Configuration System:** `bot_settings` table manages multi-admin, payment, tariff pricing, and reviews.
- **Multilingual Infrastructure:** `TRANSLATIONS` dictionary and helper methods.
- **Subscription-Based Access Control:** Main menu adapts based on user subscription tier.
- **Security:** Sensitive data stored securely in Replit Secrets.
- **Performance Optimization:** Features include timeframe segmentation, rate limiting, multithreading, optimized delays, non-blocking message cleanup, optimized database queries, parallel signal analysis, signal caching, and intelligent signal ranking.
- **Background Tasks:** Concurrent tasks for notifications, VIP offers, and continuous market analysis.
- **Payment System:** Automated via YooKassa API, with manual options and graceful fallback.
- **Two-Path Onboarding Flow:** Differentiates between new and existing Pocket Option users.

## External Dependencies
- **Telegram Bot API:** For all bot interactions (`python-telegram-bot` library).
- **Yahoo Finance:** Provides real-time market data (`yfinance` library).
- **SQLite3:** Embedded database for persistent storage.
- **YooKassa API:** For automated payment processing and subscription management.