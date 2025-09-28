#!/bin/bash
# Скрипт для проверки готовности к деплою на Railway

echo "🔍 Проверка готовности к деплою МАГА на Railway..."

# Проверяем наличие обязательных файлов
echo "📁 Проверка файлов..."

required_files=(
    "Dockerfile"
    "railway.toml" 
    "requirements.txt"
    "main.py"
    "telegram_bot.py"
    "railway.env.example"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file - ОТСУТСТВУЕТ"
        exit 1
    fi
done

# Проверяем Dockerfile
echo "🐳 Проверка Dockerfile..."
if grep -q "FROM python:3.11-slim" Dockerfile; then
    echo "✅ Python 3.11-slim"
else
    echo "❌ Неправильная версия Python"
fi

if grep -q "EXPOSE 8000" Dockerfile; then
    echo "✅ Порт 8000 настроен"
else
    echo "❌ Порт не настроен"
fi

if grep -q "USER appuser" Dockerfile; then
    echo "✅ Безопасный пользователь"
else
    echo "❌ Пользователь не настроен"
fi

# Проверяем railway.toml
echo "🚂 Проверка railway.toml..."
if grep -q 'builder = "DOCKERFILE"' railway.toml; then
    echo "✅ Dockerfile builder"
else
    echo "❌ Неправильный builder"
fi

if grep -q 'healthcheckPath = "/health"' railway.toml; then
    echo "✅ Health check настроен"
else
    echo "❌ Health check не настроен"
fi

# Проверяем main.py
echo "🐍 Проверка main.py..."
if grep -q "HealthCheckHandler" main.py; then
    echo "✅ Health check handler"
else
    echo "❌ Health check handler отсутствует"
fi

if grep -q "MAGATelegramBot" main.py; then
    echo "✅ Telegram bot инициализация"
else
    echo "❌ Telegram bot не настроен"
fi

# Проверяем переменные окружения
echo "🔧 Проверка переменных окружения..."
if grep -q "TELEGRAM_BOT_TOKEN" railway.env.example; then
    echo "✅ TELEGRAM_BOT_TOKEN"
else
    echo "❌ TELEGRAM_BOT_TOKEN отсутствует"
fi

if grep -q "GIGACHAT_CLIENT_ID" railway.env.example; then
    echo "✅ GIGACHAT_CLIENT_ID"
else
    echo "❌ GIGACHAT_CLIENT_ID отсутствует"
fi

# Проверяем зависимости
echo "📦 Проверка requirements.txt..."
if grep -q "aiogram==3.4.1" requirements.txt; then
    echo "✅ aiogram"
else
    echo "❌ aiogram отсутствует"
fi

if grep -q "python-telegram-bot==20.7" requirements.txt; then
    echo "✅ python-telegram-bot"
else
    echo "❌ python-telegram-bot отсутствует"
fi

if grep -q "faster-whisper==0.10.0" requirements.txt; then
    echo "✅ faster-whisper"
else
    echo "❌ faster-whisper отсутствует"
fi

if grep -q "edge-tts==6.1.10" requirements.txt; then
    echo "✅ edge-tts"
else
    echo "❌ edge-tts отсутствует"
fi

echo ""
echo "🎉 Проверка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Скопируйте переменные из railway.env.example в Railway Dashboard"
echo "2. Запустите: ./deploy-railway.sh"
echo "3. Проверьте логи: railway logs"
echo "4. Проверьте health check: https://your-app.railway.app/health"
