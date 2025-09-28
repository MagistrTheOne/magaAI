# -*- coding: utf-8 -*-
"""
ATS-Tailor Pack - подгонка резюме под JD с skills-map и кейсами
"""

import json
import re
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import os

try:
    from brain.ai_client import BrainManager
    from memory_palace import MemoryPalace
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Некоторые компоненты недоступны: {e}")
    COMPONENTS_AVAILABLE = False


class SkillCategory(Enum):
    """Категории навыков"""
    PROGRAMMING = "programming"
    FRAMEWORKS = "frameworks"
    DATABASES = "databases"
    TOOLS = "tools"
    SOFT_SKILLS = "soft_skills"
    LANGUAGES = "languages"


@dataclass
class Skill:
    """Навык"""
    name: str
    category: SkillCategory
    level: int  # 1-5
    experience_years: float
    keywords: List[str]
    projects: List[str] = None


@dataclass
class Project:
    """Проект"""
    name: str
    description: str
    technologies: List[str]
    results: List[str]
    duration: str
    role: str


@dataclass
class JobDescription:
    """Описание вакансии"""
    title: str
    company: str
    requirements: List[str]
    responsibilities: List[str]
    skills_required: List[str]
    experience_required: str
    salary_range: str = ""


@dataclass
class TailoredResume:
    """Подогнанное резюме"""
    original_resume: str
    tailored_resume: str
    skills_matched: List[str]
    skills_missing: List[str]
    projects_highlighted: List[str]
    keywords_added: List[str]
    match_score: float


