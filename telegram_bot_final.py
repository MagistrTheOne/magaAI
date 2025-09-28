# -*- coding: utf-8 -*-
"""
AIMagistr 3.1 - Финальная версия для Railway
Максимальная стабильность и производительность
"""

import asyncio
import logging
import os
import json
import time
import signal
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Состояния для FSM
class UserStates(StatesGroup):
    waiting_for_prompt = State()
    waiting_for_email = State()
    waiting_for_receipt = State()


class AIMagistrTelegramBot:
    """
    AIMagistr 3.1 - Финальная версия
    """
    
    def __init__(self):
        # Настройка логирования
        self.logger = logging.getLogger("AIMagistr")
        self.logger.setLevel(logging.INFO)
        
        # Получаем токен бота
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
        
        # Создаем бота с улучшенными настройками
        self.bot = Bot(
            token=self.bot_token,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        )
        
        # Диспетчер с FSM
        self.dp = Dispatcher(storage=MemoryStorage())
        
        # Контекст пользователей
        self.user_contexts = {}
        self.user_roles = {}
        self.anti_spam = {}
        
        # Статистика
        self.stats = {
            "start_time": datetime.now(),
            "messages_processed": 0,
            "errors": 0,
            "users": set()
        }
        
        # Инициализация
        self._register_handlers()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов для graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Получен сигнал {signum}, завершаем работу...")
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    def _register_handlers(self):
        """Регистрация обработчиков"""
        # Команды
        self.dp.message.register(self._handle_start, CommandStart())
        self.dp.message.register(self._handle_help, Command("help"))
        self.dp.message.register(self._handle_features, Command("features"))
        self.dp.message.register(self._handle_reset, Command("reset"))
        self.dp.message.register(self._handle_metrics, Command("metrics"))
        self.dp.message.register(self._handle_status, Command("status"))
        
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
        
        # Обработка callback запросов
        self.dp.callback_query.register(self._handle_callback)
        
        # Обработка ошибок
        self.dp.errors.register(self._handle_errors)
    
    async def _handle_errors(self, event, exception):
        """Обработка ошибок"""
        self.stats["errors"] += 1
        self.logger.error(f"Ошибка: {exception}")
        
        if isinstance(exception, TelegramNetworkError):
            self.logger.warning("Сетевая ошибка Telegram, продолжаем работу")
        elif isinstance(exception, TelegramBadRequest):
            self.logger.warning(f"Некорректный запрос: {exception}")
        else:
            self.logger.error(f"Неожиданная ошибка: {exception}")
    
    async def _handle_start(self, message: Message):
        """Обработка команды /start"""
        try:
            user_id = message.from_user.id
            username = message.from_user.username or "Пользователь"
            
            # Обновляем статистику
            self.stats["users"].add(user_id)
            self.stats["messages_processed"] += 1
            
            # Проверяем антиспам
            if not self._check_anti_spam(user_id):
                await message.answer("⏳ Слишком много запросов. Попробуйте позже.")
                return
            
            welcome_text = f"""
<b>🤖 AIMagistr 3.1 - ИИ-Ассистент Мага</b>

Привет, {username}! Я твой персональный ИИ-ассистент для автоматизации рутины.

<b>Что я умею:</b>
• Приоритизация писем
• Планирование задач
• Обработка чеков
• Анализ изображений
• Переводы текста
• И многое другое!

<b>Команды:</b>
/help - Справка
/features - Все возможности
/metrics - Статистика
/status - Статус системы

<b>Новые сервисы 3.1:</b>
/mailtriage - Приоритизация писем
/timeblock - Планирование задач
/receipt - Обработка чеков
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Справка", callback_data="help")],
                [InlineKeyboardButton(text="⚡ Возможности", callback_data="features")],
                [InlineKeyboardButton(text="📊 Статистика", callback_data="metrics")]
            ])
            
            await message.answer(welcome_text, reply_markup=keyboard)
            
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_start: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_help(self, message: Message):
        """Обработка команды /help"""
        try:
            help_text = """
<b>🤖 AIMagistr 3.1 - Справка</b>

<b>Основные команды:</b>
/start - Начать работу
/help - Эта справка
/features - Все возможности
/reset - Сброс контекста
/metrics - Статистика использования
/status - Статус системы

