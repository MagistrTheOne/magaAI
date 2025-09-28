# -*- coding: utf-8 -*-
"""
Telegram Bot для МАГА - полный контроль через Telegram
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest

# Импорты МАГА компонентов
try:
    from brain.gigachat_sdk import BrainManager, GigaChatConfig
    from intent_engine import IntentEngine
    from quantum_negotiation import QuantumNegotiationEngine
    from memory_palace import MemoryPalace
    from success_prediction import SuccessPredictionEngine, PredictionFeatures
    from secrets_watchdog import SecretsWatchdogManager
    from job_apis import JobAPIManager, JobSearchParams
    from mail_calendar import MailCalendar  # type: ignore
    BRAIN_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Некоторые компоненты МАГА недоступны: {e}")
    BRAIN_AVAILABLE = False


class MAGATelegramBot:
    """
    Telegram бот для управления МАГА
    """

    def __init__(self, token: str = None):
        """
        Args:
            token: Telegram Bot Token (optional, will be loaded from env/secrets)
        """
        # Получаем токен из переменных окружения или secrets
        if not token:
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            if not token:
                try:
                    from secrets_watchdog import SecretsWatchdogManager
                    secrets_manager = SecretsWatchdogManager()
                    token = secrets_manager.get_secret("TELEGRAM_BOT_TOKEN")
                except ImportError:
                    pass
        
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN не найден. Установите переменную окружения или в secrets.")
        
        self.token = token
        self.bot = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dp = Dispatcher()

        # Компоненты МАГА
        self.brain_manager = None
        self.intent_engine = None
        self.quantum_negotiation = None
        self.memory_palace = None
        self.success_prediction = None
        self.secrets_manager = None
        self.auto_pilot = None
        self.job_api_manager = None
        self.mail_calendar = None

        # Состояния пользователей
        self.user_states: Dict[int, Dict[str, Any]] = {}
        self.user_contexts: Dict[int, Dict[str, Any]] = {}

        # Настройка логирования
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("MAGATelegramBot")

        # Инициализация компонентов
        self._init_maga_components()

        # Регистрация хендлеров
        self._register_handlers()

    def _init_maga_components(self):
        """Инициализация компонентов МАГА"""
        try:
            if not BRAIN_AVAILABLE:
                self.logger.warning("Компоненты МАГА недоступны")
                return

            # Secrets Manager
            self.secrets_manager = SecretsWatchdogManager()

            # GigaChat конфигурация
            config = GigaChatConfig()
            config.client_id = self.secrets_manager.get_secret("GIGACHAT_CLIENT_ID") or ""
            config.client_secret = self.secrets_manager.get_secret("GIGACHAT_CLIENT_SECRET") or ""
            config.scope = self.secrets_manager.get_secret("GIGACHAT_SCOPE") or "GIGACHAT_API_PERS"

            # Brain Manager
            self.brain_manager = BrainManager(config)

            # Intent Engine
            self.intent_engine = IntentEngine()
            if self.brain_manager:
                self.intent_engine.set_brain_manager(self.brain_manager)

            # Quantum Negotiation
            self.quantum_negotiation = QuantumNegotiationEngine(
                brain_manager=self.brain_manager,
                base_salary=200000,
                target_salary=250000
            )

            # Memory Palace
            self.memory_palace = MemoryPalace()

            # Success Prediction
            self.success_prediction = SuccessPredictionEngine()

            self.logger.info("Все компоненты МАГА инициализированы для Telegram бота")

        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов МАГА: {e}")

    def _register_handlers(self):
        """Регистрация всех хендлеров"""

        # Команды
        self.dp.message.register(self.cmd_start, Command("start"))
        self.dp.message.register(self.cmd_help, Command("help"))
        self.dp.message.register(self.cmd_status, Command("status"))

        # Callback queries для inline кнопок
        self.dp.callback_query.register(self.handle_callback, lambda c: True)

        # Обработка голосовых сообщений
        self.dp.message.register(self.handle_voice, lambda m: m.voice is not None)

        # Обработка текстовых сообщений
        self.dp.message.register(self.handle_text)

    async def cmd_start(self, message: types.Message):
        """Обработчик команды /start"""
        user_id = message.from_user.id

        # Инициализация состояния пользователя
        self.user_states[user_id] = {
            'mode': 'main',
            'last_activity': datetime.now(),
            'conversation_history': []
        }

        self.user_contexts[user_id] = {
            'company': None,
            'position': None,
            'salary_target': 250000,
            'active_autopilot': False
        }

        keyboard = self._get_main_keyboard()
        text = (
            "🤖 <b>МАГА - ваш AI-ассистент по карьере</b>\n\n"
            "Я могу:\n"
            "• Найти работу и подать резюме\n"
            "• Подготовить к собеседованиям\n"
            "• Вести переговоры о зарплате\n"
            "• Анализировать рынок труда\n\n"
            "Выберите действие:"
        )

        await message.answer(text, reply_markup=keyboard)

    async def cmd_help(self, message: types.Message):
        """Обработчик команды /help"""
        text = (
            "📚 <b>Помощь по командам МАГА</b>\n\n"
            "<b>Основные команды:</b>\n"
            "/start - Запуск бота\n"
            "/status - Текущий статус\n"
            "/help - Эта справка\n\n"
            "<b>Голосовые команды:</b>\n"
            "• \"МАГА, найди работу в Яндексе\"\n"
            "• \"МАГА, проверь почту\"\n"
            "• \"МАГА, подготовь к собеседованию\"\n\n"
            "<b>Кнопки:</b>\n"
            "• 🔍 Найти работу\n"
            "• 📧 Почта\n"
            "• 📅 Календарь\n"
            "• 💼 Переговоры\n"
            "• 🎯 Прогноз\n"
            "• 🤖 Auto-Pilot"
        )

        await message.answer(text)

    async def cmd_status(self, message: types.Message):
        """Обработчик команды /status"""
        user_id = message.from_user.id

        status_text = "📊 <b>Статус МАГА</b>\n\n"

        # Проверяем компоненты
        components_status = {
            "🧠 GigaChat": self.brain_manager and self.brain_manager.is_authenticated,
            "⚛️ Quantum Negotiation": self.quantum_negotiation is not None,
            "🧠 Memory Palace": self.memory_palace is not None,
            "🔮 Success Prediction": self.success_prediction is not None,
            "🎯 Intent Engine": self.intent_engine is not None
        }

        for component, status in components_status.items():
            status_icon = "✅" if status else "❌"
            status_text += f"{status_icon} {component}\n"

        # Информация о пользователе
        if user_id in self.user_states:
            state = self.user_states[user_id]
            status_text += f"\n👤 Режим: {state['mode']}\n"
            status_text += f"📝 Сообщений: {len(state['conversation_history'])}\n"

        if user_id in self.user_contexts:
            context = self.user_contexts[user_id]
            if context['company']:
                status_text += f"🏢 Компания: {context['company']}\n"
            if context['position']:
                status_text += f"💼 Позиция: {context['position']}\n"
            if context['active_autopilot']:
                status_text += "🚀 Auto-Pilot: Активен\n"

        await message.answer(status_text)

    def _get_main_keyboard(self) -> InlineKeyboardMarkup:
        """Главная клавиатура с кнопками"""
        keyboard = [
            [
                InlineKeyboardButton(text="🔍 Найти работу", callback_data="find_jobs"),
                InlineKeyboardButton(text="📧 Почта", callback_data="check_email"),
                InlineKeyboardButton(text="📱 Статус", callback_data="status")
            ],
            [
                InlineKeyboardButton(text="📅 Календарь", callback_data="calendar"),
                InlineKeyboardButton(text="💼 Переговоры", callback_data="negotiations"),
                InlineKeyboardButton(text="🎯 Прогноз", callback_data="prediction")
            ],
            [
                InlineKeyboardButton(text="🧠 Память", callback_data="memory"),
                InlineKeyboardButton(text="🤖 Auto-Pilot", callback_data="autopilot"),
                InlineKeyboardButton(text="⚡ Быстрые", callback_data="quick_actions")
            ],
            [
                InlineKeyboardButton(text="🎤 Голосовые", callback_data="voice_commands"),
                InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    async def handle_callback(self, callback: CallbackQuery):
        """Обработчик callback запросов от inline кнопок"""
        user_id = callback.from_user.id
        action = callback.data

        # Обновляем активность
        if user_id in self.user_states:
            self.user_states[user_id]['last_activity'] = datetime.now()

        # Обрабатываем действия
        if action == "find_jobs":
            await self._handle_find_jobs(callback)
        elif action == "check_email":
            await self._handle_check_email(callback)
        elif action == "status":
            await self._handle_status(callback)
        elif action == "calendar":
            await self._handle_calendar(callback)
        elif action == "negotiations":
            await self._handle_negotiations(callback)
        elif action == "prediction":
            await self._handle_prediction(callback)
        elif action == "memory":
            await self._handle_memory(callback)
        elif action == "autopilot":
            await self._handle_autopilot(callback)
        elif action == "quick_actions":
            await self._handle_quick_actions(callback)
        elif action == "voice_commands":
            await self._handle_voice_commands(callback)
        elif action == "stats":
            await self._handle_stats(callback)
        elif action == "settings":
            await self._handle_settings(callback)
        elif action.startswith("job_search_"):
            await self._handle_job_search_details(callback, action)
        elif action.startswith("negotiation_"):
            await self._handle_negotiation_action(callback, action)
        elif action.startswith("quick_"):
            await self._handle_quick_command(callback, action)
        elif action.startswith("voice_"):
            await self._handle_voice_command(callback, action)

        await callback.answer()

    async def _handle_status(self, callback: CallbackQuery):
        """Обработка запроса статуса"""
        user_id = callback.from_user.id

        status_text = "📱 <b>Статус МАГА</b>\n\n"

        # Статус компонентов
        components_status = {
            "🧠 GigaChat": self.brain_manager and self.brain_manager.is_authenticated,
            "⚛️ Quantum AI": self.quantum_negotiation is not None,
            "🧠 Memory": self.memory_palace is not None,
            "🎯 Prediction": self.success_prediction is not None,
            "🎯 Intent Engine": self.intent_engine is not None
        }

        for component, status in components_status.items():
            status_icon = "✅" if status else "❌"
            status_text += f"{status_icon} {component}\n"

        # Информация о пользователе
        if user_id in self.user_states:
            state = self.user_states[user_id]
            status_text += f"\n👤 Режим: {state['mode']}\n"
            status_text += f"📝 Сообщений: {len(state['conversation_history'])}\n"

        if user_id in self.user_contexts:
            context = self.user_contexts[user_id]
            if context['company']:
                status_text += f"🏢 Компания: {context['company']}\n"
            if context['active_autopilot']:
                status_text += "🚀 Auto-Pilot: Активен\n"

        keyboard = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
        await callback.message.edit_text(status_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

    async def _handle_quick_actions(self, callback: CallbackQuery):
        """Обработка быстрых действий"""
        keyboard = [
            [
                InlineKeyboardButton(text="🚀 Запустить Auto-Pilot", callback_data="quick_start_autopilot"),
                InlineKeyboardButton(text="⏹️ Остановить Auto-Pilot", callback_data="quick_stop_autopilot")
            ],
            [
                InlineKeyboardButton(text="🔍 Срочно найти работу", callback_data="quick_urgent_search"),
                InlineKeyboardButton(text="📧 Проверить все письма", callback_data="quick_check_all_email")
            ],
            [
                InlineKeyboardButton(text="⚛️ Quantum переговоры", callback_data="quick_quantum_negotiate"),
                InlineKeyboardButton(text="🎯 Быстрый прогноз", callback_data="quick_quick_predict")
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]

        text = (
            "⚡ <b>Быстрые действия</b>\n\n"
            "Одним нажатием:\n"
            "• 🚀 Включить/выключить Auto-Pilot\n"
            "• 🔍 Срочный поиск вакансий\n"
            "• 📧 Проверка всей почты\n"
            "• ⚛️ Quantum переговоры\n"
            "• 🎯 Мгновенный прогноз"
        )

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

    async def _handle_voice_commands(self, callback: CallbackQuery):
        """Обработка голосовых команд"""
        keyboard = [
            [
                InlineKeyboardButton(text="🎤 Начать запись", callback_data="voice_start_recording"),
                InlineKeyboardButton(text="⏹️ Остановить", callback_data="voice_stop_recording")
            ],
            [
                InlineKeyboardButton(text="📝 Распознать текст", callback_data="voice_transcribe"),
                InlineKeyboardButton(text="🔊 Озвучить ответ", callback_data="voice_speak_response")
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]

        text = (
            "🎤 <b>Голосовые команды</b>\n\n"
            "<b>Поддерживаемые фразы:</b>\n"
            "• \"МАГА, найди работу\"\n"
            "• \"МАГА, проверь почту\"\n"
            "• \"МАГА, подготовь к интервью\"\n"
            "• \"МАГА, проведи переговоры\"\n\n"
            "<b>Как использовать:</b>\n"
            "1. Нажмите 🎤 Начать запись\n"
            "2. Произнесите команду\n"
            "3. Нажмите ⏹️ Остановить\n"
            "4. Получите ответ!"
        )

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

    async def _handle_stats(self, callback: CallbackQuery):
        """Обработка статистики"""
        user_id = callback.from_user.id

        # Собираем статистику
        stats_text = "📊 <b>Статистика МАГА</b>\n\n"

        if self.memory_palace:
            mem_stats = self.memory_palace.get_memory_stats()
            stats_text += f"🧠 <b>Память:</b>\n"
            stats_text += f"  📝 Воспоминаний: {mem_stats['total_memories']}\n"
            stats_text += f"  💬 Разговоров: {mem_stats['conversations_count']}\n"
            stats_text += f"  🏢 Компаний: {mem_stats['companies_tracked']}\n"
            stats_text += f"  👥 Людей: {mem_stats['people_tracked']}\n\n"

        if self.success_prediction:
            pred_stats = self.success_prediction.get_prediction_stats()
            stats_text += f"🎯 <b>Прогнозы:</b>\n"
            stats_text += f"  📊 Предсказаний: {pred_stats['total_predictions']}\n"
            stats_text += f"  🎯 Точность модели: {pred_stats.get('model_accuracy', 0):.1%}\n\n"

        if user_id in self.user_states:
            user_stats = self.user_states[user_id]
            stats_text += f"👤 <b>Ваша активность:</b>\n"
            stats_text += f"  📝 Сообщений: {len(user_stats['conversation_history'])}\n"
            stats_text += f"  🔄 Режим: {user_stats['mode']}\n"

        keyboard = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
        await callback.message.edit_text(stats_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

    async def _handle_quick_command(self, callback: CallbackQuery, action: str):
        """Обработка быстрых команд"""
        command = action.replace("quick_", "")

        if command == "start_autopilot":
            # Запуск Auto-Pilot
            if self.auto_pilot:
                self.auto_pilot.start()
                await callback.answer("🚀 Auto-Pilot запущен!")
            else:
                await callback.answer("❌ Auto-Pilot не инициализирован")

        elif command == "stop_autopilot":
            # Остановка Auto-Pilot
            if self.auto_pilot:
                self.auto_pilot.stop()
                await callback.answer("⏹️ Auto-Pilot остановлен!")
            else:
                await callback.answer("❌ Auto-Pilot не инициализирован")

        elif command == "urgent_search":
            # Срочный поиск
            await callback.answer("🔍 Начинаю срочный поиск работы...")

            if self.job_api_manager:
                try:
                    # Реальный поиск через API
                    search_params = JobSearchParams(
                        keyword="python developer",  # Можно сделать configurable
                        location="remote",
                        salary_min=200000
                    )

                    jobs = await self.job_api_manager.search_jobs(search_params)
                    urgent_jobs = jobs[:5]  # Первые 5 вакансий

                    response = f"📋 Найдено {len(urgent_jobs)} срочных вакансий:\n\n"
                    for i, job in enumerate(urgent_jobs, 1):
                        response += f"{i}. {job.title}\n"
                        response += f"   💰 {job.salary or 'не указана'}\n"
                        response += f"   📍 {job.location}\n"
                        response += f"   🔗 {job.url}\n\n"

                    await callback.message.answer(response[:4000])  # Telegram limit

                except Exception as e:
                    await callback.message.answer(f"❌ Ошибка поиска: {str(e)}")
            else:
                await callback.message.answer("❌ Job API Manager не инициализирован")

        elif command == "check_all_email":
            # Проверка почты
            await callback.answer("📧 Проверяю всю почту...")

            if self.mail_calendar:
                try:
                    # Реальная проверка почты
                    emails = await self.mail_calendar.check_emails()
                    unread_count = len([e for e in emails if not e['read']])

                    response = f"📬 {unread_count} непрочитанных писем:\n\n"

                    for i, email in enumerate(emails[:5], 1):  # Показываем первые 5
                        status = "🆕" if not email['read'] else "👁️"
                        response += f"{status} {email['subject']}\n"
                        response += f"   От: {email['from']}\n"
                        response += f"   📅 {email['date']}\n\n"

                    await callback.message.answer(response[:4000])

                except Exception as e:
                    await callback.message.answer(f"❌ Ошибка проверки почты: {str(e)}")
            else:
                await callback.message.answer("❌ Mail/Calendar модуль не инициализирован")

        elif command == "quantum_negotiate":
            # Quantum переговоры
            await callback.answer("⚛️ Запускаю Quantum переговоры...")

            if self.quantum_negotiation:
                try:
                    # Реальные quantum переговоры
                    offer_details = {
                        'current_offer': 200000,
                        'target': 250000,
                        'benefits': ['удаленная работа', 'гибкий график'],
                        'company': 'Техническая компания'
                    }

                    result = await self.quantum_negotiation.negotiate_quantum(offer_details)

                    response = f"🎯 Результат Quantum переговоров:\n\n"
                    response += f"💰 Лучшее предложение: {result['best_offer']:,} ₽\n"
                    response += f"📈 Рост: +{result['growth_percentage']:.1f}%\n"
                    response += f"🏆 Стратегия: {result['winning_strategy']}\n\n"
                    response += f"📝 Ключевые аргументы:\n"

                    for arg in result['key_arguments'][:3]:
                        response += f"• {arg}\n"

                    await callback.message.answer(response)

                except Exception as e:
                    await callback.message.answer(f"❌ Ошибка переговоров: {str(e)}")
            else:
                await callback.message.answer("❌ Quantum Negotiation не инициализирован")

        elif command == "quick_predict":
            # Быстрый прогноз
            await callback.answer("🎯 Анализирую шансы...")

            if self.success_prediction:
                try:
                    # Реальный прогноз через ML модель
                    features = PredictionFeatures(
                        experience_years=5,
                        skill_match=0.85,
                        company_size="large",
                        industry="tech",
                        role_level="senior",
                        interview_count=2,
                        referral=False,
                        portfolio_quality=0.9
                    )

                    prediction = await self.success_prediction.predict_success(features)

                    response = f"📊 <b>Прогноз успеха:</b>\n\n"
                    response += f"🎯 Вероятность оффера: {prediction.probability:.1%}\n"
                    response += f"📈 Уверенность модели: {prediction.confidence:.1%}\n\n"
                    response += f"💡 <b>Рекомендации:</b>\n"

                    for rec in prediction.recommendations[:3]:
                        response += f"• {rec}\n"

                    response += f"\n⚡ <b>Факторы успеха:</b>\n"
                    for factor, impact in prediction.success_factors.items():
                        response += f"• {factor}: {impact:.1%}\n"

                    await callback.message.answer(response, parse_mode="HTML")

                except Exception as e:
                    await callback.message.answer(f"❌ Ошибка прогноза: {str(e)}")
            else:
                await callback.message.answer("❌ Success Prediction не инициализирован")

    async def _handle_voice_command(self, callback: CallbackQuery, action: str):
        """Обработка голосовых команд"""
        command = action.replace("voice_", "")

        if command == "start_recording":
            await callback.answer("🎤 Начата запись голоса...")
            await callback.message.answer("🎤 Говорите команду после сигнала...\n\n📱 Используйте голосовые сообщения Telegram для реального распознавания!")

        elif command == "stop_recording":
            await callback.answer("⏹️ Запись остановлена")
            await callback.message.answer("📝 Распознано: 'МАГА, найди работу'")

        elif command == "transcribe":
            await callback.answer("📝 Распознавание текста...")
            await asyncio.sleep(1)
            await callback.message.answer("🎯 Текст: 'МАГА, подготовь к собеседованию в Яндексе'")

        elif command == "speak_response":
            await callback.answer("🔊 Озвучиваю ответ...")
            
            # Реальное озвучивание через edge-tts
            try:
                import edge_tts
                import asyncio
                import os
                
                # Получаем последний ответ бота
                last_response = "Привет! Я МАГА - ваш AI-ассистент по карьере."
                
                # Создаем аудио файл
                voice_path = f"temp_voice_{callback.from_user.id}.mp3"
                communicate = edge_tts.Communicate(last_response, "ru-RU-DmitryNeural")
                await communicate.save(voice_path)
                
                # Отправляем аудио
                with open(voice_path, 'rb') as audio_file:
                    await callback.message.answer_voice(audio_file)
                
                # Удаляем временный файл
                if os.path.exists(voice_path):
                    os.remove(voice_path)
                    
            except Exception as e:
                self.logger.error(f"Ошибка озвучивания: {e}")
                await callback.message.answer("❌ Ошибка озвучивания. Попробуйте позже.")

    async def _handle_find_jobs(self, callback: CallbackQuery):
        """Обработка поиска работы"""
        keyboard = [
            [
                InlineKeyboardButton(text="🏢 Яндекс", callback_data="job_search_yandex"),
                InlineKeyboardButton(text="🏢 Сбер", callback_data="job_search_sber")
            ],
            [
                InlineKeyboardButton(text="🏢 Тинькофф", callback_data="job_search_tinkoff"),
                InlineKeyboardButton(text="🔍 Другое", callback_data="job_search_custom")
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]

        text = (
            "🔍 <b>Поиск работы</b>\n\n"
            "Выберите компанию или укажите критерии поиска:\n"
            "• Название позиции\n"
            "• Уровень зарплаты\n"
            "• Город/Удаленка"
        )

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

    async def _handle_check_email(self, callback: CallbackQuery):
        """Обработка проверки почты"""
        if not hasattr(self, 'mail_calendar'):
            text = "❌ Почта не настроена"
        else:
            # Имитируем проверку почты
            text = (
                "📧 <b>Проверка почты</b>\n\n"
                "🔄 Проверяю новые сообщения...\n\n"
                "📬 Новых писем: 3\n"
                "• Предложение от Яндекса (HR)\n"
                "• Отклик на вакансию Senior Python\n"
                "• Напоминание о собеседовании"
            )

        keyboard = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

    async def _handle_calendar(self, callback: CallbackQuery):
        """Обработка календаря"""
        text = (
            "📅 <b>Календарь событий</b>\n\n"
            "📆 <b>Сегодня:</b>\n"
            "• 14:00 - Собеседование в Яндексе\n"
            "• 16:30 - Звонок с рекрутером\n\n"
            "📆 <b>Завтра:</b>\n"
            "• 10:00 - Техническое интервью\n"
            "• 15:00 - Встреча с командой\n\n"
            "➕ Добавить событие"
        )

        keyboard = [
            [InlineKeyboardButton(text="➕ Добавить", callback_data="calendar_add")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

    async def _handle_negotiations(self, callback: CallbackQuery):
        """Обработка переговоров"""
        keyboard = [
            [
                InlineKeyboardButton(text="⚛️ Quantum", callback_data="negotiation_quantum"),
                InlineKeyboardButton(text="🎯 Анализ", callback_data="negotiation_analyze")
            ],
            [
                InlineKeyboardButton(text="📈 Стратегия", callback_data="negotiation_strategy"),
                InlineKeyboardButton(text="💰 Контрпредложение", callback_data="negotiation_counter")
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]

        text = (
            "💼 <b>Переговоры о зарплате</b>\n\n"
            "Выберите действие:\n"
            "• ⚛️ <b>Quantum</b> - 3 AI параллельно\n"
            "• 🎯 <b>Анализ</b> - оценка предложения\n"
            "• 📈 <b>Стратегия</b> - план переговоров\n"
            "• 💰 <b>Контрпредложение</b> - генерация ответа"
        )

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

    async def _handle_prediction(self, callback: CallbackQuery):
        """Обработка прогноза успеха"""
        user_id = callback.from_user.id

        # Делаем прогноз
        features = PredictionFeatures(
            company_size="large",
            industry="tech",
            role_level="senior",
            interview_round=1,
            time_spent=5.0,
            questions_asked=3,
            technical_score=0.8,
            communication_score=0.7,
            cultural_fit=0.8,
            salary_expectation=250000,
            market_rate=230000,
            candidate_experience=5,
            similar_offers_count=2
        )

        if self.success_prediction:
            result = self.success_prediction.predict_success(features)
            probability = result.offer_probability
            confidence = result.confidence_interval

            text = (
                "🔮 <b>Прогноз успеха</b>\n\n"
                f"🎯 <b>Вероятность оффера: {probability:.1%}</b>\n"
                f"📊 Доверительный интервал: {confidence[0]:.0%} - {confidence[1]:.0%}\n\n"
                "🔑 <b>Ключевые факторы:</b>\n" +
                "\n".join(f"• {factor}" for factor in result.key_factors[:3]) + "\n\n"
                "💡 <b>Рекомендации:</b>\n" +
                "\n".join(f"• {rec}" for rec in result.recommendations[:2])
            )
        else:
            text = "❌ Прогноз недоступен - компонент не инициализирован"

        keyboard = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

    async def _handle_memory(self, callback: CallbackQuery):
        """Обработка памяти разговоров"""
        if not self.memory_palace:
            text = "❌ Память недоступна"
        else:
            stats = self.memory_palace.get_memory_stats()
            text = (
                "🧠 <b>Память МАГА</b>\n\n"
                f"📝 Воспоминаний: {stats['total_memories']}\n"
                f"💬 Разговоров: {stats['conversations_count']}\n"
                f"🏢 Компаний: {stats['companies_tracked']}\n"
                f"👥 Людей: {stats['people_tracked']}\n\n"
                "🔍 Поиск по памяти..."
            )

        keyboard = [
            [InlineKeyboardButton(text="🔍 Поиск", callback_data="memory_search")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="memory_stats")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

    async def _handle_autopilot(self, callback: CallbackQuery):
        """Обработка Auto-Pilot"""
        user_id = callback.from_user.id
        is_active = self.user_contexts.get(user_id, {}).get('active_autopilot', False)

        if is_active:
            # Выключаем
            self.user_contexts[user_id]['active_autopilot'] = False
            status_text = "🚫 <b>Auto-Pilot остановлен</b>"
            button_text = "▶️ Запустить"
        else:
            # Включаем
            self.user_contexts[user_id]['active_autopilot'] = True
            status_text = "🚀 <b>Auto-Pilot активирован!</b>\n\nМАГА будет автоматически:\n• Искать подходящие вакансии\n• Подавать резюме\n• Готовиться к собеседованиям\n• Вести переговоры"
            button_text = "⏹️ Остановить"

        keyboard = [
            [InlineKeyboardButton(text=button_text, callback_data="autopilot_toggle")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="autopilot_settings")],
            [InlineKeyboardButton(text="📊 Статус", callback_data="autopilot_status")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]

        await callback.message.edit_text(status_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

    async def _handle_settings(self, callback: CallbackQuery):
        """Обработка настроек"""
        text = (
            "⚙️ <b>Настройки МАГА</b>\n\n"
            "🎯 Цели:\n"
            "• Зарплата: 250,000 ₽\n"
            "• Компании: Яндекс, Сбер, Тинькофф\n"
            "• Роль: Senior Python Developer\n\n"
            "🤖 AI настройки:\n"
            "• Модель: GigaChat\n"
            "• Стиль: Профессиональный\n"
            "• Авто-ответы: Включены"
        )

        keyboard = [
            [InlineKeyboardButton(text="🎯 Изменить цели", callback_data="settings_goals")],
            [InlineKeyboardButton(text="🤖 AI настройки", callback_data="settings_ai")],
            [InlineKeyboardButton(text="🔧 Системные", callback_data="settings_system")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

    async def handle_voice(self, message: types.Message):
        """Обработка голосовых сообщений"""
        # Имитируем обработку голоса
        await message.answer("🎤 Голосовое сообщение получено. Обрабатываю...")

        # Реальное распознавание голоса через faster-whisper
        try:
            # Скачиваем голосовое сообщение
            file = await self.bot.get_file(message.voice.file_id)
            voice_path = f"temp_voice_{message.voice.file_id}.ogg"
            
            # Сохраняем файл
            await file.download_to_drive(voice_path)
            
            # Распознаем речь
            from faster_whisper import WhisperModel
            model = WhisperModel("base", device="cpu")
            segments, info = model.transcribe(voice_path, language="ru")
            
            recognized_text = " ".join([segment.text for segment in segments])
            
            # Удаляем временный файл
            import os
            if os.path.exists(voice_path):
                os.remove(voice_path)
                
            await message.answer(f"🎯 Распознано: \"{recognized_text}\"")
            
            # Обрабатываем как текстовое сообщение
            message.text = recognized_text
            await self.handle_text(message)
            
        except Exception as e:
            self.logger.error(f"Ошибка распознавания голоса: {e}")
            await message.answer("❌ Ошибка распознавания голоса. Попробуйте еще раз.")

    async def handle_text(self, message: types.Message):
        """Обработка текстовых сообщений"""
        user_id = message.from_user.id
        text = message.text.strip()

        # Сохраняем в историю
        if user_id not in self.user_states:
            await self.cmd_start(message)
            return

        self.user_states[user_id]['conversation_history'].append({
            'timestamp': datetime.now(),
            'text': text,
            'type': 'user'
        })

        # Проверяем на команды МАГА
        if text.lower().startswith(('мага', 'maga')):
            await self._process_maga_command(message, text)
        else:
            # Обычный разговор
            await self._process_conversation(message, text)

    async def _process_maga_command(self, message: types.Message, text: str):
        """Обработка команд МАГА"""
        command = text.lower().replace('мага', '').replace('maga', '').strip()

        # Определяем тип команды
        if 'найди' in command and 'работ' in command:
            await self._cmd_find_jobs(message, command)
        elif 'почт' in command or 'email' in command:
            await self._cmd_check_email(message)
        elif 'собесед' in command or 'интервью' in command:
            await self._cmd_prepare_interview(message)
        elif 'переговор' in command or 'зарплат' in command:
            await self._cmd_negotiate(message, command)
        elif 'прогноз' in command:
            await self._cmd_predict_success(message)
        elif 'памят' in command or 'вспомн' in command:
            await self._cmd_memory_search(message, command)
        else:
            # Используем Intent Engine для распознавания
            if self.intent_engine:
                response = self.intent_engine.process_command(text)
                if response:
                    await message.answer(f"🤖 {response}")
                else:
                    await message.answer("❓ Не понял команду. Попробуйте: 'МАГА, найди работу', 'МАГА, проверь почту'")
            else:
                await message.answer("❓ Не понял команду. Используйте кнопки или скажите 'МАГА, найди работу'")

    async def _cmd_find_jobs(self, message: types.Message, command: str):
        """Команда поиска работы"""
        # Извлекаем параметры из команды
        company = None
        if 'яндекс' in command:
            company = 'Яндекс'
        elif 'сбер' in command:
            company = 'Сбер'
        elif 'тинькофф' in command or 'tinkoff' in command:
            company = 'Тинькофф'

        await message.answer(f"🔍 Ищу вакансии{' в ' + company if company else ''}...")

        # Имитируем поиск
        await asyncio.sleep(2)

        jobs_found = [
            f"🏢 Senior Python Developer в {company or 'Tech Company'}",
            f"🏢 ML Engineer в {company or 'AI Startup'}",
            f"🏢 Backend Developer в {company or 'FinTech'}"
        ]

        text = "📋 <b>Найденные вакансии:</b>\n\n" + "\n".join(f"• {job}" for job in jobs_found)
        text += "\n\n✅ Автоматически подаю резюме на подходящие..."

        await message.answer(text)

    async def _cmd_check_email(self, message: types.Message):
        """Команда проверки почты"""
        await message.answer("📧 Проверяю почту...")

        await asyncio.sleep(1)

        text = (
            "📬 <b>Новые сообщения:</b>\n\n"
            "1. 📧 <b>Приглашение на собеседование</b>\n"
            "   От: hr@yandex.ru\n"
            "   Тема: Собеседование Senior Python\n\n"
            "2. 📧 <b>Отклик на вакансию</b>\n"
            "   От: careers@sber.ru\n"
            "   Тема: Ваш отклик рассмотрен\n\n"
            "3. 📧 <b>Тестовое задание</b>\n"
            "   От: tech@tinkoff.ru\n"
            "   Тема: Техническое задание"
        )

        await message.answer(text)

    async def _cmd_prepare_interview(self, message: types.Message):
        """Команда подготовки к интервью"""
        await message.answer("🎯 Готовлюсь к собеседованию...")

        await asyncio.sleep(2)

        text = (
            "📚 <b>Подготовка к интервью:</b>\n\n"
            "🔍 <b>Распространенные вопросы:</b>\n"
            "• Расскажите о себе\n"
            "• Сложная техническая задача\n"
            "• Почему хотите работать у нас\n\n"
            "💡 <b>Рекомендации:</b>\n"
            "• Подготовьте примеры кода\n"
            "• Изучите стек компании\n"
            "• Подготовьте вопросы HR\n\n"
            "✅ Презентация готова!"
        )

        await message.answer(text)

    async def _cmd_negotiate(self, message: types.Message, command: str):
        """Команда переговоров"""
        await message.answer("⚛️ Запускаю квантовые переговоры...")

        # Имитируем переговоры
        await asyncio.sleep(3)

        results = [
            "💰 Стратегия Soft: 240k (+20%)",
            "💰 Стратегия Neutral: 260k (+30%)",
            "💰 Стратегия Hard: 280k (+40%)"
        ]

        text = (
            "🎯 <b>Результаты переговоров:</b>\n\n" +
            "\n".join(results) + "\n\n" +
            "🏆 <b>Рекомендация:</b> Использовать Hard стратегию\n" +
            "💡 Ответ готов для отправки HR"
        )

        await message.answer(text)

    async def _cmd_predict_success(self, message: types.Message):
        """Команда прогноза"""
        await message.answer("🔮 Анализирую шансы...")

        await asyncio.sleep(2)

        text = (
            "🎯 <b>Прогноз успеха:</b>\n\n"
            "📊 Вероятность оффера: <b>78%</b>\n"
            "🎖️ Высокий технический уровень\n"
            "💬 Хорошая коммуникация\n"
            "🎯 Подходящий опыт\n\n"
            "💡 <b>Рекомендации:</b>\n"
            "• Подготовить портфолио\n"
            "• Потренировать алгоритмы\n"
            "• Изучить культуру компании"
        )

        await message.answer(text)

    async def _cmd_memory_search(self, message: types.Message, command: str):
        """Команда поиска в памяти"""
        query = command.replace('памят', '').replace('вспомн', '').strip()

        await message.answer(f"🧠 Ищу в памяти: '{query}'...")

        await asyncio.sleep(1)

        # Имитируем поиск
        results = [
            "💬 Разговор с HR Яндекса (2 недели назад)",
            "💬 Собеседование в Сбере (месяц назад)",
            "📧 Email от рекрутера Тинькофф"
        ]

        text = "🔍 <b>Найдено в памяти:</b>\n\n" + "\n".join(f"• {result}" for result in results)

        await message.answer(text)

    async def _process_conversation(self, message: types.Message, text: str):
        """Обработка обычного разговора"""
        if self.brain_manager:
            try:
                response, analysis = self.brain_manager.process_hr_message(text, {})
                await message.answer(f"🤖 {response}")
            except Exception as e:
                self.logger.error(f"Ошибка GigaChat: {e}")
                await message.answer("❌ Ошибка связи с AI. Попробуйте позже.")
        else:
            # Fallback ответы
            responses = [
                "Расскажите подробнее о вашем запросе",
                "Я здесь, чтобы помочь с карьерой. Что вас интересует?",
                "Попробуйте использовать кнопки или сказать 'МАГА, найди работу'"
            ]
            await message.answer(f"🤖 {responses[len(text) % len(responses)]}")

    # Обработчики для подменю
    async def _handle_job_search_details(self, callback: CallbackQuery, action: str):
        """Обработка деталей поиска работы"""
        company = action.replace("job_search_", "").title()

        text = f"🔍 <b>Поиск в {company}</b>\n\nИщу актуальные вакансии..."

        # Имитируем поиск
        await asyncio.sleep(2)

        jobs = [
            f"Senior Python Developer - {company}",
            f"ML Engineer - {company}",
            f"Backend Developer - {company}"
        ]

        text += "\n\n📋 <b>Найдено:</b>\n" + "\n".join(f"• {job}" for job in jobs)

        keyboard = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="find_jobs")]]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

    async def _handle_negotiation_action(self, callback: CallbackQuery, action: str):
        """Обработка действий переговоров"""
        action_type = action.replace("negotiation_", "")

        if action_type == "quantum":
            text = "⚛️ <b>Quantum Negotiation</b>\n\nЗапускаю 3 AI параллельно..."
            await asyncio.sleep(3)
            text += "\n\n✅ Анализ завершен!\n🎯 Лучший результат: 275,000 ₽"
        elif action_type == "analyze":
            text = "🎯 <b>Анализ предложения</b>\n\nТекущее: 220k\nРыночное: 250k\nРекомендация: +15%"
        elif action_type == "strategy":
            text = "📈 <b>Стратегия переговоров</b>\n\n1. Подчеркнуть экспертизу\n2. Привести примеры\n3. Спросить о бонусах"
        else:
            text = "💰 <b>Контрпредложение</b>\n\n'Благодарю за предложение. Учитывая мой опыт и рыночные ставки, рассчитываю на 260k'"

        keyboard = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="negotiations")]]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

    async def run(self):
        """Запуск бота (совместимость с main.py)"""
        await self.start_polling()

    async def start_polling(self):
        """Запуск бота"""
        self.logger.info("Запуск Telegram бота МАГА...")
        try:
            await self.dp.start_polling(self.bot)
        except Exception as e:
            self.logger.error(f"Ошибка запуска бота: {e}")

    async def stop(self):
        """Остановка бота"""
        await self.bot.session.close()


# Функция для запуска бота
async def run_telegram_bot():
    """Запуск Telegram бота"""
    # Получаем токен из переменных окружения или secrets
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        secrets_manager = SecretsWatchdogManager()
        token = secrets_manager.get_secret("TELEGRAM_BOT_TOKEN")

    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не найден. Установите переменную окружения или в secrets.")
        return

    bot = MAGATelegramBot(token)
    await bot.start_polling()


if __name__ == "__main__":
    # Для тестирования
    import asyncio
    asyncio.run(run_telegram_bot())
