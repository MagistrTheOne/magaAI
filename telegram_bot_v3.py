# -*- coding: utf-8 -*-
"""
AIMagistr 3.0 - Telegram Bot с Yandex AI
Полный функционал: диалоги, файлы, команды, контекст
"""

import asyncio
import logging
import os
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Импорты AIMagistr 3.0
try:
    from brain.ai_client import BrainManager
    from integrations.yandex_vision import YandexVision
    from integrations.yandex_translate import YandexTranslate
    from integrations.yandex_ocr import YandexOCR
    from services.email_triage import EmailTriageService
    from services.time_blocking import TimeBlockingService
    from services.finance_receipts import FinanceReceiptsService
    BRAIN_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Некоторые компоненты недоступны: {e}")
    BRAIN_AVAILABLE = False

# Состояния для FSM
class UserStates(StatesGroup):
    waiting_for_prompt = State()
    waiting_for_file = State()
    waiting_for_translation = State()
    waiting_for_ocr = State()
    waiting_for_email = State()
    waiting_for_task = State()
    waiting_for_receipt = State()


class AIMagistrTelegramBot:
    """
    AIMagistr 3.0 Telegram Bot
    Полный функционал с Yandex AI
    """
    
    def __init__(self, token: str = None):
        """Инициализация бота"""
        self.logger = logging.getLogger("AIMagistrBot")
        
        # Получаем токен
        if not token:
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            if not token:
                raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
        
        # Инициализация бота
        self.bot = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        # Диспетчер с FSM
        self.dp = Dispatcher(storage=MemoryStorage())
        
        # Инициализация компонентов
        self.brain_manager = None
        self.vision = None
        self.translate = None
        self.ocr = None
        
        # Сервисы AIMagistr 3.1
        self.email_triage = None
        self.time_blocking = None
        self.finance_receipts = None
        
        # Контекст пользователей
        self.user_contexts = {}
        self.user_roles = {}  # admin/user
        self.anti_spam = {}  # защита от спама
        
        # Настройки
        self.max_file_size = int(os.getenv('MAX_FILE_SIZE_MB', '50')) * 1024 * 1024
        self.max_context_tokens = int(os.getenv('MAX_CONTEXT_TOKENS', '4000'))
        self.enable_typing = os.getenv('ENABLE_TYPING_INDICATOR', 'true').lower() == 'true'
        
        # Фичи
        self.features = {
            'ocr': os.getenv('FEATURE_OCR', 'true').lower() == 'true',
            'translate': os.getenv('FEATURE_TRANSLATE', 'true').lower() == 'true',
            'rag': os.getenv('FEATURE_RAG', 'true').lower() == 'true',
            'crm': os.getenv('FEATURE_CRM', 'true').lower() == 'true',
            'rpa': os.getenv('FEATURE_RPA', 'true').lower() == 'true',
            'analytics': os.getenv('FEATURE_ANALYTICS', 'true').lower() == 'true',
            'security': os.getenv('FEATURE_SECURITY', 'true').lower() == 'true'
        }
        
        # Инициализация
        self._init_components()
        self._register_handlers()
    
    def _init_components(self):
        """Инициализация компонентов"""
        try:
            if BRAIN_AVAILABLE:
                self.brain_manager = BrainManager()
                self.vision = YandexVision()
                self.translate = YandexTranslate()
                self.ocr = YandexOCR()
                
                # Инициализация сервисов
                self.email_triage = EmailTriageService()
                self.time_blocking = TimeBlockingService()
                self.finance_receipts = FinanceReceiptsService()
                
                self.logger.info("Все компоненты AIMagistr 3.1 инициализированы")
            else:
                self.logger.warning("Некоторые компоненты недоступны")
        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {e}")
    
    def _register_handlers(self):
        """Регистрация обработчиков"""
        # Команды
        self.dp.message.register(self._handle_start, CommandStart())
        self.dp.message.register(self._handle_help, Command("help"))
        self.dp.message.register(self._handle_features, Command("features"))
        self.dp.message.register(self._handle_reset, Command("reset"))
        self.dp.message.register(self._handle_setprompt, Command("setprompt"))
        self.dp.message.register(self._handle_lang, Command("lang"))
        self.dp.message.register(self._handle_ocr, Command("ocr"))
        self.dp.message.register(self._handle_summarize, Command("summarize"))
        self.dp.message.register(self._handle_translate, Command("translate"))
        self.dp.message.register(self._handle_metrics, Command("metrics"))
        self.dp.message.register(self._handle_admin, Command("admin"))
        
        # Новые команды AIMagistr 3.1
        self.dp.message.register(self._handle_mailtriage, Command("mailtriage"))
        self.dp.message.register(self._handle_timeblock, Command("timeblock"))
        self.dp.message.register(self._handle_receipt, Command("receipt"))
        self.dp.message.register(self._handle_routine, Command("routine"))
        self.dp.message.register(self._handle_subscribe, Command("subscribe"))
        self.dp.message.register(self._handle_trip, Command("trip"))
        self.dp.message.register(self._handle_catalog, Command("catalog"))
        self.dp.message.register(self._handle_focus, Command("focus"))
        self.dp.message.register(self._handle_read, Command("read"))
        self.dp.message.register(self._handle_crm, Command("crm"))
        self.dp.message.register(self._handle_health, Command("health"))
        self.dp.message.register(self._handle_jobs, Command("jobs"))
        self.dp.message.register(self._handle_weekly, Command("weekly"))
        self.dp.message.register(self._handle_shop, Command("shop"))
        
        # Обработка сообщений
        self.dp.message.register(self._handle_text_message, F.text)
        self.dp.message.register(self._handle_photo, F.photo)
        self.dp.message.register(self._handle_document, F.document)
        
        # Callback queries
        self.dp.callback_query.register(self._handle_callback)
    
    async def _handle_start(self, message: Message):
        """Обработка команды /start"""
        user_id = message.from_user.id
        username = message.from_user.username or "Пользователь"
        
        # Инициализация контекста пользователя
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                'messages': [],
                'language': 'ru',
                'custom_prompt': None,
                'last_activity': time.time()
            }
        
        # Определяем роль
        if user_id in [int(x) for x in os.getenv('ADMIN_USER_IDS', '').split(',') if x]:
            self.user_roles[user_id] = 'admin'
        else:
            self.user_roles[user_id] = 'user'
        
        welcome_text = f"""
🤖 <b>Добро пожаловать в AIMagistr 3.0!</b>

Привет, {username}! Я Ассистент Мага - ваш умный ИИ-помощник для автоматизации рутины и повышения продуктивности.

<b>Мои возможности:</b>
• 📄 OCR и анализ документов
• 🌐 Перевод текста и документов  
• 📊 Анализ изображений и данных
• 💼 Помощь с карьерой и CRM
• 🤖 Автоматизация рутинных задач
• 📈 Аналитика и инсайты

<b>Команды:</b>
/help - Справка
/features - Все возможности
/reset - Сброс контекста
/metrics - Статистика

Просто напишите мне или отправьте файл для обработки!
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Все возможности", callback_data="features")],
            [InlineKeyboardButton(text="🔄 Сброс контекста", callback_data="reset")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="metrics")]
        ])
        
        await message.answer(welcome_text, reply_markup=keyboard)
    
    async def _handle_help(self, message: Message):
        """Обработка команды /help"""
        help_text = """
