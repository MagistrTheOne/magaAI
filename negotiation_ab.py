# -*- coding: utf-8 -*-
"""
A/B Negotiation - библиотека фраз/тактик + многорукий бандит
"""

import json
import random
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np

try:
    from brain.ai_client import BrainManager
    from memory_palace import MemoryPalace
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Некоторые компоненты недоступны: {e}")
    COMPONENTS_AVAILABLE = False


class NegotiationTactic(Enum):
    """Тактики переговоров"""
    AGGRESSIVE = "aggressive"
    COLLABORATIVE = "collaborative"
    ACCOMMODATING = "accommodating"
    COMPETITIVE = "competitive"
    AVOIDING = "avoiding"


class NegotiationPhase(Enum):
    """Фазы переговоров"""
    OPENING = "opening"
    EXPLORATION = "exploration"
    BARGAINING = "bargaining"
    CLOSING = "closing"


@dataclass
class NegotiationPhrase:
    """Фраза для переговоров"""
    id: str
    text: str
    tactic: NegotiationTactic
    phase: NegotiationPhase
    context: str
    success_rate: float = 0.0
    usage_count: int = 0


@dataclass
class NegotiationResult:
    """Результат переговоров"""
    tactic_used: NegotiationTactic
    phrase_used: str
    success: bool
    salary_achieved: Optional[float] = None
    feedback: str = ""
    timestamp: str = ""


