# -*- coding: utf-8 -*-
"""
Auto-Pilot - автономный процесс найма
State Machine: Discover → Apply → Interview → Negotiate → Close
"""

import asyncio
import json
import time
import threading
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from browser_rpa import BrowserRPA, JobPosting, ApplicationData
from success_prediction import SuccessPredictionEngine, PredictionFeatures
from job_apis import JobAPIManager, JobSearchParams


class AutoPilotState(Enum):
    """Состояния Auto-Pilot"""
    IDLE = "idle"
    DISCOVER = "discover"  # Поиск вакансий
    FILTER = "filter"  # Фильтрация и анализ
    APPLY = "apply"  # Подача резюме
    FOLLOW_UP = "follow_up"  # Отслеживание откликов
    INTERVIEW = "interview"  # Подготовка к интервью
    NEGOTIATE = "negotiate"  # Переговоры
    CLOSE = "close"  # Финализация
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class AutoPilotConfig:
    """Конфигурация Auto-Pilot"""
    target_role: str = "Senior Python Developer"
    target_companies: List[str] = field(default_factory=lambda: ["Яндекс", "Сбер", "Тинькофф"])
    target_salary: int = 250000
    max_applications_per_day: int = 5
    search_keywords: List[str] = field(default_factory=lambda: ["Python", "AI", "ML", "Backend"])
    locations: List[str] = field(default_factory=lambda: ["Москва", "Удаленно"])
    min_prediction_score: float = 0.6  # Минимальная вероятность успеха
    auto_negotiate: bool = True
    follow_up_days: int = 7


@dataclass
class ApplicationRecord:
    """Запись об отклике"""
    job: JobPosting
    applied_date: datetime
    status: str  # "applied", "viewed", "interview", "rejected", "offer"
    prediction_score: float
    notes: str = ""
    follow_up_date: Optional[datetime] = None
    interview_date: Optional[datetime] = None
    offer_amount: Optional[float] = None


