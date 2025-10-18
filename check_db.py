#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('crypto_signals_bot.db')
cursor = conn.cursor()

# Проверить админа
cursor.execute('SELECT user_id, pocket_option_registered, language, currency, subscription_type, subscription_end, is_premium FROM users WHERE user_id = 7746862973')
result = cursor.fetchone()

print("📊 СОСТОЯНИЕ АДМИНА В БД:")
print("="*50)
if result:
    print(f"User ID: {result[0]}")
    print(f"Pocket Option Registered: {result[1]}")
    print(f"Language: {result[2]}")
    print(f"Currency: {result[3]}")
    print(f"Subscription Type: {result[4]}")
    print(f"Subscription End: {result[5]}")
    print(f"Is Premium: {result[6]}")
else:
    print("❌ Админ не найден в базе")

conn.close()
