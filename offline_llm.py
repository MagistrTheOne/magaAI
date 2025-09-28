# -*- coding: utf-8 -*-
"""
Offline LLM Fallback Module
Локальная LLM как fallback при недоступности GigaChat
"""

import os
import json
import time
import random
from typing import Optional, Dict, List, Any
from pathlib import Path


class OfflineLLM:
    """
    Оффлайн LLM fallback с rule-based логикой
    """

    def __init__(self, model_path: str = "models", fallback_responses_file: str = "fallback_responses.json"):
        """
        Args:
            model_path: Путь к локальным моделям
            fallback_responses_file: Файл с fallback ответами
        """
        self.model_path = Path(model_path)
        self.fallback_responses_file = Path(fallback_responses_file)
        self.model_path.mkdir(exist_ok=True)

        # Состояние
        self.is_available = False
        self.model_loaded = False
        self.model = None

        # Fallback ответы
        self.fallback_responses = self._load_fallback_responses()

        # Инициализация
        self._initialize_offline_llm()

    def _initialize_offline_llm(self):
        """Инициализация оффлайн LLM"""
        try:
            # Сначала пробуем загрузить transformers-based модель
            self._init_transformers_model()
            if self.model_loaded:
                self.is_available = True
                print("[OfflineLLM] Transformers модель загружена")
                return

            # Fallback на llama.cpp
            self._init_llama_cpp_model()
            if self.model_loaded:
                self.is_available = True
                print("[OfflineLLM] llama.cpp модель загружена")
                return

            # Если ничего не загрузилось - используем rule-based fallback
            self.is_available = True  # Rule-based всегда доступен
            print("[OfflineLLM] Используем rule-based fallback")

        except Exception as e:
            print(f"[OfflineLLM] Ошибка инициализации: {e}")
            self.is_available = True  # Rule-based fallback

    def _init_transformers_model(self):
        """Инициализация модели через transformers"""
        try:
            from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM

            # Проверяем наличие модели
            model_name = "microsoft/DialoGPT-small"  # Легкая модель для fallback
            model_file = self.model_path / "dialogpt"

            if not model_file.exists():
                print("[OfflineLLM] Скачиваем DialoGPT модель...")
                # В реальном использовании нужно скачать модель
                # AutoModelForCausalLM.from_pretrained(model_name).save_pretrained(model_file)
                # AutoTokenizer.from_pretrained(model_name).save_pretrained(model_file)
                raise FileNotFoundError("Модель не скачана")

            # Загружаем модель
            self.model = pipeline('text-generation', model=model_file)
            self.model_loaded = True

        except ImportError:
            print("[OfflineLLM] transformers не установлен")
        except Exception as e:
            print(f"[OfflineLLM] Ошибка загрузки transformers модели: {e}")

    def _init_llama_cpp_model(self):
        """Инициализация llama.cpp модели"""
        try:
            from llama_cpp import Llama

            # Проверяем наличие модели
            model_file = self.model_path / "llama-2-7b-chat.gguf"

            if not model_file.exists():
                print("[OfflineLLM] llama.cpp модель не найдена")
                raise FileNotFoundError("Модель не найдена")

            # Загружаем модель
            self.model = Llama(model_path=str(model_file))
            self.model_loaded = True

        except ImportError:
            print("[OfflineLLM] llama-cpp-python не установлен")
        except Exception as e:
            print(f"[OfflineLLM] Ошибка загрузки llama.cpp модели: {e}")

    def _load_fallback_responses(self) -> Dict[str, List[str]]:
        """Загрузка fallback ответов"""
        try:
            if self.fallback_responses_file.exists():
                with open(self.fallback_responses_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Создаем базовые fallback ответы
                return self._create_default_responses()
        except Exception as e:
            print(f"[OfflineLLM] Ошибка загрузки fallback ответов: {e}")
            return self._create_default_responses()

    def _create_default_responses(self) -> Dict[str, List[str]]:
        """Создание базовых fallback ответов"""
        return {
            "greeting": [
                "Здравствуйте! Я готов помочь с вашими вопросами.",
                "Привет! Чем могу быть полезен?",
                "Добрый день! Слушаю вас."
            ],
            "job_search": [
                "Ищу подходящие вакансии по вашему профилю.",
                "Анализирую рынок труда и ищу интересные предложения.",
                "Проверяю актуальные вакансии в вашей сфере."
            ],
            "interview_prep": [
                "Готовлю материалы для собеседования.",
                "Анализирую типичные вопросы и готовлю ответы.",
                "Собираю информацию о компании и требованиях."
            ],
            "negotiation": [
                "Анализирую ситуацию и готовлю стратегию переговоров.",
                "Оцениваю предложение и готовлю контрпредложения.",
                "Изучаю рыночные ставки и готовлю аргументы."
            ],
            "email": [
                "Готовлю профессиональное email.",
                "Составляю follow-up письмо.",
                "Формирую ответ на ваше сообщение."
            ],
            "calendar": [
                "Проверяю ваше расписание.",
                "Ищу свободные слоты для встречи.",
                "Организую ваше время."
            ],
            "company_analysis": [
                "Изучаю информацию о компании.",
                "Анализирую отзывы и культуру организации.",
                "Собираю данные о работодателе."
            ],
            "technical_help": [
                "Готовлю техническую информацию.",
                "Ищу ответы на технические вопросы.",
                "Анализирую технические требования."
            ],
            "error": [
                "Извините, произошла ошибка. Попробуйте переформулировать запрос.",
                "Возникла проблема с обработкой. Давайте попробуем иначе.",
                "Что-то пошло не так. Можете повторить?"
            ],
            "unknown": [
                "Не совсем понял ваш запрос. Можете уточнить?",
                "Мне нужна дополнительная информация для ответа.",
                "Попробуйте перефразировать вопрос."
            ]
        }

    def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Генерация ответа через оффлайн LLM

        Args:
            prompt: Запрос пользователя
            context: Контекст (task, entities, etc.)
        """
        if not self.is_available:
            return "Оффлайн LLM недоступен"

        try:
            # Определяем тип запроса
            intent = self._classify_intent(prompt, context)

            # Генерируем ответ
            if self.model_loaded and self.model:
                return self._generate_with_model(prompt, intent, context)
            else:
                return self._generate_rule_based(prompt, intent, context)

        except Exception as e:
            print(f"[OfflineLLM] Ошибка генерации: {e}")
            return random.choice(self.fallback_responses.get("error", ["Ошибка обработки запроса"]))

    def _classify_intent(self, prompt: str, context: Optional[Dict] = None) -> str:
        """Классификация намерения"""
        prompt_lower = prompt.lower()

        # Ключевые слова для классификации
        intent_keywords = {
            "job_search": ["ваканси", "работ", "позици", "компани", "поиск", "найди"],
            "interview_prep": ["собес", "интервью", "подготов", "встреч", "разговор"],
            "negotiation": ["зарплат", "переговор", "оффер", "компенсаци", "бонус"],
            "email": ["письмо", "email", "напиши", "отправ", "ответ"],
            "calendar": ["календар", "встреч", "время", "расписани", "слот"],
            "company_analysis": ["компани", "отзыв", "культур", "работодател"],
            "technical_help": ["техническ", "код", "алгоритм", "систем", "программирован"],
            "greeting": ["привет", "здравств", "добр", "хай", "hello"]
        }

        for intent, keywords in intent_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                return intent

        return "unknown"

    def _generate_with_model(self, prompt: str, intent: str, context: Optional[Dict] = None) -> str:
        """Генерация ответа с использованием модели"""
        try:
            if hasattr(self.model, 'pipeline') and self.model.pipeline == 'text-generation':
                # Transformers модель
                response = self.model(
                    f"Ответь на запрос: {prompt}",
                    max_length=100,
                    num_return_sequences=1,
                    temperature=0.7
                )[0]['generated_text']

                return response.replace(f"Ответь на запрос: {prompt}", "").strip()

            elif hasattr(self.model, '__call__'):
                # llama.cpp модель
                response = self.model(
                    f"Пользователь: {prompt}\nАссистент:",
                    max_tokens=100,
                    temperature=0.7
                )['choices'][0]['text']

                return response.strip()

            else:
                # Fallback на rule-based
                return self._generate_rule_based(prompt, intent, context)

        except Exception as e:
            print(f"[OfflineLLM] Ошибка модели: {e}")
            return self._generate_rule_based(prompt, intent, context)

    def _generate_rule_based(self, prompt: str, intent: str, context: Optional[Dict] = None) -> str:
        """Rule-based генерация ответа"""
        try:
            # Получаем ответы для данного интента
            responses = self.fallback_responses.get(intent, self.fallback_responses.get("unknown", []))

            if not responses:
                responses = self.fallback_responses["unknown"]

            # Выбираем случайный ответ
            response = random.choice(responses)

            # Адаптируем под контекст
            if context:
                response = self._adapt_response_to_context(response, context)

            return response

        except Exception as e:
            print(f"[OfflineLLM] Ошибка rule-based генерации: {e}")
            return "Извините, не могу обработать запрос прямо сейчас."

    def _adapt_response_to_context(self, response: str, context: Dict) -> str:
        """Адаптация ответа под контекст"""
        try:
            # Добавляем информацию из контекста
            if "company" in context:
                company = context["company"]
                response = response.replace("компании", f"компании {company}")

            if "position" in context:
                position = context["position"]
                response = response.replace("позиции", f"позиции {position}")

            return response

        except Exception:
            return response

    def save_fallback_responses(self):
        """Сохранение fallback ответов"""
        try:
            with open(self.fallback_responses_file, 'w', encoding='utf-8') as f:
                json.dump(self.fallback_responses, f, ensure_ascii=False, indent=2)
            print(f"[OfflineLLM] Fallback ответы сохранены в {self.fallback_responses_file}")
        except Exception as e:
            print(f"[OfflineLLM] Ошибка сохранения: {e}")

    def add_fallback_response(self, intent: str, response: str):
        """Добавление fallback ответа"""
        if intent not in self.fallback_responses:
            self.fallback_responses[intent] = []

        if response not in self.fallback_responses[intent]:
            self.fallback_responses[intent].append(response)

    def get_available_intents(self) -> List[str]:
        """Получение доступных интентов"""
        return list(self.fallback_responses.keys())

    def is_model_loaded(self) -> bool:
        """Проверка, загружена ли модель"""
        return self.model_loaded

    def get_status(self) -> Dict[str, Any]:
        """Получение статуса оффлайн LLM"""
        return {
            "available": self.is_available,
            "model_loaded": self.model_loaded,
            "model_type": type(self.model).__name__ if self.model else "rule-based",
            "fallback_responses_count": sum(len(responses) for responses in self.fallback_responses.values())
        }
