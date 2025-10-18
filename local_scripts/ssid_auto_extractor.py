#!/usr/bin/env python3
"""
🤖 Pocket Option SSID Auto-Extractor
Автоматическое получение и обновление SSID для Telegram бота

⚠️ ВАЖНО: Этот скрипт работает ЛОКАЛЬНО на вашем компьютере!
Ваши логин и пароль от Pocket Option НЕ передаются на сервер.
"""

import os
import time
import json
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

class PocketOptionSSIDExtractor:
    def __init__(self):
        """Инициализация экстрактора SSID"""
        self.options = webdriver.ChromeOptions()
        
        # Настройки для стабильной работы
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option('useAutomationExtension', False)
        
        # Раскомментируйте для headless режима (без GUI)
        # self.options.add_argument('--headless')
        # self.options.add_argument('--no-sandbox')
        # self.options.add_argument('--disable-dev-shm-usage')
        
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Инициализация Selenium WebDriver"""
        try:
            print("🔧 Инициализация браузера...")
            self.driver = webdriver.Chrome(options=self.options)
            
            # Скрываем признаки автоматизации
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            self.wait = WebDriverWait(self.driver, 20)
            print("✅ Браузер успешно запущен")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка инициализации браузера: {e}")
            print("💡 Убедитесь, что Chrome и ChromeDriver установлены")
            return False
    
    def login_to_pocket_option(self, email, password):
        """Вход в аккаунт Pocket Option"""
        try:
            print("🌐 Открываем Pocket Option...")
            self.driver.get("https://pocketoption.com")
            time.sleep(2)
            
            # Ищем и кликаем кнопку входа
            print("🔍 Ищем кнопку входа...")
            try:
                # Пробуем разные варианты кнопки входа
                login_btn = self.wait.until(
                    EC.element_to_be_clickable((
                        By.XPATH, 
                        "//button[contains(text(), 'Sign In') or contains(text(), 'Войти') or contains(@class, 'login')]"
                    ))
                )
                login_btn.click()
                time.sleep(1)
            except:
                print("⚠️ Кнопка входа не найдена, возможно уже на странице логина")
            
            # Заполняем email
            print("📧 Вводим email...")
            email_field = self.wait.until(
                EC.presence_of_element_located((
                    By.XPATH, 
                    "//input[@type='email' or @name='email' or contains(@placeholder, 'mail')]"
                ))
            )
            email_field.clear()
            email_field.send_keys(email)
            time.sleep(0.5)
            
            # Заполняем пароль
            print("🔑 Вводим пароль...")
            password_field = self.driver.find_element(
                By.XPATH, 
                "//input[@type='password' or @name='password']"
            )
            password_field.clear()
            password_field.send_keys(password)
            time.sleep(0.5)
            
            # Отправляем форму
            print("✉️ Отправляем форму входа...")
            submit_btn = self.driver.find_element(
                By.XPATH, 
                "//button[@type='submit' or contains(text(), 'Sign') or contains(text(), 'Войти')]"
            )
            submit_btn.click()
            
            # Ждем загрузки личного кабинета
            print("⏳ Ждем загрузки личного кабинета...")
            time.sleep(5)
            
            # Проверяем успешность входа
            current_url = self.driver.current_url
            if "login" not in current_url.lower():
                print("✅ Успешный вход в аккаунт!")
                return True
            else:
                print("❌ Вход не удался, проверьте логин и пароль")
                return False
                
        except TimeoutException:
            print("❌ Таймаут: элемент не найден")
            return False
        except Exception as e:
            print(f"❌ Ошибка при входе: {e}")
            return False
    
    def extract_ssid(self):
        """Извлечение SSID из cookies или localStorage"""
        try:
            print("🔍 Извлекаем SSID...")
            
            # Метод 1: Проверяем cookies
            cookies = self.driver.get_cookies()
            for cookie in cookies:
                if cookie['name'].lower() == 'ssid':
                    ssid = cookie['value']
                    print(f"✅ SSID найден в cookies: {ssid[:30]}...")
                    return ssid
            
            # Метод 2: Проверяем localStorage
            ssid = self.driver.execute_script(
                "return window.localStorage.getItem('ssid') || window.localStorage.getItem('SSID');"
            )
            if ssid:
                print(f"✅ SSID найден в localStorage: {ssid[:30]}...")
                return ssid
            
            # Метод 3: Проверяем sessionStorage
            ssid = self.driver.execute_script(
                "return window.sessionStorage.getItem('ssid') || window.sessionStorage.getItem('SSID');"
            )
            if ssid:
                print(f"✅ SSID найден в sessionStorage: {ssid[:30]}...")
                return ssid
            
            print("❌ SSID не найден")
            return None
            
        except Exception as e:
            print(f"❌ Ошибка при извлечении SSID: {e}")
            return None
    
    def send_ssid_to_bot(self, ssid, user_id, bot_token):
        """Отправка SSID боту через Telegram API"""
        try:
            print("📤 Отправляем SSID боту...")
            
            # Формируем URL для Telegram Bot API
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            # Подготавливаем данные
            payload = {
                'chat_id': user_id,
                'text': f'🔑 SSID автоматически обновлен!\n\n'
                        f'SSID: `{ssid}`\n\n'
                        f'⏰ Время: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
                        f'✅ Автотрейдинг готов к использованию!',
                'parse_mode': 'Markdown'
            }
            
            # Отправляем запрос
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print("✅ SSID успешно отправлен боту!")
                
                # Также сохраняем SSID в базу данных бота через команду
                update_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                update_payload = {
                    'chat_id': user_id,
                    'text': f'/update_ssid {ssid}'
                }
                requests.post(update_url, json=update_payload, timeout=10)
                
                return True
            else:
                print(f"⚠️ Ошибка отправки: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка отправки SSID боту: {e}")
            return False
    
    def save_ssid_locally(self, ssid):
        """Сохранение SSID в локальный файл (резервная копия)"""
        try:
            with open('ssid_backup.txt', 'w') as f:
                f.write(f"SSID: {ssid}\n")
                f.write(f"Время получения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            print("💾 SSID сохранен в ssid_backup.txt")
        except Exception as e:
            print(f"⚠️ Не удалось сохранить SSID локально: {e}")
    
    def run(self):
        """Основной процесс получения SSID"""
        try:
            # Получаем данные из .env
            email = os.getenv('POCKET_EMAIL')
            password = os.getenv('POCKET_PASSWORD')
            user_id = os.getenv('TELEGRAM_USER_ID')
            bot_token = os.getenv('BOT_TOKEN')
            
            # Проверяем наличие всех данных
            if not all([email, password, user_id, bot_token]):
                print("❌ Ошибка: Не все переменные окружения настроены!")
                print("💡 Проверьте файл .env и убедитесь, что указаны:")
                print("   - POCKET_EMAIL")
                print("   - POCKET_PASSWORD")
                print("   - TELEGRAM_USER_ID")
                print("   - BOT_TOKEN")
                return False
            
            # Запускаем браузер
            if not self.setup_driver():
                return False
            
            # Выполняем вход
            if not self.login_to_pocket_option(email, password):
                return False
            
            # Получаем SSID
            ssid = self.extract_ssid()
            if not ssid:
                return False
            
            # Сохраняем локально
            self.save_ssid_locally(ssid)
            
            # Отправляем боту
            self.send_ssid_to_bot(ssid, user_id, bot_token)
            
            print("\n🎉 Процесс завершен успешно!")
            print(f"📋 SSID: {ssid[:30]}...")
            
            return True
            
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            return False
            
        finally:
            # Закрываем браузер
            if self.driver:
                print("🔄 Закрываем браузер...")
                time.sleep(2)
                self.driver.quit()

def main():
    """Главная функция"""
    print("="*60)
    print("🤖 POCKET OPTION SSID AUTO-EXTRACTOR")
    print("="*60)
    print()
    
    extractor = PocketOptionSSIDExtractor()
    success = extractor.run()
    
    print()
    print("="*60)
    if success:
        print("✅ SSID успешно получен и отправлен боту!")
    else:
        print("❌ Не удалось получить SSID")
        print("💡 Проверьте логи выше для деталей")
    print("="*60)

if __name__ == "__main__":
    main()
