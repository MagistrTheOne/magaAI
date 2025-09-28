"""
Сервис для управления операционной системой.
Интегрирует существующие компоненты AIMagistr для OS контроля.
"""
import logging
import os
import subprocess
import platform
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class OSController:
    """Контроллер операционной системы с безопасностью"""

    def __init__(self):
        self.system = platform.system().lower()
        self.allowed_commands = self._get_allowed_commands()
        self.dangerous_commands = [
            'rm', 'del', 'delete', 'format', 'fdisk', 'mkfs',
            'shutdown', 'reboot', 'halt', 'poweroff',
            'sudo', 'su', 'chmod 777', 'dd', 'rm -rf', 'rmdir /s',
            'format c:', 'fdisk', 'mkfs', 'dd if=', 'curl | bash',
            'wget | bash', 'eval', 'exec', 'system', 'shell'
        ]
        self.audit_log = []

    def _get_allowed_commands(self) -> List[str]:
        """Получить список разрешенных команд"""
        from app.settings import settings
        
        # Используем whitelist из настроек
        if hasattr(settings, 'os_whitelist_commands'):
            return settings.os_whitelist_commands
        
        # Fallback базовые команды
        base_commands = [
            # Базовые команды
            'ls', 'dir', 'cd', 'pwd', 'echo', 'cat', 'type',
            'mkdir', 'md', 'copy', 'cp', 'move', 'mv', 'rm', 'del',
            'head', 'tail', 'grep', 'find', 'which', 'where',

            # Системные команды
            'start', 'open', 'explorer', 'finder',
            'notepad', 'gedit', 'code', 'nano', 'vim',
            'chrome', 'firefox', 'edge', 'safari',

            # Python и инструменты разработки
            'python', 'python3', 'pip', 'pip3', 'git', 'npm', 'node',

            # Сетевые команды
            'ping', 'curl', 'wget', 'ssh', 'scp',

            # Архиваторы
            'tar', 'zip', 'unzip', 'gzip', 'gunzip'
        ]

        # Добавляем системные команды
        if self.system == 'windows':
            base_commands.extend([
                'tasklist', 'netstat', 'ipconfig', 'systeminfo',
                'powershell', 'cmd', 'robocopy', 'xcopy',
                'schtasks', 'taskkill', 'shutdown'
            ])
        else:
            base_commands.extend([
                'ps', 'top', 'df', 'free', 'ifconfig', 'uname',
                'htop', 'lsof', 'kill', 'killall', 'systemctl',
                'journalctl', 'crontab', 'at', 'screen', 'tmux'
            ])

        return base_commands

    async def execute_command(self, command: str, user_id: int = None) -> Dict[str, Any]:
        """
        Выполнить команду ОС с проверками безопасности

        Args:
            command: Команда для выполнения
            user_id: ID пользователя (для логирования)

        Returns:
            Dict с результатом выполнения
        """
        logger.info(f"OS команда от пользователя {user_id}: {command}")

        # Проверки безопасности через security_enhancement
        from app.services.security_enhancement import security_enhancement
        security_check = security_enhancement.validate_command_safety(command, user_id or 0)

        if security_check['blocked'] or not self._is_command_safe(command):
            self._log_audit(user_id or 0, command, 'blocked', 'Security check failed')
            return {
                'success': False,
                'error': 'Команда заблокирована из соображений безопасности',
                'command': command,
                'warnings': security_check.get('warnings', [])
            }

        if security_check['warnings']:
            logger.warning(f"Предупреждения безопасности для команды: {security_check['warnings']}")

        try:
            # Выполняем команду асинхронно
            result = await self._run_command_async(command)

            success = result.get('returncode', 0) == 0
            status = 'success' if success else 'failed'

            # Аудит выполнения команды
            audit_reason = f"Return code: {result.get('returncode', 0)}"
            if result.get('stderr'):
                audit_reason += f", stderr: {result.get('stderr')[:100]}"
            self._log_audit(user_id or 0, command, status, audit_reason)

            logger.info(f"Команда выполнена успешно: {command[:50]}...")
            return {
                'success': success,
                'output': result.get('stdout', ''),
                'error': result.get('stderr', ''),
                'return_code': result.get('returncode', 0),
                'command': command
            }

        except Exception as e:
            self._log_audit(user_id or 0, command, 'error', str(e))
            logger.error(f"Ошибка выполнения команды: {e}")
            return {
                'success': False,
                'error': f'Ошибка выполнения: {str(e)}',
                'command': command
            }

    def _is_command_safe(self, command: str) -> bool:
        """Проверить безопасность команды"""
        command_lower = command.lower()

        # Проверяем на опасные команды
        for dangerous in self.dangerous_commands:
            if dangerous in command_lower:
                logger.warning(f"Опасная команда заблокирована: {command}")
                return False

        # Проверяем на разрешенные команды
        first_word = command.split()[0].lower()
        if first_word not in self.allowed_commands and not any(cmd in first_word for cmd in ['python', 'node', 'git']):
            logger.warning(f"Неразрешенная команда: {first_word}")
            return False

        return True
    
    def _check_command_safety(self, command: str, args: List[str]) -> Dict[str, Any]:
        """Детальная проверка безопасности команды"""
        command_lower = command.lower()
        
        # Проверяем на опасные паттерны
        dangerous_patterns = [
            r'rm\s+-rf', r'del\s+/s', r'format\s+c:', r'fdisk', r'mkfs',
            r'sudo\s+', r'su\s+', r'chmod\s+777', r'dd\s+if=',
            r'curl\s+.*\|\s*bash', r'wget\s+.*\|\s*bash',
            r'eval\s*\(', r'exec\s*\(', r'system\s*\(', r'shell\s*\('
        ]
        
        import re
        for pattern in dangerous_patterns:
            if re.search(pattern, command_lower):
                return {
                    'safe': False,
                    'reason': f'Dangerous pattern detected: {pattern}'
                }
        
        # Проверяем на разрешенные команды
        if command not in self.allowed_commands:
            return {
                'safe': False,
                'reason': f'Command not in whitelist: {command}'
            }
        
        return {'safe': True, 'reason': 'Command is safe'}
    
    def _log_audit(self, user_id: int, command: str, status: str, reason: str):
        """Логирование аудита команд"""
        from datetime import datetime
        
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'command': command,
            'status': status,
            'reason': reason
        }
        
        self.audit_log.append(audit_entry)
        logger.info(f"OS Audit: User {user_id} - {status} - {command} - {reason}")
        
        # Ограничиваем размер лога
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-500:]
    
    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Получить лог аудита"""
        return self.audit_log[-limit:]

    async def _run_command_async(self, command: str) -> Dict[str, Any]:
        """Выполнить команду асинхронно"""
        # Создаем subprocess
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True
        )

        # Ждем завершения
        stdout, stderr = await process.communicate()

        return {
            'stdout': stdout.decode('utf-8', errors='ignore') if stdout else '',
            'stderr': stderr.decode('utf-8', errors='ignore') if stderr else '',
            'returncode': process.returncode
        }

    async def open_file(self, file_path: str, user_id: int = None) -> Dict[str, Any]:
        """Открыть файл в соответствующем приложении"""
        try:
            if not Path(file_path).exists():
                return {
                    'success': False,
                    'error': f'Файл не найден: {file_path}'
                }

            if self.system == 'windows':
                command = f'start "" "{file_path}"'
            elif self.system == 'darwin':  # macOS
                command = f'open "{file_path}"'
            else:  # Linux
                command = f'xdg-open "{file_path}"'

            result = await self.execute_command(command, user_id)
            return result

        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка открытия файла: {str(e)}'
            }

    async def launch_application(self, app_name: str, user_id: int = None) -> Dict[str, Any]:
        """Запустить приложение"""
        try:
            if self.system == 'windows':
                command = f'start {app_name}'
            else:
                command = app_name

            result = await self.execute_command(command, user_id)
            return result

        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка запуска приложения: {str(e)}'
            }

    async def get_system_info(self) -> Dict[str, Any]:
        """Получить информацию о системе"""
        try:
            info = {
                'system': self.system,
                'platform': platform.platform(),
                'processor': platform.processor(),
                'python_version': platform.python_version()
            }

            # Информация о дисках
            try:
                import psutil
                disk = psutil.disk_usage('/')
                info['disk_total'] = disk.total
                info['disk_used'] = disk.used
                info['disk_free'] = disk.free
            except ImportError:
                info['disk_info'] = 'psutil не установлен'

            # Информация о памяти
            try:
                import psutil
                memory = psutil.virtual_memory()
                info['memory_total'] = memory.total
                info['memory_used'] = memory.used
                info['memory_free'] = memory.free
            except ImportError:
                info['memory_info'] = 'psutil не установлен'

            return {
                'success': True,
                'system_info': info
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка получения системной информации: {str(e)}'
            }

    async def list_directory(self, path: str = ".", user_id: int = None) -> Dict[str, Any]:
        """Показать содержимое директории"""
        try:
            if not Path(path).exists():
                return {
                    'success': False,
                    'error': f'Путь не найден: {path}'
                }

            if self.system == 'windows':
                command = f'dir "{path}"'
            else:
                command = f'ls -la "{path}"'

            result = await self.execute_command(command, user_id)
            return result

        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка чтения директории: {str(e)}'
            }

    async def create_directory(self, path: str, user_id: int = None) -> Dict[str, Any]:
        """Создать директорию"""
        try:
            if self.system == 'windows':
                command = f'mkdir "{path}"'
            else:
                command = f'mkdir -p "{path}"'

            result = await self.execute_command(command, user_id)
            return result

        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка создания директории: {str(e)}'
            }

    async def search_files(self, pattern: str, path: str = ".", user_id: int = None) -> Dict[str, Any]:
        """Найти файлы по шаблону"""
        try:
            if self.system == 'windows':
                command = f'where /r "{path}" *{pattern}* 2>nul || echo "Файлы не найдены"'
            else:
                command = f'find "{path}" -name "*{pattern}*" 2>/dev/null || echo "Файлы не найдены"'

            result = await self.execute_command(command, user_id)
            return result

        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка поиска файлов: {str(e)}'
            }

    def get_allowed_commands(self) -> List[str]:
        """Получить список разрешенных команд"""
        return self.allowed_commands.copy()

    def get_system_type(self) -> str:
        """Получить тип операционной системы"""
        return self.system
