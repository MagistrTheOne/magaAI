# -*- coding: utf-8 -*-
"""
Coach Simulator Module
HR-симулятор собеседований с анализом и отчетами
"""

import json
import time
import random
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class InterviewQuestion:
    """Вопрос собеседования"""
    id: str
    category: str  # "technical", "behavioral", "system_design", etc.
    difficulty: str  # "junior", "middle", "senior"
    question: str
    expected_answer: str
    key_points: List[str]
    follow_ups: List[str]


@dataclass
class InterviewSession:
    """Сессия собеседования"""
    session_id: str
    position: str
    level: str
    start_time: datetime
    questions: List[InterviewQuestion]
    responses: List[Dict[str, Any]]
    score: float = 0.0
    completed: bool = False


@dataclass
class PerformanceReport:
    """Отчет о производительности"""
    session_id: str
    overall_score: float
    category_scores: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    improvement_plan: List[str]


class HRSimulator:
    """
    Симулятор HR собеседований
    """

    def __init__(self, questions_file: str = "interview_questions.json"):
        """
        Args:
            questions_file: Файл с вопросами для собеседований
        """
        self.questions_file = Path(questions_file)
        self.questions_db = {}
        self.sessions = {}
        self.reports = {}

        # Загружаем вопросы
        self._load_questions()

        # Создаем базовые вопросы если файл пустой
        if not self.questions_db:
            self._create_default_questions()

    def _load_questions(self):
        """Загрузка вопросов из файла"""
        try:
            if self.questions_file.exists():
                with open(self.questions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for category, questions in data.items():
                    self.questions_db[category] = []
                    for q_data in questions:
                        question = InterviewQuestion(**q_data)
                        self.questions_db[category].append(question)

                print(f"[HRSimulator] Загружено {sum(len(q) for q in self.questions_db.values())} вопросов")

        except Exception as e:
            print(f"[HRSimulator] Ошибка загрузки вопросов: {e}")

    def _create_default_questions(self):
        """Создание базовых вопросов"""
        self.questions_db = {
            "technical_python": [
                InterviewQuestion(
                    id="py_001",
                    category="technical",
                    difficulty="middle",
                    question="Расскажите о генераторах в Python. Приведите пример использования.",
                    expected_answer="Генераторы - это функции, которые возвращают итератор. Они используют yield вместо return.",
                    key_points=["lazy evaluation", "yield", "memory efficient", "iteration"],
                    follow_ups=["Чем отличается генератор от списка?", "Когда использовать генераторы?"]
                ),
                InterviewQuestion(
                    id="py_002",
                    category="technical",
                    difficulty="senior",
                    question="Как работает GIL в Python? Какие проблемы это создает?",
                    expected_answer="GIL (Global Interpreter Lock) позволяет только одному потоку выполнять Python код одновременно.",
                    key_points=["threading limitations", "multiprocessing", "async/await", "concurrent.futures"],
                    follow_ups=["Как обойти ограничения GIL?", "Когда использовать multiprocessing?"]
                )
            ],
            "system_design": [
                InterviewQuestion(
                    id="sd_001",
                    category="system_design",
                    difficulty="senior",
                    question="Как спроектировать систему обработки 1 млн запросов в секунду?",
                    expected_answer="Нужно учитывать масштабируемость, отказоустойчивость, кэширование, балансировку нагрузки.",
                    key_points=["load balancing", "caching", "database sharding", "CDN", "monitoring"],
                    follow_ups=["Как обеспечить отказоустойчивость?", "Какие метрики мониторить?"]
                )
            ],
            "behavioral": [
                InterviewQuestion(
                    id="bh_001",
                    category="behavioral",
                    difficulty="middle",
                    question="Расскажите о ситуации, когда вы решали сложную техническую проблему.",
                    expected_answer="STAR метод: ситуация, задача, действия, результат.",
                    key_points=["problem analysis", "solution approach", "teamwork", "learning"],
                    follow_ups=["Что вы узнали из этой ситуации?", "Как бы поступили иначе?"]
                )
            ],
            "ml_ai": [
                InterviewQuestion(
                    id="ml_001",
                    category="ml_ai",
                    difficulty="senior",
                    question="Как избежать переобучения модели машинного обучения?",
                    expected_answer="Кросс-валидация, регуляризация, ранняя остановка, увеличение данных.",
                    key_points=["cross-validation", "regularization", "early stopping", "data augmentation"],
                    follow_ups=["Какие метрики использовать?", "Как выбрать модель?"]
                )
            ]
        }

        # Сохраняем вопросы
        self._save_questions()

    def _save_questions(self):
        """Сохранение вопросов в файл"""
        try:
            data = {}
            for category, questions in self.questions_db.items():
                data[category] = [vars(q) for q in questions]

            with open(self.questions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"[HRSimulator] Вопросы сохранены в {self.questions_file}")

        except Exception as e:
            print(f"[HRSimulator] Ошибка сохранения вопросов: {e}")

    def start_interview_session(self,
                               position: str = "Python Developer",
                               level: str = "senior",
                               num_questions: int = 5) -> str:
        """Начало сессии собеседования"""
        session_id = f"interview_{int(time.time())}_{random.randint(1000, 9999)}"

        # Выбираем вопросы
        questions = self._select_questions(position, level, num_questions)

        session = InterviewSession(
            session_id=session_id,
            position=position,
            level=level,
            start_time=datetime.now(),
            questions=questions,
            responses=[]
        )

        self.sessions[session_id] = session

        print(f"[HRSimulator] Начата сессия собеседования: {session_id}")
        return session_id

    def _select_questions(self, position: str, level: str, num_questions: int) -> List[InterviewQuestion]:
        """Выбор вопросов для собеседования"""
        all_questions = []

        # Собираем вопросы по категориям
        position_lower = position.lower()
        if "python" in position_lower:
            all_questions.extend(self.questions_db.get("technical_python", []))
        if "ml" in position_lower or "ai" in position_lower or "machine" in position_lower:
            all_questions.extend(self.questions_db.get("ml_ai", []))
        if "system" in position_lower or "architect" in position_lower:
            all_questions.extend(self.questions_db.get("system_design", []))

        # Добавляем behavioral вопросы
        all_questions.extend(self.questions_db.get("behavioral", []))

        # Фильтруем по уровню сложности
        level_questions = [q for q in all_questions if q.difficulty == level]

        # Если недостаточно вопросов уровня, берем все
        if len(level_questions) < num_questions:
            level_questions = all_questions

        # Выбираем случайные вопросы
        selected = random.sample(level_questions, min(num_questions, len(level_questions)))

        return selected

    def get_next_question(self, session_id: str) -> Optional[InterviewQuestion]:
        """Получение следующего вопроса"""
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]
        answered_count = len(session.responses)

        if answered_count >= len(session.questions):
            return None

        return session.questions[answered_count]

    def submit_answer(self, session_id: str, answer: str) -> Dict[str, Any]:
        """Отправка ответа на вопрос"""
        if session_id not in self.sessions:
            return {"error": "Сессия не найдена"}

        session = self.sessions[session_id]
        current_question_idx = len(session.responses)

        if current_question_idx >= len(session.questions):
            return {"error": "Все вопросы отвечены"}

        question = session.questions[current_question_idx]

        # Оцениваем ответ
        score, feedback = self._evaluate_answer(question, answer)

        # Сохраняем ответ
        response_data = {
            "question_id": question.id,
            "answer": answer,
            "score": score,
            "feedback": feedback,
            "timestamp": datetime.now().isoformat()
        }

        session.responses.append(response_data)

        return {
            "score": score,
            "feedback": feedback,
            "next_question": current_question_idx + 1 < len(session.questions)
        }

    def _evaluate_answer(self, question: InterviewQuestion, answer: str) -> Tuple[float, str]:
        """Оценка ответа"""
        if not answer or len(answer.strip()) < 10:
            return 0.0, "Ответ слишком короткий. Разверните вашу мысль."

        answer_lower = answer.lower()
        score = 0.0
        feedback_points = []

        # Проверяем ключевые моменты
        covered_points = 0
        for point in question.key_points:
            if point.lower() in answer_lower:
                covered_points += 1
                score += 0.3
            else:
                feedback_points.append(f"Не упомянут: {point}")

        # Проверяем полноту ответа
        if len(answer.split()) > 50:
            score += 0.2
        else:
            feedback_points.append("Ответ можно было бы подробнее")

        # Проверяем структуру
        if any(word in answer_lower for word in ["потому что", "например", "во-первых", "во-вторых"]):
            score += 0.2
        else:
            feedback_points.append("Добавьте примеры и объяснения")

        # Ограничиваем оценку
        score = min(max(score, 0.0), 1.0)

        # Формируем фидбек
        if score >= 0.8:
            feedback = "Отличный ответ! " + (". ".join(feedback_points[:2]) if feedback_points else "")
        elif score >= 0.6:
            feedback = "Хороший ответ, но можно улучшить. " + ". ".join(feedback_points[:2])
        else:
            feedback = "Ответ требует доработки. " + ". ".join(feedback_points[:3])

        return score, feedback

    def finish_interview_session(self, session_id: str) -> Optional[PerformanceReport]:
        """Завершение сессии собеседования"""
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]
        session.completed = True

        # Генерируем отчет
        report = self._generate_report(session)
        self.reports[session_id] = report

        return report

    def _generate_report(self, session: InterviewSession) -> PerformanceReport:
        """Генерация отчета о производительности"""
        # Вычисляем общую оценку
        scores = [r["score"] for r in session.responses]
        overall_score = sum(scores) / len(scores) if scores else 0.0

        # Оценки по категориям
        category_scores = {}
        for response in session.responses:
            question = next((q for q in session.questions if q.id == response["question_id"]), None)
            if question:
                category = question.category
                if category not in category_scores:
                    category_scores[category] = []
                category_scores[category].append(response["score"])

        # Средние по категориям
        for category in category_scores:
            category_scores[category] = sum(category_scores[category]) / len(category_scores[category])

        # Определяем сильные и слабые стороны
        strengths = []
        weaknesses = []

        for category, score in category_scores.items():
            if score >= 0.8:
                strengths.append(f"Отличные знания в {category}")
            elif score < 0.6:
                weaknesses.append(f"Нужно улучшить знания в {category}")

        # Рекомендации
        recommendations = []
        if overall_score >= 0.8:
            recommendations.append("Продолжайте в том же духе! Вы готовы к позиции.")
        elif overall_score >= 0.6:
            recommendations.append("Хорошая основа. Углубите знания в слабых областях.")
        else:
            recommendations.append("Требуется серьезная подготовка. Изучите материалы по позициям с низкими оценками.")

        # План улучшений
        improvement_plan = []
        for category, score in category_scores.items():
            if score < 0.7:
                if category == "technical":
                    improvement_plan.append("Практикуйте алгоритмы и структуры данных")
                elif category == "system_design":
                    improvement_plan.append("Изучите паттерны проектирования систем")
                elif category == "behavioral":
                    improvement_plan.append("Подготовьте больше примеров из опыта")
                elif category == "ml_ai":
                    improvement_plan.append("Углубите знания в ML/AI")

        return PerformanceReport(
            session_id=session.session_id,
            overall_score=overall_score,
            category_scores=category_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            improvement_plan=improvement_plan
        )

    def add_question(self, question: InterviewQuestion):
        """Добавление вопроса в базу"""
        category = question.category
        if category not in self.questions_db:
            self.questions_db[category] = []

        self.questions_db[category].append(question)
        self._save_questions()

    def get_sessions(self) -> Dict[str, InterviewSession]:
        """Получение всех сессий"""
        return self.sessions.copy()

    def get_reports(self) -> Dict[str, PerformanceReport]:
        """Получение всех отчетов"""
        return self.reports.copy()

    def save_session(self, session_id: str, filename: str = None):
        """Сохранение сессии в файл"""
        if session_id not in self.sessions:
            return False

        if not filename:
            filename = f"interview_session_{session_id}.json"

        try:
            session = self.sessions[session_id]
            session_data = {
                "session_id": session.session_id,
                "position": session.position,
                "level": session.level,
                "start_time": session.start_time.isoformat(),
                "questions": [vars(q) for q in session.questions],
                "responses": session.responses,
                "score": session.score,
                "completed": session.completed
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

            print(f"[HRSimulator] Сессия сохранена: {filename}")
            return True

        except Exception as e:
            print(f"[HRSimulator] Ошибка сохранения сессии: {e}")
            return False

    def load_session(self, filename: str) -> Optional[str]:
        """Загрузка сессии из файла"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            # Восстанавливаем вопросы
            questions = []
            for q_data in session_data["questions"]:
                questions.append(InterviewQuestion(**q_data))

            # Создаем сессию
            session = InterviewSession(
                session_id=session_data["session_id"],
                position=session_data["position"],
                level=session_data["level"],
                start_time=datetime.fromisoformat(session_data["start_time"]),
                questions=questions,
                responses=session_data["responses"],
                score=session_data["score"],
                completed=session_data["completed"]
            )

            self.sessions[session.session_id] = session
            print(f"[HRSimulator] Сессия загружена: {session.session_id}")
            return session.session_id

        except Exception as e:
            print(f"[HRSimulator] Ошибка загрузки сессии: {e}")
            return None
