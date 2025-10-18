#!/usr/bin/env python3
"""Скрипт для сброса пользователя до нового состояния"""

import sqlite3
import sys

def reset_user(user_id):
    """Сброс пользователя до нового состояния"""
    conn = sqlite3.connect('crypto_signals_bot.db')
    cursor = conn.cursor()
    
    # Проверить существует ли пользователь
    cursor.execute('SELECT user_id, username, subscription_type FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        print(f"❌ Пользователь {user_id} не найден в базе")
        conn.close()
        return
    
    print(f"📋 Текущие данные пользователя {user_id}:")
    print(f"   Username: {user[1]}")
    print(f"   Подписка: {user[2]}")
    
    # Удалить все данные пользователя
    cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM signal_history WHERE user_id = ?', (user_id,))
    
    conn.commit()
    
    print(f"\n✅ Пользователь {user_id} успешно удален из базы!")
    print(f"При следующем /start он будет зарегистрирован как новый пользователь")
    
    conn.close()

if __name__ == "__main__":
    # ADMIN_USER_ID
    ADMIN_ID = 7746862973
    
    print("🔄 СБРОС ПОЛЬЗОВАТЕЛЯ ДО НОВОГО СОСТОЯНИЯ\n")
    reset_user(ADMIN_ID)
