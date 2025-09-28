"""
Интеграция голосового управления для AI-Maga.
Использует существующие компоненты AIMagistr.
"""
import asyncio
import logging
import threading
import time
from typing import Optional, Callable, Dict, Any
import queue

logger = logging.getLogger(__name__)


class VoiceIntegration:
    """Интеграция голосового управления"""

    def __init__(self):
        self.is_listening = False
        self.voice_thread = None
        self.command_queue = queue.Queue()
        self.on_command_callback = None
        self.is_muted = False
        self.wake_word_detected = False

    async def start_listening(self):
        """Начать прослушивание голосовых команд"""
        if self.is_listening:
            return

        self.is_listening = True

        # Запускаем голосовое прослушивание в отдельном потоке
        self.voice_thread = threading.Thread(target=self._voice_listening_loop, daemon=True)
        self.voice_thread.start()

        logger.info("Голосовое прослушивание запущено")

    def stop_listening(self):
        """Остановить прослушивание"""
        self.is_listening = False
        if self.voice_thread:
            self.voice_thread.join(timeout=1.0)
        logger.info("Голосовое прослушивание остановлено")

    def _voice_listening_loop(self):
        """Основной цикл прослушивания голоса"""
        try:
            # Импортируем существующий voice_trigger
            import sys
            sys.path.append('..')

            try:
                from voice_trigger import VoiceTrigger

                # Инициализируем voice trigger
                voice_trigger = VoiceTrigger()
                voice_trigger.on_command = self._on_voice_command

                logger.info("Voice trigger инициализирован")

                # Основной цикл
                while self.is_listening:
                    try:
                        # Здесь будет логика обработки голоса
                        # Пока просто симуляция
                        time.sleep(1.0)

                    except Exception as e:
                        logger.error(f"Ошибка в цикле голосового прослушивания: {e}")
                        time.sleep(2.0)

            except ImportError as e:
                logger.warning(f"Voice trigger недоступен, используем заглушку: {e}")
                self._fallback_voice_listening()

        except Exception as e:
            logger.error(f"Критическая ошибка голосового прослушивания: {e}")

    def _fallback_voice_listening(self):
        """Резервный вариант прослушивания - недоступен"""
        logger.warning("Voice trigger недоступен - голосовое управление отключено")
        # Не делаем ничего - просто ждем завершения
        while self.is_listening:
            time.sleep(1.0)

    def _on_voice_command(self, command: str, confidence: float = 0.0):
        """Обработчик распознанной голосовой команды"""
        from app.settings import settings
        
        # Проверяем порог уверенности из настроек
        min_confidence = getattr(settings, 'voice_confidence_threshold', 0.6)
        if confidence < min_confidence:
            logger.info(f"Низкая уверенность голосовой команды: {confidence} < {min_confidence}")
            return

        # Проверяем на wake word
        wake_word = getattr(settings, 'voice_wake_word', 'Hey AI-Maga')
        if wake_word.lower() in command.lower():
            self.wake_word_detected = True
            logger.info(f"Wake word обнаружен: {wake_word}")
            return

        # Если не обнаружен wake word и не в режиме прослушивания
        if not self.wake_word_detected and not self.is_listening:
            logger.info("Wake word не обнаружен, игнорируем команду")
            return

        # Проверяем mute статус
        if self.is_muted:
            logger.info("Голосовое управление заглушено")
            return

        logger.info(f"Распознана голосовая команда: {command} (уверенность: {confidence})")

        # Добавляем в очередь команд
        self.command_queue.put({
            'command': command,
            'confidence': confidence,
            'timestamp': time.time()
        })

        # Вызываем callback если установлен
        if self.on_command_callback:
            try:
                # Запускаем callback в event loop
                asyncio.run(self.on_command_callback(command, confidence))
            except Exception as e:
                logger.error(f"Ошибка в callback голосовой команды: {e}")

    def set_command_callback(self, callback: Callable):
        """Установить callback для обработки команд"""
        self.on_command_callback = callback

    def get_pending_commands(self) -> list:
        """Получить ожидающие команды"""
        commands = []
        while not self.command_queue.empty():
            try:
                commands.append(self.command_queue.get_nowait())
            except queue.Empty:
                break
        return commands

    async def process_voice_command(self, command: str) -> Dict[str, Any]:
        """Обработать голосовую команду"""
        # Здесь можно добавить специальную логику для голосовых команд
        # Например, более простой синтаксис, wake words и т.д.

        wake_words = ["мага", "ai", "ассистент", "компьютер"]

        # Проверяем на wake word
        command_lower = command.lower()
        for wake_word in wake_words:
            if wake_word in command_lower:
                # Убираем wake word из команды
                clean_command = command_lower.replace(wake_word, "").strip()
                if clean_command:
                    command = clean_command
                    break

        # Специальные голосовые команды
        voice_commands = {
            "стоп": "stop",
            "пауза": "pause",
            "продолжить": "resume",
            "открой браузер": "open browser",
            "закрой программу": "close application",
            "что у меня запланировано": "show schedule",
            "какие задачи": "show tasks"
        }

        # Преобразуем голосовую команду
        for voice_cmd, standard_cmd in voice_commands.items():
            if voice_cmd in command_lower:
                command = standard_cmd
                break

        return {
            'original_command': command,
            'processed_command': command,
            'is_voice': True
        }

    def get_status(self) -> Dict[str, Any]:
        """Получить статус голосовой интеграции"""
        return {
            'listening': self.is_listening,
            'pending_commands': self.command_queue.qsize(),
            'thread_alive': self.voice_thread.is_alive() if self.voice_thread else False,
            'is_muted': self.is_muted,
            'wake_word_detected': self.wake_word_detected
        }
    
    def mute_voice(self):
        """Заглушить голосовое управление"""
        self.is_muted = True
        logger.info("Голосовое управление заглушено")
    
    def unmute_voice(self):
        """Включить голосовое управление"""
        self.is_muted = False
        logger.info("Голосовое управление включено")


# Глобальный экземпляр голосовой интеграции
voice_integration = VoiceIntegration()
