# -*- coding: utf-8 -*-
"""
Скрипт для поиска секретов в коде
"""

import os
import re
import sys
from typing import List, Dict, Tuple
from pathlib import Path


class SecretScanner:
    """
    Сканер секретов в коде
    """
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        
        # Паттерны для поиска секретов
        self.secret_patterns = [
            # API ключи
            r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
            r'apikey\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            
            # Токены
            r'token\s*=\s*["\'][^"\']+["\']',
            r'access[_-]?token\s*=\s*["\'][^"\']+["\']',
            r'bearer[_-]?token\s*=\s*["\'][^"\']+["\']',
            
            # Секреты
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'client[_-]?secret\s*=\s*["\'][^"\']+["\']',
            r'private[_-]?key\s*=\s*["\'][^"\']+["\']',
            
            # ID
            r'client[_-]?id\s*=\s*["\'][^"\']+["\']',
            r'app[_-]?id\s*=\s*["\'][^"\']+["\']',
            
            # Пароли
            r'password\s*=\s*["\'][^"\']+["\']',
            r'passwd\s*=\s*["\'][^"\']+["\']',
            r'pwd\s*=\s*["\'][^"\']+["\']',
            
            # URL с секретами
            r'https?://[^"\']*[?&](?:key|token|secret|password)=[^"\']*',
            
            # Хардкод ключей
            r'["\'][A-Za-z0-9+/]{20,}["\']',  # Base64-like strings
            r'["\'][A-Za-z0-9]{32,}["\']',    # Long alphanumeric strings
        ]
        
        # Исключения (файлы/папки)
        self.exclude_patterns = [
            r'\.git/',
            r'__pycache__/',
            r'\.pyc$',
            r'\.env$',
            r'\.env\.example$',
            r'railway\.env\.example$',
            r'node_modules/',
            r'venv/',
            r'\.venv/',
            r'build/',
            r'dist/',
            r'\.pytest_cache/',
            r'\.coverage',
            r'\.tox/',
        ]
        
        # Исключения (содержимое)
        self.content_exceptions = [
            r'your_.*_key',
            r'your_.*_token',
            r'your_.*_secret',
            r'example\.com',
            r'localhost',
            r'127\.0\.0\.1',
            r'placeholder',
            r'CHANGE_ME',
            r'REPLACE_ME',
            r'your_.*_here',
        ]
    
    def should_skip_file(self, file_path: Path) -> bool:
        """Проверка, нужно ли пропустить файл"""
        file_str = str(file_path)
        
        for pattern in self.exclude_patterns:
            if re.search(pattern, file_str, re.IGNORECASE):
                return True
        
        return False
    
    def is_exception_content(self, content: str) -> bool:
        """Проверка, является ли содержимое исключением"""
        content_lower = content.lower()
        
        for pattern in self.content_exceptions:
            if re.search(pattern, content_lower):
                return True
        
        return False
    
    def scan_file(self, file_path: Path) -> List[Dict[str, any]]:
        """Сканирование файла на секреты"""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                for pattern in self.secret_patterns:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    
                    for match in matches:
                        content = match.group()
                        
                        # Проверяем исключения
                        if self.is_exception_content(content):
                            continue
                        
                        findings.append({
                            'file': str(file_path),
                            'line': line_num,
                            'content': content.strip(),
                            'pattern': pattern,
                            'context': line.strip()
                        })
        
        except Exception as e:
            print(f"Ошибка чтения файла {file_path}: {e}")
        
        return findings
    
    def scan_directory(self) -> List[Dict[str, any]]:
        """Сканирование директории"""
        all_findings = []
        
        for file_path in self.root_dir.rglob('*'):
            if file_path.is_file() and not self.should_skip_file(file_path):
                findings = self.scan_file(file_path)
                all_findings.extend(findings)
        
        return all_findings
    
    def generate_report(self, findings: List[Dict[str, any]]) -> str:
        """Генерация отчета"""
        if not findings:
            return "OK: No secrets found!"
        
        report = f"WARNING: Found {len(findings)} potential secrets:\n\n"
        
        # Группировка по файлам
        files = {}
        for finding in findings:
            file_path = finding['file']
            if file_path not in files:
                files[file_path] = []
            files[file_path].append(finding)
        
        for file_path, file_findings in files.items():
            report += f"File: {file_path} ({len(file_findings)} findings):\n"
            
            for finding in file_findings:
                report += f"  Line {finding['line']}: {finding['content']}\n"
                report += f"     Context: {finding['context']}\n"
                report += f"     Pattern: {finding['pattern']}\n\n"
        
        return report
    
    def suggest_fixes(self, findings: List[Dict[str, any]]) -> str:
        """Предложения по исправлению"""
        if not findings:
            return ""
        
        suggestions = "\nRecommendations:\n\n"
        
        # Уникальные файлы
        files = set(finding['file'] for finding in findings)
        
        for file_path in files:
            suggestions += f"{file_path}:\n"
            suggestions += f"  - Replace hardcoded values with os.getenv('VARIABLE_NAME')\n"
            suggestions += f"  - Add variable to .env.example\n"
            suggestions += f"  - Ensure value doesn't get into git\n\n"
        
        suggestions += "General recommendations:\n"
        suggestions += "  - Use environment variables for all secrets\n"
        suggestions += "  - Add .env to .gitignore\n"
        suggestions += "  - Use Railway Variables for production\n"
        suggestions += "  - Regularly scan code for secrets\n"
        
        return suggestions


def main():
    """Главная функция"""
    print("Scanning for secrets in code...")
    
    scanner = SecretScanner()
    findings = scanner.scan_directory()
    
    report = scanner.generate_report(findings)
    print(report)
    
    if findings:
        suggestions = scanner.suggest_fixes(findings)
        print(suggestions)
        
        # Возвращаем код ошибки если найдены секреты
        sys.exit(1)
    else:
        print("OK: Scanning completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
