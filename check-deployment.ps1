# PowerShell скрипт для проверки готовности к деплою на Railway

Write-Host "🔍 Проверка готовности к деплою МАГА на Railway..." -ForegroundColor Green

# Проверяем наличие обязательных файлов
Write-Host "📁 Проверка файлов..." -ForegroundColor Yellow

$required_files = @(
    "Dockerfile",
    "railway.toml", 
    "requirements.txt",
    "main.py",
    "telegram_bot.py",
    "railway.env.example"
)

foreach ($file in $required_files) {
    if (Test-Path $file) {
        Write-Host "✅ $file" -ForegroundColor Green
    } else {
        Write-Host "❌ $file - ОТСУТСТВУЕТ" -ForegroundColor Red
        exit 1
    }
}

# Проверяем Dockerfile
Write-Host "🐳 Проверка Dockerfile..." -ForegroundColor Yellow
if (Select-String -Path "Dockerfile" -Pattern "FROM python:3.11-slim" -Quiet) {
    Write-Host "✅ Python 3.11-slim" -ForegroundColor Green
} else {
    Write-Host "❌ Неправильная версия Python" -ForegroundColor Red
}

if (Select-String -Path "Dockerfile" -Pattern "EXPOSE 8000" -Quiet) {
    Write-Host "✅ Порт 8000 настроен" -ForegroundColor Green
} else {
    Write-Host "❌ Порт не настроен" -ForegroundColor Red
}

if (Select-String -Path "Dockerfile" -Pattern "USER appuser" -Quiet) {
    Write-Host "✅ Безопасный пользователь" -ForegroundColor Green
} else {
    Write-Host "❌ Пользователь не настроен" -ForegroundColor Red
}

# Проверяем railway.toml
Write-Host "🚂 Проверка railway.toml..." -ForegroundColor Yellow
if (Select-String -Path "railway.toml" -Pattern 'builder = "DOCKERFILE"' -Quiet) {
    Write-Host "✅ Dockerfile builder" -ForegroundColor Green
} else {
    Write-Host "❌ Неправильный builder" -ForegroundColor Red
}

if (Select-String -Path "railway.toml" -Pattern 'healthcheckPath = "/health"' -Quiet) {
    Write-Host "✅ Health check настроен" -ForegroundColor Green
} else {
    Write-Host "❌ Health check не настроен" -ForegroundColor Red
}

# Проверяем main.py
Write-Host "🐍 Проверка main.py..." -ForegroundColor Yellow
if (Select-String -Path "main.py" -Pattern "HealthCheckHandler" -Quiet) {
    Write-Host "✅ Health check handler" -ForegroundColor Green
} else {
    Write-Host "❌ Health check handler отсутствует" -ForegroundColor Red
}

if (Select-String -Path "main.py" -Pattern "MAGATelegramBot" -Quiet) {
    Write-Host "✅ Telegram bot инициализация" -ForegroundColor Green
} else {
    Write-Host "❌ Telegram bot не настроен" -ForegroundColor Red
}

# Проверяем переменные окружения
Write-Host "🔧 Проверка переменных окружения..." -ForegroundColor Yellow
if (Select-String -Path "railway.env.example" -Pattern "TELEGRAM_BOT_TOKEN" -Quiet) {
    Write-Host "✅ TELEGRAM_BOT_TOKEN" -ForegroundColor Green
} else {
    Write-Host "❌ TELEGRAM_BOT_TOKEN отсутствует" -ForegroundColor Red
}

if (Select-String -Path "railway.env.example" -Pattern "GIGACHAT_CLIENT_ID" -Quiet) {
    Write-Host "✅ GIGACHAT_CLIENT_ID" -ForegroundColor Green
} else {
    Write-Host "❌ GIGACHAT_CLIENT_ID отсутствует" -ForegroundColor Red
}

# Проверяем зависимости
Write-Host "📦 Проверка requirements.txt..." -ForegroundColor Yellow
if (Select-String -Path "requirements.txt" -Pattern "aiogram==3.4.1" -Quiet) {
    Write-Host "✅ aiogram" -ForegroundColor Green
} else {
    Write-Host "❌ aiogram отсутствует" -ForegroundColor Red
}

if (Select-String -Path "requirements.txt" -Pattern "python-telegram-bot==20.7" -Quiet) {
    Write-Host "✅ python-telegram-bot" -ForegroundColor Green
} else {
    Write-Host "❌ python-telegram-bot отсутствует" -ForegroundColor Red
}

if (Select-String -Path "requirements.txt" -Pattern "faster-whisper==0.10.0" -Quiet) {
    Write-Host "✅ faster-whisper" -ForegroundColor Green
} else {
    Write-Host "❌ faster-whisper отсутствует" -ForegroundColor Red
}

if (Select-String -Path "requirements.txt" -Pattern "edge-tts==6.1.10" -Quiet) {
    Write-Host "✅ edge-tts" -ForegroundColor Green
} else {
    Write-Host "❌ edge-tts отсутствует" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎉 Проверка завершена!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Следующие шаги:" -ForegroundColor Cyan
Write-Host "1. Скопируйте переменные из railway.env.example в Railway Dashboard" -ForegroundColor White
Write-Host "2. Запустите: railway up" -ForegroundColor White
Write-Host "3. Проверьте логи: railway logs" -ForegroundColor White
Write-Host "4. Проверьте health check: https://your-app.railway.app/health" -ForegroundColor White
