# -*- coding: utf-8 -*-
"""
Success Prediction Engine - ML модель для прогноза офферов
"""

import os
import json
import time
import pickle
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


@dataclass
class PredictionFeatures:
    """Фичи для прогноза"""
    company_size: str  # "startup", "mid", "enterprise"
    industry: str  # "tech", "finance", "other"
    role_level: str  # "junior", "middle", "senior", "lead"
    interview_round: int  # 1, 2, 3, 4...
    time_spent: float  # часы на подготовку
    questions_asked: int  # сколько вопросов задал кандидат
    technical_score: float  # оценка технических вопросов 0-1
    communication_score: float  # оценка коммуникации 0-1
    cultural_fit: float  # оценка культурного фита 0-1
    salary_expectation: float  # ожидаемая зарплата
    market_rate: float  # рыночная ставка для позиции
    candidate_experience: int  # лет опыта
    similar_offers_count: int  # сколько похожих офферов было


@dataclass
class PredictionResult:
    """Результат прогноза"""
    offer_probability: float
    confidence_interval: Tuple[float, float]
    key_factors: List[str]
    recommendations: List[str]
    similar_cases: List[Dict[str, Any]]
    prediction_time: datetime


class SuccessPredictionEngine:
    """
    ML движок для прогноза успеха в найме
    """

    def __init__(self,
                 model_path: str = "models",
                 training_data_path: str = "training_data",
                 min_training_samples: int = 10):
        """
        Args:
            model_path: Путь для сохранения моделей
            training_data_path: Путь для тренировочных данных
            min_training_samples: Минимальное количество сэмплов для тренировки
        """
        self.model_path = Path(model_path)
        self.training_data_path = Path(training_data_path)
        self.min_training_samples = min_training_samples

        # Создаем директории
        self.model_path.mkdir(exist_ok=True)
        self.training_data_path.mkdir(exist_ok=True)

        # Модель и данные
        self.model = None
        self.scaler = None
        self.label_encoders = {}
        self.feature_columns = []
        self.training_data = []

        # Статистика
        self.prediction_history = []
        self.model_accuracy = 0.0
        self.last_training = None

        # Инициализация
        self._initialize_prediction_engine()

    def _initialize_prediction_engine(self):
        """Инициализация движка прогнозов"""
        try:
            # Загружаем существующие данные
            self._load_training_data()
            self._load_model()

            # Если данных достаточно - тренируем модель
            if len(self.training_data) >= self.min_training_samples:
                self._train_model()

            print(f"[SuccessPrediction] Инициализирован. {len(self.training_data)} тренировочных сэмплов")

        except Exception as e:
            print(f"[SuccessPrediction] Ошибка инициализации: {e}")

    def _load_training_data(self):
        """Загрузка тренировочных данных"""
        try:
            data_file = self.training_data_path / "training_samples.json"
            if data_file.exists():
                with open(data_file, 'r', encoding='utf-8') as f:
                    self.training_data = json.load(f)

        except Exception as e:
            print(f"[SuccessPrediction] Ошибка загрузки тренировочных данных: {e}")

    def _load_model(self):
        """Загрузка обученной модели"""
        try:
            if not SKLEARN_AVAILABLE:
                print("[SuccessPrediction] scikit-learn не установлен")
                return

            model_file = self.model_path / "success_predictor.pkl"
            if model_file.exists():
                with open(model_file, 'rb') as f:
                    saved_data = pickle.load(f)

                self.model = saved_data['model']
                self.scaler = saved_data['scaler']
                self.label_encoders = saved_data['label_encoders']
                self.feature_columns = saved_data['feature_columns']
                self.model_accuracy = saved_data.get('accuracy', 0.0)
                self.last_training = saved_data.get('training_time')

                print(f"[SuccessPrediction] Модель загружена. Точность: {self.model_accuracy:.1%}")

        except Exception as e:
            print(f"[SuccessPrediction] Ошибка загрузки модели: {e}")

    def add_training_sample(self,
                           features: PredictionFeatures,
                           outcome: bool,
                           actual_offer: Optional[float] = None,
                           notes: str = ""):
        """
        Добавление тренировочного сэмпла

        Args:
            features: Фичи кандидата/компании
            outcome: True - оффер получен, False - отклонен
            actual_offer: Реальная сумма оффера
            notes: Дополнительные заметки
        """
        sample = {
            'features': features.__dict__,
            'outcome': outcome,
            'actual_offer': actual_offer,
            'notes': notes,
            'timestamp': time.time(),
            'prediction_result': None  # Будет заполнено если предсказывали
        }

        self.training_data.append(sample)

        # Автосохранение
        self._save_training_data()

        # Перетренировка модели если достаточно данных
        if len(self.training_data) >= self.min_training_samples:
            self._train_model()

    def _save_training_data(self):
        """Сохранение тренировочных данных"""
        try:
            data_file = self.training_data_path / "training_samples.json"
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(self.training_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"[SuccessPrediction] Ошибка сохранения данных: {e}")

    def _train_model(self):
        """Тренировка модели"""
        try:
            if not SKLEARN_AVAILABLE or len(self.training_data) < self.min_training_samples:
                return

            # Подготавливаем данные
            X, y = self._prepare_training_data()

            if len(X) < self.min_training_samples:
                return

            # Разделяем на train/test
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            # Тренируем модель
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            )

            self.model.fit(X_train, y_train)

            # Оцениваем точность
            y_pred = self.model.predict(X_test)
            self.model_accuracy = accuracy_score(y_test, y_pred)

            # Сохраняем модель
            self._save_model()

            self.last_training = time.time()
            print(f"[SuccessPrediction] Модель обучена. Точность: {self.model_accuracy:.1%}")

        except Exception as e:
            print(f"[SuccessPrediction] Ошибка тренировки модели: {e}")

    def _prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Подготовка данных для тренировки"""
        try:
            df_data = []

            for sample in self.training_data:
                features = sample['features']
                row = {
                    'company_size': features.get('company_size', 'unknown'),
                    'industry': features.get('industry', 'unknown'),
                    'role_level': features.get('role_level', 'unknown'),
                    'interview_round': features.get('interview_round', 1),
                    'time_spent': features.get('time_spent', 0),
                    'questions_asked': features.get('questions_asked', 0),
                    'technical_score': features.get('technical_score', 0.5),
                    'communication_score': features.get('communication_score', 0.5),
                    'cultural_fit': features.get('cultural_fit', 0.5),
                    'salary_expectation': features.get('salary_expectation', 0),
                    'market_rate': features.get('market_rate', 0),
                    'candidate_experience': features.get('candidate_experience', 0),
                    'similar_offers_count': features.get('similar_offers_count', 0),
                }
                df_data.append(row)

            df = pd.DataFrame(df_data)

            # Кодируем категориальные фичи
            categorical_cols = ['company_size', 'industry', 'role_level']
            for col in categorical_cols:
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    df[col] = self.label_encoders[col].fit_transform(df[col])
                else:
                    # Handle unseen categories
                    try:
                        df[col] = self.label_encoders[col].transform(df[col])
                    except ValueError:
                        # Для новых категорий присваиваем -1
                        df[col] = -1

            # Нормализуем числовые фичи
            numeric_cols = [col for col in df.columns if col not in categorical_cols]
            if not self.scaler:
                self.scaler = StandardScaler()
                X = self.scaler.fit_transform(df[numeric_cols])
            else:
                X = self.scaler.transform(df[numeric_cols])

            self.feature_columns = list(df.columns)

            # Целевая переменная
            y = np.array([sample['outcome'] for sample in self.training_data])

            return X, y

        except Exception as e:
            print(f"[SuccessPrediction] Ошибка подготовки данных: {e}")
            return np.array([]), np.array([])

    def _save_model(self):
        """Сохранение модели"""
        try:
            model_file = self.model_path / "success_predictor.pkl"

            saved_data = {
                'model': self.model,
                'scaler': self.scaler,
                'label_encoders': self.label_encoders,
                'feature_columns': self.feature_columns,
                'accuracy': self.model_accuracy,
                'training_time': time.time(),
                'training_samples': len(self.training_data)
            }

            with open(model_file, 'wb') as f:
                pickle.dump(saved_data, f)

        except Exception as e:
            print(f"[SuccessPrediction] Ошибка сохранения модели: {e}")

    def predict_success(self,
                       features: PredictionFeatures,
                       include_similar_cases: bool = True) -> PredictionResult:
        """
        Прогноз вероятности успеха

        Args:
            features: Фичи для прогноза
            include_similar_cases: Включать похожие кейсы
        """
        try:
            prediction_time = datetime.now()

            # Если модель не обучена - используем rule-based прогноз
            if not self.model or not SKLEARN_AVAILABLE:
                return self._rule_based_prediction(features, prediction_time)

            # Подготавливаем фичи для модели
            feature_vector = self._prepare_prediction_features(features)

            # Делаем прогноз
            probability = self.model.predict_proba(feature_vector.reshape(1, -1))[0][1]

            # Вычисляем confidence interval (простая оценка)
            confidence_interval = self._calculate_confidence_interval(probability, features)

            # Ключевые факторы
            key_factors = self._extract_key_factors(features, probability)

            # Рекомендации
            recommendations = self._generate_recommendations(features, probability)

            # Похожие кейсы
            similar_cases = []
            if include_similar_cases:
                similar_cases = self._find_similar_cases(features)

            result = PredictionResult(
                offer_probability=probability,
                confidence_interval=confidence_interval,
                key_factors=key_factors,
                recommendations=recommendations,
                similar_cases=similar_cases,
                prediction_time=prediction_time
            )

            # Сохраняем в историю
            self.prediction_history.append({
                'features': features.__dict__,
                'result': result.__dict__,
                'timestamp': time.time()
            })

            return result

        except Exception as e:
            print(f"[SuccessPrediction] Ошибка прогноза: {e}")
            return self._rule_based_prediction(features, datetime.now())

    def _prepare_prediction_features(self, features: PredictionFeatures) -> np.ndarray:
        """Подготовка фич для модели"""
        try:
            # Создаем DataFrame с одной строкой
            feature_dict = {
                'company_size': features.company_size,
                'industry': features.industry,
                'role_level': features.role_level,
                'interview_round': features.interview_round,
                'time_spent': features.time_spent,
                'questions_asked': features.questions_asked,
                'technical_score': features.technical_score,
                'communication_score': features.communication_score,
                'cultural_fit': features.cultural_fit,
                'salary_expectation': features.salary_expectation,
                'market_rate': features.market_rate,
                'candidate_experience': features.candidate_experience,
                'similar_offers_count': features.similar_offers_count,
            }

            df = pd.DataFrame([feature_dict])

            # Кодируем категориальные фичи
            for col in ['company_size', 'industry', 'role_level']:
                if col in self.label_encoders:
                    try:
                        df[col] = self.label_encoders[col].transform(df[col])
                    except ValueError:
                        df[col] = -1  # Unknown category

            # Нормализуем
            if self.scaler:
                numeric_cols = [col for col in df.columns if col not in ['company_size', 'industry', 'role_level']]
                df[numeric_cols] = self.scaler.transform(df[numeric_cols])

            return df.values[0]

        except Exception as e:
            print(f"[SuccessPrediction] Ошибка подготовки фич: {e}")
            return np.zeros(len(self.feature_columns))

    def _rule_based_prediction(self,
                              features: PredictionFeatures,
                              prediction_time: datetime) -> PredictionResult:
        """Rule-based прогноз для случаев без модели"""
        # Простые правила
        score = 0.5  # базовая вероятность

        # Положительные факторы
        if features.role_level in ['senior', 'lead']:
            score += 0.1
        if features.candidate_experience >= 3:
            score += 0.1
        if features.technical_score >= 0.8:
            score += 0.1
        if features.communication_score >= 0.8:
            score += 0.1
        if features.cultural_fit >= 0.8:
            score += 0.1
        if features.questions_asked >= 3:
            score += 0.05
        if features.time_spent >= 10:
            score += 0.05

        # Отрицательные факторы
        if features.interview_round >= 4:
            score -= 0.1  # Финальные раунды сложнее
        if abs(features.salary_expectation - features.market_rate) / max(features.market_rate, 1) > 0.2:
            score -= 0.1  # Слишком завышенные ожидания

        # Ограничиваем диапазон
        probability = max(0.1, min(0.9, score))

        return PredictionResult(
            offer_probability=probability,
            confidence_interval=(max(0.0, probability - 0.1), min(1.0, probability + 0.1)),
            key_factors=self._extract_key_factors(features, probability),
            recommendations=self._generate_recommendations(features, probability),
            similar_cases=[],
            prediction_time=prediction_time
        )

    def _calculate_confidence_interval(self, probability: float, features: PredictionFeatures) -> Tuple[float, float]:
        """Вычисление доверительного интервала"""
        # Простая оценка на основе количества данных
        data_confidence = min(1.0, len(self.training_data) / 100)  # Максимум при 100+ сэмплах
        interval_width = 0.2 * (1 - data_confidence)  # Уже при малом количестве данных

        lower = max(0.0, probability - interval_width)
        upper = min(1.0, probability + interval_width)

        return (lower, upper)

    def _extract_key_factors(self, features: PredictionFeatures, probability: float) -> List[str]:
        """Извлечение ключевых факторов"""
        factors = []

        if features.technical_score >= 0.8:
            factors.append("Высокий технический уровень")
        elif features.technical_score < 0.6:
            factors.append("Низкий технический уровень")

        if features.communication_score >= 0.8:
            factors.append("Отличная коммуникация")
        elif features.communication_score < 0.6:
            factors.append("Проблемы с коммуникацией")

        if features.cultural_fit >= 0.8:
            factors.append("Хороший культурный фит")
        elif features.cultural_fit < 0.6:
            factors.append("Возможные проблемы с культурным фитом")

        if features.candidate_experience >= 5:
            factors.append("Большой опыт")
        elif features.candidate_experience < 2:
            factors.append("Малый опыт")

        if not factors:
            factors.append("Недостаточно данных для анализа")

        return factors

    def _generate_recommendations(self, features: PredictionFeatures, probability: float) -> List[str]:
        """Генерация рекомендаций"""
        recommendations = []

        if probability >= 0.8:
            recommendations.append("Отличные шансы! Продолжайте в том же духе")
        elif probability >= 0.6:
            recommendations.append("Хорошие шансы. Подготовьтесь к техническим вопросам")
        elif probability >= 0.4:
            recommendations.append("Средние шансы. Улучшите подготовку и коммуникацию")
        else:
            recommendations.append("Низкие шансы. Рассмотрите другие вакансии")

        # Конкретные рекомендации
        if features.technical_score < 0.7:
            recommendations.append("Углубите технические знания по стеку вакансии")

        if features.communication_score < 0.7:
            recommendations.append("Потренируйте презентационные навыки")

        if features.questions_asked < 2:
            recommendations.append("Задавайте больше вопросов о команде и проектах")

        if features.time_spent < 5:
            recommendations.append("Увеличьте время подготовки к интервью")

        return recommendations

    def _find_similar_cases(self, features: PredictionFeatures, limit: int = 3) -> List[Dict[str, Any]]:
        """Поиск похожих кейсов"""
        similar_cases = []

        try:
            for sample in self.training_data[-50:]:  # Ищем в последних 50
                sample_features = sample['features']

                # Вычисляем схожесть
                similarity_score = 0

                # Сравниваем ключевые параметры
                if sample_features.get('role_level') == features.role_level:
                    similarity_score += 1
                if sample_features.get('company_size') == features.company_size:
                    similarity_score += 1
                if abs(sample_features.get('candidate_experience', 0) - features.candidate_experience) <= 1:
                    similarity_score += 1
                if abs(sample_features.get('technical_score', 0.5) - features.technical_score) <= 0.2:
                    similarity_score += 1

                if similarity_score >= 2:  # Минимум 2 совпадения
                    similar_case = {
                        'outcome': sample['outcome'],
                        'actual_offer': sample.get('actual_offer'),
                        'similarity_score': similarity_score,
                        'notes': sample.get('notes', '')
                    }
                    similar_cases.append(similar_case)

                    if len(similar_cases) >= limit:
                        break

        except Exception as e:
            print(f"[SuccessPrediction] Ошибка поиска похожих кейсов: {e}")

        return similar_cases

    def get_prediction_stats(self) -> Dict[str, Any]:
        """Статистика прогнозов"""
        if not self.prediction_history:
            return {'total_predictions': 0}

        predictions = [p['result']['offer_probability'] for p in self.prediction_history]

        return {
            'total_predictions': len(predictions),
            'avg_probability': sum(predictions) / len(predictions),
            'high_probability_count': len([p for p in predictions if p >= 0.8]),
            'low_probability_count': len([p for p in predictions if p <= 0.3]),
            'model_accuracy': self.model_accuracy,
            'training_samples': len(self.training_data)
        }

    def export_training_data(self, filename: str):
        """Экспорт тренировочных данных"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.training_data, f, ensure_ascii=False, indent=2)
            print(f"[SuccessPrediction] Данные экспортированы в {filename}")
        except Exception as e:
            print(f"[SuccessPrediction] Ошибка экспорта: {e}")

    def import_training_data(self, filename: str):
        """Импорт тренировочных данных"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)

            self.training_data.extend(imported_data)
            self._save_training_data()

            # Перетренировка
            if len(self.training_data) >= self.min_training_samples:
                self._train_model()

            print(f"[SuccessPrediction] Импортировано {len(imported_data)} сэмплов")
        except Exception as e:
            print(f"[SuccessPrediction] Ошибка импорта: {e}")

    def reset_model(self):
        """Сброс модели и данных"""
        try:
            self.model = None
            self.scaler = None
            self.label_encoders = {}
            self.training_data = []
            self.prediction_history = []

            # Удаляем файлы
            model_file = self.model_path / "success_predictor.pkl"
            data_file = self.training_data_path / "training_samples.json"

            if model_file.exists():
                model_file.unlink()
            if data_file.exists():
                data_file.unlink()

            print("[SuccessPrediction] Модель и данные сброшены")

        except Exception as e:
            print(f"[SuccessPrediction] Ошибка сброса: {e}")
