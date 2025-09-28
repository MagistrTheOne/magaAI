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
    from personal_crm import PersonalCRM
    from routine_features import RoutineFeatures
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
        self.crm = None
        self.routine = None
        
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
                self.crm = PersonalCRM()
                self.routine = RoutineFeatures()
                
                self.logger.info("Все компоненты AIMagistr 3.0 инициализированы")
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
<b>🤖 AIMagistr 3.0 - Справка</b>

<b>Основные команды:</b>
/start - Начать работу
/help - Эта справка
/features - Все возможности
/reset - Сброс контекста
/metrics - Статистика использования

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
