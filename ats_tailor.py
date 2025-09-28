# -*- coding: utf-8 -*-
"""
ATS Tailor Module
Автоподгон резюме под JD (RAG + правила), экспорт в PDF
"""

import os
import re
import json
import time
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import difflib


class ATSTailor:
    """
    ATS-оптимизация резюме под описание вакансии
    """
    
    def __init__(self, 
                 resume_dir: str = "resumes",
                 jd_dir: str = "job_descriptions",
                 output_dir: str = "tailored_resumes"):
        """
        Args:
            resume_dir: Директория с резюме
            jd_dir: Директория с описаниями вакансий
            output_dir: Директория для оптимизированных резюме
        """
        self.resume_dir = Path(resume_dir)
        self.jd_dir = Path(jd_dir)
        self.output_dir = Path(output_dir)
        
        # Создаем директории
        self.resume_dir.mkdir(exist_ok=True)
        self.jd_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        # База знаний
        self.skill_synonyms = {
            'python': ['python', 'py', 'python3', 'python 3'],
            'javascript': ['javascript', 'js', 'ecmascript'],
            'react': ['react', 'reactjs', 'react.js'],
            'node.js': ['node.js', 'nodejs', 'node'],
            'docker': ['docker', 'containerization'],
            'kubernetes': ['kubernetes', 'k8s', 'kube'],
            'aws': ['aws', 'amazon web services', 'amazon aws'],
            'machine learning': ['ml', 'machine learning', 'машинное обучение'],
            'ai': ['ai', 'artificial intelligence', 'искусственный интеллект'],
            'data science': ['data science', 'data scientist', 'data analysis']
        }
        
        # ATS правила
        self.ats_rules = {
            'keywords': {
                'weight': 0.4,
                'min_match': 0.3
            },
            'skills': {
                'weight': 0.3,
                'min_match': 0.5
            },
            'experience': {
                'weight': 0.2,
                'min_match': 0.4
            },
            'education': {
                'weight': 0.1,
                'min_match': 0.2
            }
        }
        
    def analyze_job_description(self, jd_text: str) -> Dict:
        """Анализ описания вакансии"""
        try:
            analysis = {
                'keywords': self._extract_keywords(jd_text),
                'skills': self._extract_skills(jd_text),
                'requirements': self._extract_requirements(jd_text),
                'experience_level': self._extract_experience_level(jd_text),
                'education_requirements': self._extract_education_requirements(jd_text),
                'company_info': self._extract_company_info(jd_text),
                'salary_range': self._extract_salary_range(jd_text),
                'location': self._extract_location(jd_text),
                'remote_options': self._extract_remote_options(jd_text)
            }
            
            return analysis
            
        except Exception as e:
            print(f"[ATSTailor] Ошибка анализа JD: {e}")
            return {}
            
    def _extract_keywords(self, text: str) -> List[str]:
        """Извлечение ключевых слов"""
        # Убираем стоп-слова и извлекаем значимые слова
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an'}
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [word for word in words if word not in stop_words]
        
        # Подсчитываем частоту
        keyword_freq = {}
        for word in keywords:
            keyword_freq[word] = keyword_freq.get(word, 0) + 1
            
        # Сортируем по частоте
        sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
        
        return [word for word, freq in sorted_keywords[:20]]
        
    def _extract_skills(self, text: str) -> List[str]:
        """Извлечение навыков"""
        skills = []
        
        # Ищем упоминания технологий
        tech_patterns = [
            r'\b(python|java|javascript|react|node\.?js|docker|kubernetes|aws|azure|gcp)\b',
            r'\b(machine learning|ml|ai|artificial intelligence)\b',
            r'\b(data science|data analysis|big data)\b',
            r'\b(sql|nosql|mongodb|postgresql|mysql)\b',
            r'\b(git|github|gitlab|jenkins|ci/cd)\b'
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            skills.extend(matches)
            
        return list(set(skills))
        
    def _extract_requirements(self, text: str) -> List[str]:
        """Извлечение требований"""
        requirements = []
        
        # Ищем требования в разных форматах
        req_patterns = [
            r'(?:required|must have|обязательно)[:\s]*([^.]+)',
            r'(?:preferred|nice to have|желательно)[:\s]*([^.]+)',
            r'(?:experience|опыт)[:\s]*([^.]+)',
            r'(?:skills|навыки)[:\s]*([^.]+)'
        ]
        
        for pattern in req_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            requirements.extend(matches)
            
        return requirements
        
    def _extract_experience_level(self, text: str) -> str:
        """Извлечение уровня опыта"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['senior', 'lead', 'principal', 'staff']):
            return 'senior'
        elif any(word in text_lower for word in ['junior', 'entry', 'graduate', 'intern']):
            return 'junior'
        elif any(word in text_lower for word in ['mid', 'middle', 'intermediate']):
            return 'mid'
        else:
            return 'unknown'
            
    def _extract_education_requirements(self, text: str) -> List[str]:
        """Извлечение требований к образованию"""
        education = []
        
        edu_patterns = [
            r'\b(bachelor|master|phd|doctorate|degree|диплом|высшее)\b',
            r'\b(computer science|cs|it|informatics|информатика)\b',
            r'\b(engineering|математика|физика)\b'
        ]
        
        for pattern in edu_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            education.extend(matches)
            
        return list(set(education))
        
    def _extract_company_info(self, text: str) -> Dict:
        """Извлечение информации о компании"""
        company_info = {}
        
        # Ищем название компании
        company_patterns = [
            r'at\s+([A-Z][a-zA-Z\s&]+)',
            r'company[:\s]*([A-Z][a-zA-Z\s&]+)',
            r'organization[:\s]*([A-Z][a-zA-Z\s&]+)'
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                company_info['name'] = match.group(1).strip()
                break
                
        return company_info
        
    def _extract_salary_range(self, text: str) -> Optional[Tuple[int, int]]:
        """Извлечение диапазона зарплаты"""
        salary_patterns = [
            r'\$?(\d{1,3}(?:,\d{3})*(?:k|000)?)\s*[-–—]\s*\$?(\d{1,3}(?:,\d{3})*(?:k|000)?)',
            r'(\d+)\s*[-–—]\s*(\d+)\s*(?:k|thousand|тысяч)',
            r'от\s*(\d+)\s*до\s*(\d+)'
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    min_salary = int(match.group(1).replace(',', '').replace('k', '000'))
                    max_salary = int(match.group(2).replace(',', '').replace('k', '000'))
                    return (min_salary, max_salary)
                except ValueError:
                    continue
                    
        return None
        
    def _extract_location(self, text: str) -> Optional[str]:
        """Извлечение локации"""
        location_patterns = [
            r'location[:\s]*([A-Z][a-zA-Z\s,]+)',
            r'based\s+in\s+([A-Z][a-zA-Z\s,]+)',
            r'office\s+in\s+([A-Z][a-zA-Z\s,]+)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
                
        return None
        
    def _extract_remote_options(self, text: str) -> bool:
        """Проверка возможности удаленной работы"""
        remote_keywords = ['remote', 'work from home', 'wfh', 'hybrid', 'удаленно', 'удаленная работа']
        return any(keyword in text.lower() for keyword in remote_keywords)
        
    def tailor_resume(self, resume_text: str, jd_analysis: Dict) -> Dict:
        """Оптимизация резюме под вакансию"""
        try:
            # Анализируем текущее резюме
            resume_analysis = self.analyze_job_description(resume_text)
            
            # Вычисляем совпадения
            matches = self._calculate_matches(resume_analysis, jd_analysis)
            
            # Генерируем рекомендации
            recommendations = self._generate_recommendations(resume_analysis, jd_analysis, matches)
            
            # Создаем оптимизированную версию
            tailored_resume = self._create_tailored_resume(resume_text, recommendations)
            
            return {
                'original_resume': resume_text,
                'tailored_resume': tailored_resume,
                'matches': matches,
                'recommendations': recommendations,
                'ats_score': self._calculate_ats_score(matches)
            }
            
        except Exception as e:
            print(f"[ATSTailor] Ошибка оптимизации резюме: {e}")
            return {}
            
    def _calculate_matches(self, resume_analysis: Dict, jd_analysis: Dict) -> Dict:
        """Вычисление совпадений"""
        matches = {}
        
        # Совпадение ключевых слов
        resume_keywords = set(resume_analysis.get('keywords', []))
        jd_keywords = set(jd_analysis.get('keywords', []))
        keyword_match = len(resume_keywords & jd_keywords) / max(len(jd_keywords), 1)
        matches['keywords'] = keyword_match
        
        # Совпадение навыков
        resume_skills = set(resume_analysis.get('skills', []))
        jd_skills = set(jd_analysis.get('skills', []))
        skill_match = len(resume_skills & jd_skills) / max(len(jd_skills), 1)
        matches['skills'] = skill_match
        
        # Совпадение опыта
        resume_exp = resume_analysis.get('experience_level', 'unknown')
        jd_exp = jd_analysis.get('experience_level', 'unknown')
        exp_match = 1.0 if resume_exp == jd_exp else 0.5
        matches['experience'] = exp_match
        
        # Совпадение образования
        resume_edu = set(resume_analysis.get('education_requirements', []))
        jd_edu = set(jd_analysis.get('education_requirements', []))
        edu_match = len(resume_edu & jd_edu) / max(len(jd_edu), 1)
        matches['education'] = edu_match
        
        return matches
        
    def _generate_recommendations(self, resume_analysis: Dict, jd_analysis: Dict, matches: Dict) -> List[str]:
        """Генерация рекомендаций по улучшению"""
        recommendations = []
        
        # Рекомендации по ключевым словам
        if matches['keywords'] < 0.3:
            missing_keywords = set(jd_analysis.get('keywords', [])) - set(resume_analysis.get('keywords', []))
            if missing_keywords:
                recommendations.append(f"Добавьте ключевые слова: {', '.join(list(missing_keywords)[:5])}")
                
        # Рекомендации по навыкам
        if matches['skills'] < 0.5:
            missing_skills = set(jd_analysis.get('skills', [])) - set(resume_analysis.get('skills', []))
            if missing_skills:
                recommendations.append(f"Добавьте навыки: {', '.join(list(missing_skills)[:5])}")
                
        # Рекомендации по опыту
        if matches['experience'] < 0.5:
            jd_exp = jd_analysis.get('experience_level', 'unknown')
            recommendations.append(f"Подчеркните опыт уровня: {jd_exp}")
            
        # Рекомендации по образованию
        if matches['education'] < 0.2:
            jd_edu = jd_analysis.get('education_requirements', [])
            if jd_edu:
                recommendations.append(f"Упомяните образование: {', '.join(jd_edu)}")
                
        return recommendations
        
    def _create_tailored_resume(self, original_resume: str, recommendations: List[str]) -> str:
        """Создание оптимизированного резюме"""
        # Пока что возвращаем оригинальное резюме
        # В будущем здесь будет логика автоматического редактирования
        return original_resume
        
    def _calculate_ats_score(self, matches: Dict) -> float:
        """Вычисление ATS-оценки"""
        total_score = 0
        total_weight = 0
        
        for category, match_score in matches.items():
            if category in self.ats_rules:
                weight = self.ats_rules[category]['weight']
                total_score += match_score * weight
                total_weight += weight
                
        return total_score / max(total_weight, 1)
        
    def save_tailored_resume(self, tailored_data: Dict, filename: str) -> bool:
        """Сохранение оптимизированного резюме"""
        try:
            output_path = self.output_dir / f"{filename}_tailored.json"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(tailored_data, f, ensure_ascii=False, indent=2)
                
            print(f"[ATSTailor] Оптимизированное резюме сохранено: {output_path}")
            return True
            
        except Exception as e:
            print(f"[ATSTailor] Ошибка сохранения: {e}")
            return False
            
    def load_resume(self, filename: str) -> Optional[str]:
        """Загрузка резюме из файла"""
        try:
            resume_path = self.resume_dir / filename
            if resume_path.exists():
                with open(resume_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return None
        except Exception as e:
            print(f"[ATSTailor] Ошибка загрузки резюме: {e}")
            return None
            
    def load_job_description(self, filename: str) -> Optional[str]:
        """Загрузка описания вакансии из файла"""
        try:
            jd_path = self.jd_dir / filename
            if jd_path.exists():
                with open(jd_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return None
        except Exception as e:
            print(f"[ATSTailor] Ошибка загрузки JD: {e}")
            return None
