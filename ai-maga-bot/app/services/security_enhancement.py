"""
Улучшенная безопасность для AI-Maga.
"""
import logging
import hashlib
import secrets
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class SecurityEnhancement:
    """Улучшенная система безопасности"""

    def __init__(self):
        self.audit_log = []
        self.active_sessions = {}
        self.suspicious_activities = []

    def hash_sensitive_data(self, data: str) -> str:
        """Хэширование чувствительных данных для логов"""
        if not data or len(data) < 4:
            return "***"

        # Хэшируем, оставляя первые и последние символы
        hashed = hashlib.sha256(data.encode()).hexdigest()[:8]
        return f"{data[:2]}***{hashed}***{data[-2:]}"
    
    def mask_pii_in_text(self, text: str) -> str:
        """Маскирование PII в тексте"""
        import re
        
        # Маскируем email адреса
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                     lambda m: f"{m.group(0)[:3]}***{m.group(0)[-3:]}", text)
        
        # Маскируем номера телефонов
        text = re.sub(r'\b\+?[1-9]\d{1,14}\b', 
                     lambda m: f"{m.group(0)[:3]}***{m.group(0)[-3:]}", text)
        
        # Маскируем API ключи и токены
        text = re.sub(r'\b[A-Za-z0-9]{20,}\b', 
                     lambda m: f"{m.group(0)[:4]}***{m.group(0)[-4:]}", text)
        
        return text

    def validate_command_safety(self, command: str, user_id: int) -> Dict[str, bool]:
        """Валидация безопасности команды"""
        result = {
            'safe': True,
            'warnings': [],
            'blocked': False
        }

        # Блокировка опасных команд
        dangerous_patterns = [
            'rm -rf /', 'format', 'fdisk', 'mkfs',
            'sudo su', 'chmod 777', '> /dev/null',
            'curl.*|.*wget.*|.*bash'
        ]

        command_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                result['safe'] = False
                result['blocked'] = True
                result['warnings'].append(f"Опасная команда обнаружена: {pattern}")
                break

        # Предупреждения для подозрительных команд
        warning_patterns = [
            'password', 'token', 'key', 'secret',
            'sudo', 'admin', 'root'
        ]

        for pattern in warning_patterns:
            if pattern in command_lower:
                result['warnings'].append(f"Подозрительное слово: {pattern}")

        # Логирование проверки
        self.audit_command_check(user_id, command, result)

        return result

    def audit_command_check(self, user_id: int, command: str, result: Dict):
        """Аудит проверки команды"""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'action': 'command_check',
            'command_hash': self.hash_sensitive_data(command),
            'result': result,
            'ip': 'unknown'  # В реальности брать из запроса
        }

        self.audit_log.append(audit_entry)

        # Ограничение размера лога
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-500:]

    def audit_user_action(self, user_id: int, action: str, details: Dict = None):
        """Аудит действия пользователя"""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'action': action,
            'details': details or {}
        }

        self.audit_log.append(audit_entry)

    def detect_suspicious_activity(self, user_id: int, activity: str) -> bool:
        """Обнаружение подозрительной активности"""
        # Простая логика обнаружения
        suspicious_patterns = [
            'multiple_failed_commands',
            'unusual_time_access',
            'sensitive_data_access'
        ]

        is_suspicious = any(pattern in activity for pattern in suspicious_patterns)

        if is_suspicious:
            self.suspicious_activities.append({
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'activity': activity,
                'severity': 'medium'
            })

        return is_suspicious

    def generate_secure_token(self, length: int = 32) -> str:
        """Генерация безопасного токена"""
        return secrets.token_hex(length)

    def validate_session(self, session_id: str) -> bool:
        """Валидация сессии"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            if session['expires'] > datetime.now():
                return True
            else:
                # Удаляем истекшую сессию
                del self.active_sessions[session_id]

        return False

    def create_session(self, user_id: int, duration_minutes: int = 60) -> str:
        """Создание сессии"""
        session_id = self.generate_secure_token(16)
        expires = datetime.now() + timedelta(minutes=duration_minutes)

        self.active_sessions[session_id] = {
            'user_id': user_id,
            'created': datetime.now(),
            'expires': expires
        }

        return session_id

    def get_audit_log(self, user_id: Optional[int] = None, limit: int = 100) -> List[Dict]:
        """Получение лога аудита"""
        log = self.audit_log

        if user_id is not None:
            log = [entry for entry in log if entry.get('user_id') == user_id]

        return log[-limit:]

    def get_security_report(self) -> Dict:
        """Получение отчета безопасности"""
        return {
            'total_audit_entries': len(self.audit_log),
            'active_sessions': len(self.active_sessions),
            'suspicious_activities': len(self.suspicious_activities),
            'recent_warnings': [
                entry for entry in self.audit_log[-50:]
                if entry.get('result', {}).get('warnings')
            ]
        }

    def cleanup_expired_sessions(self):
        """Очистка истекших сессий"""
        current_time = datetime.now()
        expired_sessions = [
            session_id for session_id, session in self.active_sessions.items()
            if session['expires'] < current_time
        ]

        for session_id in expired_sessions:
            del self.active_sessions[session_id]

        if expired_sessions:
            logger.info(f"Очищено {len(expired_sessions)} истекших сессий")


# Глобальный экземпляр системы безопасности
security_enhancement = SecurityEnhancement()
