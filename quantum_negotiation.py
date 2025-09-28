# -*- coding: utf-8 -*-
"""
Quantum Negotiation Engine - параллельные AI стратегии переговоров
"""

import asyncio
import threading
import time
import json
import random
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging


@dataclass
class NegotiationStrategy:
    """Стратегия переговоров"""
    name: str
    style: str  # "soft", "hard", "neutral", "aggressive"
    personality: str  # "professional", "friendly", "analytical"
    risk_level: str  # "low", "medium", "high"
    target_multiplier: float  # 1.1 = +10% к целевой зарплате


@dataclass
class NegotiationResult:
    """Результат переговоров"""
    strategy: NegotiationStrategy
    final_offer: float
    confidence_score: float
    response_chain: List[str]
    execution_time: float
    reasoning: str


@dataclass
class QuantumNegotiationResult:
    """Результат квантовых переговоров"""
    best_result: NegotiationResult
    all_results: List[NegotiationResult]
    recommendation: str
    expected_gain: float
    total_time: float


class QuantumNegotiationEngine:
    """
    Квантовый движок переговоров - запускает несколько AI параллельно
    """

    def __init__(self,
                 brain_manager=None,
                 base_salary: float = 200000,
                 target_salary: float = 250000,
                 max_parallel: int = 3,
                 timeout: int = 60):
        """
        Args:
            brain_manager: Менеджер мозга для AI агентов
            base_salary: Базовая зарплата
            target_salary: Целевая зарплата
            max_parallel: Максимум параллельных агентов
            timeout: Таймаут на переговоры (сек)
        """
        self.brain_manager = brain_manager
        self.base_salary = base_salary
        self.target_salary = target_salary
        self.max_parallel = max_parallel
        self.timeout = timeout

        # Стратегии переговоров
        self.strategies = self._initialize_strategies()

        # История переговоров
        self.negotiation_history = []

        # Логирование
        self.logger = logging.getLogger("QuantumNegotiation")

    def _initialize_strategies(self) -> List[NegotiationStrategy]:
        """Инициализация стратегий переговоров"""
        return [
            # Soft strategies
            NegotiationStrategy("soft_professional", "soft", "professional", "low", 1.05),
            NegotiationStrategy("soft_friendly", "soft", "friendly", "low", 1.08),
            NegotiationStrategy("soft_analytical", "soft", "analytical", "medium", 1.12),

            # Neutral strategies
            NegotiationStrategy("neutral_professional", "neutral", "professional", "medium", 1.15),
            NegotiationStrategy("neutral_balanced", "neutral", "friendly", "medium", 1.18),
            NegotiationStrategy("neutral_data_driven", "neutral", "analytical", "medium", 1.20),

            # Hard strategies
            NegotiationStrategy("hard_professional", "hard", "professional", "high", 1.25),
            NegotiationStrategy("hard_aggressive", "hard", "aggressive", "high", 1.30),
            NegotiationStrategy("hard_maximum", "hard", "analytical", "high", 1.35),
        ]

    def negotiate_quantum(self,
                         hr_message: str,
                         context: Dict = None,
                         progress_callback: Optional[Callable] = None) -> QuantumNegotiationResult:
        """
        Запуск квантовых переговоров - несколько стратегий параллельно
        """
        if context is None:
            context = {}

        start_time = time.time()

        # Выбираем топ стратегий для параллельного запуска
        selected_strategies = self._select_top_strategies()

        self.logger.info(f"Запуск {len(selected_strategies)} параллельных переговоров")

        # Запускаем параллельные переговоры
        results = []
        with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            futures = []

            for i, strategy in enumerate(selected_strategies):
                future = executor.submit(
                    self._negotiate_with_strategy,
                    strategy,
                    hr_message,
                    context.copy(),
                    i
                )
                futures.append(future)

            # Собираем результаты
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=self.timeout)
                    results.append(result)

                    if progress_callback:
                        progress = len(results) / len(selected_strategies)
                        progress_callback(progress, f"Завершена стратегия: {result.strategy.name}")

                except Exception as e:
                    self.logger.error(f"Ошибка в параллельных переговорах: {e}")

        # Анализируем результаты
        quantum_result = self._analyze_results(results, start_time)

        # Сохраняем в историю
        self.negotiation_history.append({
            'timestamp': time.time(),
            'hr_message': hr_message,
            'quantum_result': quantum_result,
            'duration': quantum_result.total_time
        })

        return quantum_result

    def _select_top_strategies(self) -> List[NegotiationStrategy]:
        """Выбор лучших стратегий для запуска"""
        # Для начала берем разнообразные стратегии
        # В будущем можно использовать ML для выбора
        selected = []

        # 1 soft, 1 neutral, 1 hard
        soft_strategies = [s for s in self.strategies if s.style == "soft"]
        neutral_strategies = [s for s in self.strategies if s.style == "neutral"]
        hard_strategies = [s for s in self.strategies if s.style == "hard"]

        if soft_strategies:
            selected.append(random.choice(soft_strategies))
        if neutral_strategies:
            selected.append(random.choice(neutral_strategies))
        if hard_strategies and len(selected) < self.max_parallel:
            selected.append(random.choice(hard_strategies))

        # Если нужно больше - добавляем оставшиеся
        remaining = [s for s in self.strategies if s not in selected]
        while len(selected) < self.max_parallel and remaining:
            selected.append(random.choice(remaining))
            remaining = [s for s in remaining if s not in selected]

        return selected

    def _negotiate_with_strategy(self,
                               strategy: NegotiationStrategy,
                               hr_message: str,
                               context: Dict,
                               agent_id: int) -> NegotiationResult:
        """
        Переговоры с конкретной стратегией
        """
        start_time = time.time()

        # Подготавливаем контекст для стратегии
        strategy_context = context.copy()
        strategy_context.update({
            'strategy': strategy,
            'negotiation_style': strategy.style,
            'personality': strategy.personality,
            'target_salary': self.target_salary * strategy.target_multiplier,
            'risk_level': strategy.risk_level
        })

        response_chain = []
        confidence_score = 0.5  # Начальная уверенность
        final_offer = self.base_salary

        try:
            # Если есть brain_manager - используем AI
            if self.brain_manager:
                # Первый ответ
                response, analysis = self.brain_manager.process_hr_message(
                    hr_message,
                    strategy_context
                )
                response_chain.append(response)

                # Симулируем цепочку переговоров (2-3 раунда)
                for round_num in range(2):
                    # Имитируем ответ HR
                    hr_response = self._simulate_hr_response(response, strategy, round_num)

                    # Наш ответ
                    follow_up_response, follow_up_analysis = self.brain_manager.process_hr_message(
                        hr_response,
                        strategy_context
                    )
                    response_chain.append(follow_up_response)

                    # Обновляем оценку оффера
                    final_offer = self._extract_offer_from_response(follow_up_response, final_offer)

                # Вычисляем финальную уверенность
                confidence_score = self._calculate_confidence(strategy, final_offer)

            else:
                # Fallback - простые ответы
                response_chain = [f"Использую стратегию {strategy.name} для переговоров"]
                confidence_score = 0.3

        except Exception as e:
            self.logger.error(f"Ошибка в стратегии {strategy.name}: {e}")
            response_chain = [f"Ошибка в стратегии {strategy.name}"]
            confidence_score = 0.1

        execution_time = time.time() - start_time

        return NegotiationResult(
            strategy=strategy,
            final_offer=final_offer,
            confidence_score=confidence_score,
            response_chain=response_chain,
            execution_time=execution_time,
            reasoning=self._generate_reasoning(strategy, final_offer, confidence_score)
        )

    def _simulate_hr_response(self, our_response: str, strategy: NegotiationStrategy, round_num: int) -> str:
        """Симуляция ответа HR"""
        # Простая симуляция на основе стратегии
        if strategy.style == "soft":
            responses = [
                "Спасибо за интерес. Наша вилка 180k-220k. Что скажете?",
                "Хорошо, можем обсудить. Максимум 210k. Есть equity?",
                "Понятно. Давайте 195k + бонусы. Подходит?"
            ]
        elif strategy.style == "hard":
            responses = [
                "Это выше нашего бюджета. Максимум 190k.",
                "Извините, но 200k - наш потолок для этой позиции.",
                "Мы ценим ваш опыт, но бюджет ограничен 185k."
            ]
        else:  # neutral
            responses = [
                "Спасибо. Можем предложить 200k. Что думаете?",
                "Хорошее предложение. Давайте 205k + рело.",
                "Принимаем. Оформляем 195k + бонусы."
            ]

        return responses[round_num % len(responses)]

    def _extract_offer_from_response(self, response: str, current_offer: float) -> float:
        """Извлечение оффера из ответа"""
        import re

        # Ищем числа в ответе (зарплаты)
        numbers = re.findall(r'\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\b', response)

        for num_str in numbers:
            num = float(num_str.replace(',', ''))
            # Если число похоже на зарплату (100k+)
            if 50000 <= num <= 1000000:
                # Проверяем единицы измерения
                if 'k' in response.lower() or num < 1000:
                    num *= 1000
                return num

        return current_offer

    def _calculate_confidence(self, strategy: NegotiationStrategy, final_offer: float) -> float:
        """Вычисление уверенности в результате"""
        base_confidence = 0.5

        # Бонус за высокий оффер
        offer_ratio = final_offer / self.target_salary
        if offer_ratio >= 1.0:
            base_confidence += 0.3
        elif offer_ratio >= 0.9:
            base_confidence += 0.1

        # Штраф за рискованные стратегии
        if strategy.risk_level == "high":
            base_confidence -= 0.1
        elif strategy.risk_level == "low":
            base_confidence += 0.1

        return max(0.0, min(1.0, base_confidence))

    def _generate_reasoning(self, strategy: NegotiationStrategy, final_offer: float, confidence: float) -> str:
        """Генерация объяснения результата"""
        offer_ratio = final_offer / self.target_salary

        if offer_ratio >= 1.0:
            result = f"Отличный результат! Стратегия {strategy.name} принесла {final_offer:,.0f} (+{offer_ratio-1:.1%})"
        elif offer_ratio >= 0.9:
            result = f"Хороший результат. Стратегия {strategy.name} дала {final_offer:,.0f} (близко к цели)"
        else:
            result = f"Результат ниже цели. Стратегия {strategy.name} принесла {final_offer:,.0f}"

        return f"{result}. Уверенность: {confidence:.1%}"

    def _analyze_results(self, results: List[NegotiationResult], start_time: float) -> QuantumNegotiationResult:
        """Анализ результатов всех стратегий"""
        if not results:
            # Fallback результат
            fallback_strategy = self.strategies[0]
            fallback_result = NegotiationResult(
                strategy=fallback_strategy,
                final_offer=self.base_salary,
                confidence_score=0.1,
                response_chain=["Ошибка: нет результатов"],
                execution_time=0.1,
                reasoning="Не удалось выполнить переговоры"
            )
            return QuantumNegotiationResult(
                best_result=fallback_result,
                all_results=[fallback_result],
                recommendation="Попробуйте еще раз",
                expected_gain=0,
                total_time=time.time() - start_time
            )

        # Сортируем по офферу (лучший первый)
        sorted_results = sorted(results, key=lambda x: x.final_offer, reverse=True)
        best_result = sorted_results[0]

        # Вычисляем ожидаемую прибыль
        expected_gain = best_result.final_offer - self.base_salary

        # Генерируем рекомендацию
        recommendation = self._generate_recommendation(best_result, sorted_results)

        return QuantumNegotiationResult(
            best_result=best_result,
            all_results=sorted_results,
            recommendation=recommendation,
            expected_gain=expected_gain,
            total_time=time.time() - start_time
        )

    def _generate_recommendation(self, best_result: NegotiationResult, all_results: List[NegotiationResult]) -> str:
        """Генерация рекомендации"""
        best_offer = best_result.final_offer
        offer_ratio = best_offer / self.target_salary

        if offer_ratio >= 1.0:
            recommendation = f"🎉 Отличный результат! Используйте стратегию {best_result.strategy.name} - получили {best_offer:,.0f} (+{offer_ratio-1:.1%} к цели)"
        elif offer_ratio >= 0.95:
            recommendation = f"👍 Хороший результат. Стратегия {best_result.strategy.name} дала {best_offer:,.0f}. Можно попробовать улучшить"
        elif offer_ratio >= 0.85:
            recommendation = f"🤝 Приемлемый результат. {best_offer:,.0f} - хорошая основа для начала"
        else:
            recommendation = f"📈 Результат ниже ожиданий. {best_offer:,.0f} - стоит попробовать другие аргументы"

        # Добавляем сравнение стратегий
        if len(all_results) > 1:
            other_offers = [r.final_offer for r in all_results[1:]]
            max_other = max(other_offers) if other_offers else 0
            diff = best_offer - max_other
            if diff > 10000:
                recommendation += f". Эта стратегия лучше других на {diff:,.0f}"

        return recommendation

    def get_negotiation_history(self) -> List[Dict]:
        """Получение истории переговоров"""
        return self.negotiation_history.copy()

    def get_strategy_stats(self) -> Dict[str, Dict]:
        """Статистика по стратегиям"""
        stats = {}

        for result in self.negotiation_history:
            quantum_result = result.get('quantum_result')
            if quantum_result:
                strategy_name = quantum_result.best_result.strategy.name
                if strategy_name not in stats:
                    stats[strategy_name] = {
                        'wins': 0,
                        'avg_offer': 0,
                        'total_runs': 0
                    }

                stats[strategy_name]['wins'] += 1
                stats[strategy_name]['avg_offer'] = (
                    (stats[strategy_name]['avg_offer'] * stats[strategy_name]['total_runs'] +
                     quantum_result.best_result.final_offer) /
                    (stats[strategy_name]['total_runs'] + 1)
                )
                stats[strategy_name]['total_runs'] += 1

        return stats

    def export_results(self, quantum_result: QuantumNegotiationResult, filename: str = None) -> str:
        """Экспорт результатов в JSON"""
        if not filename:
            timestamp = int(time.time())
            filename = f"quantum_negotiation_{timestamp}.json"

        export_data = {
            'timestamp': time.time(),
            'best_strategy': quantum_result.best_result.strategy.name,
            'final_offer': quantum_result.best_result.final_offer,
            'expected_gain': quantum_result.expected_gain,
            'confidence': quantum_result.best_result.confidence_score,
            'total_time': quantum_result.total_time,
            'recommendation': quantum_result.recommendation,
            'all_strategies': [
                {
                    'name': r.strategy.name,
                    'style': r.strategy.style,
                    'offer': r.final_offer,
                    'confidence': r.confidence_score,
                    'time': r.execution_time,
                    'reasoning': r.reasoning
                }
                for r in quantum_result.all_results
            ]
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        return filename
