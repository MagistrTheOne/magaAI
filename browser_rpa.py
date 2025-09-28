# -*- coding: utf-8 -*-
"""
Browser RPA - веб-автоматизация с Playwright
"""

import asyncio
import json
import time
import re
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs
import logging

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import pyautogui
import pyperclip


@dataclass
class JobPosting:
    """Вакансия"""
    title: str
    company: str
    location: str
    salary: Optional[str]
    description: str
    url: str
    source: str  # "hh", "linkedin", "habr"
    posted_date: Optional[str]


@dataclass
class ApplicationData:
    """Данные для отклика"""
    resume_path: str
    cover_letter: str
    job_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None


class BrowserRPA:
    """
    Browser RPA для автоматизации поиска работы и подачи резюме
    """

    def __init__(self, headless: bool = True, slow_mo: int = 100):
        """
        Args:
            headless: Запускать браузер в фоновом режиме
            slow_mo: Задержка между действиями (мс)
        """
        self.headless = headless
        self.slow_mo = slow_mo

        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        self.logger = logging.getLogger("BrowserRPA")

        # Настройки сайтов
        self.site_configs = {
            "hh_ru": {
                "base_url": "https://hh.ru",
                "search_url": "https://hh.ru/search/vacancy",
                "login_required": False,
                "selectors": {
                    "search_input": "[data-qa='search-input']",
                    "search_button": "[data-qa='search-button']",
                    "vacancy_title": "[data-qa='vacancy-serp__vacancy-title']",
                    "vacancy_company": "[data-qa='vacancy-serp__vacancy-employer-text']",
                    "vacancy_salary": "[data-qa='vacancy-serp__vacancy-compensation']",
                    "apply_button": "[data-qa='vacancy-response-link-top']"
                }
            },
            "linkedin": {
                "base_url": "https://www.linkedin.com",
                "search_url": "https://www.linkedin.com/jobs/search",
                "login_required": True,
                "selectors": {
                    "search_input": "input[aria-label*='Search']",
                    "job_cards": ".job-card-container",
                    "job_title": ".job-card-list__title",
                    "company_name": ".job-card-container__company-name",
                    "apply_button": ".jobs-apply-button"
                }
            },
            "habr": {
                "base_url": "https://career.habr.com",
                "search_url": "https://career.habr.com/vacancies",
                "login_required": False,
                "selectors": {
                    "search_input": "input[name='q']",
                    "vacancy_cards": ".vacancy-card",
                    "vacancy_title": ".vacancy-card__title",
                    "company_name": ".vacancy-card__company-name",
                    "apply_button": ".vacancy-card__apply-button"
                }
            }
        }

        # История действий
        self.action_history = []

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_browser()

    async def start_browser(self):
        """Запуск браузера"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--single-process',
                    '--disable-gpu'
                ]
            )

            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )

            self.page = await self.context.new_page()
            self.logger.info("Browser RPA initialized")

        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            raise

    async def close_browser(self):
        """Закрытие браузера"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()

            self.logger.info("Browser RPA closed")

        except Exception as e:
            self.logger.error(f"Error closing browser: {e}")

    async def navigate_to(self, url: str, wait_for_load: bool = True):
        """Навигация на URL"""
        try:
            await self.page.goto(url)
            if wait_for_load:
                await self.page.wait_for_load_state('networkidle')
            self.logger.info(f"Navigated to {url}")

        except Exception as e:
            self.logger.error(f"Navigation failed: {e}")
            raise

    async def search_jobs_hh(self, query: str, location: str = "Москва",
                           experience: str = "1-3") -> List[JobPosting]:
        """Поиск вакансий на HH.ru"""
        try:
            config = self.site_configs["hh_ru"]
            search_url = f"{config['search_url']}?text={query}&area=1&experience={experience}"

            await self.navigate_to(search_url)

            # Ждем загрузки результатов
            await self.page.wait_for_selector(config['selectors']['vacancy_title'], timeout=10000)

            # Парсим вакансии
            jobs_data = await self.page.evaluate("""
                () => {
                    const jobs = [];
                    const titles = document.querySelectorAll("[data-qa='vacancy-serp__vacancy-title']");
                    const companies = document.querySelectorAll("[data-qa='vacancy-serp__vacancy-employer-text']");
                    const salaries = document.querySelectorAll("[data-qa='vacancy-serp__vacancy-compensation']");
                    const links = document.querySelectorAll("[data-qa='vacancy-serp__vacancy-title']");

                    for (let i = 0; i < Math.min(titles.length, 10); i++) {
                        jobs.push({
                            title: titles[i]?.textContent?.trim() || '',
                            company: companies[i]?.textContent?.trim() || '',
                            salary: salaries[i]?.textContent?.trim() || null,
                            url: links[i]?.href || '',
                            location: 'Москва'
                        });
                    }
                    return jobs;
                }
            """)

            # Преобразуем в объекты JobPosting
            jobs = []
            for job_data in jobs_data:
                job = JobPosting(
                    title=job_data['title'],
                    company=job_data['company'],
                    location=job_data['location'],
                    salary=job_data['salary'],
                    description="",  # Будет заполнено при детальном просмотре
                    url=job_data['url'],
                    source="hh",
                    posted_date=None
                )
                jobs.append(job)

            self.logger.info(f"Found {len(jobs)} jobs on HH.ru for '{query}'")
            return jobs

        except Exception as e:
            self.logger.error(f"HH.ru search failed: {e}")
            return []

    async def search_jobs_linkedin(self, query: str, location: str = "Moscow") -> List[JobPosting]:
        """Поиск вакансий на LinkedIn"""
        try:
            config = self.site_configs["linkedin"]
            search_url = f"{config['search_url']}?keywords={query}&location={location}"

            await self.navigate_to(search_url)

            # Ждем загрузки
            await asyncio.sleep(3)

            # Парсим вакансии
            jobs_data = await self.page.evaluate("""
                () => {
                    const jobs = [];
                    const cards = document.querySelectorAll('.job-card-container');

                    for (let i = 0; i < Math.min(cards.length, 10); i++) {
                        const card = cards[i];
                        const title = card.querySelector('.job-card-list__title')?.textContent?.trim();
                        const company = card.querySelector('.job-card-container__company-name')?.textContent?.trim();
                        const location = card.querySelector('.job-card-container__metadata-item')?.textContent?.trim();

                        if (title && company) {
                            jobs.push({
                                title: title,
                                company: company,
                                location: location || '',
                                salary: null,
                                url: card.href || '',
                                description: ''
                            });
                        }
                    }
                    return jobs;
                }
            """)

            jobs = []
            for job_data in jobs_data:
                job = JobPosting(
                    title=job_data['title'],
                    company=job_data['company'],
                    location=job_data['location'],
                    salary=job_data['salary'],
                    description=job_data['description'],
                    url=job_data['url'],
                    source="linkedin",
                    posted_date=None
                )
                jobs.append(job)

            self.logger.info(f"Found {len(jobs)} jobs on LinkedIn for '{query}'")
            return jobs

        except Exception as e:
            self.logger.error(f"LinkedIn search failed: {e}")
            return []

    async def apply_to_job_hh(self, job_url: str, application_data: ApplicationData) -> bool:
        """Подача резюме на HH.ru"""
        try:
            await self.navigate_to(job_url)

            # Ждем кнопку отклика
            config = self.site_configs["hh_ru"]
            apply_button = self.page.locator(config['selectors']['apply_button'])

            try:
                await apply_button.wait_for(timeout=5000)
                await apply_button.click()
            except:
                self.logger.warning("Apply button not found or not clickable")
                return False

            # Ждем загрузки формы
            await asyncio.sleep(2)

            # Заполняем сопроводительное письмо
            try:
                cover_letter_selector = "[data-qa='vacancy-response-popup-letter-input']"
                cover_letter_field = self.page.locator(cover_letter_selector)
                await cover_letter_field.fill(application_data.cover_letter)
            except Exception as e:
                self.logger.warning(f"Could not fill cover letter: {e}")

            # Прикрепляем резюме если нужно
            if application_data.resume_path:
                try:
                    file_input = self.page.locator("input[type='file']")
                    await file_input.set_input_files(application_data.resume_path)
                except Exception as e:
                    self.logger.warning(f"Could not attach resume: {e}")

            # Отправляем
            try:
                submit_button = self.page.locator("[data-qa='vacancy-response-popup-submit']")
                await submit_button.click()
                await asyncio.sleep(2)
                self.logger.info(f"Successfully applied to job: {job_url}")
                return True
            except Exception as e:
                self.logger.error(f"Could not submit application: {e}")
                return False

        except Exception as e:
            self.logger.error(f"HH application failed: {e}")
            return False

    async def login_linkedin(self, email: str, password: str) -> bool:
        """Авторизация в LinkedIn"""
        try:
            await self.navigate_to("https://www.linkedin.com/login")

            # Заполняем форму
            await self.page.fill("#username", email)
            await self.page.fill("#password", password)

            # Нажимаем войти
            await self.page.click("button[type='submit']")

            # Ждем перехода
            await self.page.wait_for_url("**/feed/**", timeout=10000)

            self.logger.info("Successfully logged in to LinkedIn")
            return True

        except Exception as e:
            self.logger.error(f"LinkedIn login failed: {e}")
            return False

    async def apply_to_job_linkedin(self, job_url: str, application_data: ApplicationData) -> bool:
        """Подача резюме на LinkedIn"""
        try:
            await self.navigate_to(job_url)

            # Ждем кнопку Easy Apply
            await asyncio.sleep(3)

            try:
                apply_button = self.page.locator("button:has-text('Easy Apply')").or_(
                    self.page.locator("button:has-text('Apply')")
                )
                await apply_button.click()
            except:
                self.logger.warning("Apply button not found")
                return False

            # Ждем загрузки формы
            await asyncio.sleep(2)

            # Заполняем поля
            try:
                # Phone number
                phone_input = self.page.locator("input[type='tel']")
                await phone_input.fill("+79991234567")  # Заглушка

                # Cover letter
                cover_textarea = self.page.locator("textarea").first
                await cover_textarea.fill(application_data.cover_letter)

            except Exception as e:
                self.logger.warning(f"Could not fill application form: {e}")

            # Отправляем
            try:
                submit_button = self.page.locator("button:has-text('Submit application')").or_(
                    self.page.locator("button:has-text('Apply')")
                )
                await submit_button.click()

                await asyncio.sleep(2)
                self.logger.info(f"Successfully applied to LinkedIn job: {job_url}")
                return True

            except Exception as e:
                self.logger.error(f"Could not submit LinkedIn application: {e}")
                return False

        except Exception as e:
            self.logger.error(f"LinkedIn application failed: {e}")
            return False

    async def apply_to_job(self, application_data: ApplicationData) -> bool:
        """Общий метод подачи резюме"""
        job_url = application_data.job_url if hasattr(application_data, 'job_url') else getattr(application_data, 'url', '')

        if not job_url:
            self.logger.error("No job URL provided")
            return False

        # Определяем платформу по URL
        if "hh.ru" in job_url:
            return await self.apply_to_job_hh(job_url, application_data)
        elif "linkedin.com" in job_url:
            return await self.apply_to_job_linkedin(job_url, application_data)
        else:
            self.logger.warning(f"Unsupported job platform for URL: {job_url}")
            return False

    async def fill_job_application_form(self, form_data: Dict[str, Any]) -> bool:
        """Автоматическое заполнение формы отклика"""
        try:
            # Находим все input поля
            inputs = await self.page.query_selector_all("input, textarea, select")

            for input_elem in inputs:
                try:
                    input_type = await input_elem.get_attribute("type") or "text"
                    input_name = await input_elem.get_attribute("name") or ""
                    placeholder = await input_elem.get_attribute("placeholder") or ""

                    # Определяем что заполнять
                    value = self._get_form_value(input_name, placeholder, input_type, form_data)

                    if value:
                        if input_type in ["text", "email", "tel", "url"]:
                            await input_elem.fill(value)
                        elif input_type == "checkbox":
                            await input_elem.check()
                        elif input_type == "radio":
                            await input_elem.check()

                except Exception as e:
                    self.logger.warning(f"Could not fill input: {e}")
                    continue

            return True

        except Exception as e:
            self.logger.error(f"Form filling failed: {e}")
            return False

    def _get_form_value(self, name: str, placeholder: str, input_type: str, form_data: Dict[str, Any]) -> Optional[str]:
        """Определяет значение для поля формы"""
        name_lower = name.lower()
        placeholder_lower = placeholder.lower()

        # Email
        if "email" in name_lower or "email" in placeholder_lower:
            return form_data.get("email", "candidate@example.com")

        # Phone
        if "phone" in name_lower or "телефон" in placeholder_lower:
            return form_data.get("phone", "+79991234567")

        # Name
        if "name" in name_lower or "имя" in placeholder_lower:
            return form_data.get("name", "Максим Онюшко")

        # LinkedIn
        if "linkedin" in name_lower:
            return form_data.get("linkedin_url")

        # GitHub
        if "github" in name_lower:
            return form_data.get("github_url")

        # Portfolio
        if "portfolio" in name_lower:
            return form_data.get("portfolio_url")

        return None

    async def take_screenshot(self, filename: str = None) -> Optional[str]:
        """Скриншот страницы"""
        try:
            if not filename:
                timestamp = int(time.time())
                filename = f"screenshot_{timestamp}.png"

            await self.page.screenshot(path=filename, full_page=True)
            self.logger.info(f"Screenshot saved: {filename}")
            return filename

        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            return None

    async def extract_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """Извлечение детальной информации о вакансии"""
        try:
            await self.navigate_to(job_url)

            # Ждем загрузки контента
            await asyncio.sleep(2)

            details = await self.page.evaluate("""
                () => {
                    const title = document.querySelector("[data-qa='vacancy-title']")?.textContent?.trim();
                    const company = document.querySelector("[data-qa='vacancy-company-name']")?.textContent?.trim();
                    const salary = document.querySelector("[data-qa='vacancy-salary']")?.textContent?.trim();
                    const description = document.querySelector("[data-qa='vacancy-description']")?.textContent?.trim();
                    const requirements = document.querySelector("[data-qa='vacancy-requirements']")?.textContent?.trim();

                    return {
                        title: title,
                        company: company,
                        salary: salary,
                        description: description,
                        requirements: requirements
                    };
                }
            """)

            return details

        except Exception as e:
            self.logger.error(f"Could not extract job details: {e}")
            return None

    async def search_multiple_sites(self, query: str, sites: List[str] = None) -> List[JobPosting]:
        """Поиск вакансий на нескольких сайтах"""
        if sites is None:
            sites = ["hh_ru", "linkedin"]

        all_jobs = []

        for site in sites:
            try:
                if site == "hh_ru":
                    jobs = await self.search_jobs_hh(query)
                elif site == "linkedin":
                    jobs = await self.search_jobs_linkedin(query)
                else:
                    continue

                all_jobs.extend(jobs)
                await asyncio.sleep(1)  # Задержка между запросами

            except Exception as e:
                self.logger.error(f"Search failed on {site}: {e}")

        # Убираем дубликаты
        unique_jobs = []
        seen_urls = set()

        for job in all_jobs:
            if job.url not in seen_urls:
                unique_jobs.append(job)
                seen_urls.add(job.url)

        self.logger.info(f"Total unique jobs found: {len(unique_jobs)}")
        return unique_jobs

    def log_action(self, action: str, details: Dict[str, Any] = None):
        """Логирование действия"""
        entry = {
            'timestamp': time.time(),
            'action': action,
            'details': details or {}
        }
        self.action_history.append(entry)
        self.logger.info(f"Action logged: {action}")

    def get_action_history(self) -> List[Dict[str, Any]]:
        """Получение истории действий"""
        return self.action_history.copy()

    async def wait_and_click(self, selector: str, timeout: int = 5000):
        """Ожидание и клик по селектору"""
        try:
            element = self.page.locator(selector)
            await element.wait_for(timeout=timeout)
            await element.click()
            return True
        except Exception as e:
            self.logger.warning(f"Could not click {selector}: {e}")
            return False

    async def safe_fill(self, selector: str, text: str):
        """Безопасное заполнение поля"""
        try:
            element = self.page.locator(selector)
            await element.wait_for(timeout=3000)
            await element.fill(text)
            return True
        except Exception as e:
            self.logger.warning(f"Could not fill {selector}: {e}")
            return False