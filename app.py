# app.py - главный файл для Hostbot
print("🚀 CRYPTO BOT ЗАПУЩЕН!")
print("✅ Используется app.py вместо main.py")

import time
import os

# Проверяем настройки
print("🔧 Проверка конфигурации:")
print(f"Supabase: {'✅' if os.getenv('SUPABASE_URL') else '❌'}")
print(f"Telegram: {'✅' if os.getenv('TELEGRAM_BOT_TOKEN') else '❌'}")

# Простой рабочий цикл
count = 0
while True:
    count += 1
    print(f"🔄 Работаю... Цикл #{count}")
    time.sleep(30)  # 30 секунд
