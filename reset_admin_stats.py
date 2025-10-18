import sqlite3
from datetime import datetime, timedelta

# Подключиться к базе данных
conn = sqlite3.connect('crypto_signals_bot.db')
cursor = conn.cursor()

admin_id = 7746862973

# Показать текущие данные
print("=== ТЕКУЩИЕ ДАННЫЕ АДМИНА ===")
cursor.execute('''
    SELECT user_id, username, subscription_type, subscription_end, 
           current_balance, signals_used, free_trials_used
    FROM users WHERE user_id = ?
''', (admin_id,))
result = cursor.fetchone()
if result:
    print(f"User ID: {result[0]}")
    print(f"Username: {result[1]}")
    print(f"Subscription: {result[2]}")
    print(f"Sub End: {result[3]}")
    print(f"Balance: {result[4]}")
    print(f"Signals Used: {result[5]}")
    print(f"Free Trials: {result[6]}")
else:
    print("Пользователь не найден!")

# Обнулить статистику и выдать пожизненный VIP
print("\n=== ОБНУЛЕНИЕ СТАТИСТИКИ ===")

# Установить пожизненный VIP (подписка до 2099 года)
lifetime_end = datetime(2099, 12, 31, 23, 59, 59).isoformat()

cursor.execute('''
    UPDATE users 
    SET subscription_type = 'vip',
        subscription_end = ?,
        current_balance = 10000,
        initial_balance = 10000,
        signals_used = 0,
        free_trials_used = 0,
        is_premium = 1,
        language = NULL,
        currency = NULL
    WHERE user_id = ?
''', (lifetime_end, admin_id))

# Удалить всю историю сигналов админа
cursor.execute('DELETE FROM signal_history WHERE user_id = ?', (admin_id,))

conn.commit()

# Показать обновленные данные
print("\n=== ОБНОВЛЕННЫЕ ДАННЫЕ ===")
cursor.execute('''
    SELECT user_id, username, subscription_type, subscription_end, 
           current_balance, signals_used, free_trials_used
    FROM users WHERE user_id = ?
''', (admin_id,))
result = cursor.fetchone()
if result:
    print(f"User ID: {result[0]}")
    print(f"Username: {result[1]}")
    print(f"Subscription: {result[2]}")
    print(f"Sub End: {result[3]}")
    print(f"Balance: {result[4]}")
    print(f"Signals Used: {result[5]}")
    print(f"Free Trials: {result[6]}")

print("\n✅ Статистика обнулена! Пожизненный VIP выдан до 31.12.2099!")

conn.close()
