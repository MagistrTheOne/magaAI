# -*- coding: utf-8 -*-
"""
Система безопасности AIMagistr 3.0
Сканирование секретов, PII и аудит
"""

import os
import re
import json
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import time


class SecretsScanner:
    """
    Сканер секретов и PII для AIMagistr 3.0
    """
    
    def __init__(self):
        self.logger = logging.getLogger("SecretsScanner")
        
        # Паттерны для поиска секретов
        self.secret_patterns = {
            # API ключи
            'api_key': [
                r'api[_-]?key["\s]*[:=]["\s]*([a-zA-Z0-9_-]{20,})',
                r'apikey["\s]*[:=]["\s]*([a-zA-Z0-9_-]{20,})',
                r'api_key["\s]*[:=]["\s]*([a-zA-Z0-9_-]{20,})'
            ],
            # Токены
            'token': [
                r'token["\s]*[:=]["\s]*([a-zA-Z0-9_-]{20,})',
                r'access_token["\s]*[:=]["\s]*([a-zA-Z0-9_-]{20,})',
                r'bearer_token["\s]*[:=]["\s]*([a-zA-Z0-9_-]{20,})'
            ],
            # Пароли
            'password': [
                r'password["\s]*[:=]["\s]*([^"\s]{8,})',
                r'passwd["\s]*[:=]["\s]*([^"\s]{8,})',
                r'pwd["\s]*[:=]["\s]*([^"\s]{8,})'
            ],
            # Секретные ключи
            'secret': [
                r'secret["\s]*[:=]["\s]*([a-zA-Z0-9_-]{20,})',
                r'secret_key["\s]*[:=]["\s]*([a-zA-Z0-9_-]{20,})',
                r'private_key["\s]*[:=]["\s]*([a-zA-Z0-9_-]{20,})'
            ],
            # Telegram Bot Token
            'telegram_bot_token': [
                r'telegram[_-]?bot[_-]?token["\s]*[:=]["\s]*([0-9]{8,}:[a-zA-Z0-9_-]{35})',
                r'bot[_-]?token["\s]*[:=]["\s]*([0-9]{8,}:[a-zA-Z0-9_-]{35})'
            ],
            # Yandex API
            'yandex_api_key': [
                r'yandex[_-]?api[_-]?key["\s]*[:=]["\s]*([a-zA-Z0-9_-]{20,})',
                r'yandex[_-]?folder[_-]?id["\s]*[:=]["\s]*([a-zA-Z0-9_-]{20,})'
            ],
            # AWS
            'aws_access_key': [
                r'aws[_-]?access[_-]?key[_-]?id["\s]*[:=]["\s]*([A-Z0-9]{20})',
                r'aws[_-]?secret[_-]?access[_-]?key["\s]*[:=]["\s]*([a-zA-Z0-9/+=]{40})'
            ],
            # Google
            'google_api_key': [
                r'google[_-]?api[_-]?key["\s]*[:=]["\s]*([a-zA-Z0-9_-]{39})',
                r'gcp[_-]?api[_-]?key["\s]*[:=]["\s]*([a-zA-Z0-9_-]{39})'
            ],
            # GitHub
            'github_token': [
                r'github[_-]?token["\s]*[:=]["\s]*([a-zA-Z0-9_-]{36})',
                r'gh[_-]?token["\s]*[:=]["\s]*([a-zA-Z0-9_-]{36})'
            ]
        }
        
        # Паттерны для PII
        self.pii_patterns = {
            # Email
            'email': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            # Телефон
            'phone': [
                r'\+?[1-9]\d{1,14}',
                r'\+?[1-9]\d{3,14}',
                r'\+?[1-9]\d{2,3}[-.\s]?\d{3,4}[-.\s]?\d{2,4}'
            ],
            # ИНН
            'inn': [
                r'\b\d{10}\b',
                r'\b\d{12}\b'
            ],
            # СНИЛС
            'snils': [
                r'\b\d{3}-\d{3}-\d{3}\s\d{2}\b'
            ],
            # Паспорт
            'passport': [
                r'\b\d{4}\s\d{6}\b'
            ],
            # Банковские карты
            'credit_card': [
                r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'
            ]
        }
        
        # Исключения (файлы, которые не нужно сканировать)
        self.exclude_patterns = [
            r'\.git/',
            r'node_modules/',
            r'__pycache__/',
            r'\.env\.example',
            r'railway\.env\.example',
            r'\.md$',
            r'\.txt$',
            r'\.log$',
            r'\.tmp$',
            r'\.cache$'
        ]
        
        # Результаты сканирования
        self.scan_results = {
            'secrets': [],
            'pii': [],
            'files_scanned': 0,
            'scan_time': 0,
            'timestamp': None
        }
    
    def _should_scan_file(self, file_path: str) -> bool:
        """Проверка, нужно ли сканировать файл"""
        try:
            # Проверяем исключения
            for pattern in self.exclude_patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    return False
            
            # Проверяем расширение файла
            allowed_extensions = ['.py', '.js', '.ts', '.json', '.yaml', '.yml', '.env', '.config']
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext not in allowed_extensions:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка проверки файла {file_path}: {e}")
            return False
    
    def _scan_file_content(self, file_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """Сканирование содержимого файла"""
        results = {
            'secrets': [],
            'pii': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Сканируем секреты
            for secret_type, patterns in self.secret_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        secret_value = match.group(1) if match.groups() else match.group(0)
                        
                        # Проверяем, что это не пример
                        if self._is_example_value(secret_value):
                            continue
                        
                        # Находим номер строки
                        line_num = content[:match.start()].count('\n') + 1
                        
                        results['secrets'].append({
                            'type': secret_type,
                            'value': secret_value,
                            'file': file_path,
                            'line': line_num,
                            'context': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                            'severity': self._get_severity(secret_type)
                        })
            
            # Сканируем PII
            for pii_type, patterns in self.pii_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        pii_value = match.group(0)
                        
                        # Проверяем, что это не пример
                        if self._is_example_value(pii_value):
                            continue
                        
                        # Находим номер строки
                        line_num = content[:match.start()].count('\n') + 1
                        
                        results['pii'].append({
                            'type': pii_type,
                            'value': pii_value,
                            'file': file_path,
                            'line': line_num,
                            'context': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                            'severity': 'medium'
                        })
            
        except Exception as e:
            self.logger.error(f"Ошибка сканирования файла {file_path}: {e}")
        
        return results
    
    def _is_example_value(self, value: str) -> bool:
        """Проверка, является ли значение примером"""
        example_patterns = [
            r'your_.*',
            r'example_.*',
            r'test_.*',
            r'sample_.*',
            r'placeholder',
            r'xxx',
            r'123',
            r'000',
            r'fake',
            r'dummy'
        ]
        
        for pattern in example_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False
    
    def _get_severity(self, secret_type: str) -> str:
        """Определение серьезности найденного секрета"""
        high_severity = ['password', 'secret', 'private_key', 'aws_secret_access_key']
        medium_severity = ['api_key', 'token', 'telegram_bot_token', 'yandex_api_key']
        
        if secret_type in high_severity:
            return 'high'
        elif secret_type in medium_severity:
            return 'medium'
        else:
            return 'low'
    
    def scan_directory(self, directory: str, recursive: bool = True) -> Dict[str, Any]:
        """Сканирование директории на наличие секретов"""
        start_time = time.time()
        
        self.scan_results = {
            'secrets': [],
            'pii': [],
            'files_scanned': 0,
            'scan_time': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            directory_path = Path(directory)
            
            if not directory_path.exists():
                self.logger.error(f"Директория не существует: {directory}")
                return self.scan_results
            
            # Собираем файлы для сканирования
            files_to_scan = []
            
            if recursive:
                for file_path in directory_path.rglob('*'):
                    if file_path.is_file() and self._should_scan_file(str(file_path)):
                        files_to_scan.append(str(file_path))
            else:
                for file_path in directory_path.iterdir():
                    if file_path.is_file() and self._should_scan_file(str(file_path)):
                        files_to_scan.append(str(file_path))
            
            self.logger.info(f"Найдено {len(files_to_scan)} файлов для сканирования")
            
            # Сканируем файлы
            for file_path in files_to_scan:
                try:
                    file_results = self._scan_file_content(file_path)
                    
                    self.scan_results['secrets'].extend(file_results['secrets'])
                    self.scan_results['pii'].extend(file_results['pii'])
                    self.scan_results['files_scanned'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Ошибка сканирования файла {file_path}: {e}")
            
            # Подсчитываем статистику
            self.scan_results['scan_time'] = time.time() - start_time
            
            # Группируем по серьезности
            self.scan_results['severity_stats'] = self._get_severity_stats()
            
            self.logger.info(f"Сканирование завершено: {self.scan_results['files_scanned']} файлов, "
                           f"{len(self.scan_results['secrets'])} секретов, "
                           f"{len(self.scan_results['pii'])} PII")
            
        except Exception as e:
            self.logger.error(f"Ошибка сканирования директории: {e}")
        
        return self.scan_results
    
    def _get_severity_stats(self) -> Dict[str, int]:
        """Получение статистики по серьезности"""
        stats = {'high': 0, 'medium': 0, 'low': 0}
        
        for secret in self.scan_results['secrets']:
            severity = secret.get('severity', 'low')
            stats[severity] += 1
        
        return stats
    
    def get_report(self) -> str:
        """Получение отчета о сканировании"""
        if not self.scan_results['timestamp']:
            return "Сканирование не проводилось"
        
        report = f"""
# Отчет о сканировании безопасности AIMagistr 3.0

**Время сканирования:** {self.scan_results['timestamp']}
**Файлов просканировано:** {self.scan_results['files_scanned']}
**Время выполнения:** {self.scan_results['scan_time']:.2f} секунд

## Найденные секреты: {len(self.scan_results['secrets'])}

"""
        
        # Группируем секреты по типу
        secrets_by_type = {}
        for secret in self.scan_results['secrets']:
            secret_type = secret['type']
            if secret_type not in secrets_by_type:
                secrets_by_type[secret_type] = []
            secrets_by_type[secret_type].append(secret)
        
        for secret_type, secrets in secrets_by_type.items():
            report += f"### {secret_type.upper()}: {len(secrets)} найдено\n\n"
            
            for secret in secrets:
                report += f"- **Файл:** {secret['file']}\n"
                report += f"  **Строка:** {secret['line']}\n"
                report += f"  **Значение:** {secret['value'][:20]}...\n"
                report += f"  **Контекст:** {secret['context']}\n"
                report += f"  **Серьезность:** {secret['severity']}\n\n"
        
        # PII
        if self.scan_results['pii']:
            report += f"## Найденные PII: {len(self.scan_results['pii'])}\n\n"
            
            pii_by_type = {}
            for pii in self.scan_results['pii']:
                pii_type = pii['type']
                if pii_type not in pii_by_type:
                    pii_by_type[pii_type] = []
                pii_by_type[pii_type].append(pii)
            
            for pii_type, pii_list in pii_by_type.items():
                report += f"### {pii_type.upper()}: {len(pii_list)} найдено\n\n"
                
                for pii in pii_list:
                    report += f"- **Файл:** {pii['file']}\n"
                    report += f"  **Строка:** {pii['line']}\n"
                    report += f"  **Значение:** {pii['value']}\n"
                    report += f"  **Контекст:** {pii['context']}\n\n"
        
        # Статистика по серьезности
        if self.scan_results.get('severity_stats'):
            stats = self.scan_results['severity_stats']
            report += f"## Статистика по серьезности\n\n"
            report += f"- **Высокая:** {stats['high']}\n"
            report += f"- **Средняя:** {stats['medium']}\n"
            report += f"- **Низкая:** {stats['low']}\n\n"
        
        return report
    
    def save_report(self, output_file: str = "security_scan_report.md"):
        """Сохранение отчета в файл"""
        try:
            report = self.get_report()
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            self.logger.info(f"Отчет сохранен: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения отчета: {e}")
            return False
    
    def get_scan_summary(self) -> Dict[str, Any]:
        """Получение краткой сводки сканирования"""
        return {
            'timestamp': self.scan_results['timestamp'],
            'files_scanned': self.scan_results['files_scanned'],
            'scan_time': self.scan_results['scan_time'],
            'secrets_found': len(self.scan_results['secrets']),
            'pii_found': len(self.scan_results['pii']),
            'severity_stats': self.scan_results.get('severity_stats', {}),
            'has_high_severity': any(
                secret.get('severity') == 'high' 
                for secret in self.scan_results['secrets']
            )
        }
    
    def clear_results(self):
        """Очистка результатов сканирования"""
        self.scan_results = {
            'secrets': [],
            'pii': [],
            'files_scanned': 0,
            'scan_time': 0,
            'timestamp': None
        }


# Функция для тестирования
def test_secrets_scanner():
    """Тестирование сканера секретов"""
    scanner = SecretsScanner()
    
    print("Testing Secrets Scanner...")
    
    # Сканируем текущую директорию
    results = scanner.scan_directory(".", recursive=False)
    
    print(f"Files scanned: {results['files_scanned']}")
    print(f"Secrets found: {len(results['secrets'])}")
    print(f"PII found: {len(results['pii'])}")
    
    # Сохраняем отчет
    scanner.save_report("test_security_report.md")
    
    # Краткая сводка
    summary = scanner.get_scan_summary()
    print(f"Summary: {summary}")


if __name__ == "__main__":
    test_secrets_scanner()