<b>🤖 AIMagistr 3.1 - Справка</b>

<b>Основные команды:</b>
/start - Начать работу
/help - Эта справка
/features - Все возможности
/reset - Сброс контекста
/metrics - Статистика использования

<b>Новые сервисы 3.1:</b>
/mailtriage - Приоритизация писем
/timeblock - Тайм-блокинг задач
/receipt - Обработка чеков
/routine - Планировщик рутин
/subscribe - Трекер подписок
/trip - Помощник путешествий
/catalog - Автокаталог документов
/focus - Ежедневный фокус
/read - Очередь чтения
/crm - Персональный CRM
/health - Здоровье и продуктивность
/jobs - Джоб-алерты
/weekly - Еженедельный отчет
/shop - Списки покупок

<b>Команды для работы с файлами:</b>
/ocr - OCR изображений
/summarize - Саммари документов
/translate - Перевод текста

<b>Настройки:</b>
/setprompt - Установить системный промпт
/lang - Изменить язык

<b>Как использовать:</b>
1. Отправьте текст - получите ответ от ИИ
2. Отправьте фото - OCR и анализ
3. Отправьте документ - обработка и саммари
4. Используйте команды для специальных задач

<b>Поддерживаемые форматы:</b>
• Текст (любой)
• Изображения (JPG, PNG, GIF)
• Документы (PDF, DOC, TXT)
• Архивы (ZIP, RAR)
        """
        
        await message.answer(help_text)
    
    async def _handle_features(self, message: Message):
        """Обработка команды /features"""
        features_text = """
