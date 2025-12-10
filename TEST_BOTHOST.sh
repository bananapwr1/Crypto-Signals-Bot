#!/bin/bash

# ======================================
# Скрипт для тестирования сборки BotHost
# ======================================

echo "🧪 ТЕСТИРОВАНИЕ СБОРКИ BOTHOST"
echo "======================================"

# Проверка наличия файлов
echo ""
echo "📁 Проверка файлов..."

if [ -f "Dockerfile.bothost" ]; then
    echo "✅ Dockerfile.bothost существует"
else
    echo "❌ Dockerfile.bothost НЕ НАЙДЕН!"
    exit 1
fi

if [ -f "requirements-bothost.txt" ]; then
    echo "✅ requirements-bothost.txt существует"
else
    echo "❌ requirements-bothost.txt НЕ НАЙДЕН!"
    exit 1
fi

# Проверка размера requirements
echo ""
echo "📊 Размер зависимостей:"
echo "   requirements-bothost.txt: $(wc -l < requirements-bothost.txt) строк"
echo "   requirements-full.txt:    $(wc -l < requirements-full.txt) строк"

# Тестовая сборка (опционально)
echo ""
echo "🔨 ТЕСТОВАЯ СБОРКА (займет 3-5 минут):"
echo "   docker build -f Dockerfile.bothost -t test-bothost ."
echo ""
echo "⚠️  Запустить тестовую сборку? (y/n)"
read -r answer

if [ "$answer" = "y" ]; then
    echo "🚀 Запуск сборки..."
    start_time=$(date +%s)
    
    if docker build -f Dockerfile.bothost -t test-bothost . ; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        
        echo ""
        echo "✅ СБОРКА УСПЕШНА!"
        echo "⏱️  Время сборки: ${duration} секунд"
        
        # Проверка размера образа
        size=$(docker images test-bothost --format "{{.Size}}")
        echo "📦 Размер образа: $size"
        
        echo ""
        echo "🧹 Удалить тестовый образ? (y/n)"
        read -r cleanup
        if [ "$cleanup" = "y" ]; then
            docker rmi test-bothost
            echo "✅ Образ удален"
        fi
    else
        echo ""
        echo "❌ ОШИБКА СБОРКИ!"
        echo "Проверьте логи выше"
        exit 1
    fi
else
    echo "⏭️  Сборка пропущена"
fi

echo ""
echo "======================================"
echo "✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО"
echo "======================================"
echo ""
echo "Следующие шаги:"
echo "1. Загрузите проект на BotHost"
echo "2. Укажите Dockerfile: Dockerfile.bothost"
echo "3. Добавьте переменные окружения"
echo "4. Запустите сборку"
echo ""
echo "Документация: BOTHOST_QUICKSTART.md"
