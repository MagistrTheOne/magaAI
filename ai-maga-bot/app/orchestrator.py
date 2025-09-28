"""
Единый оркестратор AI-Maga - соединяет все компоненты AIMagistr в единый организм
"""
import asyncio
import logging
import os
import sys
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from pathlib import Path
import json

from app.settings import settings
from app.services.mode import get_user_mode, set_user_mode
from app.services.tts import synthesize
from app.services.yandex_llm import complete_text
from app.services.tg_utils import send_text_message, send_voice_message, send_audio_message

# Импорт существующих компонентов AIMagistr
sys.path.append('..')  # Добавляем путь к корню проекта

# Импорт RAG и Memory компонентов
try:
    from brain.rag_index import RAGManager
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger.warning("RAG компонент недоступен")

try:
    from memory_palace import MemoryPalace
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    logger.warning("Memory Palace компонент недоступен")

try:
    from integrations.yandex_vision import YandexVision
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False
    logger.warning("Yandex Vision компонент недоступен")

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Простой circuit breaker для защиты от cascade failures"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open

    def call(self, func, *args, **kwargs):
        """Выполнить функцию через circuit breaker"""
        if self.state == 'open':
            if self._should_attempt_reset():
                self.state = 'half-open'
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Проверить, пора ли пытаться сбросить circuit breaker"""
        if self.last_failure_time is None:
            return False
        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def _on_success(self):
        """Обработка успешного вызова"""
        if self.state == 'half-open':
            self.state = 'closed'
            self.failure_count = 0
            logger.info("Circuit breaker reset to CLOSED")

    def _on_failure(self):
        """Обработка неудачного вызова"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class AIMagaOrchestrator:
    """Главный оркестратор AI-Maga - объединяет все компоненты"""

    def __init__(self):
        self.components = {}
        self.active_tasks = {}
        self.user_sessions = {}
        self.meeting_sessions = {}  # {meeting_id: MeetingSession}
        self.initialized = False

        # RAG, Memory и Vision компоненты
        self.rag_manager = None
        self.memory_palace = None
        self.vision_client = None

        # Circuit breakers для внешних API
        self.llm_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        self.vision_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        self.stt_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

    async def initialize(self):
        """Инициализация всех компонентов"""
        if self.initialized:
            return

        logger.info("🚀 Инициализация AI-Maga Orchestrator...")

        try:
            # Инициализация AI мозга
            await self._init_ai_brain()

            # Инициализация сервисов
            await self._init_services()

            # Инициализация голосового управления
            await self._init_voice_control()

            # Инициализация OS контроля
            await self._init_os_control()

            # Инициализация автономного режима
            await self._init_autonomous_mode()

            # Инициализация коммуникаций
            await self._init_communications()

            # Инициализация Zoom интеграции
            await self._init_zoom_integration()

            # Инициализация RAG и Memory
            await self._init_rag_memory()

            self.initialized = True
            logger.info("AI-Maga Orchestrator полностью инициализирован")

        except Exception as e:
            logger.error(f"Ошибка инициализации оркестратора: {e}")
            raise

    async def _init_ai_brain(self):
        """Инициализация AI мозга"""
        try:
            # Импортируем существующий AI клиент
            from brain.ai_client import YandexAIClient

            self.components['ai_brain'] = YandexAIClient()
            logger.info("AI мозг инициализирован")
        except ImportError as e:
            logger.warning(f"AI мозг недоступен: {e}")
            self.components['ai_brain'] = None

    async def _init_services(self):
        """Инициализация сервисов AIMagistr"""
        services_to_load = [
            'daily_focus', 'personal_crm', 'health_nudges', 'reading_queue',
            'doc_autocatalog', 'email_triage', 'finance_receipts', 'routines',
            'subscriptions', 'time_blocking', 'travel_assistant'
        ]

        for service_name in services_to_load:
            try:
                module = __import__(f'services.{service_name}', fromlist=[service_name])
                service_class = getattr(module, service_name.replace('_', ' ').title().replace(' ', ''))
                self.components[service_name] = service_class()
                logger.info(f"📦 Сервис {service_name} загружен")
            except Exception as e:
                logger.warning(f"Сервис {service_name} недоступен: {e}")

    async def _init_voice_control(self):
        """Инициализация голосового управления"""
        try:
            from app.services.voice_integration import voice_integration

            self.components['voice_integration'] = voice_integration
            voice_integration.set_command_callback(self.handle_voice_command)

            # Запускаем прослушивание
            await voice_integration.start_listening()
            logger.info("Голосовое управление инициализировано")
        except Exception as e:
            logger.warning(f"Голосовое управление недоступно: {e}")

    async def _init_os_control(self):
        """Инициализация OS контроля"""
        try:
            from app.services.os_controller import OSController

            self.components['os_control'] = OSController()
            logger.info("OS контроль инициализирован")
        except ImportError as e:
            logger.warning(f"OS контроль недоступен: {e}")
            # Fallback на базовый OS контроллер
            try:
                self.components['os_control'] = OSController()
                logger.info("Базовый OS контроль инициализирован")
            except Exception as e2:
                logger.warning(f"Базовый OS контроль недоступен: {e2}")

    async def _init_autonomous_mode(self):
        """Инициализация автономного режима"""
        try:
            from app.services.autonomous_agent import autonomous_agent

            self.components['autonomous_agent'] = autonomous_agent
            await autonomous_agent.start()
            logger.info("Автономный режим инициализирован")
        except Exception as e:
            logger.warning(f"Автономный режим недоступен: {e}")

    async def _init_communications(self):
        """Инициализация коммуникаций"""
        try:
            from meeting_assistant import MeetingAssistant
            from smart_mail import SmartMail

            self.components['meeting_assistant'] = MeetingAssistant()
            self.components['smart_mail'] = SmartMail()
            logger.info("Коммуникации инициализированы")
        except ImportError as e:
            logger.warning(f"Коммуникации недоступны: {e}")

    async def process_image(self, user_id: int, image_path: str, caption: str = None) -> Dict[str, Any]:
        """
        Обработка изображения через Vision API

        Args:
            user_id: ID пользователя
            image_path: Путь к изображению
            caption: Подпись к изображению

        Returns:
            Dict с результатом анализа
        """
        logger.info(f"Обработка изображения от пользователя {user_id}: {image_path}")

        try:
            if not self.vision_client:
                return {
                    'type': 'text',
                    'text': 'Анализ изображений недоступен - Vision API не настроен',
                    'service': 'vision'
                }

            # Извлекаем текст из изображения (OCR) через circuit breaker
            try:
                extracted_text = await self.vision_circuit_breaker.call(
                    self.vision_client.extract_text,
                    image_path
                )
            except Exception as e:
                logger.warning(f"Vision circuit breaker triggered for OCR: {e}")
                extracted_text = ""

            if extracted_text:
                # Если есть текст, анализируем его через LLM
                analysis_prompt = f"""
                Проанализируй этот текст, извлеченный из изображения:

                "{extracted_text}"

                {f"Подпись к изображению: {caption}" if caption else ""}

                Дай краткую выжимку основного содержания и ключевых моментов.
                """

                analysis = await complete_text(
                    system_prompt="Ты - эксперт по анализу изображений и текста. Давай точные и полезные выжимки.",
                    user_message=analysis_prompt
                )

                # Сохраняем в память
                if self.memory_palace:
                    try:
                        self.memory_palace.add_memory(
                            content=f"Image analysis: {extracted_text[:200]}...\nAnalysis: {analysis[:200]}...",
                            metadata={
                                'user_id': user_id,
                                'image_path': image_path,
                                'extracted_text': extracted_text,
                                'analysis': analysis,
                                'interaction_type': 'image_analysis'
                            },
                            tags=['image_analysis', 'vision', 'ocr']
                        )
                    except Exception as e:
                        logger.warning(f"Ошибка сохранения анализа изображения в память: {e}")

                return {
                    'type': 'text',
                    'text': f"Извлеченный текст:\n{extracted_text}\n\nАнализ:\n{analysis}",
                    'service': 'vision',
                    'extracted_text': extracted_text,
                    'analysis': analysis
                }
            else:
                # Детекция объектов если текста нет через circuit breaker
                try:
                    objects = await self.vision_circuit_breaker.call(
                        self.vision_client.detect_objects,
                        image_path
                    )
                except Exception as e:
                    logger.warning(f"Vision circuit breaker triggered for object detection: {e}")
                    objects = []
                if objects:
                    object_list = [f"- {obj['name']} ({obj['score']:.2f})" for obj in objects[:5]]
                    objects_text = "\n".join(object_list)

                    return {
                        'type': 'text',
                        'text': f"Обнаруженные объекты на изображении:\n{objects_text}",
                        'service': 'vision',
                        'objects': objects
                    }
                else:
                    return {
                        'type': 'text',
                        'text': 'Не удалось проанализировать изображение - нет текста или объектов',
                        'service': 'vision'
                    }

        except Exception as e:
            logger.error(f"Ошибка обработки изображения: {e}")
            return {
                'type': 'error',
                'text': f"Ошибка анализа изображения: {str(e)}",
                'service': 'vision'
            }

    async def process_message(self, user_id: int, message_text: str, message_type: str = "text") -> Dict[str, Any]:
        """
        Обработка входящего сообщения через все компоненты

        Args:
            user_id: ID пользователя
            message_text: Текст сообщения
            message_type: Тип сообщения (text/voice)

        Returns:
            Dict с результатом обработки
        """
        logger.info(f"📨 Обработка сообщения от {user_id}: {message_text[:100]}...")

        try:
            # Анализ intent через AI мозг
            intent = await self._analyze_intent(message_text)

            # Маршрутизация по сервисам
            response = await self._route_to_service(user_id, intent, message_text, message_type)

            # Постобработка (улучшение ответа, добавление контекста)
            response = await self._post_process_response(user_id, response)

            return response

        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            return {
                "type": "error",
                "text": f"Произошла ошибка: {str(e)}",
                "voice_response": None
            }

    async def _analyze_intent(self, message_text: str) -> Dict[str, Any]:
        """Анализ намерения сообщения"""
        if self.components.get('ai_brain'):
            try:
                # Используем существующий intent engine
                from intent_engine import IntentEngine
                intent_engine = IntentEngine()
                return await intent_engine.analyze(message_text)
            except Exception as e:
                logger.warning(f"Intent анализ недоступен: {e}")

        # Fallback: простой анализ по ключевым словам
        return self._simple_intent_analysis(message_text)

    def _simple_intent_analysis(self, message_text: str) -> Dict[str, Any]:
        """Простой анализ намерения по ключевым словам"""
        text_lower = message_text.lower()

        intents = {
            'daily_focus': ['фокус', 'приоритет', 'задачи', 'план'],
            'health_nudges': ['здоровье', 'спорт', 'еда', 'отдых'],
            'personal_crm': ['контакт', 'встреча', 'люди', 'связи'],
            'email_triage': ['почта', 'email', 'письмо', 'сообщение'],
            'finance': ['деньги', 'финансы', 'бюджет', 'расходы'],
            'calendar': ['календарь', 'время', 'расписание', 'встреча'],
            'os_control': ['открой', 'запустить', 'файл', 'программа'],
            'meeting': ['zoom', 'встреча', 'митинг', 'звонок']
        }

        for intent, keywords in intents.items():
            if any(keyword in text_lower for keyword in keywords):
                return {
                    'intent': intent,
                    'confidence': 0.8,
                    'entities': [],
                    'original_text': message_text
                }

        return {
            'intent': 'general_chat',
            'confidence': 0.5,
            'entities': [],
            'original_text': message_text
        }

    async def _route_to_service(self, user_id: int, intent: Dict, message_text: str, message_type: str) -> Dict[str, Any]:
        """Маршрутизация запроса к соответствующему сервису"""
        intent_name = intent.get('intent', 'general_chat')

        # Маршрутизация по существующим сервисам
        service_mapping = {
            'daily_focus': 'daily_focus',
            'health_nudges': 'health_nudges',
            'personal_crm': 'personal_crm',
            'email_triage': 'email_triage',
            'finance': 'finance_receipts',
            'calendar': 'time_blocking',
            'os_control': 'os_control',
            'meeting': 'meeting_assistant'
        }

        service_name = service_mapping.get(intent_name)
        if service_name and service_name in self.components:
            return await self._execute_service(service_name, user_id, message_text, intent)

        # Общий чат через AI
        return await self._handle_general_chat(user_id, message_text, message_type)

    async def _execute_service(self, service_name: str, user_id: int, message_text: str, intent: Dict) -> Dict[str, Any]:
        """Выполнение сервиса"""
        service = self.components[service_name]

        try:
            if service_name == 'daily_focus':
                result = await service.get_daily_focus(user_id)
                return {
                    'type': 'text',
                    'text': f"Ваш ежедневный фокус:\n{result}",
                    'service': 'daily_focus'
                }

            elif service_name == 'health_nudges':
                result = await service.get_health_nudges(user_id)
                return {
                    'type': 'text',
                    'text': f"Советы по здоровью:\n{result}",
                    'service': 'health_nudges'
                }

            elif service_name == 'os_control':
                # Проверка безопасности команды
                from app.services.security_enhancement import security_enhancement
                security_check = security_enhancement.validate_command_safety(
                    message_text, intent.get('user_id', 0)
                )

                if security_check['blocked']:
                    return {
                        'type': 'text',
                        'text': f"Команда заблокирована по соображениям безопасности:\n{'; '.join(security_check['warnings'])}",
                        'service': 'os_control'
                    }

                if security_check['warnings']:
                    logger.warning(f"Предупреждения безопасности: {security_check['warnings']}")

                # OS команды с подтверждением
                await self._confirm_os_command(message_text)
                result = await service.execute_command(message_text, intent.get('user_id'))
                if result['success']:
                    return {
                        'type': 'text',
                        'text': f"Выполнено:\n{result.get('output', 'OK')}",
                        'service': 'os_control'
                    }
                else:
                    return {
                        'type': 'text',
                        'text': f"Ошибка: {result.get('error', 'Неизвестная ошибка')}",
                        'service': 'os_control'
                    }

            # Добавьте другие сервисы по аналогии...

        except Exception as e:
            logger.error(f"Ошибка выполнения сервиса {service_name}: {e}")
            return {
                'type': 'error',
                'text': f"Ошибка сервиса {service_name}: {str(e)}",
                'service': service_name
            }

    async def _handle_general_chat(self, user_id: int, message_text: str, message_type: str) -> Dict[str, Any]:
        """Обработка общего чата через AI"""
        try:
            # Получаем режим ответа пользователя
            response_mode = get_user_mode(user_id)

            # Получаем контекст из RAG (graceful degradation)
            rag_context = ""
            if self.rag_manager:
                try:
                    rag_context = self.rag_manager.search_context(message_text, max_length=500)
                    if rag_context and rag_context != "Контекст не найден":
                        rag_context = f"\n\nРелевантная информация из памяти:\n{rag_context}"
                    else:
                        logger.debug("RAG контекст не найден или пустой")
                except Exception as e:
                    logger.warning(f"Ошибка получения RAG контекста, продолжаем без него: {e}")
            else:
                logger.debug("RAG менеджер недоступен, продолжаем без контекста")

            # Формируем системный промпт с учетом профиля решений
            decision_profile = getattr(settings, 'ai_decision_profile', 'balanced')
            profile_prompts = {
                'conservative': "Будь осторожен, не предлагай рискованные действия. Запрашивай подтверждение для важных решений.",
                'balanced': "Отвечай кратко и по делу, предлагай конкретные действия.",
                'active': "Будь инициативен, предлагай дополнительные действия и улучшения. Автоматизируй рутинные задачи."
            }

            base_prompt = """Ты - AI-Maga, умный персональный ассистент.
            Ты можешь управлять операционной системой, планировать задачи, анализировать данные,
            работать с почтой, календарем и многими другими функциями."""

            system_prompt = f"{base_prompt}\n{profile_prompts.get(decision_profile, profile_prompts['balanced'])}{rag_context}"

            # Используем circuit breaker для LLM
            try:
                ai_response = await self.llm_circuit_breaker.call(
                    complete_text,
                    system_prompt=system_prompt,
                    user_message=message_text
                )
            except Exception as e:
                logger.warning(f"LLM circuit breaker triggered: {e}")
                # Graceful degradation - возвращаем базовый ответ
                ai_response = "Извините, в данный момент ИИ недоступен. Попробуйте позже."

            # Сохраняем взаимодействие в Memory Palace (graceful degradation)
            if self.memory_palace:
                try:
                    self.memory_palace.add_memory(
                        content=f"User: {message_text}\nAI: {ai_response}",
                        metadata={
                            'user_id': user_id,
                            'message_type': message_type,
                            'interaction_type': 'chat',
                            'decision_profile': decision_profile
                        },
                        tags=['user_interaction', 'ai_response', message_type]
                    )
                except Exception as e:
                    logger.warning(f"Ошибка сохранения в память, продолжаем: {e}")
            else:
                logger.debug("Memory Palace недоступен, пропускаем сохранение")

            # Проверяем активные встречи Zoom для gating
            active_meetings = [mid for mid, session in self.meeting_sessions.items() if not session.ai_muted]
            if active_meetings:
                # Применяем политику встречи к ответу
                for meeting_id in active_meetings:
                    session = self.meeting_sessions[meeting_id]
                    policy_result = await session.check_message(ai_response)
                    if not policy_result.allowed:
                        logger.info(f"Ответ заблокирован политикой встречи {meeting_id}: {policy_result.reason}")
                        ai_response = f"[Заглушен на встрече {meeting_id}] {ai_response}"
                        break

            # Определяем тип ответа
            if response_mode == "voice" or message_type == "voice":
                try:
                    audio_result = await synthesize(ai_response)
                    return {
                        'type': 'voice' if audio_result['type'] == 'voice' else 'audio',
                        'text': ai_response,
                        'audio_data': audio_result['data'],
                        'service': 'ai_chat'
                    }
                except Exception as e:
                    logger.warning(f"TTS недоступен, возвращаем текст: {e}")

            return {
                'type': 'text',
                'text': ai_response,
                'service': 'ai_chat'
            }

        except Exception as e:
            logger.error(f"Ошибка общего чата: {e}")
            return {
                'type': 'error',
                'text': "Извините, произошла ошибка при обработке запроса",
                'service': 'ai_chat'
            }

    async def _confirm_os_command(self, command: str) -> bool:
        """Подтверждение опасных OS команд"""
        dangerous_commands = ['rm', 'del', 'delete', 'format', 'shutdown']

        if any(cmd in command.lower() for cmd in dangerous_commands):
            logger.warning(f"Опасная команда заблокирована: {command}")
            raise ValueError("Опасная команда заблокирована для безопасности")

        return True

    async def _post_process_response(self, user_id: int, response: Dict[str, Any]) -> Dict[str, Any]:
        """Постобработка ответа - добавление контекста, улучшений"""
        # Добавляем timestamp
        response['timestamp'] = datetime.now().isoformat()

        # Добавляем user_id
        response['user_id'] = user_id

        # Сохраняем взаимодействие в Memory Palace
        if self.memory_palace and response.get('type') != 'error':
            try:
                content = f"Service: {response.get('service', 'unknown')}\nResponse: {response.get('text', '')}"
                if response.get('type') == 'voice' or response.get('type') == 'audio':
                    content += " [Voice/Audio response]"

                self.memory_palace.add_memory(
                    content=content,
                    metadata={
                        'user_id': user_id,
                        'response_type': response.get('type'),
                        'service': response.get('service'),
                        'interaction_type': 'service_response'
                    },
                    tags=['system_response', response.get('service', 'unknown'), response.get('type', 'text')]
                )
            except Exception as e:
                logger.warning(f"Ошибка сохранения ответа в память: {e}")

        return response

    async def handle_voice_command(self, command: str, confidence: float):
        """Обработка голосовых команд"""
        if confidence < 0.7:
            logger.info(f"Низкая уверенность голосовой команды: {confidence}")
            return

        logger.info(f"Голосовая команда: {command}")

        # Предварительная обработка голосовой команды
        try:
            from app.services.voice_integration import voice_integration
            processed = await voice_integration.process_voice_command(command)
            command = processed['processed_command']
        except Exception as e:
            logger.warning(f"Ошибка обработки голосовой команды: {e}")

        # Обработка как обычное сообщение с голосом
        # Используем фиктивный user_id для голосовых команд
        voice_user_id = 0  # Системный пользователь для голоса

        try:
            result = await self.process_message(voice_user_id, command, "voice")

            # Для голосовых команд можно добавить специальную обработку
            # Например, озвучить ответ или выполнить действие

            if result.get('type') == 'text':
                logger.info(f"Голосовая команда обработана: {result['text']}")
                # Здесь можно добавить озвучивание ответа

        except Exception as e:
            logger.error(f"Ошибка обработки голосовой команды: {e}")

    async def start_autonomous_mode(self, user_id: int):
        """Запуск автономного режима"""
        if 'auto_pilot' not in self.components:
            logger.warning("Автономный режим недоступен")
            return

        logger.info(f"Запуск автономного режима для пользователя {user_id}")

        # Запуск фоновых задач
        task = asyncio.create_task(self._run_autonomous_tasks(user_id))
        self.active_tasks[user_id] = task

    async def stop_autonomous_mode(self, user_id: int):
        """Остановка автономного режима"""
        if user_id in self.active_tasks:
            self.active_tasks[user_id].cancel()
            del self.active_tasks[user_id]
            logger.info(f"Автономный режим остановлен для пользователя {user_id}")

    async def _run_autonomous_tasks(self, user_id: int):
        """Выполнение автономных задач"""
        try:
            while True:
                # Проверка календаря на предстоящие встречи
                await self._check_upcoming_meetings(user_id)

                # Проверка важных email
                await self._check_important_emails(user_id)

                # Мониторинг здоровья и продуктивности
                await self._monitor_health_productivity(user_id)

                # Планирование задач
                await self._plan_tasks(user_id)

                # Пауза 30 минут
                await asyncio.sleep(1800)

        except asyncio.CancelledError:
            logger.info(f"Автономные задачи остановлены для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка в автономных задачах: {e}")

    async def _check_upcoming_meetings(self, user_id: int):
        """Проверка предстоящих встреч"""
        try:
            zoom_client = self.components.get('zoom_client')
            if zoom_client:
                meetings = await zoom_client.list_meetings()
                upcoming = [m for m in meetings if m.get('status') == 'scheduled']
                if upcoming:
                    logger.info(f"Найдено {len(upcoming)} предстоящих встреч для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка проверки встреч: {e}")

    async def _check_important_emails(self, user_id: int):
        """Проверка важных email"""
        try:
            email_service = self.components.get('email_triage')
            if email_service:
                # Здесь будет вызов метода проверки важных email
                logger.info(f"Проверка email для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка проверки email: {e}")

    async def _monitor_health_productivity(self, user_id: int):
        """Мониторинг здоровья и продуктивности"""
        try:
            health_service = self.components.get('health_nudges')
            if health_service:
                # Здесь будет вызов метода мониторинга здоровья
                logger.info(f"Мониторинг здоровья для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка мониторинга здоровья: {e}")

    async def _plan_tasks(self, user_id: int):
        """Планирование задач"""
        try:
            focus_service = self.components.get('daily_focus')
            if focus_service:
                # Здесь будет вызов метода планирования задач
                logger.info(f"Планирование задач для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка планирования задач: {e}")

    def get_available_services(self) -> List[str]:
        """Получить список доступных сервисов"""
        return list(self.components.keys())

    async def get_health_status(self) -> Dict[str, Any]:
        """Получить статус здоровья всех компонентов"""
        health = {
            'overall_status': 'healthy',
            'components': {},
            'circuit_breakers': {},
            'timestamp': datetime.now().isoformat()
        }

        # Проверяем основные компоненты
        components_to_check = {
            'rag_manager': self.rag_manager,
            'memory_palace': self.memory_palace,
            'vision_client': self.vision_client
        }

        for component_name, component in components_to_check.items():
            try:
                if component is None:
                    health['components'][component_name] = {'status': 'not_available'}
                elif hasattr(component, 'get_stats'):
                    stats = component.get_stats()
                    health['components'][component_name] = {'status': 'healthy', 'stats': stats}
                elif hasattr(component, 'get_usage_stats'):
                    stats = await component.get_usage_stats()
                    health['components'][component_name] = {'status': 'healthy', 'stats': stats}
                else:
                    health['components'][component_name] = {'status': 'healthy'}
            except Exception as e:
                health['components'][component_name] = {'status': 'error', 'error': str(e)}
                health['overall_status'] = 'degraded'

        # Проверяем circuit breakers
        circuit_breakers = {
            'llm_circuit_breaker': self.llm_circuit_breaker,
            'vision_circuit_breaker': self.vision_circuit_breaker,
            'stt_circuit_breaker': self.stt_circuit_breaker
        }

        for cb_name, cb in circuit_breakers.items():
            health['circuit_breakers'][cb_name] = {
                'state': cb.state,
                'failure_count': cb.failure_count,
                'last_failure_time': cb.last_failure_time
            }
            if cb.state == 'open':
                health['overall_status'] = 'degraded'

        # Проверяем основные сервисы
        for service_name, service in self.components.items():
            try:
                if hasattr(service, 'get_status'):
                    service_status = service.get_status()
                    health['components'][f'service_{service_name}'] = service_status
                else:
                    health['components'][f'service_{service_name}'] = {'status': 'unknown'}
            except Exception as e:
                health['components'][f'service_{service_name}'] = {'status': 'error', 'error': str(e)}
                health['overall_status'] = 'degraded'

        return health

    def get_system_metrics(self) -> Dict[str, Any]:
        """Получить системные метрики"""
        import psutil
        import os

        metrics = {
            'timestamp': datetime.now().isoformat(),
            'process': {
                'pid': os.getpid(),
                'cpu_percent': psutil.Process().cpu_percent(),
                'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024,
                'threads': psutil.Process().num_threads()
            },
            'system': {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            },
            'orchestrator': {
                'active_tasks': len(self.active_tasks),
                'meeting_sessions': len(self.meeting_sessions),
                'initialized': self.initialized
            }
        }

        # Добавляем метрики компонентов
        if self.memory_palace and hasattr(self.memory_palace, 'get_memory_stats'):
            try:
                memory_stats = self.memory_palace.get_memory_stats()
                metrics['memory_palace'] = memory_stats
            except Exception as e:
                metrics['memory_palace'] = {'error': str(e)}

        if self.rag_manager and hasattr(self.rag_manager, 'index') and hasattr(self.rag_manager.index, 'get_stats'):
            try:
                rag_stats = self.rag_manager.index.get_stats()
                metrics['rag_index'] = rag_stats
            except Exception as e:
                metrics['rag_index'] = {'error': str(e)}

        return metrics

    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Получить статус сервиса"""
        if service_name in self.components:
            return {
                'name': service_name,
                'status': 'active',
                'type': type(self.components[service_name]).__name__
            }
        return {
            'name': service_name,
            'status': 'not_available'
        }

    async def _init_zoom_integration(self):
        """Инициализация Zoom интеграции"""
        try:
            from app.services.zoom_api import zoom_client
            from app.services.meeting_policy import MeetingSession, MeetingProfile
            
            self.components['zoom_client'] = zoom_client
            self.components['meeting_policy'] = MeetingSession
            self.components['meeting_profile'] = MeetingProfile
            
            logger.info("Zoom интеграция инициализирована")
        except ImportError as e:
            logger.warning(f"Zoom интеграция недоступна: {e}")
            self.components['zoom_client'] = None

    async def on_zoom_webhook(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка webhook событий Zoom"""
        try:
            event_type = event.get("event")
            meeting_id = event.get("payload", {}).get("object", {}).get("id")
            
            if not meeting_id:
                return {"status": "error", "message": "No meeting ID in event"}
            
            if event_type == "meeting.started":
                await self._handle_meeting_started(meeting_id, event)
            elif event_type == "meeting.ended":
                await self._handle_meeting_ended(meeting_id, event)
            elif event_type == "recording.completed":
                await self._handle_recording_completed(meeting_id, event)
            
            return {"status": "success", "event": event_type, "meeting_id": meeting_id}
            
        except Exception as e:
            logger.error(f"Ошибка обработки Zoom webhook: {e}")
            return {"status": "error", "message": str(e)}

    async def _handle_meeting_started(self, meeting_id: str, event: Dict[str, Any]):
        """Обработка начала встречи"""
        from app.services.meeting_policy import MeetingSession, MeetingProfile
        
        # Создаем сессию встречи
        session = MeetingSession(meeting_id, MeetingProfile.NOTE_TAKER)
        self.meeting_sessions[meeting_id] = session
        session.start_time = datetime.now()
        
        logger.info(f"Встреча {meeting_id} началась, создана сессия")

    async def _handle_meeting_ended(self, meeting_id: str, event: Dict[str, Any]):
        """Обработка окончания встречи"""
        session = self.meeting_sessions.get(meeting_id)
        if not session:
            return
        
        session.end_time = datetime.now()
        
        # Получаем стенограмму и создаем резюме
        await self._create_meeting_summary(meeting_id, session)
        
        # Удаляем сессию
        del self.meeting_sessions[meeting_id]
        logger.info(f"Встреча {meeting_id} завершена, сессия удалена")

    async def _handle_recording_completed(self, meeting_id: str, event: Dict[str, Any]):
        """Обработка завершения записи"""
        session = self.meeting_sessions.get(meeting_id)
        if session:
            # Обрабатываем запись если нужно
            await self._process_meeting_recording(meeting_id, session)

    async def _create_meeting_summary(self, meeting_id: str, session):
        """Создание резюме встречи через Yandex LLM"""
        try:
            zoom_client = self.components.get('zoom_client')
            if not zoom_client:
                return
            
            # Получаем стенограмму
            transcript = await zoom_client.get_transcript(meeting_id)
            
            # Если нет стенограммы, пытаемся получить через STT
            if not transcript:
                logger.info(f"Стенограмма недоступна для встречи {meeting_id}, пытаемся STT fallback")
                transcript = await self._get_transcript_via_stt(meeting_id, zoom_client)
            
            if not transcript:
                logger.warning(f"Не удалось получить стенограмму для встречи {meeting_id}")
                return
            
            # Создаем резюме через LLM
            summary_prompt = f"""
            Сделай итоги встречи: цели, ключевые решения, договоренности, риски, явные next steps с владельцами и дедлайнами. Будь лаконичен.
            
            Стенограмма:
            {transcript}
            """
            
            summary = await complete_text(summary_prompt)
            
            # Если включен перевод, переводим
            if settings.yandex_translate_enabled:
                from app.services.yandex_translate import translate_text
                translated_summary = await translate_text(summary, target_lang="en")
                summary = f"🇷🇺 {summary}\n\n🇺🇸 {translated_summary}"
            
            # Сохраняем резюме
            await self._save_meeting_summary(meeting_id, summary, session)
            
            logger.info(f"Резюме встречи {meeting_id} создано")
            
        except Exception as e:
            logger.error(f"Ошибка создания резюме встречи {meeting_id}: {e}")

    async def _get_transcript_via_stt(self, meeting_id: str, zoom_client) -> Optional[str]:
        """Получение стенограммы через STT fallback"""
        import tempfile
        import os
        import httpx

        try:
            # Получаем файлы записи
            recording_files = await zoom_client.get_recording_files(meeting_id)
            if not recording_files:
                logger.info(f"Нет файлов записи для встречи {meeting_id}")
                return None

            # Ищем аудио файлы (предпочитаем M4A, затем MP3, затем WAV)
            audio_files = [f for f in recording_files if f.get('file_type') in ['M4A', 'MP3', 'WAV']]
            if not audio_files:
                logger.info(f"Нет аудио файлов для STT обработки встречи {meeting_id}")
                return None

            # Сортируем по предпочтению формата
            format_priority = {'M4A': 0, 'WAV': 1, 'MP3': 2}
            audio_files.sort(key=lambda x: format_priority.get(x.get('file_type', 'MP3'), 3))
            audio_file = audio_files[0]

            logger.info(f"Обрабатываем аудио файл {audio_file.get('file_name')} через STT")

            # Скачиваем файл записи
            download_url = audio_file.get('download_url')
            if not download_url:
                logger.warning(f"Нет URL для скачивания файла {audio_file.get('file_name')}")
                return None

            # Скачиваем с авторизацией
            headers = {"Authorization": f"Bearer {await zoom_client._get_access_token()}"}

            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 минут таймаут для больших файлов
                response = await client.get(download_url, headers=headers)
                response.raise_for_status()
                audio_data = response.content

            if not audio_data:
                logger.warning(f"Пустые данные аудио файла {audio_file.get('file_name')}")
                return None

            logger.info(f"Скачан аудио файл: {len(audio_data)} байт")

            # Сохраняем во временный файл
            file_ext = audio_file.get('file_type', 'M4A').lower()
            with tempfile.NamedTemporaryFile(suffix=f'.{file_ext}', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_audio_path = temp_file.name

            try:
                # Конвертируем в WAV если нужно (Yandex STT лучше работает с WAV)
                wav_path = temp_audio_path
                if file_ext != 'wav':
                    wav_path = await self._convert_audio_to_wav(temp_audio_path, file_ext)
                    if not wav_path:
                        logger.warning(f"Не удалось конвертировать {file_ext} в WAV")
                        return None

                # Обрабатываем через Yandex STT с circuit breaker
                try:
                    transcript = await self.stt_circuit_breaker.call(
                        self._process_audio_with_stt,
                        wav_path
                    )
                except Exception as e:
                    logger.warning(f"STT circuit breaker triggered: {e}")
                    transcript = None

                if transcript:
                    logger.info(f"Получена стенограмма через STT: {len(transcript)} символов")
                    return transcript
                else:
                    logger.warning("STT не вернул стенограмму")
                    return None

            finally:
                # Очищаем временные файлы
                try:
                    os.unlink(temp_audio_path)
                    if wav_path != temp_audio_path:
                        os.unlink(wav_path)
                except Exception as e:
                    logger.warning(f"Ошибка очистки временных файлов: {e}")

        except Exception as e:
            logger.error(f"Ошибка STT fallback для встречи {meeting_id}: {e}")
            return None

    async def _convert_audio_to_wav(self, input_path: str, input_format: str) -> Optional[str]:
        """Конвертация аудио в WAV формат"""
        import ffmpeg
        import tempfile
        import os

        try:
            # Проверяем наличие ffmpeg
            try:
                import subprocess
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning("ffmpeg не установлен, конвертация невозможна")
                return None

            # Создаем временный файл для WAV
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                output_path = temp_wav.name

            # Конвертируем через ffmpeg-python
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(stream, output_path,
                                 acodec='pcm_s16le',  # WAV формат
                                 ar='16000',         # 16kHz sample rate
                                 ac=1)               # mono

            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            logger.info(f"Аудио конвертировано: {input_format} -> WAV")
            return output_path

        except Exception as e:
            logger.error(f"Ошибка конвертации аудио: {e}")
            # Очищаем выходной файл если он был создан
            try:
                if 'output_path' in locals():
                    os.unlink(output_path)
            except:
                pass
            return None

    async def _process_audio_with_stt(self, wav_path: str) -> Optional[str]:
        """Обработка WAV файла через Yandex STT"""
        try:
            from app.services.yandex_stt import recognize_speech

            # Читаем файл
            with open(wav_path, 'rb') as f:
                audio_data = f.read()

            # Разбиваем на чанки если файл большой (Yandex STT имеет лимиты)
            chunk_size = 10 * 1024 * 1024  # 10MB chunks
            if len(audio_data) > chunk_size:
                logger.info("Файл большой, разбиваем на чанки для STT")
                return await self._process_audio_chunks(audio_data, chunk_size)
            else:
                # Обрабатываем одним чанком
                transcript = await recognize_speech(
                    audio_data=audio_data,
                    format='lpcm',  # WAV format for Yandex
                    language='ru-RU'  # Можно сделать configurable
                )

                return transcript

        except Exception as e:
            logger.error(f"Ошибка обработки аудио через STT: {e}")
            return None

    async def _process_audio_chunks(self, audio_data: bytes, chunk_size: int) -> Optional[str]:
        """Обработка больших аудио файлов по чанкам"""
        try:
            from app.services.yandex_stt import recognize_speech

            transcripts = []

            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                logger.info(f"Обрабатываем чанк {i // chunk_size + 1}")

                try:
                    chunk_transcript = await recognize_speech(
                        audio_data=chunk,
                        format='lpcm',
                        language='ru-RU'
                    )

                    if chunk_transcript:
                        transcripts.append(chunk_transcript)

                except Exception as e:
                    logger.warning(f"Ошибка обработки чанка {i // chunk_size + 1}: {e}")
                    continue

            # Объединяем все транскрипты
            if transcripts:
                full_transcript = " ".join(transcripts)
                logger.info(f"Собрана полная стенограмма из {len(transcripts)} чанков")
                return full_transcript
            else:
                return None

        except Exception as e:
            logger.error(f"Ошибка обработки чанков: {e}")
            return None

    async def _save_meeting_summary(self, meeting_id: str, summary: str, session):
        """Сохранение резюме встречи"""
        # Сохраняем в файл
        summary_file = f"meeting_summaries/{meeting_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        os.makedirs("meeting_summaries", exist_ok=True)
        
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(f"Встреча: {meeting_id}\n")
            f.write(f"Время: {session.start_time} - {session.end_time}\n")
            f.write(f"Профиль: {session.profile.value}\n")
            f.write(f"Язык: {session.language}\n\n")
            f.write("РЕЗЮМЕ:\n")
            f.write(summary)
        
        logger.info(f"Резюме сохранено в {summary_file}")

    async def _process_meeting_recording(self, meeting_id: str, session):
        """Обработка записи встречи"""
        try:
            zoom_client = self.components.get('zoom_client')
            if not zoom_client:
                return
            
            # Получаем файлы записи
            recording_files = await zoom_client.get_recording_files(meeting_id)
            if not recording_files:
                logger.info(f"Нет файлов записи для встречи {meeting_id}")
                return
            
            # Ищем аудио файлы для STT
            audio_files = [f for f in recording_files if f.get('file_type') in ['M4A', 'MP3', 'WAV']]
            if audio_files:
                logger.info(f"Найдено {len(audio_files)} аудио файлов для обработки")
                # Здесь будет обработка через Yandex STT
        except Exception as e:
            logger.error(f"Ошибка обработки записи встречи {meeting_id}: {e}")

    # Zoom команды для Telegram
    async def zoom_join_meeting(self, user_id: int, meeting_id: str, password: str = None) -> Dict[str, Any]:
        """Присоединение к встрече Zoom"""
        try:
            zoom_client = self.components.get('zoom_client')
            if not zoom_client:
                return {"status": "error", "message": "Zoom client not available"}
            
            join_info = await zoom_client.join_meeting(meeting_id, password)
            return {"status": "success", "data": join_info}
            
        except Exception as e:
            logger.error(f"Ошибка присоединения к встрече {meeting_id}: {e}")
            return {"status": "error", "message": str(e)}

    async def zoom_create_meeting(self, user_id: int, topic: str, **kwargs) -> Dict[str, Any]:
        """Создание встречи Zoom"""
        try:
            zoom_client = self.components.get('zoom_client')
            if not zoom_client:
                return {"status": "error", "message": "Zoom client not available"}
            
            meeting = await zoom_client.create_meeting(topic, **kwargs)
            return {"status": "success", "data": meeting}
            
        except Exception as e:
            logger.error(f"Ошибка создания встречи: {e}")
            return {"status": "error", "message": str(e)}

    async def zoom_set_meeting_mode(self, user_id: int, meeting_id: str, mode: str) -> Dict[str, Any]:
        """Установка режима ИИ на встрече"""
        try:
            from app.services.meeting_policy import MeetingProfile
            
            session = self.meeting_sessions.get(meeting_id)
            if not session:
                return {"status": "error", "message": "Meeting session not found"}
            
            # Парсим режим
            profile_map = {
                "silent": MeetingProfile.SILENT,
                "note_taker": MeetingProfile.NOTE_TAKER,
                "cohost": MeetingProfile.COHOST
            }
            
            if mode not in profile_map:
                return {"status": "error", "message": f"Invalid mode: {mode}"}
            
            session.set_profile(profile_map[mode])
            return {"status": "success", "mode": mode}
            
        except Exception as e:
            logger.error(f"Ошибка установки режима встречи: {e}")
            return {"status": "error", "message": str(e)}

    async def zoom_mute_ai(self, user_id: int, meeting_id: str) -> Dict[str, Any]:
        """Заглушить ИИ на встрече"""
        try:
            session = self.meeting_sessions.get(meeting_id)
            if not session:
                return {"status": "error", "message": "Meeting session not found"}
            
            session.mute_ai()
            return {"status": "success", "muted": True}
            
        except Exception as e:
            logger.error(f"Ошибка заглушения ИИ: {e}")
            return {"status": "error", "message": str(e)}

    async def zoom_get_status(self, user_id: int, meeting_id: str = None) -> Dict[str, Any]:
        """Получить статус встреч"""
        try:
            zoom_client = self.components.get('zoom_client')
            if not zoom_client:
                return {"status": "error", "message": "Zoom client not available"}
            
            if meeting_id:
                # Статус конкретной встречи
                session = self.meeting_sessions.get(meeting_id)
                if session:
                    return {
                        "status": "success",
                        "meeting_id": meeting_id,
                        "profile": session.profile.value,
                        "ai_muted": session.ai_muted,
                        "start_time": session.start_time.isoformat() if session.start_time else None
                    }
                else:
                    return {"status": "error", "message": "Meeting session not found"}
            else:
                # Список активных встреч
                active_meetings = []
                for mid, session in self.meeting_sessions.items():
                    active_meetings.append({
                        "meeting_id": mid,
                        "profile": session.profile.value,
                        "ai_muted": session.ai_muted,
                        "start_time": session.start_time.isoformat() if session.start_time else None
                    })
                
                return {"status": "success", "active_meetings": active_meetings}
                
        except Exception as e:
            logger.error(f"Ошибка получения статуса: {e}")
            return {"status": "error", "message": str(e)}

    async def _init_rag_memory(self):
        """Инициализация RAG и Memory Palace"""
        try:
            # Инициализация RAG
            if RAG_AVAILABLE:
                self.rag_manager = RAGManager()
                if self.rag_manager.initialize():
                    logger.info("RAG менеджер инициализирован")
                else:
                    logger.warning("Не удалось инициализировать RAG менеджер")
                    self.rag_manager = None
            else:
                logger.warning("RAG компонент недоступен")

            # Инициализация Memory Palace
            if MEMORY_AVAILABLE:
                self.memory_palace = MemoryPalace()
                logger.info("Memory Palace инициализирован")
            else:
                logger.warning("Memory Palace компонент недоступен")

            # Инициализация Vision
            if VISION_AVAILABLE and settings.vision_enabled:
                self.vision_client = YandexVision()
                logger.info("Yandex Vision инициализирован")
            elif VISION_AVAILABLE and not settings.vision_enabled:
                logger.info("Yandex Vision отключен в настройках")
            else:
                logger.warning("Yandex Vision компонент недоступен")

        except Exception as e:
            logger.error(f"Ошибка инициализации RAG/Memory: {e}")
            self.rag_manager = None
            self.memory_palace = None


# Глобальный экземпляр оркестратора
orchestrator = AIMagaOrchestrator()


async def get_orchestrator() -> AIMagaOrchestrator:
    """Получить инициализированный оркестратор"""
    if not orchestrator.initialized:
        await orchestrator.initialize()
    return orchestrator
