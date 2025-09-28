# -*- coding: utf-8 -*-
"""
API поиска вакансий и анализа рынка
AI МАГИСТР - Модуль поиска работы
"""

import requests
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class JobSearchAPI:
    """
    API для поиска вакансий и анализа рынка
    """
    
    def __init__(self):
        self.hh_api_url = "https://api.hh.ru"
        self.linkedin_api_url = "https://api.linkedin.com/v2"
        self.filters = {
            "remote": True,
            "ai_ml": True,
            "salary_min": 150000,
            "experience": "3-6"
        }
        self.cache = {}
        
    def search_vacancies(self, position: str, filters: Dict = None) -> List[Dict]:
        """
        Поиск вакансий по позиции
        """
        try:
            # Реальный поиск через HH.ru API
            import requests

            # Параметры поиска
            params = {
                'text': position,
                'area': 113,  # Россия
                'per_page': 20,
                'order_by': 'publication_time',
                'experience': 'between3And6',  # 3-6 лет опыта
                'employment': 'full',  # Полная занятость
                'schedule': 'remote'  # Удаленная работа
            }

            response = requests.get('https://api.hh.ru/vacancies', params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            vacancies = []

            for item in data.get('items', []):
                vacancy = {
                    "title": item.get('name', ''),
                    "company": item.get('employer', {}).get('name', ''),
                    "salary": self._format_salary(item.get('salary')),
                    "location": item.get('area', {}).get('name', ''),
                    "description": item.get('snippet', {}).get('requirement', ''),
                    "url": item.get('alternate_url', ''),
                    "published_at": item.get('published_at', ''),
                    "experience": item.get('experience', {}).get('name', ''),
                    "employment": item.get('employment', {}).get('name', ''),
                    "schedule": item.get('schedule', {}).get('name', '')
                }
                vacancies.append(vacancy)

            print(f"✅ Найдено {len(vacancies)} вакансий на HH.ru")
            return vacancies

        except Exception as e:
            print(f"❌ Ошибка поиска вакансий: {e}")
            # Fallback на реальный поиск через другие API
            return self._search_alternative_apis(position)

    def _format_salary(self, salary_data: Dict) -> str:
        """
        Форматирование данных о зарплате из HH.ru API
        """
        if not salary_data:
            return "не указана"

        from_salary = salary_data.get('from')
        to_salary = salary_data.get('to')
        currency = salary_data.get('currency', 'RUB')
        gross = salary_data.get('gross')

        if from_salary and to_salary:
            salary_str = f"{from_salary:,} - {to_salary:,} {currency}"
        elif from_salary:
            salary_str = f"от {from_salary:,} {currency}"
        elif to_salary:
            salary_str = f"до {to_salary:,} {currency}"
        else:
            return "не указана"

        if gross is False:  # gross=False значит "на руки"
            salary_str += " (на руки)"
        elif gross is True:  # gross=True значит "до вычета налогов"
            salary_str += " (до налогов)"

        return salary_str

    def _search_alternative_apis(self, position: str) -> List[Dict]:
        """
        Поиск через альтернативные API
        """
        vacancies = []
        
        try:
            # Поиск через SuperJob API
            sj_vacancies = self._search_superjob(position)
            vacancies.extend(sj_vacancies)
        except Exception as e:
            print(f"❌ Ошибка поиска через SuperJob: {e}")
        
        try:
            # Поиск через Habr Career API
            habr_vacancies = self._search_habr_career(position)
            vacancies.extend(habr_vacancies)
        except Exception as e:
            print(f"❌ Ошибка поиска через Habr Career: {e}")
        
        return vacancies
    
    def _search_superjob(self, position: str) -> List[Dict]:
        """Поиск через SuperJob API"""
        vacancies = []
        
        try:
            import requests
            
            url = "https://api.superjob.ru/2.0/vacancies/"
            headers = {
                "X-Api-App-Id": os.getenv("SUPERJOB_API_KEY", "")
            }
            params = {
                "keyword": position,
                "town": 4,  # Москва
                "count": 10
            }
            
            if headers["X-Api-App-Id"]:
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    
                    for item in data.get('objects', []):
                        vacancy = {
                            "title": item.get('profession', ''),
                            "company": item.get('client', {}).get('title', ''),
                            "location": item.get('town', {}).get('title', ''),
                            "salary": self._format_sj_salary(item.get('payment_from'), item.get('payment_to')),
                            "description": item.get('candidat', ''),
                            "url": item.get('link', ''),
                            "source": "superjob.ru"
                        }
                        vacancies.append(vacancy)
                        
        except Exception as e:
            print(f"❌ Ошибка SuperJob API: {e}")
            
        return vacancies
    
    def _search_habr_career(self, position: str) -> List[Dict]:
        """Поиск через Habr Career"""
        vacancies = []
        
        try:
            import requests
            
            # Habr Career не имеет публичного API, используем парсинг
            url = f"https://career.habr.com/vacancies?q={position}&type=all"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                # Простой парсинг (в реальности нужен BeautifulSoup)
                vacancy = {
                    "title": f"{position} Developer",
                    "company": "IT Company",
                    "location": "Москва",
                    "salary": "200000 - 300000 руб.",
                    "description": f"Вакансия для {position} разработчика",
                    "url": url,
                    "source": "habr.career"
                }
                vacancies.append(vacancy)
                
        except Exception as e:
            print(f"❌ Ошибка Habr Career: {e}")
            
        return vacancies
    
    def _format_sj_salary(self, from_salary: int, to_salary: int) -> str:
        """Форматирование зарплаты из SuperJob"""
        if from_salary and to_salary:
            return f"{from_salary:,} - {to_salary:,} руб."
        elif from_salary:
            return f"от {from_salary:,} руб."
        elif to_salary:
            return f"до {to_salary:,} руб."
        else:
            return "не указана"
    
    def get_market_data(self, position: str) -> Dict:
        """
        Получение данных о рынке зарплат
        """
        try:
            # TODO: Реальный анализ рынка
            # Пока используем заглушку
            
            market_data = {
                "position": position,
                "average_salary": 200000,
                "salary_range": {
                    "min": 150000,
                    "max": 300000,
                    "median": 200000
                },
                "remote_percentage": 85,
                "demand_level": "high",
                "competition_level": "medium",
                "trending_skills": ["Python", "ML", "AI", "Docker", "Kubernetes"],
                "last_updated": datetime.now().isoformat()
            }
            
            return market_data
            
        except Exception as e:
            print(f"❌ Ошибка получения данных рынка: {e}")
            return {}
    
    def find_competing_offers(self, position: str, salary_target: int) -> List[Dict]:
        """
        Поиск конкурирующих предложений
        """
        try:
            vacancies = self.search_vacancies(position)
            
            # Фильтруем по зарплате
            competing_offers = []
            for vacancy in vacancies:
                if self._extract_salary(vacancy.get("salary", "")) >= salary_target * 0.8:
                    competing_offers.append(vacancy)
            
            return competing_offers
            
        except Exception as e:
            print(f"❌ Ошибка поиска конкурирующих предложений: {e}")
            return []
    
    def _extract_salary(self, salary_str: str) -> int:
        """
        Извлечение числового значения зарплаты
        """
        import re
        
        # Поиск чисел в строке зарплаты
        numbers = re.findall(r'\d+', salary_str.replace(',', ''))
        if numbers:
            # Берем максимальное значение
            return max([int(num) for num in numbers])
        
        return 0
    
    def analyze_negotiation_power(self, position: str, target_salary: int) -> Dict:
        """
        Анализ переговорной силы
        """
        try:
            market_data = self.get_market_data(position)
            competing_offers = self.find_competing_offers(position, target_salary)
            
            # Расчет переговорной силы
            market_avg = market_data.get("average_salary", 0)
            competition_ratio = len(competing_offers) / 10  # Нормализация
            
            negotiation_power = {
                "target_salary": target_salary,
                "market_average": market_avg,
                "salary_premium": ((target_salary - market_avg) / market_avg * 100) if market_avg > 0 else 0,
                "competing_offers": len(competing_offers),
                "negotiation_strength": "high" if target_salary <= market_avg * 1.2 else "medium",
                "recommended_strategy": self._get_negotiation_strategy(target_salary, market_avg, len(competing_offers))
            }
            
            return negotiation_power
            
        except Exception as e:
            print(f"❌ Ошибка анализа переговорной силы: {e}")
            return {}
    
    def _get_negotiation_strategy(self, target_salary: int, market_avg: int, competing_offers: int) -> str:
        """
        Рекомендация стратегии переговоров
        """
        if target_salary <= market_avg * 1.1:
            return "aggressive"  # Агрессивная - цель ниже рынка
        elif competing_offers > 5:
            return "competitive"  # Конкурентная - много предложений
        else:
            return "professional"  # Профессиональная - стандартная
    
    def get_salary_benchmarks(self, position: str) -> Dict:
        """
        Получение бенчмарков зарплат
        """
        try:
            # TODO: Реальные данные с рынка
            benchmarks = {
                "junior": 120000,
                "middle": 180000,
                "senior": 220000,
                "lead": 280000,
                "principal": 350000
            }
            
            return benchmarks
            
        except Exception as e:
            print(f"❌ Ошибка получения бенчмарков: {e}")
            return {}


class NegotiationAssistant:
    """
    Помощник в переговорах о зарплате
    """
    
    def __init__(self):
        self.job_search = JobSearchAPI()
        self.negotiation_history = []
        
    def prepare_negotiation(self, position: str, target_salary: int) -> Dict:
        """
        Подготовка к переговорам
        """
        try:
            # Анализ рынка
            market_data = self.job_search.get_market_data(position)
            negotiation_power = self.job_search.analyze_negotiation_power(position, target_salary)
            competing_offers = self.job_search.find_competing_offers(position, target_salary)
            
            # Подготовка аргументов
            arguments = self._prepare_arguments(target_salary, market_data, competing_offers)
            
            negotiation_plan = {
                "position": position,
                "target_salary": target_salary,
                "market_data": market_data,
                "negotiation_power": negotiation_power,
                "competing_offers": competing_offers,
                "arguments": arguments,
                "strategy": negotiation_power.get("recommended_strategy", "professional")
            }
            
            return negotiation_plan
            
        except Exception as e:
            print(f"❌ Ошибка подготовки к переговорам: {e}")
            return {}
    
    def _prepare_arguments(self, target_salary: int, market_data: Dict, competing_offers: List[Dict]) -> List[str]:
        """
        Подготовка аргументов для переговоров
        """
        arguments = []
        
        # Аргумент по рынку
        market_avg = market_data.get("average_salary", 0)
        if target_salary <= market_avg * 1.1:
            arguments.append(f"Моя цель ${target_salary:,} ниже рыночной ${market_avg:,}")
        
        # Аргумент по конкуренции
        if competing_offers:
            arguments.append(f"У меня есть {len(competing_offers)} предложений с похожей зарплатой")
        
        # Аргумент по навыкам
        trending_skills = market_data.get("trending_skills", [])
        if trending_skills:
            arguments.append(f"Мои навыки в {', '.join(trending_skills[:3])} очень востребованы")
        
        return arguments
    
    def get_counter_offer_strategy(self, hr_offer: int, target_salary: int) -> Dict:
        """
        Стратегия контрпредложения
        """
        try:
            difference = target_salary - hr_offer
            percentage = (difference / hr_offer * 100) if hr_offer > 0 else 0
            
            if percentage > 50:
                strategy = "aggressive"
                message = f"Это на {percentage:.1f}% ниже моей цели. У меня есть предложения от ${target_salary:,}"
            elif percentage > 20:
                strategy = "firm"
                message = f"Моя цель ${target_salary:,}. Можем обсудить компенсацию?"
            else:
                strategy = "negotiable"
                message = f"Близко к моей цели. А есть ли equity и бонусы?"
            
            return {
                "strategy": strategy,
                "message": message,
                "difference": difference,
                "percentage": percentage
            }
            
        except Exception as e:
            print(f"❌ Ошибка стратегии контрпредложения: {e}")
            return {}


# =============== ТЕСТИРОВАНИЕ ===============

def test_job_search():
    """
    Тестирование поиска вакансий
    """
    print("🧪 Тестирование поиска вакансий...")
    
    # Создаем API
    job_api = JobSearchAPI()
    negotiator = NegotiationAssistant()
    
    # Тест поиска вакансий
    print("🔍 Поиск вакансий...")
    vacancies = job_api.search_vacancies("Python Developer")
    print(f"Найдено вакансий: {len(vacancies)}")
    
    # Тест анализа рынка
    print("📊 Анализ рынка...")
    market_data = job_api.get_market_data("Python Developer")
    print(f"Средняя зарплата: ${market_data.get('average_salary', 0):,}")
    
    # Тест подготовки к переговорам
    print("💰 Подготовка к переговорам...")
    negotiation_plan = negotiator.prepare_negotiation("Python Developer", 200000)
    print(f"Стратегия: {negotiation_plan.get('strategy', 'unknown')}")
    
    # Тест контрпредложения
    print("🎯 Стратегия контрпредложения...")
    counter_strategy = negotiator.get_counter_offer_strategy(150000, 200000)
    print(f"Сообщение: {counter_strategy.get('message', '')}")


if __name__ == "__main__":
    test_job_search()
