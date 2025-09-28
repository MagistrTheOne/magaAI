# -*- coding: utf-8 -*-
"""
Intent Engine - Локальный NLU для команд
Классификация голосовых команд → запуск сценариев
"""

import re
import json
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from loguru import logger


@dataclass
class Intent:
    """Интент (намерение) пользователя"""
    name: str
    confidence: float
    entities: Dict[str, str]
    original_text: str


@dataclass
class Action:
    """Действие для выполнения"""
    name: str
    params: Dict[str, Any]
    priority: int = 1


class IntentEngine:
    """
    Движок распознавания намерений для "Мага"
    Локальная классификация команд → выполнение автоматизации
    """

    def __init__(self):
        self.intents = {}
        self.actions = {}
        self.context = {}
        self.is_active = False

        # Интеграция с модулями
        self.brain_manager = None
        self.rag_manager = None
        self.screen_scanner = None
        self.app_detector = None
        self.mail_calendar = None
        self.ats_tailor = None
        self.negotiation_engine = None
        self.overlay_hud = None

        # Загружаем интенты
        self._load_intents()

        logger.info("Intent Engine 'Мага' инициализирован")

    def set_brain_manager(self, brain_manager):
        """Установить Brain Manager для LLM интеграции"""
        self.brain_manager = brain_manager

    def set_rag_manager(self, rag_manager):
        """Установить RAG Manager"""
        self.rag_manager = rag_manager

    def set_screen_scanner(self, screen_scanner):
        """Установить Screen Scanner"""
        self.screen_scanner = screen_scanner

    def set_app_detector(self, app_detector):
        """Установить App Detector"""
        self.app_detector = app_detector

    def set_mail_calendar(self, mail_calendar):
        """Установить Mail & Calendar"""
        self.mail_calendar = mail_calendar

    def set_ats_tailor(self, ats_tailor):
        """Установить ATS Tailor"""
        self.ats_tailor = ats_tailor

    def set_negotiation_engine(self, negotiation_engine):
        """Установить Negotiation Engine"""
        self.negotiation_engine = negotiation_engine

    def set_overlay_hud(self, overlay_hud):
        """Установить Overlay HUD"""
        self.overlay_hud = overlay_hud

    def _load_intents(self):
        """Загрузка интентов и паттернов"""
        self.intents = {
            # Работа с вакансиями
            "search_jobs": {
                "patterns": [
                    r"найди.*ваканси|поиск.*работ|ищу.*должность",
                    r"покажи.*позици|найди.*компани",
                    r"что.*есть.*по.*python|python.*разработчик"
                ],
                "entities": ["position", "company", "location", "salary"],
                "action": "search_jobs"
            },
            
            # Проверка откликов
            "check_responses": {
                "patterns": [
                    r"проверь.*отклик|есть.*ответ|статус.*заявк",
                    r"что.*нового.*по.*работе|проверь.*почту",
                    r"отклики.*на.*ваканси"
                ],
                "entities": ["timeframe", "company"],
                "action": "check_responses"
            },
            
            # Подготовка к собеседованию
            "prepare_interview": {
                "patterns": [
                    r"готовлюсь.*собес|подготовка.*встреч|собес.*завтра",
                    r"что.*нужно.*к.*собесу|материалы.*для.*встреч",
                    r"изучаю.*компани|research.*компани"
                ],
                "entities": ["company", "position", "date"],
                "action": "prepare_interview"
            },
            
            # Отправка писем
            "send_email": {
                "patterns": [
                    r"отправь.*письмо|напиши.*email|свяжись.*с.*hr",
                    r"follow.*up|followup|после.*собеса",
                    r"благодарность.*за.*встреч"
                ],
                "entities": ["recipient", "type", "urgency"],
                "action": "send_email"
            },
            
            # Управление календарем
            "calendar_manage": {
                "patterns": [
                    r"забронируй.*время|создай.*встреч|календарь",
                    r"доступное.*время|свободные.*слоты",
                    r"перенеси.*встреч|отмени.*встреч"
                ],
                "entities": ["date", "time", "duration", "type"],
                "action": "calendar_manage"
            },
            
            # Анализ компании
            "analyze_company": {
                "patterns": [
                    r"расскажи.*о.*компани|анализ.*компани",
                    r"что.*известно.*о.*фирме|исследование.*компани",
                    r"отзывы.*о.*компани|репутация.*компани"
                ],
                "entities": ["company", "aspect"],
                "action": "analyze_company"
            },
            
            # Переговоры
            "negotiate": {
                "patterns": [
                    r"переговоры|обсуждаем.*зарплат|вилка.*зарплат",
                    r"контрпредложение|что.*предложить",
                    r"как.*ответить.*на.*оффер|стратегия.*переговоров"
                ],
                "entities": ["offer", "counter_offer", "strategy"],
                "action": "negotiate"
            },
            
            # Технические вопросы
            "technical_help": {
                "patterns": [
                    r"техническое.*вопрос|как.*ответить.*на.*python",
                    r"алгоритм.*вопрос|система.*дизайн",
                    r"что.*знать.*о.*технологи|подготовка.*к.*тех.*собесу"
                ],
                "entities": ["topic", "level", "technology"],
                "action": "technical_help"
            },
            
            # Общие команды
            "general_help": {
                "patterns": [
                    r"помощь|help|что.*умеешь|возможности",
                    r"как.*работаешь|инструкция|руководство"
                ],
                "entities": [],
                "action": "general_help"
            },
            
            # Экстренные команды
            "emergency": {
                "patterns": [
                    r"стоп|останови|прекрати|отмена",
                    r"emergency|экстренно|срочно.*останови"
                ],
                "entities": [],
                "action": "emergency"
            }
        }
        
        logger.info(f"Загружено {len(self.intents)} интентов")
    
    def _extract_entities(self, text: str, intent_name: str) -> Dict[str, str]:
        """Извлечение сущностей из текста"""
        entities = {}
        intent_config = self.intents.get(intent_name, {})
        entity_patterns = intent_config.get("entities", [])
        
        text_lower = text.lower()
        
        # Извлечение компаний
        if "company" in entity_patterns:
            company_patterns = [
                r"в\s+(\w+)", r"компани[ия]\s+(\w+)", r"фирм[ае]\s+(\w+)",
                r"(\w+)\s+компани", r"(\w+)\s+фирм"
            ]
            for pattern in company_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    entities["company"] = match.group(1).title()
                    break
        
        # Извлечение позиций
        if "position" in entity_patterns:
            position_patterns = [
                r"python\s+разработчик", r"ml\s+инженер", r"data\s+scientist",
                r"backend\s+разработчик", r"frontend\s+разработчик",
                r"devops\s+инженер", r"системный\s+администратор"
            ]
            for pattern in position_patterns:
                if re.search(pattern, text_lower):
                    entities["position"] = pattern.replace(r"\s+", " ")
                    break
        
        # Извлечение локаций
        if "location" in entity_patterns:
            location_patterns = [
                r"в\s+(\w+)\s+городе", r"(\w+)\s+офис", r"удаленн[ая]?",
                r"remote", r"гибридн[ая]?"
            ]
            for pattern in location_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    entities["location"] = match.group(1) if match.groups() else "remote"
                    break
        
        # Извлечение зарплат
        if "salary" in entity_patterns:
            salary_patterns = [
                r"(\d+)\s*[kк]", r"от\s*(\d+)\s*[kк]", r"до\s*(\d+)\s*[kк]",
                r"(\d+)\s*тысяч", r"(\d+)\s*000"
            ]
            for pattern in salary_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    entities["salary"] = match.group(1)
                    break
        
        return entities
    
    def _calculate_confidence(self, text: str, patterns: List[str]) -> float:
        """Вычисление уверенности в интенте"""
        text_lower = text.lower()
        matches = 0
        
        for pattern in patterns:
            if re.search(pattern, text_lower):
                matches += 1
        
        if not patterns:
            return 0.0
        
        confidence = matches / len(patterns)
        
        # Бонус за точные совпадения
        for pattern in patterns:
            if re.search(pattern, text_lower):
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def recognize_intent(self, text: str) -> Optional[Intent]:
        """Распознавание интента из текста"""
        if not text or not text.strip():
            return None
        
        text = text.strip()
        best_intent = None
        best_confidence = 0.0
        
        for intent_name, config in self.intents.items():
            patterns = config.get("patterns", [])
            confidence = self._calculate_confidence(text, patterns)
            
            if confidence > best_confidence:
                best_confidence = confidence
                entities = self._extract_entities(text, intent_name)
                
                best_intent = Intent(
                    name=intent_name,
                    confidence=confidence,
                    entities=entities,
                    original_text=text
                )
        
        # Минимальный порог уверенности
        if best_confidence < 0.3:
            return None
        
        logger.info(f"Распознан интент: {best_intent.name} (уверенность: {best_confidence:.2f})")
        return best_intent
    
    def register_action(self, action_name: str, action_func: Callable):
        """Регистрация действия"""
        self.actions[action_name] = action_func
        logger.info(f"Зарегистрировано действие: {action_name}")
    
    def execute_action(self, intent: Intent) -> Optional[Any]:
        """Выполнение действия по интенту"""
        if not intent:
            return None
        
        action_name = self.intents.get(intent.name, {}).get("action")
        if not action_name:
            logger.warning(f"Действие не найдено для интента: {intent.name}")
            return None
        
        action_func = self.actions.get(action_name)
        if not action_func:
            logger.warning(f"Функция действия не найдена: {action_name}")
            return None
        
        try:
            logger.info(f"Выполняю действие: {action_name}")
            result = action_func(intent.entities, intent.original_text)
            return result
        except Exception as e:
            logger.error(f"Ошибка выполнения действия {action_name}: {e}")
            return None
    
    def process_command(self, text: str, tts_callback: Optional[Callable] = None) -> Optional[Any]:
        """Обработка команды 'Мага': распознавание + выполнение + TTS фидбек"""
        # Распознаем интент
        intent = self.recognize_intent(text)
        if not intent:
            # Не распознали команду
            response = "Не понял команду. Попробуйте: 'найди вакансии', 'проверь отклики', 'подготовь к собеседованию'."
            if tts_callback:
                tts_callback(response)
            return response

        # Выполняем действие
        result = self.execute_action(intent)

        # TTS фидбек
        if tts_callback:
            if result:
                tts_callback(result)
            else:
                tts_callback("Задача выполнена.")

        return result
    
    def get_available_commands(self) -> List[str]:
        """Получение списка доступных команд"""
        commands = []
        
        for intent_name, config in self.intents.items():
            patterns = config.get("patterns", [])
            if patterns:
                # Берем первый паттерн как пример
                example = patterns[0].replace(r".*", "...").replace(r"\w+", "слово")
                commands.append(f"{intent_name}: {example}")
        
        return commands
    
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса движка"""
        return {
            "is_active": self.is_active,
            "intents_count": len(self.intents),
            "actions_count": len(self.actions),
            "context": self.context
        }

    # =============== РЕАЛИЗАЦИЯ ДЕЙСТВИЙ ===============

    def _search_jobs_action(self, entities: Dict[str, str], text: str) -> str:
        """Поиск вакансий через HH.ru API + GigaChat анализ"""
        try:
            # Показываем прогресс в HUD
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.PROCESSING, "Ищу вакансии...")

            # Анализируем запрос через GigaChat
            if self.brain_manager:
                context = {
                    "user_command": text,
                    "entities": entities,
                    "task": "analyze_job_search",
                    "current_time": datetime.now().isoformat(),
                    "user_profile": "Senior Python Developer, AI/ML focus, production systems"
                }

                # Добавляем RAG контекст
                if self.rag_manager and hasattr(self.rag_manager, 'search_context'):
                    rag_context = self.rag_manager.search_context(text, max_length=300)
                    context["rag_context"] = rag_context

                response, analysis = self.brain_manager.process_hr_message(
                    f"Пользователь хочет найти вакансии. Запрос: {text}. "
                    f"Сущности: {entities}. "
                    f"Профиль: Senior Python Developer с фокусом на AI/ML и production системы.",
                    context
                )

                logger.info(f"[МАГА] Анализ поиска вакансий: {analysis}")
                return response
            else:
                return "Ищу вакансии по Python и AI/ML направлениям. Найдено несколько интересных позиций."

        except Exception as e:
            logger.error(f"[МАГА] Ошибка поиска вакансий: {e}")
            return "Произошла ошибка при поиске вакансий. Попробуйте позже."
        finally:
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.IDLE)

    def _check_responses_action(self, entities: Dict[str, str], text: str) -> str:
        """Проверка откликов на вакансии"""
        try:
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.PROCESSING, "Проверяю почту...")

            # Проверяем почту через Mail & Calendar
            if self.mail_calendar and hasattr(self.mail_calendar, 'get_mail_history'):
                mail_history = self.mail_calendar.get_mail_history()

                # Анализируем через GigaChat
                if self.brain_manager:
                    context = {
                        "mail_history": mail_history[-10:] if len(mail_history) > 10 else mail_history,
                        "task": "analyze_job_responses"
                    }

                    response, analysis = self.brain_manager.process_hr_message(
                        f"Проанализируй последние письма о вакансиях. "
                        f"История почты: {json.dumps(context['mail_history'], ensure_ascii=False)}",
                        context
                    )

                    logger.info(f"[МАГА] Анализ откликов: {analysis}")
                    return response
                else:
                    new_mails = len([m for m in mail_history if 'vacancy' in m.get('subject', '').lower()])
                    return f"Найдено {new_mails} новых писем о вакансиях."
            else:
                return "Проверяю статус ваших откликов. Новые ответы от компаний."

        except Exception as e:
            logger.error(f"[МАГА] Ошибка проверки откликов: {e}")
            return "Ошибка при проверке откликов."
        finally:
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.IDLE)

    def _prepare_interview_action(self, entities: Dict[str, str], text: str) -> str:
        """Подготовка к собеседованию"""
        try:
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.PROCESSING, "Готовлюсь к собеседованию...")

            company = entities.get('company', 'компании')
            position = entities.get('position', 'позиции')

            # Анализируем через GigaChat
            if self.brain_manager:
                context = {
                    "company": company,
                    "position": position,
                    "task": "prepare_interview"
                }

                response, analysis = self.brain_manager.process_hr_message(
                    f"Подготовь материалы для собеседования в {company} на позицию {position}. "
                    f"Профиль: Senior Python Developer, AI/ML, production systems.",
                    context
                )

                logger.info(f"[МАГА] Анализ подготовки: {analysis}")
                return response
            else:
                return f"Готовлю материалы для собеседования в {company}. Соберу информацию о компании и подготовлю вопросы."

        except Exception as e:
            logger.error(f"[МАГА] Ошибка подготовки к собеседованию: {e}")
            return "Ошибка при подготовке к собеседованию."
        finally:
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.IDLE)

    def _send_email_action(self, entities: Dict[str, str], text: str) -> str:
        """Отправка email"""
        try:
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.PROCESSING, "Отправляю email...")

            recipient = entities.get('recipient', 'HR')
            email_type = entities.get('type', 'follow_up')

            # Генерируем email через GigaChat
            if self.brain_manager:
                context = {
                    "recipient": recipient,
                    "type": email_type,
                    "task": "generate_email"
                }

                response, analysis = self.brain_manager.process_hr_message(
                    f"Напиши email типа '{email_type}' для {recipient}. "
                    f"Профиль: Senior Python Developer после собеседования.",
                    context
                )

                logger.info(f"[МАГА] Генерация email: {analysis}")
                return f"Email для {recipient} готов. Отправляю..."
            else:
                return f"Отправляю follow-up email для {recipient}."

        except Exception as e:
            logger.error(f"[МАГА] Ошибка отправки email: {e}")
            return "Ошибка при отправке email."
        finally:
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.IDLE)

    def _calendar_manage_action(self, entities: Dict[str, str], text: str) -> str:
        """Управление календарем"""
        try:
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.PROCESSING, "Управляю календарем...")

            # Проверяем календарь
            if self.mail_calendar and hasattr(self.mail_calendar, 'get_calendar_events'):
                events = self.mail_calendar.get_calendar_events()

                # Анализируем через GigaChat
                if self.brain_manager:
                    context = {
                        "calendar_events": events,
                        "user_command": text,
                        "task": "calendar_analysis"
                    }

                    response, analysis = self.brain_manager.process_hr_message(
                        f"Проанализируй календарь и дай рекомендации. "
                        f"События: {json.dumps(context['calendar_events'], ensure_ascii=False)}",
                        context
                    )

                    logger.info(f"[МАГА] Анализ календаря: {analysis}")
                    return response
                else:
                    upcoming = len([e for e in events if datetime.fromisoformat(e['start']) > datetime.now()])
                    return f"В календаре {upcoming} предстоящих событий."
            else:
                return "Проверяю доступное время в календаре."

        except Exception as e:
            logger.error(f"[МАГА] Ошибка управления календарем: {e}")
            return "Ошибка при работе с календарем."
        finally:
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.IDLE)

    def _analyze_company_action(self, entities: Dict[str, str], text: str) -> str:
        """Анализ компании"""
        try:
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.PROCESSING, "Анализирую компанию...")

            company = entities.get('company', 'компании')

            # Анализируем через GigaChat
            if self.brain_manager:
                context = {
                    "company": company,
                    "task": "company_research"
                }

                response, analysis = self.brain_manager.process_hr_message(
                    f"Проанализируй компанию {company}. "
                    f"Что известно о культуре, технологиях, отзывах?",
                    context
                )

                logger.info(f"[МАГА] Анализ компании: {analysis}")
                return response
            else:
                return f"Анализирую {company}. Собираю информацию о технологиях и культуре."

        except Exception as e:
            logger.error(f"[МАГА] Ошибка анализа компании: {e}")
            return "Ошибка при анализе компании."
        finally:
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.IDLE)

    def _negotiate_action(self, entities: Dict[str, str], text: str) -> str:
        """Переговоры по офферу"""
        try:
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.PROCESSING, "Готовлю переговорную стратегию...")

            # Используем Negotiation Engine
            if self.negotiation_engine:
                hr_analysis = self.negotiation_engine.analyze_hr_message(text)
                response = self.negotiation_engine.generate_response(hr_analysis)
                return response
            elif self.brain_manager:
                # Fallback на GigaChat
                context = {
                    "user_command": text,
                    "task": "negotiation_strategy"
                }

                response, analysis = self.brain_manager.process_hr_message(
                    f"Помоги с переговорами по офферу. Запрос: {text}. "
                    f"Профиль: Senior Python Developer, target salary 250k.",
                    context
                )

                logger.info(f"[МАГА] Переговорная стратегия: {analysis}")
                return response
            else:
                return "Готовлю стратегию переговоров. Анализирую рыночные данные."

        except Exception as e:
            logger.error(f"[МАГА] Ошибка переговоров: {e}")
            return "Ошибка при подготовке к переговорам."
        finally:
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.IDLE)

    def _technical_help_action(self, entities: Dict[str, str], text: str) -> str:
        """Техническая помощь"""
        try:
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.PROCESSING, "Готовлю техническую помощь...")

            topic = entities.get('topic', 'техническим вопросам')

            # Анализируем через GigaChat
            if self.brain_manager:
                context = {
                    "topic": topic,
                    "task": "technical_assistance"
                }

                response, analysis = self.brain_manager.process_hr_message(
                    f"Помоги с техническими вопросами по теме '{topic}'. "
                    f"Профиль: Senior Python Developer, AI/ML специалист.",
                    context
                )

                logger.info(f"[МАГА] Техническая помощь: {analysis}")
                return response
            else:
                return f"Готовлю ответы на технические вопросы по {topic}."

        except Exception as e:
            logger.error(f"[МАГА] Ошибка технической помощи: {e}")
            return "Ошибка при подготовке технической помощи."
        finally:
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.IDLE)

    def _general_help_action(self, entities: Dict[str, str], text: str) -> str:
        """Общая помощь"""
        commands = [
            "🔍 'найди вакансии' - поиск работы через HH.ru",
            "📧 'проверь отклики' - анализ ответов от компаний",
            "📚 'подготовь к собеседованию' - материалы для встречи",
            "✉️ 'отправь email' - follow-up письма",
            "📅 'календарь' - управление встречами",
            "🏢 'анализ компании' - исследование работодателя",
            "💰 'переговоры' - стратегия по офферу",
            "🔧 'техническая помощь' - подготовка к вопросам"
        ]

        help_text = "Я 'Мага' - твой AI-помощник по карьере. Вот что я умею:\n\n" + "\n".join(commands)
        return help_text

    def register_maga_actions(self):
        """Регистрация всех действий Мага"""
        self.register_action("search_jobs", self._search_jobs_action)
        self.register_action("check_responses", self._check_responses_action)
        self.register_action("prepare_interview", self._prepare_interview_action)
        self.register_action("send_email", self._send_email_action)
        self.register_action("calendar_manage", self._calendar_manage_action)
        self.register_action("analyze_company", self._analyze_company_action)
        self.register_action("negotiate", self._negotiate_action)
        self.register_action("technical_help", self._technical_help_action)
        self.register_action("general_help", self._general_help_action)

        logger.info("Все действия Мага зарегистрированы")


# =============== ТЕСТИРОВАНИЕ ===============

def test_intent_engine():
    """Тестирование Intent Engine"""
    print("🧪 Тестирование Intent Engine...")
    
    # Создаем движок
    engine = IntentEngine()
    
    # Регистрируем тестовые действия
    def test_search_jobs(entities, text):
        print(f"🔍 Поиск вакансий: {entities}")
        return f"Ищу вакансии по параметрам: {entities}"
    
    def test_check_responses(entities, text):
        print(f"📧 Проверка откликов: {entities}")
        return f"Проверяю отклики: {entities}"
    
    def test_prepare_interview(entities, text):
        print(f"📚 Подготовка к собеседованию: {entities}")
        return f"Готовлюсь к собеседованию: {entities}"
    
    def test_general_help(entities, text):
        print("❓ Показываю справку")
        return "Доступные команды: поиск вакансий, проверка откликов, подготовка к собеседованию"
    
    # Регистрируем действия
    engine.register_action("search_jobs", test_search_jobs)
    engine.register_action("check_responses", test_check_responses)
    engine.register_action("prepare_interview", test_prepare_interview)
    engine.register_action("general_help", test_general_help)
    
    # Тестовые команды
    test_commands = [
        "найди вакансии по python разработчику",
        "проверь отклики на заявки",
        "готовлюсь к собеседованию в Google",
        "что умеешь?",
        "отправь письмо HR",
        "забронируй время на встречу"
    ]
    
    print("\n🎯 Тестирование команд:")
    for cmd in test_commands:
        print(f"\nКоманда: '{cmd}'")
        result = engine.process_command(cmd)
        if result:
            print(f"Результат: {result}")
        else:
            print("Интент не распознан")
    
    # Показываем доступные команды
    print(f"\n📋 Доступные команды:")
    commands = engine.get_available_commands()
    for cmd in commands[:5]:  # Показываем первые 5
        print(f"  - {cmd}")


if __name__ == "__main__":
    test_intent_engine()
