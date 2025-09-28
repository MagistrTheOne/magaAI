# AI-Maga Telegram Bot

Telegram бот с интеграцией Yandex Foundation Models (LLM) и SpeechKit (TTS/STT), авто-режимом ответа и FastAPI webhook.

## 🚀 Возможности

- **Авто-режим ответа**: голос → голос, текст → текст, с маркерами 🔊 → голос
- **Yandex LLM**: текстовые ответы через Foundation Models
- **TTS провайдеры**: Yandex TTS (oggopus) и ElevenLabs TTS v2 (Liam, mp3)
- **Yandex STT**: распознавание речи (опционально)
- **Режимы ответа**: `/mode auto|text|voice`
- **Безопасность**: валидация webhook, rate limiting
- **Docker**: готовый контейнер для Railway

## 📋 Требования

- Python 3.11
- Telegram Bot Token
- Yandex Cloud API ключ
- Yandex Cloud папка с доступом к Foundation Models и SpeechKit

## 🛠 Установка и запуск

### Локальная разработка

1. **Клонируйте репозиторий:**
   ```bash
   git clone <repository-url>
   cd ai-maga-bot
   ```

2. **Создайте виртуальное окружение:**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Настройте переменные окружения:**
   ```bash
   cp .env.example .env
   # Отредактируйте .env файл с вашими данными
   ```

5. **Запустите приложение:**
   ```bash
   python -m app.main
   ```

### Docker

```bash
# Сборка образа
docker build -t ai-maga-bot .

# Запуск контейнера
docker run -p 8080:8080 --env-file .env ai-maga-bot
```

## ⚙️ Конфигурация

### Переменные окружения

#### Основные настройки
| Переменная | Описание | Обязательная |
|------------|----------|--------------|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота | ✅ |
| `TELEGRAM_WEBHOOK_SECRET` | Секрет для webhook | ✅ |
| `BASE_PUBLIC_URL` | Публичный URL приложения | ✅ |
| `LLM_PROVIDER` | LLM провайдер (yandex) | ❌ |
| `TTS_PROVIDER` | TTS провайдер (yandex\|elevenlabs) | ❌ |

