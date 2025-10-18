#!/usr/bin/env python3
"""
Скрипт для полного сброса всех статистик
Удаляет все данные о сигналах, историю, performance, market_history
Сбрасывает балансы пользователей и выбор стратегии
"""

import sqlite3
import sys

def reset_all_stats():
    """Сбросить все статистики и данные"""
    try:
        conn = sqlite3.connect('crypto_signals_bot.db')
        cursor = conn.cursor()
        
        print("🔄 Начинаем полный сброс статистик...")
        
        # 1. Удалить всю историю сигналов
        cursor.execute('DELETE FROM signal_history')
        deleted_signals = cursor.rowcount
        print(f"✅ Удалено {deleted_signals} сигналов из истории")
        
        # 2. Очистить статистику производительности активов
        cursor.execute('DELETE FROM signal_performance')
        deleted_performance = cursor.rowcount
        print(f"✅ Удалено {deleted_performance} записей производительности")
        
        # 3. Очистить историю рынка
        cursor.execute('DELETE FROM market_history')
        deleted_market = cursor.rowcount
        print(f"✅ Удалено {deleted_market} записей истории рынка")
        
        # 4. Сбросить балансы пользователей и мартингейл
        cursor.execute('''
            UPDATE users SET 
                initial_balance = NULL,
                current_balance = NULL,
                current_martingale_level = 0,
                consecutive_losses = 0,
                short_base_stake = 100,
                long_percentage = 2.5,
                trading_strategy = NULL
        ''')
        updated_users = cursor.rowcount
        print(f"✅ Сброшены балансы и стратегии для {updated_users} пользователей")
        
        # 5. Сбросить счетчики бесплатных сигналов
        cursor.execute('''
            UPDATE users SET 
                free_short_signals_today = 0,
                free_short_signals_date = NULL,
                free_long_signals_today = 0,
                free_long_signals_date = NULL
        ''')
        print(f"✅ Сброшены счетчики бесплатных сигналов")
        
        conn.commit()
        print("\n✅ ВСЕ СТАТИСТИКИ УСПЕШНО СБРОШЕНЫ!")
        print("\n📊 Что было сброшено:")
        print(f"   • {deleted_signals} сигналов")
        print(f"   • {deleted_performance} записей производительности")
        print(f"   • {deleted_market} записей истории рынка")
        print(f"   • Балансы {updated_users} пользователей")
        print(f"   • Счетчики бесплатных сигналов")
        print(f"   • Выбор стратегий пользователей")
        print("\n🎯 Бот готов к новому тестированию!")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при сбросе статистик: {e}")
        return False

if __name__ == "__main__":
    print("⚠️  ВНИМАНИЕ: Это удалит ВСЕ статистики и данные!")
    print("Вы уверены? (yes/no): ", end='')
    
    confirmation = input().strip().lower()
    
    if confirmation in ['yes', 'y', 'да']:
        success = reset_all_stats()
        sys.exit(0 if success else 1)
    else:
        print("❌ Отменено пользователем")
        sys.exit(1)
