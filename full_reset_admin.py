#!/usr/bin/env python3
"""Полный сброс админа"""
import sqlite3

conn = sqlite3.connect('crypto_signals_bot.db')
cursor = conn.cursor()

ADMIN_ID = 7746862973

# Полностью удалить админа
cursor.execute('DELETE FROM users WHERE user_id = ?', (ADMIN_ID,))
cursor.execute('DELETE FROM signal_history WHERE user_id = ?', (ADMIN_ID,))

conn.commit()
print(f"✅ Админ {ADMIN_ID} полностью удален из базы")
print(f"При запуске бота он получит VIP и пройдет onboarding заново")

conn.close()