class ATSTailorPack:
    """
    ATS-Tailor Pack для подгонки резюме
    """
    
    def __init__(self):
        self.logger = logging.getLogger("ATSTailorPack")
        
        # Компоненты
        self.brain_manager = None
        self.memory_palace = None
        
        # Навыки и проекты
        self.skills_map = self._load_skills_map()
        self.projects = self._load_projects()
        
        # Шаблоны
        self.templates = self._load_templates()
        
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
            
            self.logger.info("Компоненты ATS Tailor Pack инициализированы")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {e}")
    
    def _load_skills_map(self) -> Dict[str, Skill]:
        """Загрузка карты навыков"""
        skills = {
            # Programming Languages
            "python": Skill(
                name="Python",
                category=SkillCategory.PROGRAMMING,
                level=5,
                experience_years=7.0,
                keywords=["python", "py", "django", "flask", "fastapi", "pandas", "numpy"],
                projects=["AI Assistant", "Data Pipeline", "Web API"]
            ),
            "javascript": Skill(
                name="JavaScript",
                category=SkillCategory.PROGRAMMING,
                level=4,
                experience_years=5.0,
                keywords=["javascript", "js", "nodejs", "react", "vue", "typescript"],
                projects=["Frontend App", "Node.js API", "React Dashboard"]
            ),
            "java": Skill(
                name="Java",
                category=SkillCategory.PROGRAMMING,
                level=3,
                experience_years=3.0,
                keywords=["java", "spring", "maven", "gradle", "junit"],
                projects=["Spring Boot API", "Microservices"]
            ),
            
            # Frameworks
            "django": Skill(
                name="Django",
                category=SkillCategory.FRAMEWORKS,
                level=5,
                experience_years=6.0,
                keywords=["django", "django-rest", "django-orm", "django-admin"],
                projects=["E-commerce Platform", "CRM System", "API Backend"]
            ),
            "react": Skill(
                name="React",
                category=SkillCategory.FRAMEWORKS,
                level=4,
                experience_years=4.0,
                keywords=["react", "jsx", "hooks", "redux", "nextjs"],
                projects=["SPA Application", "Admin Dashboard", "Mobile App"]
            ),
            
            # Databases
            "postgresql": Skill(
                name="PostgreSQL",
                category=SkillCategory.DATABASES,
                level=4,
                experience_years=5.0,
                keywords=["postgresql", "postgres", "sql", "database", "orm"],
                projects=["Data Warehouse", "Analytics DB", "User Management"]
            ),
            "redis": Skill(
                name="Redis",
                category=SkillCategory.DATABASES,
                level=3,
                experience_years=2.0,
                keywords=["redis", "cache", "session", "pubsub"],
                projects=["Caching Layer", "Session Store", "Real-time Features"]
            ),
            
            # Tools
            "docker": Skill(
                name="Docker",
                category=SkillCategory.TOOLS,
                level=4,
                experience_years=4.0,
                keywords=["docker", "container", "dockerfile", "docker-compose"],
                projects=["Microservices", "CI/CD Pipeline", "Development Environment"]
            ),
            "kubernetes": Skill(
                name="Kubernetes",
                category=SkillCategory.TOOLS,
                level=3,
                experience_years=2.0,
                keywords=["kubernetes", "k8s", "helm", "deployment", "service"],
                projects=["Container Orchestration", "Auto-scaling", "Service Mesh"]
            ),
            
            # Soft Skills
            "leadership": Skill(
                name="Leadership",
                category=SkillCategory.SOFT_SKILLS,
                level=4,
                experience_years=5.0,
                keywords=["leadership", "team", "mentoring", "management", "coaching"],
                projects=["Team Lead", "Mentoring Program", "Process Improvement"]
            ),
            "communication": Skill(
                name="Communication",
                category=SkillCategory.SOFT_SKILLS,
                level=5,
                experience_years=7.0,
                keywords=["communication", "presentation", "documentation", "training"],
                projects=["Technical Presentations", "Documentation", "Client Communication"]
            )
        }
        
        return skills
    
    def _load_projects(self) -> List[Project]:
        """Загрузка проектов"""
        projects = [
            Project(
                name="AI-Powered Job Assistant",
                description="Разработка интеллектуального ассистента для поиска работы с использованием ML и NLP",
                technologies=["Python", "Django", "PostgreSQL", "Redis", "Docker"],
                results=["Увеличил эффективность поиска работы на 40%", "Автоматизировал 80% рутинных задач"],
                duration="6 месяцев",
                role="Full-stack Developer & AI Engineer"
            ),
            Project(
                name="Microservices E-commerce Platform",
                description="Создание масштабируемой платформы электронной коммерции с микросервисной архитектурой",
                technologies=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Kubernetes"],
                results=["Обработка 10,000+ заказов в день", "99.9% uptime", "Снижение времени отклика на 60%"],
                duration="8 месяцев",
                role="Backend Developer & DevOps Engineer"
            ),
            Project(
                name="Real-time Analytics Dashboard",
                description="Разработка дашборда для анализа данных в реальном времени с визуализацией",
                technologies=["Python", "Django", "React", "PostgreSQL", "WebSocket"],
                results=["Улучшил принятие решений на 50%", "Сократил время анализа с часов до минут"],
                duration="4 месяца",
                role="Full-stack Developer"
            ),
            Project(
                name="Machine Learning Pipeline",
                description="Создание пайплайна для обучения и развертывания ML моделей",
                technologies=["Python", "Pandas", "Scikit-learn", "TensorFlow", "Docker", "Kubernetes"],
                results=["Автоматизировал процесс ML", "Улучшил точность предсказаний на 25%"],
                duration="5 месяцев",
                role="ML Engineer"
            )
        ]
        
        return projects
    
    def _load_templates(self) -> Dict[str, str]:
        """Загрузка шаблонов"""
        return {
            "summary_template": """
            Опытный {role} с {experience} лет опыта в разработке {technologies}.
            Специализируюсь на {specialization} и имею опыт работы с {key_technologies}.
            Успешно реализовал проекты, которые {achievements}.
            """,
            
            "experience_template": """
            {company} | {role} | {period}
            • {responsibility_1}
            • {responsibility_2}
            • {achievement}
            """,
            
            "skills_template": """
            Технические навыки: {technical_skills}
            Инструменты: {tools}
            Soft Skills: {soft_skills}
            """,
            
            "projects_template": """
            {project_name} | {technologies} | {duration}
            {description}
            Достижения: {achievements}
            """
        }
    
    async def analyze_job_description(self, jd_text: str) -> JobDescription:
        """Анализ описания вакансии"""
        try:
            if not self.brain_manager:
                return self._fallback_jd_analysis(jd_text)
            
            prompt = f"""
            Проанализируй описание вакансии и извлеки ключевую информацию:
            
            {jd_text}
            
            Верни JSON с полями:
            - title: должность
            - company: компания
            - requirements: список требований
            - responsibilities: список обязанностей
            - skills_required: список требуемых навыков
            - experience_required: требуемый опыт
            - salary_range: зарплатная вилка (если есть)
            """
            
            response = await self.brain_manager.generate_response(prompt)
            
            # Пытаемся извлечь JSON из ответа
            try:
                # Ищем JSON в ответе
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    jd_data = json.loads(json_match.group())
                    return JobDescription(**jd_data)
            except:
                pass
            
            # Fallback - простой анализ
            return self._fallback_jd_analysis(jd_text)
            
        except Exception as e:
            self.logger.error(f"Ошибка анализа JD: {e}")
            return self._fallback_jd_analysis(jd_text)
    
    def _fallback_jd_analysis(self, jd_text: str) -> JobDescription:
        """Простой анализ JD без AI"""
        # Извлекаем навыки из текста
        skills_required = []
        for skill_name, skill in self.skills_map.items():
            if any(keyword in jd_text.lower() for keyword in skill.keywords):
                skills_required.append(skill_name)
        
        return JobDescription(
            title="Software Developer",
            company="Unknown",
            requirements=jd_text.split('\n')[:5],
            responsibilities=jd_text.split('\n')[5:10],
            skills_required=skills_required,
            experience_required="3+ years"
        )
    
    def match_skills(self, jd: JobDescription) -> Tuple[List[str], List[str]]:
        """Сопоставление навыков с JD"""
        matched_skills = []
        missing_skills = []
        
        for required_skill in jd.skills_required:
            found = False
            for skill_name, skill in self.skills_map.items():
                if any(keyword in required_skill.lower() for keyword in skill.keywords):
                    matched_skills.append(skill_name)
                    found = True
                    break
            
            if not found:
                missing_skills.append(required_skill)
        
        return matched_skills, missing_skills
    
    def select_relevant_projects(self, jd: JobDescription, matched_skills: List[str]) -> List[Project]:
        """Выбор релевантных проектов"""
        relevant_projects = []
        
        for project in self.projects:
            # Проверяем пересечение технологий
            project_techs = [tech.lower() for tech in project.technologies]
            jd_skills = [skill.lower() for skill in jd.skills_required]
            
            intersection = set(project_techs) & set(jd_skills)
            if len(intersection) > 0:
                relevant_projects.append(project)
        
        # Сортируем по релевантности
        relevant_projects.sort(
            key=lambda p: len(set([tech.lower() for tech in p.technologies]) & set([skill.lower() for skill in jd.skills_required])),
            reverse=True
        )
        
        return relevant_projects[:3]  # Топ 3 проекта
    
    async def tailor_resume(self, original_resume: str, jd: JobDescription) -> TailoredResume:
        """Подгонка резюме под JD"""
        try:
            # Анализируем навыки
            matched_skills, missing_skills = self.match_skills(jd)
            
            # Выбираем релевантные проекты
            relevant_projects = self.select_relevant_projects(jd, matched_skills)
            
            # Генерируем подогнанное резюме
            if self.brain_manager:
                tailored_resume = await self._generate_tailored_resume_ai(
                    original_resume, jd, matched_skills, relevant_projects
                )
            else:
                tailored_resume = await self._generate_tailored_resume_simple(
                    original_resume, jd, matched_skills, relevant_projects
                )
            
            # Вычисляем score соответствия
            match_score = len(matched_skills) / len(jd.skills_required) if jd.skills_required else 0
            
            # Извлекаем добавленные ключевые слова
            keywords_added = self._extract_keywords(tailored_resume, jd)
            
            return TailoredResume(
                original_resume=original_resume,
                tailored_resume=tailored_resume,
                skills_matched=matched_skills,
                skills_missing=missing_skills,
                projects_highlighted=[p.name for p in relevant_projects],
                keywords_added=keywords_added,
                match_score=match_score
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка подгонки резюме: {e}")
            return TailoredResume(
                original_resume=original_resume,
                tailored_resume=original_resume,
                skills_matched=[],
                skills_missing=[],
                projects_highlighted=[],
                keywords_added=[],
                match_score=0.0
            )
    
    async def _generate_tailored_resume_ai(self, original_resume: str, jd: JobDescription, 
                                        matched_skills: List[str], relevant_projects: List[Project]) -> str:
        """Генерация подогнанного резюме с AI"""
        prompt = f"""
        Подгони резюме под описание вакансии:
        
        Оригинальное резюме:
        {original_resume}
        
        Описание вакансии:
        Должность: {jd.title}
        Компания: {jd.company}
        Требования: {', '.join(jd.requirements)}
        Навыки: {', '.join(jd.skills_required)}
        
        Мои подходящие навыки: {', '.join(matched_skills)}
        Релевантные проекты: {[p.name for p in relevant_projects]}
        
        Создай оптимизированное резюме, которое:
        1. Подчеркивает релевантные навыки
        2. Включает ключевые слова из JD
        3. Выделяет подходящие проекты
        4. Соответствует формату ATS
        """
        
        return await self.brain_manager.generate_response(prompt)
    
    async def _generate_tailored_resume_simple(self, original_resume: str, jd: JobDescription,
                                             matched_skills: List[str], relevant_projects: List[Project]) -> str:
        """Простая генерация без AI"""
        tailored = original_resume
        
        # Добавляем ключевые слова в начало
        if matched_skills:
            skills_section = f"\n\nКлючевые навыки: {', '.join(matched_skills)}\n"
            tailored = skills_section + tailored
        
        # Добавляем релевантные проекты
        if relevant_projects:
            projects_section = "\n\nРелевантные проекты:\n"
            for project in relevant_projects:
                projects_section += f"• {project.name}: {project.description}\n"
            tailored += projects_section
        
        return tailored
    
    def _extract_keywords(self, resume: str, jd: JobDescription) -> List[str]:
        """Извлечение добавленных ключевых слов"""
        jd_keywords = []
        for skill in jd.skills_required:
            jd_keywords.extend(skill.lower().split())
        
        resume_words = resume.lower().split()
        added_keywords = []
        
        for keyword in jd_keywords:
            if keyword in resume_words and keyword not in resume.lower():
                added_keywords.append(keyword)
        
        return added_keywords
    
    def get_skills_recommendations(self, missing_skills: List[str]) -> List[Dict[str, Any]]:
        """Рекомендации по изучению недостающих навыков"""
        recommendations = []
        
        for skill in missing_skills:
            # Ищем похожие навыки в нашей карте
            similar_skills = []
            for skill_name, skill_obj in self.skills_map.items():
                if any(keyword in skill.lower() for keyword in skill_obj.keywords):
                    similar_skills.append({
                        'name': skill_obj.name,
                        'level': skill_obj.level,
                        'experience_years': skill_obj.experience_years,
                        'learning_path': f"Изучите {skill_obj.name} - уровень {skill_obj.level}/5"
                    })
            
            if similar_skills:
                recommendations.extend(similar_skills)
        
        return recommendations
    
    def format_tailored_resume(self, tailored: TailoredResume) -> str:
        """Форматирование подогнанного резюме"""
        text = f"📄 <b>Подогнанное резюме</b>\n\n"
        
        text += f"🎯 Соответствие: {tailored.match_score:.1%}\n"
        text += f"✅ Подходящие навыки: {', '.join(tailored.skills_matched)}\n"
        text += f"❌ Недостающие навыки: {', '.join(tailored.skills_missing)}\n"
        text += f"🚀 Выделенные проекты: {', '.join(tailored.projects_highlighted)}\n"
        text += f"🔑 Добавленные ключевые слова: {', '.join(tailored.keywords_added)}\n\n"
        
        text += f"📝 <b>Подогнанное резюме:</b>\n"
        text += f"{tailored.tailored_resume[:500]}...\n" if len(tailored.tailored_resume) > 500 else tailored.tailored_resume
        
        return text


# Функция для тестирования
async def test_ats_tailor_pack():
    """Тестирование ATS Tailor Pack"""
    tailor = ATSTailorPack()
    
    print("📄 Тестирование ATS Tailor Pack...")
    
    # Тестовое JD
    jd_text = """
    Python Developer
    Требования:
    - Опыт работы с Python 3+ лет
    - Знание Django/FastAPI
    - Опыт с PostgreSQL
    - Docker, Kubernetes
    - Опыт с ML/Data Science
    """
    
    # Анализ JD
    jd = await tailor.analyze_job_description(jd_text)
    print(f"Анализ JD: {jd.title} - {jd.company}")
    print(f"Требуемые навыки: {jd.skills_required}")
    
    # Тестовое резюме
    original_resume = """
    Максим Онюшко
    Python Developer
    
    Опыт работы:
    - Разработка веб-приложений на Python
    - Работа с базами данных
    - Docker контейнеризация
    """
    
    # Подгонка резюме
    tailored = await tailor.tailor_resume(original_resume, jd)
    print(f"\nРезультат подгонки:")
    print(tailor.format_tailored_resume(tailored))
    
    # Рекомендации
    if tailored.skills_missing:
        recommendations = tailor.get_skills_recommendations(tailored.skills_missing)
        print(f"\nРекомендации по изучению:")
        for rec in recommendations[:3]:
            print(f"• {rec['learning_path']}")


if __name__ == "__main__":
    asyncio.run(test_ats_tailor_pack())
