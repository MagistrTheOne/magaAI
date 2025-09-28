#!/bin/bash
# Скрипт для тестирования Docker сборки локально

echo "🐳 Тестирование Docker сборки для Railway..."

# Сборка образа
echo "📦 Сборка Docker образа..."
docker build -t maga-ai-railway .

if [ $? -eq 0 ]; then
    echo "✅ Docker образ собран успешно"
    
    # Тестирование запуска
    echo "🚀 Тестирование запуска контейнера..."
    docker run --rm -p 8000:8000 \
        -e TELEGRAM_BOT_TOKEN="test_token" \
        -e HEADLESS=1 \
        -e DISPLAY="" \
        maga-ai-railway python main.py --health
    
    if [ $? -eq 0 ]; then
        echo "✅ Контейнер запускается успешно"
        echo "🎉 Docker конфигурация готова для Railway!"
    else
        echo "❌ Ошибка запуска контейнера"
        exit 1
    fi
else
    echo "❌ Ошибка сборки Docker образа"
    exit 1
fi