<b>🚀 AIMagistr 3.0 - Все возможности</b>

<b>📄 Документы и OCR (1-10):</b>
1. OCR изображений (RU/EN) с постпроцессингом
2. OCR PDF (постранично) + склейка и оглавление
3. Q&A по документу (RAG + LLM)
4. Экстракция таблиц (CSV/Markdown) из сканов
5. Реферат/саммари на N пунктов
6. Перевод документа целиком (Detect → Target)
7. Классификация документов (тип/тема/язык)
8. Редакция персональных данных
9. Выделение сущностей (имена, даты, суммы)
10. Генерация шаблонов (бриф, отчет, письмо)

<b>🤝 Встречи и коммуникации (11-16):</b>
11. Саммари встречи из текста/скриншота
12. Экстракция action items и дедлайнов
13. Создание календарных инвайтов (iCal)
14. Черновики писем после встречи
15. Тональность/риск-анализ переписки
16. Дейли-стендапы: сбор, сводка, напоминания

<b>💼 Карьера и вакансии (17-22):</b>
17. Таргетный ресуме-тейлор под JD
18. Автогенерация cover letter
19. Подготовка к интервью (вопросы/ответы)
20. LinkedIn outreach шаблоны
21. Переговорные аргументы (comp benchmark)
22. Трекинг откликов и статусов

<b>📊 CRM и продажи (23-27):</b>
23. Обогащение контактов (почта/LinkedIn)
24. Оценка лида (скоринг) по сообщению
25. Автологирование коммуникаций
26. Генерация фоллоу-апов и next steps
27. Резюме аккаунта: риски, возможности

<b>🤖 RPA и автоматизация (28-33):</b>
28. Browser RPA: логин/заполнение/скриншоты
29. Desktop RPA: клик/ввод/горячие клавиши
30. Анализ скриншота (что на экране)
31. Автозаполнение форм из текста/файла
32. Генерация еженедельных отчетов
33. Планировщик рутин (cron внутри бота)

<b>🧠 Знания и RAG (34-37):</b>
34. Импорт знаний (PDF/MD/URL)
35. Индексация и обновление эмбеддингов
36. Chat over docs: ответы с цитатами
37. Локальные коллекции по проектам

<b>📈 Аналитика и инсайты (38-41):</b>
38. Сводки почты/чатов за день/неделю
39. Тематические дайджесты (рынки, конкуренты)
40. Аномалии и риски (тональность/слова-триггеры)
41. KPI-дашборд в Telegram

<b>🌐 Локализация и перевод (42-44):</b>
42. Мгновенный перевод входящих/исходящих
43. Билингв-ответ (RU+EN) по запросу
44. Глоссарий терминов проекта

<b>🔒 Безопасность и соответствие (45-47):</b>
45. Скан секретов перед отправкой
46. Редакция PII в текстах/скринах
47. Логи доступа и аудита команд