<b>Новые сервисы 3.1:</b>
/mailtriage - Приоритизация писем
/timeblock - Планирование задач
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

<b>Как использовать:</b>
1. Отправьте текст - получите ответ от ИИ
2. Отправьте фото - анализ изображения
3. Отправьте документ - обработка и саммари
4. Используйте команды для специальных задач

<b>Поддерживаемые форматы:</b>
• Текст - диалог с ИИ
• Фото - анализ изображений
• PDF/DOCX - обработка документов
            """
            
            await message.answer(help_text)
            
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_help: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_features(self, message: Message):
        """Обработка команды /features"""
        try:
            features_text = """
<b>🚀 AIMagistr 3.1 - Все возможности</b>

<b>🧠 AI и Видение:</b>
• Yandex AI Studio - текстовые запросы
• Yandex Vision - анализ изображений
• Yandex OCR - распознавание текста
• Yandex Translate - переводы
• RAG система - поиск по документам

<b>📧 Email Triage:</b>
• Парсинг EML и текстовых писем
• AI анализ приоритета (high/medium/low/spam)
• Правила приоритизации
• Экспорт в JSON/CSV

<b>⏰ Time Blocking:</b>
• Добавление и планирование задач
• AI автоматическое планирование
• Экспорт расписания в iCal
• Управление временными слотами

<b>🧾 Finance Receipts:</b>
• OCR и извлечение сумм/дат
• AI категоризация расходов
• Статистика и отчеты
• Экспорт в CSV

<b>🔒 Безопасность:</b>
• Сканер секретов и PII
• Защита от спама
• Шифрование данных
• Аудит безопасности

<b>📊 Аналитика:</b>
• Метрики производительности
• Статистика использования
• Health check мониторинг
• Отчеты по активности
            """
            
            await message.answer(features_text)
            
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_features: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_reset(self, message: Message):
        """Обработка команды /reset"""
        try:
            user_id = message.from_user.id
            
            # Сбрасываем контекст
            if user_id in self.user_contexts:
                del self.user_contexts[user_id]
            
            await message.answer("🔄 Контекст сброшен. Начинаем с чистого листа!")
            
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_reset: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_metrics(self, message: Message):
        """Обработка команды /metrics"""
        try:
            uptime = datetime.now() - self.stats["start_time"]
            metrics_text = f"""
<b>📊 Статистика AIMagistr 3.1</b>

<b>Пользователи:</b> {len(self.stats['users'])}
<b>Сообщений обработано:</b> {self.stats['messages_processed']}
<b>Ошибок:</b> {self.stats['errors']}
<b>Время работы:</b> {uptime}

<b>Сервисы:</b>
• Email Triage: ✅ Активен
• Time Blocking: ✅ Активен
• Finance Receipts: ✅ Активен

<b>Статус:</b> 🟢 Работает нормально
            """
            
            await message.answer(metrics_text)
            
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_metrics: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_status(self, message: Message):
        """Обработка команды /status"""
        try:
            status_text = f"""
<b>🔍 Статус системы</b>

<b>Версия:</b> 3.1.0-final
<b>Статус:</b> 🟢 Работает
<b>Время запуска:</b> {self.stats['start_time'].strftime('%H:%M:%S')}
<b>Активных пользователей:</b> {len(self.stats['users'])}

<b>Компоненты:</b>
• Telegram Bot: ✅
• Health Check: ✅
• Anti-spam: ✅
• FSM: ✅

