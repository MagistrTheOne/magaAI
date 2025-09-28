# -*- coding: utf-8 -*-
"""
Job APIs - интеграция с API поиска вакансий
HH.ru API, LinkedIn API, и другие
"""

import asyncio
import json
import time
import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import requests
from urllib.parse import urlencode, quote

from browser_rpa import JobPosting


@dataclass
class JobSearchParams:
    """Параметры поиска вакансий"""
    query: str = ""
    location: str = ""
    experience: str = ""  # "noExperience", "between1And3", "between3And6", "moreThan6"
    employment: str = ""  # "full", "part", "project", "volunteer", "probation"
    schedule: str = ""    # "fullDay", "shift", "flexible", "remote", "flyInFlyOut"
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "RUR"
    company_blacklist: List[str] = None
    company_whitelist: List[str] = None
    limit: int = 50


@dataclass
class APIConfig:
    """Конфигурация API"""
    base_url: str
    headers: Dict[str, str] = None
    auth_required: bool = False
    rate_limit: int = 10  # запросов в минуту
    timeout: int = 30


class JobAPIManager:
    """
    Менеджер API для поиска вакансий
    """

    def __init__(self):
        self.logger = logging.getLogger("JobAPIManager")

        # Конфигурации API
        self.api_configs = {
            "hh_ru": APIConfig(
                base_url="https://api.hh.ru",
                headers={"User-Agent": "MAGAAssistant/1.0"},
                auth_required=False,
                rate_limit=20
            ),
            "linkedin": APIConfig(
                base_url="https://api.linkedin.com/v2",
                auth_required=True,
                rate_limit=5,
                timeout=60
            ),
            "indeed": APIConfig(
                base_url="https://api.indeed.com/ads",
                auth_required=True,
                rate_limit=10
            )
        }

        # Rate limiting
        self.last_requests = {}

        # Кэш результатов
        self.cache = {}
        self.cache_ttl = 3600  # 1 час

    async def search_jobs_multi_api(self, params: JobSearchParams) -> List[JobPosting]:
        """
        Поиск вакансий через несколько API параллельно
        """
        tasks = []

        # HH.ru (всегда доступен)
        tasks.append(self.search_hh_ru(params))

        # LinkedIn (если есть токен)
        if self._has_linkedin_token():
            tasks.append(self.search_linkedin(params))

        # Indeed (если есть ключ)
        if self._has_indeed_key():
            tasks.append(self.search_indeed(params))

        # Выполняем параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs = []
        for result in results:
            if isinstance(result, list):
                all_jobs.extend(result)
            elif isinstance(result, Exception):
                self.logger.error(f"API search failed: {result}")

        # Фильтруем дубликаты и применяем фильтры
        unique_jobs = self._filter_and_deduplicate(all_jobs, params)

        self.logger.info(f"Found {len(unique_jobs)} unique jobs from {len(tasks)} APIs")
        return unique_jobs

    async def search_hh_ru(self, params: JobSearchParams) -> List[JobPosting]:
        """
        Поиск вакансий через HH.ru API
        """
        try:
            # Проверяем rate limit
            if not self._check_rate_limit("hh_ru"):
                self.logger.warning("HH.ru rate limit exceeded")
                return []

            # Формируем параметры запроса
            query_params = {
                "text": params.query,
                "area": self._get_hh_area_id(params.location),
                "experience": self._map_experience_hh(params.experience),
                "employment": params.employment,
                "schedule": params.schedule,
                "per_page": min(params.limit, 100),
                "order_by": "publication_time"
            }

            if params.salary_min:
                query_params["salary"] = params.salary_min
                query_params["currency"] = params.currency

            # Формируем URL
            config = self.api_configs["hh_ru"]
            url = f"{config.base_url}/vacancies?{urlencode(query_params, quote_via=quote)}"

            # Делаем запрос
            async with self._get_session() as session:
                async with session.get(url, headers=config.headers, timeout=config.timeout) as response:
                    if response.status == 200:
                        data = await response.json()

                        jobs = []
                        for item in data.get("items", []):
                            job = self._parse_hh_job(item)
                            if job:
                                jobs.append(job)

                        self._update_rate_limit("hh_ru")
                        self.logger.info(f"HH.ru: Found {len(jobs)} jobs for '{params.query}'")
                        return jobs
                    else:
                        self.logger.error(f"HH.ru API error: {response.status}")
                        return []

        except Exception as e:
            self.logger.error(f"HH.ru search failed: {e}")
            return []

    async def search_linkedin(self, params: JobSearchParams) -> List[JobPosting]:
        """
        Поиск вакансий через LinkedIn API
        """
        try:
            if not self._check_rate_limit("linkedin"):
                return []

            # Получаем токен доступа
            access_token = self._get_linkedin_token()
            if not access_token:
                return []

            config = self.api_configs["linkedin"]
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0"
            }

            # LinkedIn API для поиска вакансий
            # Используем Job Search API
            search_params = {
                "keywords": params.query,
                "location": params.location,
                "experience": self._map_experience_linkedin(params.experience),
                "jobType": self._map_employment_linkedin(params.employment),
                "count": min(params.limit, 50)
            }

            url = f"{config.base_url}/jobSearch?{urlencode(search_params)}"

            async with self._get_session() as session:
                async with session.get(url, headers=headers, timeout=config.timeout) as response:
                    if response.status == 200:
                        data = await response.json()

                        jobs = []
                        for element in data.get("elements", []):
                            job = self._parse_linkedin_job(element)
                            if job:
                                jobs.append(job)

                        self._update_rate_limit("linkedin")
                        self.logger.info(f"LinkedIn: Found {len(jobs)} jobs")
                        return jobs
                    else:
                        self.logger.warning(f"LinkedIn API error: {response.status}")
                        return []

        except Exception as e:
            self.logger.error(f"LinkedIn search failed: {e}")
            return []

    async def search_indeed(self, params: JobSearchParams) -> List[JobPosting]:
        """
        Поиск вакансий через Indeed API
        """
        try:
            if not self._check_rate_limit("indeed"):
                return []

            # Indeed API требует publisher key
            publisher_key = self._get_indeed_key()
            if not publisher_key:
                return []

            config = self.api_configs["indeed"]

            search_params = {
                "publisher": publisher_key,
                "q": params.query,
                "l": params.location,
                "sort": "date",
                "radius": 25,
                "st": "",
                "jt": params.employment,
                "start": 0,
                "limit": min(params.limit, 25),
                "fromage": "",
                "filter": 1,
                "latlong": 1,
                "co": "ru",
                "chnl": "",
                "userip": "1.2.3.4",
                "useragent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "v": 2
            }

            url = f"{config.base_url}/apisearch?{urlencode(search_params)}"

            async with self._get_session() as session:
                async with session.get(url, timeout=config.timeout) as response:
                    if response.status == 200:
                        data = await response.json()

                        jobs = []
                        for result in data.get("results", []):
                            job = self._parse_indeed_job(result)
                            if job:
                                jobs.append(job)

                        self._update_rate_limit("indeed")
                        self.logger.info(f"Indeed: Found {len(jobs)} jobs")
                        return jobs
                    else:
                        self.logger.warning(f"Indeed API error: {response.status}")
                        return []

        except Exception as e:
            self.logger.error(f"Indeed search failed: {e}")
            return []

    def _parse_hh_job(self, item: Dict[str, Any]) -> Optional[JobPosting]:
        """Парсинг вакансии HH.ru"""
        try:
            title = item.get("name", "")
            company = item.get("employer", {}).get("name", "")
            url = item.get("alternate_url", "")

            # Зарплата
            salary_info = item.get("salary")
            salary = None
            if salary_info:
                if salary_info.get("from") and salary_info.get("to"):
                    salary = f"{salary_info['from']}-{salary_info['to']} {salary_info.get('currency', 'RUR')}"
                elif salary_info.get("from"):
                    salary = f"от {salary_info['from']} {salary_info.get('currency', 'RUR')}"
                elif salary_info.get("to"):
                    salary = f"до {salary_info['to']} {salary_info.get('currency', 'RUR')}"

            # Локация
            location = ""
            address = item.get("address")
            if address:
                city = address.get("city")
                if city:
                    location = city

            # Описание
            description = item.get("snippet", {}).get("requirement", "")

            return JobPosting(
                title=title,
                company=company,
                location=location,
                salary=salary,
                description=description,
                url=url,
                source="hh",
                posted_date=item.get("published_at")
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse HH job: {e}")
            return None

    def _parse_linkedin_job(self, element: Dict[str, Any]) -> Optional[JobPosting]:
        """Парсинг вакансии LinkedIn"""
        try:
            job_data = element.get("jobPosting", {})

            title = job_data.get("title", "")
            company = job_data.get("companyName", "")
            location = job_data.get("formattedLocation", "")
            url = element.get("jobPostingUrl", "")

            # Описание
            description = job_data.get("description", "")

            return JobPosting(
                title=title,
                company=company,
                location=location,
                salary=None,  # LinkedIn редко показывает зарплату
                description=description,
                url=url,
                source="linkedin",
                posted_date=job_data.get("listedAt")
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse LinkedIn job: {e}")
            return None

    def _parse_indeed_job(self, result: Dict[str, Any]) -> Optional[JobPosting]:
        """Парсинг вакансии Indeed"""
        try:
            title = result.get("jobtitle", "")
            company = result.get("company", "")
            location = result.get("formattedLocation", "")
            url = result.get("url", "")
            salary = result.get("formattedRelativeTime", "")  # Indeed использует это поле для зарплаты

            # Описание из сниппета
            description = result.get("snippet", "")

            return JobPosting(
                title=title,
                company=company,
                location=location,
                salary=salary,
                description=description,
                url=url,
                source="indeed",
                posted_date=result.get("date")
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse Indeed job: {e}")
            return None

    def _filter_and_deduplicate(self, jobs: List[JobPosting], params: JobSearchParams) -> List[JobPosting]:
        """Фильтрация и удаление дубликатов"""
        filtered_jobs = []

        # Группируем по ключу для дедупликации
        seen = set()

        for job in jobs:
            # Создаем ключ для дедупликации
            key = (job.title.lower(), job.company.lower(), job.location.lower())

            if key in seen:
                continue
            seen.add(key)

            # Применяем фильтры
            if self._passes_filters(job, params):
                filtered_jobs.append(job)

        return filtered_jobs[:params.limit]

    def _passes_filters(self, job: JobPosting, params: JobSearchParams) -> bool:
        """Проверка фильтров"""
        # Черный список компаний
        if params.company_blacklist:
            if any(company.lower() in job.company.lower() for company in params.company_blacklist):
                return False

        # Белый список компаний
        if params.company_whitelist:
            if not any(company.lower() in job.company.lower() for company in params.company_whitelist):
                return False

        # Фильтр по зарплате (простая проверка)
        if params.salary_min and job.salary:
            try:
                # Извлекаем число из строки зарплаты
                salary_num = self._extract_salary_number(job.salary)
                if salary_num and salary_num < params.salary_min:
                    return False
            except:
                pass  # Игнорируем ошибки парсинга

        return True

    def _extract_salary_number(self, salary_str: str) -> Optional[int]:
        """Извлечение числа из строки зарплаты"""
        import re
        numbers = re.findall(r'\d+', salary_str.replace(' ', ''))
        if numbers:
            return int(numbers[0])
        return None

    def _get_hh_area_id(self, location: str) -> str:
        """Получение ID региона HH.ru"""
        # Москва
        if "москв" in location.lower():
            return "1"
        # Санкт-Петербург
        elif "петербург" in location.lower() or "спб" in location.lower():
            return "2"
        # Россия
        else:
            return "113"  # Россия

    def _map_experience_hh(self, experience: str) -> str:
        """Маппинг опыта для HH.ru"""
        mapping = {
            "noExperience": "noExperience",
            "between1And3": "between1And3",
            "between3And6": "between3And6",
            "moreThan6": "moreThan6"
        }
        return mapping.get(experience, "")

    def _map_experience_linkedin(self, experience: str) -> str:
        """Маппинг опыта для LinkedIn"""
        mapping = {
            "noExperience": "1",  # Internship
            "between1And3": "2",  # Entry level
            "between3And6": "3",  # Associate
            "moreThan6": "4"      # Mid-Senior level
        }
        return mapping.get(experience, "")

    def _map_employment_linkedin(self, employment: str) -> str:
        """Маппинг типа занятости для LinkedIn"""
        mapping = {
            "full": "F",      # Full-time
            "part": "P",      # Part-time
            "contract": "C",  # Contract
            "temporary": "T"  # Temporary
        }
        return mapping.get(employment, "")

    def _check_rate_limit(self, api_name: str) -> bool:
        """Проверка rate limit"""
        now = time.time()
        config = self.api_configs[api_name]

        if api_name not in self.last_requests:
            return True

        time_since_last = now - self.last_requests[api_name]
        min_interval = 60 / config.rate_limit  # секунд между запросами

        return time_since_last >= min_interval

    def _update_rate_limit(self, api_name: str):
        """Обновление времени последнего запроса"""
        self.last_requests[api_name] = time.time()

    def _has_linkedin_token(self) -> bool:
        """Проверка наличия LinkedIn токена"""
        # В реальности нужно получить из secrets
        return False  # Пока не реализовано

    def _has_indeed_key(self) -> bool:
        """Проверка наличия Indeed ключа"""
        return False  # Пока не реализовано

    def _get_linkedin_token(self) -> Optional[str]:
        """Получение LinkedIn токена"""
        # TODO: реализовать через secrets manager
        return None

    def _get_indeed_key(self) -> Optional[str]:
        """Получение Indeed ключа"""
        # TODO: реализовать через secrets manager
        return None

    async def _get_session(self):
        """Получение HTTP сессии (aiohttp)"""
        # Для простоты используем requests, но в продакшене лучше aiohttp
        return None  # В данной реализации используем requests

    def get_api_status(self) -> Dict[str, Any]:
        """Получение статуса API"""
        status = {}
        for api_name, config in self.api_configs.items():
            status[api_name] = {
                "available": True,  # Пока считаем все доступными
                "rate_limit": config.rate_limit,
                "last_request": self.last_requests.get(api_name, 0)
            }
        return status

    async def get_job_details(self, job_url: str, source: str) -> Optional[Dict[str, Any]]:
        """Получение детальной информации о вакансии"""
        try:
            if source == "hh":
                return await self._get_hh_job_details(job_url)
            elif source == "linkedin":
                return await self._get_linkedin_job_details(job_url)
            elif source == "indeed":
                return await self._get_indeed_job_details(job_url)
            else:
                return None
        except Exception as e:
            self.logger.error(f"Failed to get job details: {e}")
            return None

    async def _get_hh_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Детальная информация с HH.ru"""
        # Извлекаем ID вакансии из URL
        vacancy_id = job_url.split('/')[-1].split('?')[0]

        config = self.api_configs["hh_ru"]
        url = f"{config.base_url}/vacancies/{vacancy_id}"

        try:
            async with self._get_session() as session:
                async with session.get(url, headers=config.headers, timeout=config.timeout) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            self.logger.error(f"HH job details failed: {e}")

        return None

    async def _get_linkedin_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Детальная информация с LinkedIn"""
        # LinkedIn API требует дополнительной авторизации
        # Пока возвращаем базовую информацию
        return {"url": job_url, "source": "linkedin"}

    async def _get_indeed_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Детальная информация с Indeed"""
        # Indeed не предоставляет детального API
        return {"url": job_url, "source": "indeed"}

    def cache_result(self, query_key: str, results: List[JobPosting]):
        """Кэширование результатов"""
        self.cache[query_key] = {
            "results": results,
            "timestamp": time.time()
        }

    def get_cached_result(self, query_key: str) -> Optional[List[JobPosting]]:
        """Получение кэшированных результатов"""
        if query_key in self.cache:
            cached = self.cache[query_key]
            if time.time() - cached["timestamp"] < self.cache_ttl:
                return cached["results"]
            else:
                # Удаляем просроченный кэш
                del self.cache[query_key]
        return None

    def clear_cache(self):
        """Очистка кэша"""
        self.cache.clear()
        self.logger.info("API cache cleared")