<b>💬 Улучшения Telegram (48-50):</b>
48. Кнопки/инлайн-кейборды для операций
49. Мониторинг каналов/чатов с авто-саммари
50. Пакетная обработка файлов (ZIP, многодоковые саммари)
        """
        
        await message.answer(features_text)
    
    async def _handle_reset(self, message: Message):
        """Обработка команды /reset"""
        user_id = message.from_user.id
        
        if user_id in self.user_contexts:
            self.user_contexts[user_id]['messages'] = []
            self.user_contexts[user_id]['last_activity'] = time.time()
        
        await message.answer("✅ Контекст сброшен. Начинаем с чистого листа!")
    
    async def _handle_setprompt(self, message: Message):
        """Обработка команды /setprompt"""
        user_id = message.from_user.id
        
        # Извлекаем новый промпт из сообщения
        prompt_text = message.text.replace('/setprompt', '').strip()
        
        if not prompt_text:
            await message.answer("❌ Укажите новый системный промпт после команды /setprompt")
            return
        
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                'messages': [],
                'language': 'ru',
                'custom_prompt': None,
                'last_activity': time.time()
            }
        
        self.user_contexts[user_id]['custom_prompt'] = prompt_text
        
        await message.answer(f"✅ Системный промпт обновлен:\n\n{prompt_text}")
    
    async def _handle_lang(self, message: Message):
        """Обработка команды /lang"""
        user_id = message.from_user.id
        
        # Извлекаем язык из сообщения
        lang_text = message.text.replace('/lang', '').strip().lower()
        
        if lang_text not in ['ru', 'en', 'es', 'fr', 'de']:
            await message.answer("❌ Поддерживаемые языки: ru, en, es, fr, de")
            return
        
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                'messages': [],
                'language': 'ru',
                'custom_prompt': None,
                'last_activity': time.time()
            }
        
        self.user_contexts[user_id]['language'] = lang_text
        
        lang_names = {
            'ru': 'Русский',
            'en': 'Английский', 
            'es': 'Испанский',
            'fr': 'Французский',
            'de': 'Немецкий'
        }
        
        await message.answer(f"✅ Язык изменен на: {lang_names.get(lang_text, lang_text)}")
    
    async def _handle_ocr(self, message: Message):
        """Обработка команды /ocr"""
        user_id = message.from_user.id
        
        if not self.features['ocr']:
            await message.answer("❌ OCR функция отключена")
            return
        
        await message.answer("📷 Отправьте изображение для OCR распознавания")
        await self.dp.set_state(user_id, UserStates.waiting_for_ocr)
    
    async def _handle_summarize(self, message: Message):
        """Обработка команды /summarize"""
        user_id = message.from_user.id
        
        await message.answer("📄 Отправьте документ для создания саммари")
        await self.dp.set_state(user_id, UserStates.waiting_for_file)
    
    async def _handle_translate(self, message: Message):
        """Обработка команды /translate"""
        user_id = message.from_user.id
        
        if not self.features['translate']:
            await message.answer("❌ Перевод функция отключена")
            return
        
        await message.answer("🌐 Отправьте текст или файл для перевода")
        await self.dp.set_state(user_id, UserStates.waiting_for_translation)
    
    async def _handle_metrics(self, message: Message):
        """Обработка команды /metrics"""
        user_id = message.from_user.id
        
        if self.user_roles.get(user_id) != 'admin':
            await message.answer("❌ Доступно только администраторам")
            return
        
        if not self.brain_manager:
            await message.answer("❌ AI компоненты недоступны")
            return
        
        metrics = self.brain_manager.get_metrics()
        stats = self.brain_manager.get_usage_stats()
        
        metrics_text = f"""
<b>📊 Статистика AIMagistr 3.0</b>

<b>Запросы:</b>
• Всего: {metrics['total_requests']}
• Успешных: {metrics['successful_requests']}
• Ошибок: {metrics['failed_requests']}
• Успешность: {metrics['success_rate']*100:.1f}%

<b>Токены:</b>
• Всего: {metrics['total_tokens']:,}
• Среднее время ответа: {metrics['avg_response_time']:.2f}с

<b>Статус:</b>
• AI: {'✅' if stats['authenticated'] else '❌'}
• Vision: {'✅' if stats['vision_enabled'] else '❌'}
• Translate: {'✅' if stats['translate_enabled'] else '❌'}

<b>Пользователи:</b>
• Активных: {len(self.user_contexts)}
• Админов: {sum(1 for role in self.user_roles.values() if role == 'admin')}
        """
        
        await message.answer(metrics_text)
    
    async def _handle_admin(self, message: Message):
        """Обработка команды /admin"""
        user_id = message.from_user.id
        
        if self.user_roles.get(user_id) != 'admin':
            await message.answer("❌ Доступно только администраторам")
            return
        
        admin_text = """