#### Yandex Cloud
| Переменная | Описание | Обязательная |
|------------|----------|--------------|
| `YANDEX_API_KEY` | API ключ Yandex Cloud | ✅ |
| `YANDEX_FOLDER_ID` | ID папки Yandex Cloud | ✅ |
| `YANDEX_LLM_MODEL` | Модель LLM (gpt://catalog-id/model) | ✅ |
| `YANDEX_MODEL_URI` | Алиас для модели LLM | ❌ |
| `YANDEX_TTS_VOICE` | Голос для TTS (по умолчанию: alyss) | ❌ |
| `YANDEX_TTS_FORMAT` | Формат аудио (по умолчанию: oggopus) | ❌ |
| `YANDEX_STT_ENABLE` | Включить STT (по умолчанию: false) | ❌ |
| `YANDEX_TRANSLATE_ENABLED` | Включить перевод (по умолчанию: false) | ❌ |
| `YANDEX_VISION_ENABLED` | Включить визион (по умолчанию: false) | ❌ |

#### ElevenLabs (опционально)
| Переменная | Описание | Обязательная |
|------------|----------|--------------|
| `ELEVENLABS_API_KEY` | API ключ ElevenLabs | ❌ |
| `ELEVENLABS_VOICE_ID` | ID голоса Liam | ❌ |
| `ELEVENLABS_MODEL_ID` | Модель (по умолчанию: eleven_multilingual_v2) | ❌ |
| `ELEVENLABS_OUTPUT_FORMAT` | Формат аудио (по умолчанию: mp3_44100_128) | ❌ |
| `ELEVENLABS_CONVERT_TO_OGG` | Конвертировать в OGG/OPUS (по умолчанию: false) | ❌ |

#### Сервер
| Переменная | Описание | Обязательная |
|------------|----------|--------------|
| `PORT` | Порт сервера (по умолчанию: 8080) | ❌ |
| `LOG_LEVEL` | Уровень логирования (по умолчанию: INFO) | ❌ |

### Настройка Yandex Cloud

1. Создайте сервисный аккаунт в Yandex Cloud
2. Назначьте роли: `ai.languageModels.user`, `ai.speechkit.user`
3. Создайте API ключ
4. Получите ID папки
5. Настройте модель LLM в каталоге

### Настройка ElevenLabs (опционально)

1. Зарегистрируйтесь на [ElevenLabs](https://elevenlabs.io)
2. Получите API ключ в [Dashboard](https://elevenlabs.io/app/settings/api-keys)
3. Найдите ID голоса Liam в [Voices](https://elevenlabs.io/app/voice-library)
4. Установите `TTS_PROVIDER=elevenlabs` в `.env`
5. Настройте переменные ElevenLabs

**Важно**: ElevenLabs возвращает MP3, который отправляется как `audio` в Telegram. Для отправки как `voice` (OGG/OPUS) установите `ELEVENLABS_CONVERT_TO_OGG=true` и добавьте ffmpeg в Docker.

## 🤖 Команды бота

- `/start` - приветствие и текущий режим
- `/mode auto|text|voice` - переключение режима ответа
- Отправка текста - получение ответа от LLM
- Отправка голоса - распознавание + ответ (если STT включен)

## 🔧 Режимы ответа

- **auto** (по умолчанию): автоматический выбор
  - Голосовое сообщение → голосовой ответ
  - Текст с маркерами 🔊, "voice", "/voice" → голосовой ответ
  - Остальное → текстовый ответ

- **text**: всегда текстовые ответы
- **voice**: всегда голосовые ответы

## 🎵 TTS Провайдеры

### Yandex TTS (по умолчанию)
- **Формат**: OGG/OPUS (voice в Telegram)
- **Голоса**: alyss, jane, omazh, zahar, ermil
- **Преимущества**: быстрый, без дополнительных зависимостей

### ElevenLabs TTS v2
- **Формат**: MP3 (audio в Telegram)
- **Голос**: Liam (естественный английский)
- **Модель**: eleven_multilingual_v2
- **Конвертация**: опциональная в OGG/OPUS через ffmpeg

**Выбор провайдера**: установите `TTS_PROVIDER=yandex` или `TTS_PROVIDER=elevenlabs` в `.env`

## 🚀 Деплой на Railway

### 1. Подготовка

1. Создайте аккаунт на [Railway](https://railway.app)
2. Подключите GitHub репозиторий
3. Создайте новый проект

### 2. Настройка переменных окружения

В Railway Dashboard → Variables добавьте:

```
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_WEBHOOK_SECRET=your-secret-key
BASE_PUBLIC_URL=https://your-app.railway.app
YANDEX_API_KEY=your-yandex-api-key
YANDEX_FOLDER_ID=your-folder-id
YANDEX_LLM_MODEL=gpt://catalog-id/model-name
YANDEX_TTS_VOICE=alyss
YANDEX_TTS_FORMAT=oggopus
YANDEX_STT_ENABLE=false
PORT=8080
LOG_LEVEL=INFO
```

### 3. Деплой

1. Railway автоматически определит Dockerfile
2. Build будет выполнен автоматически
3. После деплоя получите публичный URL

### 4. Настройка webhook

Webhook установится автоматически при запуске. Для ручной установки:

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook?url=$BASE_PUBLIC_URL/webhook/telegram/$TELEGRAM_WEBHOOK_SECRET"
```

## 🧪 Тестирование

```bash
# Запуск тестов
pytest tests/

# Проверка health endpoint
curl https://your-app.railway.app/healthz
```

## 📁 Структура проекта

```
ai-maga-bot/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI приложение
│   ├── router.py               # aiogram обработчики
│   ├── settings.py             # Настройки и валидация
│   ├── schemas.py              # Pydantic модели
│   ├── services/
│   │   ├── yandex_llm.py       # Yandex LLM клиент
│   │   ├── yandex_tts.py       # Yandex TTS клиент
│   │   ├── yandex_stt.py       # Yandex STT клиент
│   │   ├── mode.py             # Логика режимов
│   │   └── tg_utils.py         # Telegram утилиты
│   └── middleware/
│       └── webhook_guard.py    # Защита webhook
├── tests/
│   ├── test_health.py          # Тесты health endpoint
│   └── test_yandex_client.py   # Тесты Yandex API
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## 🔍 Мониторинг

- **Health check**: `GET /healthz`
- **Логи**: выводятся в stdout
- **Метрики**: можно добавить Prometheus/Grafana

## 🐛 Устранение неполадок

### Container не слушает порт
- Убедитесь, что FastAPI запущен на `0.0.0.0:$PORT`
- Проверьте переменную `PORT` в Railway

### Telegram webhook не работает
- Проверьте `BASE_PUBLIC_URL` и `TELEGRAM_WEBHOOK_SECRET`
- Убедитесь, что URL доступен извне
- Переустановите webhook вручную

### Ошибки Yandex API
- Проверьте `YANDEX_API_KEY` и `YANDEX_FOLDER_ID`
- Убедитесь в правильности ролей сервисного аккаунта
- Проверьте доступность модели LLM

### Аудио не воспроизводится
- Используйте `YANDEX_TTS_FORMAT=oggopus`
- Отправляйте как `voice` с `content_type=application/ogg`

## 📝 Лицензия

MIT License

## 🤝 Вклад в проект

1. Fork репозиторий
2. Создайте feature branch
3. Commit изменения
4. Push в branch
5. Создайте Pull Request
