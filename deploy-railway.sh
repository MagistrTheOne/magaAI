#!/bin/bash
# Скрипт для быстрого развертывания МАГА на Railway

echo "🚀 Развертывание МАГА на Railway..."

# Проверяем наличие Railway CLI
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI не найден. Установите: npm install -g @railway/cli"
    exit 1
fi

# Проверяем авторизацию
if ! railway whoami &> /dev/null; then
    echo "🔐 Авторизация в Railway..."
    railway login
fi

echo "📦 Создание проекта Railway..."
railway init

echo "🔧 Настройка переменных окружения..."
echo "Добавьте переменные из railway.env.example в Railway Dashboard:"
echo "https://railway.app/dashboard"

echo "📋 Обязательные переменные:"
echo "- TELEGRAM_BOT_TOKEN"
echo "- GIGACHAT_CLIENT_ID" 
echo "- GIGACHAT_CLIENT_SECRET"
echo "- GIGACHAT_SCOPE"
echo "- GIGACHAT_AUTH_KEY"

echo "🚀 Запуск деплоя..."
railway up

echo "✅ Деплой завершен!"
echo "🔗 Проверьте статус: railway status"
echo "📊 Логи: railway logs"
echo "🌐 URL: railway domain"
