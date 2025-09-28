# Развертывание МАГА на Railway

## Проблемы и решения

### 1. Ошибка с pip в Nixpacks
**Проблема:** `python -m pip install --upgrade pip` не работает в Nixpacks
**Решение:** Переключились на Dockerfile

### 2. Несуществующие пакеты в requirements.txt
**Проблема:** `asyncio`, `typing`, `soundcard`, `Tortoise-TTS`, `pygetwindow`, `pywin32` не существуют
**Решение:** Удалили несуществующие пакеты

### 3. Ошибки в telegram_bot.py
**Проблема:** Конструктор требовал обязательный параметр token
**Решение:** Сделали token опциональным, добавили автозагрузку из env/secrets

## Файлы для развертывания

### Dockerfile
- Использует Python 3.11-slim
- Устанавливает системные зависимости (ffmpeg, libsndfile)
- Устанавливает Python пакеты
- Настраивает playwright и nltk
- Запускает main.py

### railway.toml
- Использует DOCKERFILE builder вместо NIXPACKS
- Настроен health check на /health
- Автоматический перезапуск при ошибках

### requirements.txt
- Очищен от несуществующих пакетов
- Добавлен nltk для работы с текстом
- Убраны проблемные зависимости

## Переменные окружения

Установите в Railway:
- `TELEGRAM_BOT_TOKEN` - токен Telegram бота
- `GIGACHAT_CLIENT_ID` - ID клиента GigaChat (опционально)
- `GIGACHAT_CLIENT_SECRET` - секрет GigaChat (опционально)
- `GIGACHAT_SCOPE` - область GigaChat (опционально)

## Локальное тестирование

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows)
venv\Scripts\activate

# Установить зависимости
pip install aiogram==3.4.1 python-telegram-bot==20.7 requests==2.31.0

# Тестировать
python test_local.py
```

## Развертывание на Railway

### 1. Подготовка
1. Подключите GitHub репозиторий к Railway
2. Railway автоматически обнаружит Dockerfile
3. Установите переменные окружения из `railway.env.example`

### 2. Переменные окружения Railway
```bash
# ОБЯЗАТЕЛЬНЫЕ (из .env.example)
TELEGRAM_BOT_TOKEN=7982777819:AAEi1DVROTDWpCq1EMfKP6useaIlNHIRrIg
GIGACHAT_CLIENT_ID=0199824b-4c1e-7ef1-b423-bb3156ddecee
GIGACHAT_CLIENT_SECRET=c3c67b8e-1c84-47a0-8cb6-8b392664e4a9
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_AUTH_KEY=MDE5OTgyNGItNGMxZS03ZWYxLWI0MjMtYmIzMTU2ZGRlY2VlOmMzYzY3YjhlLTFjODQtNDdhMC04Y2I2LThiMzkyNjY0ZTRhOQ==

# ПЕРСОНАЛЬНЫЕ ДАННЫЕ
PHONE_NUMBER=+79884135937
EMAIL_ADDRESS=maxonyushko71@gmail.com
NAME=Максим Онюшко
LINKEDIN_URL=https://www.linkedin.com/in/magistrtheone/
GITHUB_URL=https://github.com/MagistrTheOne
PORTFOLIO_URL=https://magistrtheone.vercel.app/

# ОПЦИОНАЛЬНЫЕ
SUPERJOB_API_KEY=your_superjob_key
LINKEDIN_ACCESS_TOKEN=your_linkedin_token
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
```

### 3. Docker конфигурация
- ✅ Python 3.11-slim
- ✅ Системные зависимости (ffmpeg, tesseract, OpenGL)
- ✅ Playwright с Chromium
- ✅ NLTK данные
- ✅ Безопасный пользователь
- ✅ Headless режим

### 4. Быстрая проверка готовности
```bash
# Проверить готовность к деплою
chmod +x check-deployment.sh
./check-deployment.sh
```

### 5. Тестирование локально
```bash
# Сделать скрипт исполняемым
chmod +x docker-test.sh

# Запустить тест
./docker-test.sh
```

### 6. Быстрый деплой
```bash
# Установить Railway CLI
npm install -g @railway/cli

# Авторизация
railway login

# Быстрый деплой
chmod +x deploy-railway.sh
./deploy-railway.sh
```

### 5. Health Check
Приложение доступно по адресу: `https://your-app.railway.app/health`

Ответ:
```json
{
  "status": "healthy",
  "service": "maga-ai",
  "timestamp": 1234567890.123
}
```

### 6. Мониторинг
- Railway автоматически перезапускает при сбоях
- Health check каждые 30 секунд
- Логи доступны в Railway Dashboard
