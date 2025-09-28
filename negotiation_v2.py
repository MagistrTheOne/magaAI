# -*- coding: utf-8 -*-
"""
Negotiation v2 Module
Переговорные тактики и A/B фразы для автономных переговоров
"""

import random
import time
from typing import List, Dict, Optional, Tuple
from enum import Enum
import json


class NegotiationTactic(Enum):
    """Тактики переговоров"""
    AGGRESSIVE = "aggressive"
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    ANALYTICAL = "analytical"
    COLLABORATIVE = "collaborative"


class NegotiationContext(Enum):
    """Контекст переговоров"""
    SALARY = "salary"
    BENEFITS = "benefits"
    LOCATION = "location"
    REMOTE = "remote"
    EQUITY = "equity"
    BONUS = "bonus"
    VACATION = "vacation"
    START_DATE = "start_date"


class NegotiationEngine:
    """
    Движок переговоров с тактиками и A/B тестированием
    """
    
    def __init__(self, 
                 base_salary: int = 200000,
                 target_salary: int = 250000,
                 min_acceptable: int = 180000):
        """
        Args:
            base_salary: Базовая зарплата
            target_salary: Целевая зарплата
            min_acceptable: Минимально приемлемая зарплата
        """
        self.base_salary = base_salary
        self.target_salary = target_salary
        self.min_acceptable = min_acceptable
        
        # Состояние переговоров
        self.current_tactic = NegotiationTactic.PROFESSIONAL
        self.negotiation_history = []
        self.counter_offers = []
        self.hr_responses = []
        
        # A/B тестирование
        self.ab_tests = {}
        self.ab_results = {}
        
        # Инициализация фраз
        self._initialize_phrases()
        
    def _initialize_phrases(self):
        """Инициализация фраз для переговоров"""
        self.phrases = {
            NegotiationTactic.AGGRESSIVE: {
                NegotiationContext.SALARY: [
                    "Это ниже рыночной ставки. У меня есть предложения от 220k.",
                    "Слушайте, у меня есть еще 3 собеседования на этой неделе.",
                    "Время дорого. Давайте к делу - какая реальная вилка?",
                    "Я рассматриваю несколько предложений. Что у вас уникального?",
                    "Это несерьезно. Давайте поговорим о реальных цифрах."
                ],
                NegotiationContext.BENEFITS: [
                    "А что с equity? Stock options?",
                    "Медицинская страховка покрывает семью?",
                    "Есть ли 401k matching?",
                    "А бонусы? Performance bonus?",
                    "Что с профессиональным развитием? Конференции, курсы?"
                ],
                NegotiationContext.REMOTE: [
                    "Удаленка - это не опция, а требование.",
                    "Я работаю только remote. Это принципиально.",
                    "Офис - это прошлый век. Давайте о гибкости.",
                    "Сколько дней в неделю можно работать из дома?",
                    "Есть ли budget на home office setup?"
                ]
            },
            NegotiationTactic.PROFESSIONAL: {
                NegotiationContext.SALARY: [
                    "Интересно. А какая вилка у вас в голове?",
                    "Давайте поговорим о компенсации. Что вы готовы предложить?",
                    "Хм, это ниже рыночной. У меня есть предложения от 180k.",
                    "Отлично! А есть ли equity?",
                    "Спасибо, это уже ближе к реальности."
                ],
                NegotiationContext.BENEFITS: [
                    "А какая у вас система бенефитов?",
                    "Интересно. А как вы видите развитие команды?",
                    "Понятно. А какие у вас планы на AI/ML?",
                    "А бонусы? Медицинская страховка?",
                    "Что с профессиональным развитием?"
                ],
                NegotiationContext.REMOTE: [
                    "А какая у вас политика по remote work?",
                    "Интересно. А как вы видите гибкость рабочего места?",
                    "Понятно. А какие у вас планы по гибридной модели?",
                    "Сколько дней в неделю можно работать из дома?",
                    "Есть ли budget на home office setup?"
                ]
            },
            NegotiationTactic.FRIENDLY: {
                NegotiationContext.SALARY: [
                    "Отлично! А какая вилка у вас в голове?",
                    "Давайте поговорим о компенсации. Что вы готовы предложить?",
                    "Хм, это ниже рыночной. У меня есть предложения от 180k.",
                    "Отлично! А есть ли equity?",
                    "Спасибо, это уже ближе к реальности."
                ],
                NegotiationContext.BENEFITS: [
                    "А какая у вас система бенефитов?",
                    "Интересно. А как вы видите развитие команды?",
                    "Понятно. А какие у вас планы на AI/ML?",
                    "А бонусы? Медицинская страховка?",
                    "Что с профессиональным развитием?"
                ],
                NegotiationContext.REMOTE: [
                    "А какая у вас политика по remote work?",
                    "Интересно. А как вы видите гибкость рабочего места?",
                    "Понятно. А какие у вас планы по гибридной модели?",
                    "Сколько дней в неделю можно работать из дома?",
                    "Есть ли budget на home office setup?"
                ]
            }
        }
        
    def analyze_hr_message(self, message: str) -> Dict:
        """Анализ сообщения HR"""
        analysis = {
            'context': self._detect_context(message),
            'sentiment': self._detect_sentiment(message),
            'salary_mentioned': self._extract_salary(message),
            'benefits_mentioned': self._extract_benefits(message),
            'urgency': self._detect_urgency(message),
            'tone': self._detect_tone(message)
        }
        
        return analysis
        
    def _detect_context(self, message: str) -> NegotiationContext:
        """Определение контекста переговоров"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['salary', 'compensation', 'pay', 'зарплата', 'компенсация']):
            return NegotiationContext.SALARY
        elif any(word in message_lower for word in ['benefits', 'insurance', 'бенефиты', 'страховка']):
            return NegotiationContext.BENEFITS
        elif any(word in message_lower for word in ['remote', 'work from home', 'удаленно', 'удаленная работа']):
            return NegotiationContext.REMOTE
        elif any(word in message_lower for word in ['equity', 'stock', 'опционы', 'акции']):
            return NegotiationContext.EQUITY
        elif any(word in message_lower for word in ['bonus', 'бонус']):
            return NegotiationContext.BONUS
        elif any(word in message_lower for word in ['vacation', 'отпуск', 'holiday']):
            return NegotiationContext.VACATION
        elif any(word in message_lower for word in ['start date', 'дата начала', 'когда начать']):
            return NegotiationContext.START_DATE
        else:
            return NegotiationContext.SALARY  # По умолчанию
            
    def _detect_sentiment(self, message: str) -> str:
        """Определение тональности сообщения"""
        positive_words = ['great', 'excellent', 'wonderful', 'amazing', 'отлично', 'прекрасно', 'замечательно']
        negative_words = ['unfortunately', 'sorry', 'can\'t', 'cannot', 'к сожалению', 'извините', 'не можем']
        
        message_lower = message.lower()
        
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
            
    def _extract_salary(self, message: str) -> Optional[int]:
        """Извлечение упомянутой зарплаты"""
        import re
        
        salary_patterns = [
            r'\$?(\d{1,3}(?:,\d{3})*(?:k|000)?)',
            r'(\d+)\s*(?:k|thousand|тысяч)',
            r'от\s*(\d+)\s*до\s*(\d+)'
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                try:
                    salary = int(match.group(1).replace(',', '').replace('k', '000'))
                    return salary
                except ValueError:
                    continue
                    
        return None
        
    def _extract_benefits(self, message: str) -> List[str]:
        """Извлечение упомянутых бенефитов"""
        benefits = []
        message_lower = message.lower()
        
        benefit_keywords = {
            'health insurance': ['health', 'medical', 'insurance', 'медицинская', 'страховка'],
            'dental': ['dental', 'стоматологическая'],
            'vision': ['vision', 'глазная'],
            '401k': ['401k', 'retirement', 'пенсия'],
            'vacation': ['vacation', 'pto', 'отпуск'],
            'sick leave': ['sick', 'больничный'],
            'maternity': ['maternity', 'paternity', 'декрет'],
            'gym': ['gym', 'fitness', 'спортзал'],
            'transportation': ['transportation', 'commute', 'транспорт'],
            'food': ['food', 'lunch', 'еда', 'обед']
        }
        
        for benefit, keywords in benefit_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                benefits.append(benefit)
                
        return benefits
        
    def _detect_urgency(self, message: str) -> str:
        """Определение срочности"""
        urgent_words = ['urgent', 'asap', 'immediately', 'срочно', 'немедленно', 'быстро']
        message_lower = message.lower()
        
        if any(word in message_lower for word in urgent_words):
            return 'high'
        else:
            return 'normal'
            
    def _detect_tone(self, message: str) -> str:
        """Определение тона сообщения"""
        formal_words = ['please', 'thank you', 'appreciate', 'пожалуйста', 'спасибо', 'благодарю']
        casual_words = ['hey', 'hi', 'привет', 'давай', 'давайте']
        
        message_lower = message.lower()
        
        formal_count = sum(1 for word in formal_words if word in message_lower)
        casual_count = sum(1 for word in casual_words if word in message_lower)
        
        if formal_count > casual_count:
            return 'formal'
        elif casual_count > formal_count:
            return 'casual'
        else:
            return 'neutral'
            
    def generate_response(self, hr_analysis: Dict) -> str:
        """Генерация ответа на основе анализа HR"""
        context = hr_analysis['context']
        sentiment = hr_analysis['sentiment']
        salary_mentioned = hr_analysis['salary_mentioned']
        
        # Выбираем тактику на основе контекста
        tactic = self._select_tactic(hr_analysis)
        
        # Получаем фразы для контекста и тактики
        if tactic in self.phrases and context in self.phrases[tactic]:
            phrases = self.phrases[tactic][context]
        else:
            # Fallback на профессиональную тактику
            phrases = self.phrases[NegotiationTactic.PROFESSIONAL][context]
            
        # Выбираем фразу на основе A/B тестирования
        selected_phrase = self._select_phrase_with_ab_test(phrases, context, tactic)
        
        # Адаптируем фразу под контекст
        adapted_phrase = self._adapt_phrase_to_context(selected_phrase, hr_analysis)
        
        # Логируем ответ
        self._log_response(adapted_phrase, tactic, context, hr_analysis)
        
        return adapted_phrase
        
    def _select_tactic(self, hr_analysis: Dict) -> NegotiationTactic:
        """Выбор тактики на основе анализа HR"""
        sentiment = hr_analysis['sentiment']
        urgency = hr_analysis['urgency']
        tone = hr_analysis['tone']
        
        # Агрессивная тактика для негативных или срочных ситуаций
        if sentiment == 'negative' or urgency == 'high':
            return NegotiationTactic.AGGRESSIVE
            
        # Профессиональная тактика для формального тона
        elif tone == 'formal':
            return NegotiationTactic.PROFESSIONAL
            
        # Дружелюбная тактика для позитивного тона
        elif sentiment == 'positive' and tone == 'casual':
            return NegotiationTactic.FRIENDLY
            
        # По умолчанию - профессиональная
        else:
            return NegotiationTactic.PROFESSIONAL
            
    def _select_phrase_with_ab_test(self, phrases: List[str], context: NegotiationContext, tactic: NegotiationTactic) -> str:
        """Выбор фразы с A/B тестированием"""
        test_key = f"{context.value}_{tactic.value}"
        
        # Инициализируем A/B тест если нужно
        if test_key not in self.ab_tests:
            self.ab_tests[test_key] = {
                'phrases': phrases,
                'counts': [0] * len(phrases),
                'responses': [0] * len(phrases)
            }
            
        # Выбираем фразу (пока случайно, в будущем - по результатам A/B)
        selected_index = random.randint(0, len(phrases) - 1)
        
        # Обновляем счетчики
        self.ab_tests[test_key]['counts'][selected_index] += 1
        
        return phrases[selected_index]
        
    def _adapt_phrase_to_context(self, phrase: str, hr_analysis: Dict) -> str:
        """Адаптация фразы под контекст"""
        adapted_phrase = phrase
        
        # Добавляем конкретные цифры если есть
        salary_mentioned = hr_analysis['salary_mentioned']
        if salary_mentioned and salary_mentioned < self.min_acceptable:
            adapted_phrase += f" Мой минимум - {self.min_acceptable}k."
        elif salary_mentioned and salary_mentioned < self.target_salary:
            adapted_phrase += f" Я рассматриваю предложения от {self.target_salary}k."
            
        # Добавляем urgency если нужно
        if hr_analysis['urgency'] == 'high':
            adapted_phrase += " Время ограничено."
            
        return adapted_phrase
        
    def _log_response(self, response: str, tactic: NegotiationTactic, context: NegotiationContext, hr_analysis: Dict):
        """Логирование ответа"""
        log_entry = {
            'timestamp': time.time(),
            'response': response,
            'tactic': tactic.value,
            'context': context.value,
            'hr_analysis': hr_analysis
        }
        
        self.negotiation_history.append(log_entry)
        
        # Ограничиваем историю
        if len(self.negotiation_history) > 1000:
            self.negotiation_history = self.negotiation_history[-500:]
            
    def get_negotiation_history(self) -> List[Dict]:
        """Получить историю переговоров"""
        return self.negotiation_history.copy()
        
    def get_ab_test_results(self) -> Dict:
        """Получить результаты A/B тестирования"""
        return self.ab_tests.copy()
        
    def set_tactic(self, tactic: NegotiationTactic):
        """Установить тактику переговоров"""
        self.current_tactic = tactic
        
    def get_current_tactic(self) -> NegotiationTactic:
        """Получить текущую тактику"""
        return self.current_tactic
        
    def clear_history(self):
        """Очистить историю переговоров"""
        self.negotiation_history.clear()
        self.ab_tests.clear()
        self.ab_results.clear()