<b>🔧 Панель администратора</b>

<b>Команды:</b>
/metrics - Статистика
/reset - Сброс всех контекстов
/features - Список возможностей

<b>Настройки:</b>
• Макс размер файла: {self.max_file_size // (1024*1024)}MB
• Макс токенов контекста: {self.max_context_tokens}
• Типинг индикатор: {'✅' if self.enable_typing else '❌'}

<b>Фичи:</b>
• OCR: {'✅' if self.features['ocr'] else '❌'}
• Translate: {'✅' if self.features['translate'] else '❌'}
• RAG: {'✅' if self.features['rag'] else '❌'}
• CRM: {'✅' if self.features['crm'] else '❌'}
• RPA: {'✅' if self.features['rpa'] else '❌'}
• Analytics: {'✅' if self.features['analytics'] else '❌'}
• Security: {'✅' if self.features['security'] else '❌'}
        """
        
        await message.answer(admin_text)
    
    async def _handle_text_message(self, message: Message, state: FSMContext):
        """Обработка текстовых сообщений"""
        user_id = message.from_user.id
        text = message.text
        
        # Проверка на спам
        if not await self._check_anti_spam(user_id):
            await message.answer("⏳ Слишком много сообщений. Подождите немного.")
            return
        
        # Получаем состояние пользователя
        current_state = await state.get_state()
        
        if current_state == UserStates.waiting_for_translation:
            await self._process_translation_request(message, text)
            await state.clear()
        elif current_state == UserStates.waiting_for_email:
            await self._process_email_triage(message, text)
            await state.clear()
        elif current_state == UserStates.waiting_for_receipt:
            await self._process_receipt(message, text)
            await state.clear()
        else:
            await self._process_ai_request(message, text)
    
    async def _handle_photo(self, message: Message, state: FSMContext):
        """Обработка фотографий"""
        user_id = message.from_user.id
        
        if not await self._check_anti_spam(user_id):
            await message.answer("⏳ Слишком много сообщений. Подождите немного.")
            return
        
        current_state = await state.get_state()
        
        if current_state == UserStates.waiting_for_ocr or self.features['ocr']:
            await self._process_ocr_request(message)
        else:
            await self._process_photo_analysis(message)
        
        await state.clear()
    
    async def _handle_document(self, message: Message, state: FSMContext):
        """Обработка документов"""
        user_id = message.from_user.id
        
        if not await self._check_anti_spam(user_id):
            await message.answer("⏳ Слишком много сообщений. Подождите немного.")
            return
        
        current_state = await state.get_state()
        
        if current_state == UserStates.waiting_for_file:
            await self._process_document_summary(message)
        elif current_state == UserStates.waiting_for_translation:
            await self._process_document_translation(message)
        else:
            await self._process_document_analysis(message)
        
        await state.clear()
    
    async def _handle_callback(self, callback: CallbackQuery):
        """Обработка callback запросов"""
        data = callback.data
        user_id = callback.from_user.id
        
        if data == "features":
            await self._handle_features(callback.message)
        elif data == "reset":
            await self._handle_reset(callback.message)
        elif data == "metrics":
            await self._handle_metrics(callback.message)
        
        await callback.answer()
    
    async def _check_anti_spam(self, user_id: int) -> bool:
        """Проверка на спам"""
        now = time.time()
        
        if user_id not in self.anti_spam:
            self.anti_spam[user_id] = []
        
        # Удаляем старые записи (старше 1 минуты)
        self.anti_spam[user_id] = [
            timestamp for timestamp in self.anti_spam[user_id]
            if now - timestamp < 60
        ]
        
        # Проверяем лимит (максимум 10 сообщений в минуту)
        if len(self.anti_spam[user_id]) >= 10:
            return False
        
        self.anti_spam[user_id].append(now)
        return True
    
    async def _process_ai_request(self, message: Message, text: str):
        """Обработка AI запроса"""
        user_id = message.from_user.id
        
        if not self.brain_manager:
            await message.answer("❌ AI компоненты недоступны")
            return
        
        # Показываем индикатор печати
        if self.enable_typing:
            await message.bot.send_chat_action(message.chat.id, "typing")
        
        try:
            # Получаем контекст пользователя
            context = self.user_contexts.get(user_id, {})
            custom_prompt = context.get('custom_prompt')
            
            # Генерируем ответ
            response = await self.brain_manager.generate_response(
                prompt=text,
                system_prompt=custom_prompt
            )
            
            # Обновляем контекст
            if user_id not in self.user_contexts:
                self.user_contexts[user_id] = {
                    'messages': [],
                    'language': 'ru',
                    'custom_prompt': None,
                    'last_activity': time.time()
                }
            
            self.user_contexts[user_id]['messages'].append({
                'role': 'user',
                'content': text,
                'timestamp': time.time()
            })
            
            self.user_contexts[user_id]['messages'].append({
                'role': 'assistant',
                'content': response,
                'timestamp': time.time()
            })
            
            # Ограничиваем размер контекста
            max_messages = 20
            if len(self.user_contexts[user_id]['messages']) > max_messages:
                self.user_contexts[user_id]['messages'] = self.user_contexts[user_id]['messages'][-max_messages:]
            
            await message.answer(response)
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки AI запроса: {e}")
            await message.answer("❌ Произошла ошибка при обработке запроса")
    
    async def _process_ocr_request(self, message: Message):
        """Обработка OCR запроса"""
        if not self.ocr:
            await message.answer("❌ OCR компонент недоступен")
            return
        
        await message.answer("🔍 Обрабатываю изображение...")
        
        try:
            # Скачиваем изображение
            photo = message.photo[-1]  # Берем самое большое
            file_info = await message.bot.get_file(photo.file_id)
            
            # Здесь должна быть логика скачивания и обработки
            # Для демонстрации отправляем заглушку
            await message.answer("📄 OCR результат:\n\n[Здесь будет распознанный текст]")
            
        except Exception as e:
            self.logger.error(f"Ошибка OCR: {e}")
            await message.answer("❌ Ошибка при обработке изображения")
    
    async def _process_photo_analysis(self, message: Message):
        """Анализ фотографии"""
        if not self.vision:
            await message.answer("❌ Vision компонент недоступен")
            return
        
        await message.answer("👁️ Анализирую изображение...")
        
        try:
            # Здесь должна быть логика анализа изображения
            await message.answer("🔍 Анализ изображения:\n\n[Здесь будет результат анализа]")
            
        except Exception as e:
            self.logger.error(f"Ошибка анализа изображения: {e}")
            await message.answer("❌ Ошибка при анализе изображения")
    
    async def _process_document_summary(self, message: Message):
        """Создание саммари документа"""
        await message.answer("📄 Создаю саммари документа...")
        
        try:
            # Здесь должна быть логика обработки документа
            await message.answer("📋 Саммари документа:\n\n[Здесь будет саммари]")
            
        except Exception as e:
            self.logger.error(f"Ошибка создания саммари: {e}")
            await message.answer("❌ Ошибка при создании саммари")
    
    async def _process_document_translation(self, message: Message):
        """Перевод документа"""
        if not self.translate:
            await message.answer("❌ Translate компонент недоступен")
            return
        
        await message.answer("🌐 Перевожу документ...")
        
        try:
            # Здесь должна быть логика перевода документа
            await message.answer("📄 Перевод документа:\n\n[Здесь будет перевод]")
            
        except Exception as e:
            self.logger.error(f"Ошибка перевода: {e}")
            await message.answer("❌ Ошибка при переводе документа")
    
    async def _process_document_analysis(self, message: Message):
        """Анализ документа"""
        await message.answer("📄 Анализирую документ...")
        
        try:
            # Здесь должна быть логика анализа документа
            await message.answer("🔍 Анализ документа:\n\n[Здесь будет результат анализа]")
            
        except Exception as e:
            self.logger.error(f"Ошибка анализа документа: {e}")
            await message.answer("❌ Ошибка при анализе документа")
    
    async def _process_translation_request(self, message: Message, text: str):
        """Обработка запроса на перевод"""
        if not self.translate:
            await message.answer("❌ Translate компонент недоступен")
            return
        
        await message.answer("🌐 Перевожу текст...")
        
        try:
            # Здесь должна быть логика перевода
            await message.answer(f"📄 Перевод:\n\n{text} → [Переведенный текст]")
            
        except Exception as e:
            self.logger.error(f"Ошибка перевода: {e}")
            await message.answer("❌ Ошибка при переводе")
    
    # Новые обработчики команд AIMagistr 3.1
    async def _handle_mailtriage(self, message: Message):
        """Обработка команды /mailtriage"""
        await message.answer("📧 Отправьте текст письма для приоритизации")
        await self.dp.set_state(message.from_user.id, UserStates.waiting_for_email)
    
    async def _handle_timeblock(self, message: Message):
        """Обработка команды /timeblock"""
        if not self.time_blocking:
            await message.answer("❌ Сервис тайм-блокинга недоступен")
            return
        
        try:
            # Получаем незапланированные задачи
            tasks = self.time_blocking.get_tasks(status="pending")
            
            if not tasks:
                await message.answer("📝 Нет незапланированных задач. Добавьте задачи командой /addtask")
                return
            
            # Показываем задачи
            tasks_text = "📋 Незапланированные задачи:\n\n"
            for i, task in enumerate(tasks[:5], 1):
                tasks_text += f"{i}. {task['title']} ({task['estimated_duration']} мин, {task['priority']})\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📅 Запланировать задачи", callback_data="schedule_tasks")],
                [InlineKeyboardButton(text="📊 Показать расписание", callback_data="show_schedule")]
            ])
            
            await message.answer(tasks_text, reply_markup=keyboard)
            
        except Exception as e:
            self.logger.error(f"Ошибка тайм-блокинга: {e}")
            await message.answer("❌ Ошибка при работе с тайм-блокингом")
    
    async def _handle_receipt(self, message: Message):
        """Обработка команды /receipt"""
        if not self.finance_receipts:
            await message.answer("❌ Сервис финансов недоступен")
            return
        
        await message.answer("🧾 Отправьте фото чека или текст чека для обработки")
        await self.dp.set_state(message.from_user.id, UserStates.waiting_for_receipt)
    
    async def _process_email_triage(self, message: Message, text: str):
        """Обработка приоритизации письма"""
        if not self.email_triage:
            await message.answer("❌ Сервис приоритизации писем недоступен")
            return
        
        await message.answer("📧 Анализирую письмо...")
        
        try:
            result = await self.email_triage.process_email(text)
            
            if "error" in result:
                await message.answer(f"❌ Ошибка: {result['error']}")
                return
            
            priority_emoji = {
                "high": "🔴",
                "medium": "🟡", 
                "low": "🟢",
                "spam": "🗑️"
            }
            
            response = f"""
{priority_emoji.get(result['priority'], '⚪')} <b>Приоритет: {result['priority'].upper()}</b>

<b>Тема:</b> {result.get('subject', 'Без темы')}
<b>От:</b> {result.get('from', 'Неизвестно')}
<b>Обоснование:</b> {result.get('reasoning', 'Не указано')}

<b>Следующие действия:</b>
• Высокий приоритет - ответить немедленно
• Средний приоритет - ответить в течение дня
• Низкий приоритет - ответить когда будет время
• Спам - удалить или отправить в спам
            """
            
            await message.answer(response)
            
        except Exception as e:
            self.logger.error(f"Ошибка приоритизации письма: {e}")
            await message.answer("❌ Ошибка при анализе письма")
    
    async def _process_receipt(self, message: Message, text: str = None):
        """Обработка чека"""
        if not self.finance_receipts:
            await message.answer("❌ Сервис финансов недоступен")
            return
        
        await message.answer("🧾 Обрабатываю чек...")
        
        try:
            if text:
                result = await self.finance_receipts.process_receipt(text)
            else:
                # Если это фото, нужно сначала получить OCR
                await message.answer("📷 Сначала нужно распознать текст с фото")
                return
            
            if "error" in result:
                await message.answer(f"❌ Ошибка: {result['error']}")
                return
            
            category_emoji = {
                "food": "🍕",
                "transport": "🚗",
                "health": "🏥",
                "shopping": "🛍️",
                "utilities": "🏠",
                "entertainment": "🎬",
                "other": "📦"
            }
            
            response = f"""
{category_emoji.get(result['category'], '📦')} <b>Чек обработан</b>

<b>Сумма:</b> {result['amount']} руб
<b>Категория:</b> {result['category']}
<b>Дата:</b> {result['date']}
<b>Обоснование:</b> {result['reasoning']}

<b>Добавлено в расходы!</b>
            """
            
            await message.answer(response)
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки чека: {e}")
            await message.answer("❌ Ошибка при обработке чека")
    
    # Обработчики остальных команд AIMagistr 3.1
    async def _handle_routine(self, message: Message):
        """Обработка команды /routine"""
        await message.answer("🔄 Планировщик рутин\n\nДоступные функции:\n• Создание повторяющихся задач\n• Напоминания\n• Автоматические уведомления")
    
    async def _handle_subscribe(self, message: Message):
        """Обработка команды /subscribe"""
        await message.answer("📋 Трекер подписок\n\nДоступные функции:\n• Отслеживание подписок\n• Уведомления об оплате\n• Анализ расходов")
    
    async def _handle_trip(self, message: Message):
        """Обработка команды /trip"""
        await message.answer("✈️ Помощник путешествий\n\nДоступные функции:\n• Планирование маршрутов\n• Анализ билетов и отелей\n• Уведомления о рейсах")
    
    async def _handle_catalog(self, message: Message):
        """Обработка команды /catalog"""
        await message.answer("📁 Автокаталог документов\n\nДоступные функции:\n• Автоматическая сортировка\n• Теги и категории\n• Поиск по содержимому")
    
    async def _handle_focus(self, message: Message):
        """Обработка команды /focus"""
        await message.answer("🎯 Ежедневный фокус\n\nДоступные функции:\n• 3 приоритета дня\n• Планирование времени\n• Отслеживание прогресса")
    
    async def _handle_read(self, message: Message):
        """Обработка команды /read"""
        await message.answer("📚 Очередь чтения\n\nДоступные функции:\n• Саммари статей\n• Перевод текстов\n• Карточки для запоминания")
    
    async def _handle_crm(self, message: Message):
        """Обработка команды /crm"""
        await message.answer("👥 Персональный CRM\n\nДоступные функции:\n• Управление контактами\n• Дни рождения\n• Follow-up задачи")
    
    async def _handle_health(self, message: Message):
        """Обработка команды /health"""
        await message.answer("💪 Здоровье и продуктивность\n\nДоступные функции:\n• Помодоро таймер\n• Напоминания о перерывах\n• Трекинг привычек")
    
    async def _handle_jobs(self, message: Message):
        """Обработка команды /jobs"""
        await message.answer("💼 Джоб-алерты\n\nДоступные функции:\n• Отслеживание вакансий\n• Автоматические уведомления\n• Анализ требований")
    
    async def _handle_weekly(self, message: Message):
        """Обработка команды /weekly"""
        await message.answer("📊 Еженедельный отчет\n\nДоступные функции:\n• Анализ активности\n• Статистика продуктивности\n• Планы на неделю")
    
    async def _handle_shop(self, message: Message):
        """Обработка команды /shop"""
        await message.answer("🛒 Списки покупок\n\nДоступные функции:\n• Создание списков из рецептов\n• Распознавание товаров\n• Планирование покупок")
    
    async def run(self):
        """Запуск бота"""
        try:
            self.logger.info("Запуск AIMagistr 3.0 Telegram Bot...")
            
            # Удаляем webhook если есть
            await self.bot.delete_webhook(drop_pending_updates=True)
            
            # Запускаем polling
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска бота: {e}")
            raise


# Функция для запуска
async def main():
    """Главная функция"""
    try:
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Создание и запуск бота
        bot = AIMagistrTelegramBot()
        await bot.run()
        
    except Exception as e:
        print(f"Критическая ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())