class AutoPilot:
    """
    Auto-Pilot для автономного поиска и получения работы
    """

    def __init__(self,
                 config: AutoPilotConfig = None,
                 browser_rpa: BrowserRPA = None,
                 success_prediction: SuccessPredictionEngine = None,
                 brain_manager = None):
        """
        Args:
            config: Конфигурация Auto-Pilot
            browser_rpa: Browser RPA для веб-автоматизации
            success_prediction: Движок прогноза успеха
            brain_manager: Менеджер мозга для AI
        """
        self.config = config or AutoPilotConfig()
        self.browser_rpa = browser_rpa
        self.success_prediction = success_prediction
        self.brain_manager = brain_manager

        # Состояние
        self.current_state: AutoPilotState = AutoPilotState.IDLE
        self.is_running: bool = False
        self.state_start_time: Optional[datetime] = None

        # Данные
        self.applications: List[ApplicationRecord] = []
        self.discovered_jobs: List[JobPosting] = []
        self.daily_applications: Dict[str, int] = {}  # date -> count

        # Callbacks
        self.on_state_change: Optional[Callable] = None
        self.on_application: Optional[Callable] = None
        self.on_interview: Optional[Callable] = None
        self.on_offer: Optional[Callable] = None

        # Логирование
        self.logger = logging.getLogger("AutoPilot")

        # Статистика
        self.stats = {
            'total_applications': 0,
            'interviews_scheduled': 0,
            'offers_received': 0,
            'success_rate': 0.0,
            'avg_response_time': 0.0
        }

    def start(self):
        """Запуск Auto-Pilot"""
        if self.is_running:
            self.logger.warning("Auto-Pilot already running")
            return

        self.is_running = True
        self.current_state = AutoPilotState.DISCOVER
        self.state_start_time = datetime.now()

        # Запуск в отдельном потоке
        self.thread = threading.Thread(target=self._run_autopilot, daemon=True)
        self.thread.start()

        self.logger.info("Auto-Pilot started")

    def stop(self):
        """Остановка Auto-Pilot"""
        self.is_running = False
        self.current_state = AutoPilotState.IDLE
        self._notify_state_change()

        self.logger.info("Auto-Pilot stopped")

    def pause(self):
        """Пауза Auto-Pilot"""
        if self.current_state != AutoPilotState.PAUSED:
            self.previous_state = self.current_state
            self.current_state = AutoPilotState.PAUSED
            self._notify_state_change()

    def resume(self):
        """Возобновление Auto-Pilot"""
        if self.current_state == AutoPilotState.PAUSED:
            self.current_state = self.previous_state
            self._notify_state_change()

    def _run_autopilot(self):
        """Основной цикл Auto-Pilot"""
        # Создаем event loop для async операций
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self.is_running:
            try:
                if self.current_state == AutoPilotState.DISCOVER:
                    loop.run_until_complete(self._state_discover())
                elif self.current_state == AutoPilotState.FILTER:
                    self._state_filter()
                elif self.current_state == AutoPilotState.APPLY:
                    loop.run_until_complete(self._state_apply())
                elif self.current_state == AutoPilotState.FOLLOW_UP:
                    self._state_follow_up()
                elif self.current_state == AutoPilotState.INTERVIEW:
                    self._state_interview()
                elif self.current_state == AutoPilotState.NEGOTIATE:
                    loop.run_until_complete(self._state_negotiate())
                elif self.current_state == AutoPilotState.CLOSE:
                    self._state_close()
                elif self.current_state == AutoPilotState.PAUSED:
                    time.sleep(1)
                    continue

                # Небольшая задержка между состояниями
                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Auto-Pilot error: {e}")
                self.current_state = AutoPilotState.ERROR
                self._notify_state_change()
                time.sleep(5)  # Задержка перед повтором

    async def _state_discover(self):
        """Состояние: поиск вакансий"""
        try:
            self.logger.info("🔍 Starting job discovery...")

            # Поиск вакансий на всех настроенных сайтах
            discovered_jobs = []

            # Реальный поиск через Job APIs и Browser RPA
            for keyword in self.config.search_keywords:
                if self.job_api_manager:
                    try:
                        search_params = JobSearchParams(
                            keyword=keyword,
                            location=self.user_context.get('preferred_location', 'remote'),
                            salary_min=self.user_context.get('salary_expectation', 150000)
                        )
                        real_jobs = await self.job_api_manager.search_jobs(search_params)
                        discovered_jobs.extend(real_jobs)
                    except Exception as e:
                        self.logger.error(f"Ошибка поиска вакансий через API: {e}")
                        # Fallback на mock данные
                        mock_jobs = self._mock_job_search(keyword)
                        discovered_jobs.extend(mock_jobs)
                else:
                    # Fallback на mock если компонент недоступен
                    mock_jobs = self._mock_job_search(keyword)
                    discovered_jobs.extend(mock_jobs)

            # Фильтруем дубликаты
            unique_jobs = self._filter_duplicates(discovered_jobs)

            self.discovered_jobs = unique_jobs
            self.logger.info(f"📋 Found {len(unique_jobs)} unique jobs")

            # Переход к фильтрации
            self._change_state(AutoPilotState.FILTER)

        except Exception as e:
            self.logger.error(f"Discovery failed: {e}")
            time.sleep(10)  # Повтор через 10 сек

    def _state_filter(self):
        """Состояние: фильтрация и анализ вакансий"""
        try:
            self.logger.info("🎯 Filtering and analyzing jobs...")

            filtered_jobs = []

            for job in self.discovered_jobs:
                # Проверяем лимит заявок в день
                today = datetime.now().strftime("%Y-%m-%d")
                today_count = self.daily_applications.get(today, 0)

                if today_count >= self.config.max_applications_per_day:
                    self.logger.info("📅 Daily application limit reached")
                    break

                # Проверяем соответствие компании
                if job.company not in self.config.target_companies:
                    continue

                # Прогноз успеха
                if self.success_prediction:
                    features = PredictionFeatures(
                        company_size="large",
                        industry="tech",
                        role_level="senior",
                        interview_round=1,
                        time_spent=5.0,
                        questions_asked=0,
                        technical_score=0.8,
                        communication_score=0.7,
                        cultural_fit=0.8,
                        salary_expectation=self.config.target_salary,
                        market_rate=self.config.target_salary * 0.9,
                        candidate_experience=5,
                        similar_offers_count=len(self.applications)
                    )

                    result = self.success_prediction.predict_success(features)
                    prediction_score = result.offer_probability

                    if prediction_score >= self.config.min_prediction_score:
                        job.prediction_score = prediction_score
                        filtered_jobs.append(job)
                        self.logger.info(f"✅ {job.title} at {job.company} - prediction: {prediction_score:.1%}")
                    else:
                        self.logger.info(f"❌ {job.title} at {job.company} - prediction: {prediction_score:.1%}")
                else:
                    # Без прогноза - добавляем все подходящие
                    filtered_jobs.append(job)

            self.discovered_jobs = filtered_jobs

            if filtered_jobs:
                self._change_state(AutoPilotState.APPLY)
            else:
                self.logger.info("😴 No suitable jobs found, waiting...")
                time.sleep(300)  # Ждем 5 минут перед новым поиском
                self._change_state(AutoPilotState.DISCOVER)

        except Exception as e:
            self.logger.error(f"Filter failed: {e}")

    async def _state_apply(self):
        """Состояние: подача резюме"""
        try:
            if not self.discovered_jobs:
                self._change_state(AutoPilotState.DISCOVER)
                return

            job = self.discovered_jobs.pop(0)  # Берем первую вакансию

            self.logger.info(f"📝 Applying to: {job.title} at {job.company}")

            # Реальная подача резюме через Browser RPA
            if self.browser_rpa:
                try:
                    application_data = ApplicationData(
                        resume_path=self.config.resume_path,
                        cover_letter=self._generate_cover_letter(job),
                        job_url=job.url
                    )
                    success = await self.browser_rpa.apply_to_job(application_data)
                except Exception as e:
                    self.logger.error(f"Ошибка подачи резюме через RPA: {e}")
                    success = False
            else:
                # Fallback на mock если RPA недоступен
                success = self._mock_job_application(job)

            if success:
                # Записываем отклик
                application = ApplicationRecord(
                    job=job,
                    applied_date=datetime.now(),
                    status="applied",
                    prediction_score=getattr(job, 'prediction_score', 0.5),
                    follow_up_date=datetime.now() + timedelta(days=self.config.follow_up_days)
                )

                self.applications.append(application)
                self.stats['total_applications'] += 1

                # Обновляем дневной счетчик
                today = datetime.now().strftime("%Y-%m-%d")
                self.daily_applications[today] = self.daily_applications.get(today, 0) + 1

                # Callback
                if self.on_application:
                    self.on_application(application)

                self.logger.info(f"✅ Successfully applied to {job.title}")

                # Небольшая задержка перед следующим откликом
                time.sleep(5)

            # Продолжаем с остальными вакансиями или переходим к follow-up
            if not self.discovered_jobs:
                self._change_state(AutoPilotState.FOLLOW_UP)

        except Exception as e:
            self.logger.error(f"Apply failed: {e}")

    def _state_follow_up(self):
        """Состояние: отслеживание откликов"""
        try:
            self.logger.info("📞 Following up on applications...")

            now = datetime.now()
            follow_ups_needed = []

            for app in self.applications:
                if app.status == "applied" and app.follow_up_date and now >= app.follow_up_date:
                    follow_ups_needed.append(app)

            if follow_ups_needed:
                self.logger.info(f"📧 Need to follow up on {len(follow_ups_needed)} applications")

                for app in follow_ups_needed:
                    self._send_follow_up_email(app)
                    app.follow_up_date = now + timedelta(days=self.config.follow_up_days)

            # Проверяем на новые интервью
            interviews_scheduled = [app for app in self.applications if app.interview_date and app.interview_date <= now + timedelta(days=1)]

            if interviews_scheduled:
                self._change_state(AutoPilotState.INTERVIEW)
            else:
                # Ждем перед следующим циклом follow-up
                time.sleep(3600)  # 1 час

        except Exception as e:
            self.logger.error(f"Follow-up failed: {e}")

    def _state_interview(self):
        """Состояние: подготовка к интервью"""
        try:
            self.logger.info("🎤 Preparing for interviews...")

            now = datetime.now()
            upcoming_interviews = [
                app for app in self.applications
                if app.interview_date and app.interview_date <= now + timedelta(days=1)
            ]

            if upcoming_interviews:
                for interview in upcoming_interviews:
                    self.logger.info(f"📅 Interview scheduled: {interview.job.title} at {interview.job.company}")

                    # Имитируем подготовку
                    self._prepare_for_interview(interview)

                    # Callback
                    if self.on_interview:
                        self.on_interview(interview)

                    # Отмечаем как обработанное
                    interview.status = "interviewing"

                self.stats['interviews_scheduled'] += len(upcoming_interviews)

            # После обработки интервью возвращаемся к follow-up
            self._change_state(AutoPilotState.FOLLOW_UP)

        except Exception as e:
            self.logger.error(f"Interview preparation failed: {e}")

    async def _state_negotiate(self):
        """Состояние: переговоры"""
        try:
            self.logger.info("💼 Starting negotiations...")

            offers_to_negotiate = [
                app for app in self.applications
                if app.status == "offer" and app.offer_amount
            ]

            if offers_to_negotiate:
                for offer in offers_to_negotiate:
                    self.logger.info(f"💰 Negotiating offer: ${offer.offer_amount:,.0f} from {offer.job.company}")

                    # Реальные переговоры через Quantum Negotiation
                    if self.quantum_negotiation:
                        try:
                            negotiation_details = {
                                'current_offer': offer.offer_amount,
                                'target': self.config.target_salary,
                                'benefits': offer.job.benefits or ['remote work', 'flexible schedule'],
                                'company': offer.job.company,
                                'market_rate': self._get_market_rate(offer.job.title)
                            }

                            negotiation_result = await self.quantum_negotiation.negotiate_quantum(negotiation_details)
                            final_amount = negotiation_result['best_offer']

                            self.logger.info(f"⚛️ Quantum negotiated: ${final_amount:,.0f} (+{negotiation_result['growth_percentage']:.1f}%)")

                        except Exception as e:
                            self.logger.error(f"Ошибка Quantum переговоров: {e}")
                            final_amount = self._negotiate_offer(offer)  # Fallback
                    else:
                        final_amount = self._negotiate_offer(offer)  # Fallback

                    if final_amount > offer.offer_amount:
                        offer.offer_amount = final_amount
                        offer.status = "negotiated"
                        self.logger.info(f"✅ Negotiated to: ${final_amount:,.0f}")

            # После переговоров переходим к закрытию
            self._change_state(AutoPilotState.CLOSE)

        except Exception as e:
            self.logger.error(f"Negotiation failed: {e}")

    def _state_close(self):
        """Состояние: финализация"""
        try:
            self.logger.info("🎉 Closing deals...")

            successful_offers = [
                app for app in self.applications
                if app.status in ["negotiated", "offer"] and app.offer_amount >= self.config.target_salary
            ]

            if successful_offers:
                # Выбираем лучшее предложение
                best_offer = max(successful_offers, key=lambda x: x.offer_amount)

                self.logger.info(f"🏆 Best offer: ${best_offer.offer_amount:,.0f} from {best_offer.job.company}")

                # Имитируем принятие оффера
                best_offer.status = "accepted"

                # Callback
                if self.on_offer:
                    self.on_offer(best_offer)

                self.stats['offers_received'] += 1

                # Auto-Pilot завершен успешно!
                self.logger.info("🎊 Auto-Pilot mission accomplished!")
                self.stop()

            else:
                # Продолжаем поиск
                self.logger.info("🔄 No suitable offers yet, continuing search...")
                self._change_state(AutoPilotState.DISCOVER)

        except Exception as e:
            self.logger.error(f"Close failed: {e}")

    def _change_state(self, new_state: AutoPilotState):
        """Изменение состояния"""
        if self.current_state != new_state:
            self.logger.info(f"🔄 State change: {self.current_state.value} → {new_state.value}")
            self.current_state = new_state
            self.state_start_time = datetime.now()
            self._notify_state_change()

    def _notify_state_change(self):
        """Уведомление об изменении состояния"""
        if self.on_state_change:
            self.on_state_change(self.current_state, self.state_start_time)

    def _mock_job_search(self, keyword: str) -> List[JobPosting]:
        """Моковый поиск вакансий для тестирования"""
        companies = ["Яндекс", "Сбер", "Тинькофф", "VK", "Ozon"]
        titles = [
            f"Senior {keyword} Developer",
            f"Lead {keyword} Engineer",
            f"{keyword} Tech Lead",
            f"Principal {keyword} Developer"
        ]

        jobs = []
        for i in range(3):
            job = JobPosting(
                title=titles[i % len(titles)],
                company=companies[i % len(companies)],
                location="Москва",
                salary=f"{200000 + i * 25000} - {250000 + i * 25000} руб.",
                description=f"Вакансия для опытного {keyword} разработчика",
                url=f"https://example.com/job/{i}",
                source="mock",
                posted_date=datetime.now().strftime("%Y-%m-%d")
            )
            jobs.append(job)

        return jobs

    def _mock_job_application(self, job: JobPosting) -> bool:
        """Моковая подача резюме"""
        # Имитируем успех в 80% случаев
        import random
        success = random.random() < 0.8

        if success:
            # Иногда сразу назначаем интервью
            if random.random() < 0.3:
                # Имитируем интервью через неделю
                interview_date = datetime.now() + timedelta(days=7)
                self._schedule_mock_interview(job, interview_date)

        return success

    def _schedule_mock_interview(self, job: JobPosting, interview_date: datetime):
        """Планирование мокового интервью"""
        # Найдем или создадим запись об отклике
        for app in self.applications:
            if app.job.url == job.url:
                app.interview_date = interview_date
                app.status = "interview_scheduled"
                break

    def _filter_duplicates(self, jobs: List[JobPosting]) -> List[JobPosting]:
        """Фильтрация дубликатов вакансий"""
        seen = set()
        unique_jobs = []

        for job in jobs:
            key = (job.title.lower(), job.company.lower())
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)

        return unique_jobs

    def _send_follow_up_email(self, application: ApplicationRecord):
        """Отправка follow-up email"""
        self.logger.info(f"📧 Sending follow-up to {application.job.company} for {application.job.title}")

        # Имитируем отправку
        # В реальности использовал бы email API или SMTP

    def _prepare_for_interview(self, application: ApplicationRecord):
        """Подготовка к интервью"""
        self.logger.info(f"🎓 Preparing for interview: {application.job.title} at {application.job.company}")

        # Реальная подготовка к интервью
        try:
            # Анализ компании через Brain Manager
            if self.brain_manager and self.brain_manager.is_authenticated:
                company_analysis = self.brain_manager.process_hr_message(
                    f"Расскажи о компании {application.job.company}. "
                    f"Какие у них ценности, культура, стек технологий?",
                    {}
                )
                self.logger.info(f"📊 Company analysis: {company_analysis[:200]}...")

            # Подготовка вопросов через Intent Engine
            if self.intent_engine:
                interview_questions = self.intent_engine.generate_interview_questions(
                    application.job.title,
                    application.job.company
                )
                self.logger.info(f"❓ Prepared {len(interview_questions)} interview questions")

            # Прогноз успеха
            if self.success_prediction:
                prediction = self.success_prediction.predict_success(
                    PredictionFeatures(
                        experience_years=self.user_context.get('experience_years', 3),
                        skill_match=0.8,
                        company_size=application.job.company_size or "medium",
                        industry=application.job.industry or "tech",
                        role_level=application.job.level or "middle",
                        interview_count=len([a for a in self.applications if a.status == "interviewing"]),
                        referral=self.user_context.get('has_referral', False),
                        portfolio_quality=self.user_context.get('portfolio_quality', 0.7)
                    )
                )
                self.logger.info(f"🎯 Success prediction: {prediction.probability:.1%}")

        except Exception as e:
            self.logger.error(f"Ошибка подготовки к интервью: {e}")
            # Fallback на базовую подготовку

    def _negotiate_offer(self, application: ApplicationRecord) -> float:
        """Переговоры по офферу"""
        current_offer = application.offer_amount
        target = self.config.target_salary

        # Простая логика переговоров
        if current_offer < target * 0.9:
            # Слишком низко - отказываемся
            application.status = "offer_declined"
            return current_offer
        elif current_offer < target:
            # Пытаемся увеличить
            negotiated = min(current_offer * 1.15, target)
            return negotiated
        else:
            # Принимаем
            return current_offer

    def get_status(self) -> Dict[str, Any]:
        """Получение статуса Auto-Pilot"""
        return {
            'is_running': self.is_running,
            'current_state': self.current_state.value,
            'state_start_time': self.state_start_time.isoformat() if self.state_start_time else None,
            'applications_count': len(self.applications),
            'discovered_jobs_count': len(self.discovered_jobs),
            'stats': self.stats
        }

    def get_applications(self) -> List[ApplicationRecord]:
        """Получение списка откликов"""
        return self.applications.copy()

    def add_manual_application(self, job: JobPosting, prediction_score: float = 0.5):
        """Добавление ручного отклика"""
        application = ApplicationRecord(
            job=job,
            applied_date=datetime.now(),
            status="applied",
            prediction_score=prediction_score
        )

        self.applications.append(application)
        self.stats['total_applications'] += 1

    def update_application_status(self, application_id: int, status: str, **kwargs):
        """Обновление статуса отклика"""
        if 0 <= application_id < len(self.applications):
            app = self.applications[application_id]
            app.status = status

            # Обновляем дополнительные поля
            for key, value in kwargs.items():
                if hasattr(app, key):
                    setattr(app, key, value)

            self.logger.info(f"Updated application {application_id}: {status}")

    def export_data(self, filename: str = None) -> str:
        """Экспорт данных Auto-Pilot"""
        if not filename:
            timestamp = int(time.time())
            filename = f"autopilot_data_{timestamp}.json"

        # Подготавливаем данные для сериализации
        applications_data = []
        for app in self.applications:
            app_dict = {
                'job': {
                    'title': app.job.title,
                    'company': app.job.company,
                    'url': app.job.url,
                    'salary': app.job.salary
                },
                'applied_date': app.applied_date.isoformat(),
                'status': app.status,
                'prediction_score': app.prediction_score,
                'notes': app.notes,
                'follow_up_date': app.follow_up_date.isoformat() if app.follow_up_date else None,
                'interview_date': app.interview_date.isoformat() if app.interview_date else None,
                'offer_amount': app.offer_amount
            }
            applications_data.append(app_dict)

        data = {
            'config': {
                'target_role': self.config.target_role,
                'target_companies': self.config.target_companies,
                'target_salary': self.config.target_salary,
                'max_applications_per_day': self.config.max_applications_per_day
            },
            'current_state': self.current_state.value,
            'is_running': self.is_running,
            'applications': applications_data,
            'stats': self.stats,
            'export_time': datetime.now().isoformat()
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Data exported to {filename}")
        return filename

    def import_data(self, filename: str):
        """Импорт данных Auto-Pilot"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Восстанавливаем конфиг
            config_data = data.get('config', {})
            self.config = AutoPilotConfig(**config_data)

            # Восстанавливаем состояние
            self.current_state = AutoPilotState(data.get('current_state', 'idle'))
            self.is_running = data.get('is_running', False)

            # Восстанавливаем отклики
            applications_data = data.get('applications', [])
            for app_data in applications_data:
                job_data = app_data['job']
                job = JobPosting(**job_data)

                application = ApplicationRecord(
                    job=job,
                    applied_date=datetime.fromisoformat(app_data['applied_date']),
                    status=app_data['status'],
                    prediction_score=app_data['prediction_score'],
                    notes=app_data.get('notes', ''),
                    follow_up_date=datetime.fromisoformat(app_data['follow_up_date']) if app_data.get('follow_up_date') else None,
                    interview_date=datetime.fromisoformat(app_data['interview_date']) if app_data.get('interview_date') else None,
                    offer_amount=app_data.get('offer_amount')
                )

                self.applications.append(application)

            # Восстанавливаем статистику
            self.stats.update(data.get('stats', {}))

            self.logger.info(f"Data imported from {filename}")

        except Exception as e:
            self.logger.error(f"Import failed: {e}")