class MultiArmedBandit:
    """
    Многорукий бандит для выбора тактик
    """
    
    def __init__(self, tactics: List[NegotiationTactic]):
        self.tactics = tactics
        self.rewards = {tactic: [] for tactic in tactics}
        self.counts = {tactic: 0 for tactic in tactics}
        self.alpha = 1.0  # Параметр для UCB
        self.beta = 1.0   # Параметр для UCB
    
    def select_tactic(self) -> NegotiationTactic:
        """Выбор тактики с использованием UCB"""
        total_counts = sum(self.counts.values())
        
        if total_counts < len(self.tactics):
            # Если не все тактики попробованы, выбираем случайную
            untried = [t for t in self.tactics if self.counts[t] == 0]
            return random.choice(untried)
        
        # UCB формула
        ucb_values = {}
        for tactic in self.tactics:
            if self.counts[tactic] == 0:
                ucb_values[tactic] = float('inf')
            else:
                avg_reward = np.mean(self.rewards[tactic]) if self.rewards[tactic] else 0
                confidence = np.sqrt(2 * np.log(total_counts) / self.counts[tactic])
                ucb_values[tactic] = avg_reward + self.alpha * confidence
        
        return max(ucb_values, key=ucb_values.get)
    
    def update_reward(self, tactic: NegotiationTactic, reward: float):
        """Обновление награды для тактики"""
        self.rewards[tactic].append(reward)
        self.counts[tactic] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики"""
        stats = {}
        for tactic in self.tactics:
            if self.counts[tactic] > 0:
                stats[tactic.value] = {
                    'count': self.counts[tactic],
                    'avg_reward': np.mean(self.rewards[tactic]),
                    'total_reward': sum(self.rewards[tactic])
                }
            else:
                stats[tactic.value] = {
                    'count': 0,
                    'avg_reward': 0.0,
                    'total_reward': 0.0
                }
        return stats


class NegotiationAB:
    """
    A/B система переговоров
    """
    
    def __init__(self):
        self.logger = logging.getLogger("NegotiationAB")
        
        # Компоненты
        self.brain_manager = None
        self.memory_palace = None
        
        # Тактики и фразы
        self.tactics = list(NegotiationTactic)
        self.phrases = self._load_phrases()
        self.bandit = MultiArmedBandit(self.tactics)
        
        # Результаты
        self.results: List[NegotiationResult] = []
        
        # Инициализация компонентов
        self._init_components()
    
    def _init_components(self):
        """Инициализация компонентов"""
        try:
            if not COMPONENTS_AVAILABLE:
                self.logger.warning("Компоненты недоступны")
                return
            
            # Brain Manager
            self.brain_manager = BrainManager()
            
            # Memory Palace
            self.memory_palace = MemoryPalace()
            
            self.logger.info("Компоненты Negotiation AB инициализированы")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {e}")
    
    def _load_phrases(self) -> List[NegotiationPhrase]:
        """Загрузка фраз для переговоров"""
        phrases = [
            # Агрессивные фразы
            NegotiationPhrase(
                id="agg_001",
                text="Учитывая мой опыт и рыночные ставки, рассчитываю на {salary}",
                tactic=NegotiationTactic.AGGRESSIVE,
                phase=NegotiationPhase.OPENING,
                context="opening_salary"
            ),
            NegotiationPhrase(
                id="agg_002", 
                text="Это ниже рыночной ставки для моей квалификации",
                tactic=NegotiationTactic.AGGRESSIVE,
                phase=NegotiationPhase.BARGAINING,
                context="counter_offer"
            ),
            NegotiationPhrase(
                id="agg_003",
                text="У меня есть другие предложения с более высокой компенсацией",
                tactic=NegotiationTactic.AGGRESSIVE,
                phase=NegotiationPhase.BARGAINING,
                context="leverage"
            ),
            
            # Коллаборативные фразы
            NegotiationPhrase(
                id="collab_001",
                text="Давайте найдем решение, которое устроит обе стороны",
                tactic=NegotiationTactic.COLLABORATIVE,
                phase=NegotiationPhase.EXPLORATION,
                context="collaboration"
            ),
            NegotiationPhrase(
                id="collab_002",
                text="Я готов рассмотреть пакет в целом, не только зарплату",
                tactic=NegotiationTactic.COLLABORATIVE,
                phase=NegotiationPhase.BARGAINING,
                context="total_package"
            ),
            NegotiationPhrase(
                id="collab_003",
                text="Можем ли мы обсудить возможности роста в компании?",
                tactic=NegotiationTactic.COLLABORATIVE,
                phase=NegotiationPhase.EXPLORATION,
                context="growth"
            ),
            
            # Аккомодационные фразы
            NegotiationPhrase(
                id="acc_001",
                text="Понимаю бюджетные ограничения, готов к компромиссу",
                tactic=NegotiationTactic.ACCOMMODATING,
                phase=NegotiationPhase.BARGAINING,
                context="budget_constraints"
            ),
            NegotiationPhrase(
                id="acc_002",
                text="Главное для меня - интересные задачи и команда",
                tactic=NegotiationTactic.ACCOMMODATING,
                phase=NegotiationPhase.EXPLORATION,
                context="motivation"
            ),
            
            # Конкурентные фразы
            NegotiationPhrase(
                id="comp_001",
                text="Мои навыки стоят дороже на рынке",
                tactic=NegotiationTactic.COMPETITIVE,
                phase=NegotiationPhase.BARGAINING,
                context="market_value"
            ),
            NegotiationPhrase(
                id="comp_002",
                text="Это не соответствует моим ожиданиям",
                tactic=NegotiationTactic.COMPETITIVE,
                phase=NegotiationPhase.BARGAINING,
                context="expectations"
            ),
            
            # Избегающие фразы
            NegotiationPhrase(
                id="avoid_001",
                text="Давайте вернемся к этому вопросу позже",
                tactic=NegotiationTactic.AVOIDING,
                phase=NegotiationPhase.EXPLORATION,
                context="delay"
            ),
            NegotiationPhrase(
                id="avoid_002",
                text="Мне нужно время подумать",
                tactic=NegotiationTactic.AVOIDING,
                phase=NegotiationPhase.BARGAINING,
                context="thinking_time"
            )
        ]
        
        return phrases
    
    def select_phrase(self, tactic: NegotiationTactic, phase: NegotiationPhase, context: str = None) -> NegotiationPhrase:
        """Выбор фразы для переговоров"""
        # Фильтруем фразы по тактике и фазе
        candidate_phrases = [
            p for p in self.phrases 
            if p.tactic == tactic and p.phase == phase
        ]
        
        # Если есть контекст, приоритизируем соответствующие фразы
        if context:
            context_phrases = [p for p in candidate_phrases if context in p.context]
            if context_phrases:
                candidate_phrases = context_phrases
        
        if not candidate_phrases:
            # Fallback - берем любую фразу с нужной тактикой
            candidate_phrases = [p for p in self.phrases if p.tactic == tactic]
        
        if not candidate_phrases:
            # Последний fallback - случайная фраза
            candidate_phrases = self.phrases
        
        # Выбираем фразу с лучшим success_rate
        best_phrase = max(candidate_phrases, key=lambda p: p.success_rate)
        return best_phrase
    
    async def generate_negotiation_response(self, context: Dict[str, Any]) -> str:
        """Генерация ответа для переговоров"""
        try:
            # Выбираем тактику
            tactic = self.bandit.select_tactic()
            
            # Определяем фазу переговоров
            phase = self._determine_phase(context)
            
            # Выбираем фразу
            phrase = self.select_phrase(tactic, phase, context.get('context'))
            
            # Генерируем персонализированный ответ
            if self.brain_manager:
                prompt = f"""
                Контекст переговоров: {context.get('situation', '')}
                Текущее предложение: {context.get('current_offer', '')}
                Мои ожидания: {context.get('expected_salary', '')}
                
                Используй тактику: {tactic.value}
                Фаза: {phase.value}
                Базовая фраза: {phrase.text}
                
                Создай персонализированный ответ для переговоров.
                """
                
                response = await self.brain_manager.generate_response(prompt)
                return response
            else:
                # Fallback - используем базовую фразу
                return phrase.text.format(**context)
                
        except Exception as e:
            self.logger.error(f"Ошибка генерации ответа: {e}")
            return "Давайте обсудим условия подробнее"
    
    def _determine_phase(self, context: Dict[str, Any]) -> NegotiationPhase:
        """Определение фазы переговоров"""
        if context.get('is_opening', False):
            return NegotiationPhase.OPENING
        elif context.get('is_exploring', False):
            return NegotiationPhase.EXPLORATION
        elif context.get('is_bargaining', False):
            return NegotiationPhase.BARGAINING
        elif context.get('is_closing', False):
            return NegotiationPhase.CLOSING
        else:
            return NegotiationPhase.EXPLORATION
    
    async def record_result(self, tactic: NegotiationTactic, phrase: str, success: bool, 
                          salary_achieved: float = None, feedback: str = ""):
        """Запись результата переговоров"""
        try:
            result = NegotiationResult(
                tactic_used=tactic,
                phrase_used=phrase,
                success=success,
                salary_achieved=salary_achieved,
                feedback=feedback,
                timestamp=datetime.now().isoformat()
            )
            
            self.results.append(result)
            
            # Обновляем бандит
            reward = 1.0 if success else 0.0
            if salary_achieved:
                # Дополнительная награда за высокую зарплату
                reward += min(salary_achieved / 100000, 0.5)  # Нормализация
            
            self.bandit.update_reward(tactic, reward)
            
            # Обновляем статистику фраз
            for phrase_obj in self.phrases:
                if phrase_obj.text == phrase:
                    phrase_obj.usage_count += 1
                    if success:
                        # Обновляем success_rate
                        current_rate = phrase_obj.success_rate
                        usage_count = phrase_obj.usage_count
                        phrase_obj.success_rate = (current_rate * (usage_count - 1) + 1.0) / usage_count
                    break
            
            # Сохраняем в память
            if self.memory_palace:
                await self.memory_palace.add_memory(
                    content=f"Результат переговоров: {tactic.value} - {'Успех' if success else 'Неудача'}",
                    metadata={
                        'type': 'negotiation_result',
                        'tactic': tactic.value,
                        'success': success,
                        'salary': salary_achieved,
                        'feedback': feedback
                    }
                )
            
            self.logger.info(f"Записан результат: {tactic.value} - {'Успех' if success else 'Неудача'}")
            
        except Exception as e:
            self.logger.error(f"Ошибка записи результата: {e}")
    
    def get_best_tactics(self, limit: int = 3) -> List[Tuple[NegotiationTactic, float]]:
        """Получение лучших тактик"""
        stats = self.bandit.get_statistics()
        sorted_tactics = sorted(
            stats.items(),
            key=lambda x: x[1]['avg_reward'],
            reverse=True
        )
        return [(NegotiationTactic(tactic), data['avg_reward']) for tactic, data in sorted_tactics[:limit]]
    
    def get_best_phrases(self, tactic: NegotiationTactic, limit: int = 5) -> List[NegotiationPhrase]:
        """Получение лучших фраз для тактики"""
        tactic_phrases = [p for p in self.phrases if p.tactic == tactic]
        sorted_phrases = sorted(tactic_phrases, key=lambda p: p.success_rate, reverse=True)
        return sorted_phrases[:limit]
    
    def get_negotiation_analytics(self) -> Dict[str, Any]:
        """Получение аналитики переговоров"""
        if not self.results:
            return {"message": "Нет данных о переговорах"}
        
        total_results = len(self.results)
        successful_results = len([r for r in self.results if r.success])
        success_rate = successful_results / total_results if total_results > 0 else 0
        
        # Статистика по тактикам
        tactic_stats = {}
        for tactic in self.tactics:
            tactic_results = [r for r in self.results if r.tactic_used == tactic]
            if tactic_results:
                tactic_success_rate = len([r for r in tactic_results if r.success]) / len(tactic_results)
                avg_salary = np.mean([r.salary_achieved for r in tactic_results if r.salary_achieved])
                tactic_stats[tactic.value] = {
                    'count': len(tactic_results),
                    'success_rate': tactic_success_rate,
                    'avg_salary': avg_salary
                }
        
        # Средняя зарплата
        salaries = [r.salary_achieved for r in self.results if r.salary_achieved]
        avg_salary = np.mean(salaries) if salaries else 0
        
        return {
            'total_negotiations': total_results,
            'success_rate': success_rate,
            'avg_salary': avg_salary,
            'tactic_stats': tactic_stats,
            'best_tactics': self.get_best_tactics(),
            'bandit_stats': self.bandit.get_statistics()
        }
    
    def format_analytics(self, analytics: Dict[str, Any]) -> str:
        """Форматирование аналитики"""
        text = f"📊 <b>Аналитика переговоров</b>\n\n"
        
        text += f"🎯 Всего переговоров: {analytics.get('total_negotiations', 0)}\n"
        text += f"✅ Успешность: {analytics.get('success_rate', 0):.1%}\n"
        text += f"💰 Средняя зарплата: {analytics.get('avg_salary', 0):,.0f} руб\n\n"
        
        if analytics.get('tactic_stats'):
            text += f"📈 <b>Статистика по тактикам:</b>\n"
            for tactic, stats in analytics['tactic_stats'].items():
                text += f"• {tactic}: {stats['success_rate']:.1%} ({stats['count']} раз)\n"
            text += "\n"
        
        if analytics.get('best_tactics'):
            text += f"🏆 <b>Лучшие тактики:</b>\n"
            for tactic, score in analytics['best_tactics']:
                text += f"• {tactic.value}: {score:.2f}\n"
        
        return text


# Функция для тестирования
async def test_negotiation_ab():
    """Тестирование A/B переговоров"""
    ab = NegotiationAB()
    
    print("🤝 Тестирование A/B переговоров...")
    
    # Симуляция переговоров
    contexts = [
        {
            'situation': 'Первое собеседование',
            'current_offer': '200000',
            'expected_salary': '250000',
            'is_opening': True
        },
        {
            'situation': 'Обсуждение условий',
            'current_offer': '220000',
            'expected_salary': '250000',
            'is_bargaining': True
        }
    ]
    
    for i, context in enumerate(contexts):
        print(f"\nПереговоры {i+1}:")
        response = await ab.generate_negotiation_response(context)
        print(f"Ответ: {response}")
        
        # Симулируем результат
        success = random.random() > 0.3  # 70% успеха
        salary = random.randint(200000, 300000)
        
        await ab.record_result(
            tactic=ab.bandit.select_tactic(),
            phrase="Тестовая фраза",
            success=success,
            salary_achieved=salary if success else None
        )
    
    # Аналитика
    analytics = ab.get_negotiation_analytics()
    print(f"\nАналитика:")
    print(ab.format_analytics(analytics))


if __name__ == "__main__":
    asyncio.run(test_negotiation_ab())