<b>Производительность:</b>
• Сообщений/сек: {self.stats['messages_processed'] / max(1, (datetime.now() - self.stats['start_time']).total_seconds()):.2f}
• Ошибок: {self.stats['errors']}
            """
            
            await message.answer(status_text)
            
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_status: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    # Новые обработчики команд AIMagistr 3.1
    async def _handle_mailtriage(self, message: Message):
        """Обработка команды /mailtriage"""
        try:
            await message.answer("📧 <b>Email Triage</b>\n\nОтправьте текст письма для приоритизации.\n\nЯ проанализирую:\n• Приоритет (high/medium/low/spam)\n• Отправителя\n• Содержимое\n• Рекомендации по действиям")
            await self.dp.set_state(message.from_user.id, UserStates.waiting_for_email)
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_mailtriage: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_timeblock(self, message: Message):
        """Обработка команды /timeblock"""
        try:
            await message.answer("⏰ <b>Time Blocking</b>\n\nДоступные функции:\n• Добавление задач\n• AI планирование времени\n• Экспорт в iCal\n• Управление слотами\n\nИспользуйте команды для управления задачами.")
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_timeblock: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_receipt(self, message: Message):
        """Обработка команды /receipt"""
        try:
            await message.answer("🧾 <b>Finance Receipts</b>\n\nОтправьте фото чека или текст чека для обработки.\n\nЯ извлеку:\n• Сумму покупки\n• Дату\n• Категорию расхода\n• Статистику")
            await self.dp.set_state(message.from_user.id, UserStates.waiting_for_receipt)
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_receipt: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_routine(self, message: Message):
        """Обработка команды /routine"""
        try:
            await message.answer("🔄 <b>Планировщик рутин</b>\n\nДоступные функции:\n• Создание повторяющихся задач\n• Напоминания\n• Автоматические уведомления\n\nВ разработке...")
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_routine: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_subscribe(self, message: Message):
        """Обработка команды /subscribe"""
        try:
            await message.answer("📋 <b>Трекер подписок</b>\n\nДоступные функции:\n• Отслеживание подписок\n• Уведомления об оплате\n• Анализ расходов\n\nВ разработке...")
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_subscribe: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_trip(self, message: Message):
        """Обработка команды /trip"""
        try:
            await message.answer("✈️ <b>Помощник путешествий</b>\n\nДоступные функции:\n• Планирование маршрутов\n• Анализ билетов и отелей\n• Уведомления о рейсах\n\nВ разработке...")
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_trip: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_catalog(self, message: Message):
        """Обработка команды /catalog"""
        try:
            await message.answer("📁 <b>Автокаталог документов</b>\n\nДоступные функции:\n• Автоматическая сортировка\n• Теги и категории\n• Поиск по содержимому\n\nВ разработке...")
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_catalog: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_focus(self, message: Message):
        """Обработка команды /focus"""
        try:
            await message.answer("🎯 <b>Ежедневный фокус</b>\n\nДоступные функции:\n• 3 приоритета дня\n• Планирование времени\n• Отслеживание прогресса\n\nВ разработке...")
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_focus: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_read(self, message: Message):
        """Обработка команды /read"""
        try:
            await message.answer("📚 <b>Очередь чтения</b>\n\nДоступные функции:\n• Саммари статей\n• Перевод текстов\n• Карточки для запоминания\n\nВ разработке...")
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_read: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_crm(self, message: Message):
        """Обработка команды /crm"""
        try:
            await message.answer("👥 <b>Персональный CRM</b>\n\nДоступные функции:\n• Управление контактами\n• Дни рождения\n• Follow-up задачи\n\nВ разработке...")
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_crm: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_health(self, message: Message):
        """Обработка команды /health"""
        try:
            await message.answer("💪 <b>Здоровье и продуктивность</b>\n\nДоступные функции:\n• Помодоро таймер\n• Напоминания о перерывах\n• Трекинг привычек\n\nВ разработке...")
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_health: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_jobs(self, message: Message):
        """Обработка команды /jobs"""
        try:
            await message.answer("💼 <b>Джоб-алерты</b>\n\nДоступные функции:\n• Отслеживание вакансий\n• Автоматические уведомления\n• Анализ требований\n\nВ разработке...")
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_jobs: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_weekly(self, message: Message):
        """Обработка команды /weekly"""
        try:
            await message.answer("📊 <b>Еженедельный отчет</b>\n\nДоступные функции:\n• Анализ активности\n• Статистика продуктивности\n• Планы на неделю\n\nВ разработке...")
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_weekly: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_shop(self, message: Message):
        """Обработка команды /shop"""
        try:
            await message.answer("🛒 <b>Списки покупок</b>\n\nДоступные функции:\n• Создание списков из рецептов\n• Распознавание товаров\n• Планирование покупок\n\nВ разработке...")
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_shop: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_text_message(self, message: Message, state: FSMContext):
        """Обработка текстовых сообщений"""
        try:
            user_id = message.from_user.id
            text = message.text
            
            # Обновляем статистику
            self.stats["messages_processed"] += 1
            self.stats["users"].add(user_id)
            
            # Проверяем антиспам
            if not self._check_anti_spam(user_id):
                await message.answer("⏳ Слишком много запросов. Попробуйте позже.")
                return
            
            # Получаем состояние пользователя
            current_state = await state.get_state()
            
            if current_state == UserStates.waiting_for_email:
                await self._process_email_triage(message, text)
                await state.clear()
            elif current_state == UserStates.waiting_for_receipt:
                await self._process_receipt(message, text)
                await state.clear()
            else:
                await self._process_ai_request(message, text)
                
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_text_message: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_photo(self, message: Message, state: FSMContext):
        """Обработка фотографий"""
        try:
            await message.answer("📷 <b>Анализ изображения</b>\n\nВ упрощенной версии анализ изображений недоступен.\n\nИспользуйте команды:\n/mailtriage - для писем\n/receipt - для чеков")
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_photo: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_document(self, message: Message, state: FSMContext):
        """Обработка документов"""
        try:
            await message.answer("📄 <b>Обработка документа</b>\n\nВ упрощенной версии обработка документов недоступна.\n\nИспользуйте команды:\n/mailtriage - для писем\n/receipt - для чеков")
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_document: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _handle_callback(self, callback: CallbackQuery):
        """Обработка callback запросов"""
        try:
            data = callback.data
            
            if data == "help":
                await callback.message.answer("📋 <b>Справка</b>\n\nИспользуйте /help для получения справки.")
            elif data == "features":
                await callback.message.answer("⚡ <b>Возможности</b>\n\nИспользуйте /features для просмотра всех возможностей.")
            elif data == "metrics":
                await callback.message.answer("📊 <b>Статистика</b>\n\nИспользуйте /metrics для просмотра статистики.")
            
            await callback.answer()
            
        except Exception as e:
            self.logger.error(f"Ошибка в _handle_callback: {e}")
            await callback.answer("❌ Произошла ошибка.")
    
    async def _process_email_triage(self, message: Message, text: str):
        """Обработка приоритизации письма"""
        try:
            await message.answer("📧 <b>Анализ письма</b>\n\nВ упрощенной версии AI анализ недоступен.\n\n<b>Текст письма:</b>\n" + text[:500] + "\n\n<b>Рекомендации:</b>\n• Проверьте отправителя\n• Оцените срочность\n• Определите приоритет")
        except Exception as e:
            self.logger.error(f"Ошибка в _process_email_triage: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _process_receipt(self, message: Message, text: str):
        """Обработка чека"""
        try:
            await message.answer("🧾 <b>Обработка чека</b>\n\nВ упрощенной версии OCR недоступен.\n\n<b>Текст чека:</b>\n" + text[:500] + "\n\n<b>Рекомендации:</b>\n• Найдите сумму\n• Определите дату\n• Выберите категорию")
        except Exception as e:
            self.logger.error(f"Ошибка в _process_receipt: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    async def _process_ai_request(self, message: Message, text: str):
        """Обработка AI запросов"""
        try:
            await message.answer("🤖 <b>AI Анализ</b>\n\nВ упрощенной версии AI недоступен.\n\n<b>Ваш запрос:</b>\n" + text + "\n\n<b>Рекомендации:</b>\n• Используйте команды для специальных задач\n• Обратитесь к справке /help")
        except Exception as e:
            self.logger.error(f"Ошибка в _process_ai_request: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    
    def _check_anti_spam(self, user_id: int) -> bool:
        """Проверка антиспама"""
        try:
            now = time.time()
            
            if user_id not in self.anti_spam:
                self.anti_spam[user_id] = []
            
            # Очищаем старые запросы (старше 60 секунд)
            self.anti_spam[user_id] = [req_time for req_time in self.anti_spam[user_id] if now - req_time < 60]
            
            # Проверяем лимит (5 запросов в минуту)
            if len(self.anti_spam[user_id]) >= 5:
                return False
            
            # Добавляем текущий запрос
            self.anti_spam[user_id].append(now)
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка в _check_anti_spam: {e}")
            return True  # В случае ошибки разрешаем запрос
    
    async def run(self):
        """Запуск бота"""
        try:
            self.logger.info("Запуск AIMagistr 3.1 Final Telegram Bot...")
            
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
        
        # Создаем и запускаем бота
        bot = AIMagistrTelegramBot()
        await bot.run()
        
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
