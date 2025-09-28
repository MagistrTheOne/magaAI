# MAGA AI - Ultimate Career Automation Assistant

🤖 **МАГА** - это ИИ-ассистент для полной автоматизации карьерного роста. От поиска работы до переговоров по зарплате - все в одном решении.

## 🚀 Возможности

### 🎯 Auto-Pilot Mode
- **Автоматический поиск вакансий** через HH.ru, LinkedIn, Indeed
- **Автоподача резюме** через Browser RPA
- **Подготовка к интервью** с AI-анализом компании
- **Quantum переговоры** по зарплате (несколько параллельных стратегий)
- **Отслеживание офферов** и финализация контрактов

### 🤖 AI Компоненты
- **GigaChat Brain** - продвинутый AI для общения с HR
- **Quantum Negotiation** - параллельные переговорные стратегии
- **Memory Palace** - векторная память разговоров
- **Success Prediction** - ML прогноз вероятности оффера
- **Intent Engine** - распознавание команд и намерений

### 📱 Telegram Bot
- **Полный контроль** через Telegram
- **Голосовые команды** и текстовые сообщения
- **Быстрые действия** - одним нажатием кнопки
- **Real-time уведомления** о прогрессе
- **Inline клавиатура** для удобного управления

### 🖥️ Desktop & Browser Automation
- **Browser RPA** - автоматическая подача резюме
- **Desktop RPA** - управление приложениями (Zoom, Outlook)
- **Computer Vision** - анализ экрана и документов
- **OCR** - распознавание текста с экрана

## 🛠️ Установка

### 1. Клонирование репозитория
```bash
git clone https://github.com/MagistrTheOne/magaAI.git
cd magaAI
```

### 2. Создание виртуального окружения
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Настройка API токенов
Создайте файл `.env` в корне проекта:
```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# GigaChat API
GIGACHAT_CLIENT_ID=your_client_id
GIGACHAT_CLIENT_SECRET=your_client_secret
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_AUTH_KEY=your_auth_key

# Другие API (опционально)
LINKEDIN_ACCESS_TOKEN=your_linkedin_token
INDEED_PUBLISHER_KEY=your_indeed_key
```

## 🚀 Запуск

### GUI режим (Windows)
```bash
python ghost_assistant_win.py
```

### Headless режим (сервер)
```bash
tk.Tk = lambda: None
python ghost_assistant_win.py
```

### Только Telegram бот
```bash
python -c "from telegram_bot import MAGATelegramBot; bot = MAGATelegramBot(); bot.run()"
```

## 📱 Использование Telegram бота

1. **Запустите бота** через GUI или напрямую
2. **Напишите** `/start` для инициализации
3. **Используйте кнопки** для быстрого доступа к функциям:
   - 🔍 **Найти работу** - поиск вакансий
   - 📧 **Почта** - проверка email
   - 📱 **Статус** - состояние системы
   - ⚡ **Быстрые** - быстрые действия
   - 🎤 **Голосовые** - голосовые команды
   - 📊 **Статистика** - аналитика
   - 🤖 **Auto-Pilot** - автономный режим

### Голосовые команды:
- "МАГА, найди работу"
- "МАГА, проверь почту"
- "МАГА, подготовь к интервью"
- "МАГА, проведи переговоры"

## 🏗️ Архитектура

```
MAGA AI
├── 🧠 Brain Manager (GigaChat)
├── ⚛️ Quantum Negotiation
├── 🧠 Memory Palace (ChromaDB)
├── 🎯 Success Prediction (ML)
├── 🎯 Intent Engine
├── 🤖 Telegram Bot
├── 🚀 Auto-Pilot (State Machine)
├── 🌐 Job APIs (HH.ru, LinkedIn)
├── 🖥️ Browser RPA (Playwright)
├── 🖥️ Desktop RPA (PyAutoGUI)
├── 📧 Mail/Calendar (IMAP, Outlook)
└── 📊 Analytics & Reporting
```

## 🎯 Auto-Pilot State Machine

```
Discover → Apply → Interview → Negotiate → Close
    ↓        ↓         ↓           ↓         ↓
Поиск    Подача   Подготовка  Переговоры  Финализация
вакансий  резюме    к интервью   оффера    контракта
```

## 📊 API интеграции

| API | Статус | Описание |
|-----|--------|----------|
| **Telegram** | ✅ Готов | Бот для управления |
| **GigaChat** | ⚠️ Токен | AI для HR общения |
| **HH.ru** | ✅ Готов | Поиск вакансий |
| **LinkedIn** | ⏳ Ожидает | Профессиональная сеть |
| **Indeed** | ⏳ Ожидает | Глобальный поиск |

## 🔧 Настройка для Railway

### 1. Переменные окружения
В Railway dashboard добавьте переменные из `.env`

### 2. Build command
```bash
pip install -r requirements.txt
```

### 3. Start command
```bash
python -c "import os; os.environ['HEADLESS']='1'; from telegram_bot import MAGATelegramBot; bot = MAGATelegramBot(); bot.run()"
```

### 4. Health check
```
/health
```

## 🤝 Вклад в проект

1. Fork репозиторий
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📝 Лицензия

Этот проект лицензирован под MIT License - смотрите файл [LICENSE](LICENSE) для деталей.

## ⚠️ Важные замечания

- **Безопасность**: Все API токены хранятся в зашифрованном виде
- **Этика**: AI используется только для помощи в карьерном росте
- **Легальность**: Соблюдайте правила платформ при автоматизации
- **Тестирование**: Всегда тестируйте на тестовых аккаунтах

## 🎪 Будущие возможности

- [ ] Deepfake Avatar для Zoom
- [ ] Voice Cloning (Tortoise TTS)
- [ ] Multi-language support
- [ ] Advanced CV optimization
- [ ] Interview simulation with HR bot
- [ ] LinkedIn networking automation

---

**Создано с ❤️ для революции в карьере через AI**

*Made by MagistrTheOne*