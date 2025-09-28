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

1. Подключите GitHub репозиторий к Railway
2. Railway автоматически обнаружит Dockerfile
3. Установите переменные окружения
4. Деплой произойдет автоматически

## Health Check

Приложение доступно по адресу: `https://your-app.railway.app/health`

Ответ:
```json
{
  "status": "healthy",
  "service": "maga-ai",
  "timestamp": 1234567890.123
}
```
