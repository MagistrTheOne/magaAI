# -*- coding: utf-8 -*-
"""
Voice Trigger Core - Wake Phrase Detection
"Мага, запускай — пора взрывать рынок"
"""

import asyncio
import io
import re
import threading
import time
from datetime import datetime
from typing import Optional, List, Callable
import queue

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from loguru import logger


class VoiceTrigger:
    """
    Wake phrase detector с VAD + STT
    """
    
    def __init__(self, 
                 wake_phrase: str = "мага запускай пора взрывать рынок",
                 mic_device: Optional[int] = None,
                 response_callback: Optional[Callable] = None):
        """
        Инициализация Voice Trigger
        
        Args:
            wake_phrase: Фраза-триггер (без пунктуации, lowercase)
            mic_device: Индекс микрофона (None = автоопределение)
            response_callback: Функция для вызова при срабатывании
        """
        self.wake_phrase = wake_phrase.lower()
        self.mic_device = mic_device
        self.response_callback = response_callback
        
        # Состояние
        self.is_listening = False
        self.is_triggered = False
        self.last_trigger_time = 0
        self.debounce_seconds = 8.0  # Дебаунс между срабатываниями
        
        # VAD настройки
        self.sample_rate = 16000
        self.frame_duration = 0.25  # сек
        self.vad_threshold = 0.01
        self.silence_duration = 0.8  # сек тишины для завершения
        
        # STT модель
        self.whisper_model = None
        self._init_whisper()
        
        # Потоки
        self.listener_thread = None
        self.stop_event = threading.Event()
        
        # Реакции на триггер
        self.trigger_responses = [
            "Слушаю, командир.",
            "Выполняю, босс.",
            "Читаю логи… рынок дрожит.",
            "Боевые пайплайны подгружены.",
            "Готов к уничтожению лимитов."
        ]
        
        # Регексы для распознавания (с опечатками и вариантами)
        self._compile_patterns()
        
        logger.info(f"Voice Trigger инициализирован: '{self.wake_phrase}'")
    
    def _init_whisper(self):
        """Инициализация Whisper модели"""
        try:
            self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
            logger.info("Whisper модель загружена (tiny)")
        except Exception as e:
            logger.error(f"Ошибка загрузки Whisper: {e}")
            self.whisper_model = None
    
    def _compile_patterns(self):
        """Компиляция регексов для распознавания фразы"""
        # Основные варианты фразы
        patterns = [
            r"мага\s+запускай\s+пора\s+взрывать\s+рынок",
            r"мага\s+запускай\s+взрывать\s+рынок",
            r"мага\s+запускай\s+пора",
            r"мага\s+взрывать\s+рынок",
            r"мага\s+запускай",
            r"мага\s+пора\s+взрывать",
        ]
        
        # Добавляем варианты с опечатками
        typos = [
            (r"мага", r"мага|маг|магаа|магааа"),
            (r"запускай", r"запускай|запуска|запускаа|запускааа"),
            (r"пора", r"пора|пор|пораа|порааа"),
            (r"взрывать", r"взрывать|взрыва|взрываа|взрывааа"),
            (r"рынок", r"рынок|рынк|рынка|рынкаа"),
        ]
        
        # Создаем регексы с опечатками
        for typo_old, typo_new in typos:
            for i, pattern in enumerate(patterns):
                patterns.append(pattern.replace(typo_old, typo_new))
        
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        logger.info(f"Скомпилировано {len(self.patterns)} паттернов для распознавания")
    
    def _find_microphone(self) -> Optional[int]:
        """Поиск микрофона"""
        if self.mic_device is not None:
            return self.mic_device
        
        # Ищем микрофон по ключевым словам
        mic_keywords = ["microphone", "mic", "микрофон", "audio", "input"]
        
        for idx, device in enumerate(sd.query_devices()):
            if device["max_input_channels"] > 0:
                device_name = device["name"].lower()
                if any(keyword in device_name for keyword in mic_keywords):
                    logger.info(f"Найден микрофон: {device['name']}")
                    return idx
        
        # Fallback на первое доступное устройство ввода
        for idx, device in enumerate(sd.query_devices()):
            if device["max_input_channels"] > 0:
                logger.info(f"Используем микрофон: {device['name']}")
                return idx
        
        logger.error("Микрофон не найден!")
        return None
    
    def _detect_speech(self, audio: np.ndarray) -> bool:
        """VAD - детекция речи"""
        rms = np.sqrt(np.mean(audio ** 2) + 1e-9)
        return rms > self.vad_threshold
    
    def _transcribe_audio(self, audio: np.ndarray) -> str:
        """Транскрипция аудио через Whisper"""
        if self.whisper_model is None:
            return ""
        
        try:
            segments, _ = self.whisper_model.transcribe(
                audio, 
                language="ru", 
                vad_filter=False,
                beam_size=1,
                best_of=1
            )
            text = " ".join(segment.text.strip() for segment in segments)
            return text.lower().strip()
        except Exception as e:
            logger.error(f"Ошибка транскрипции: {e}")
            return ""
    
    def _check_wake_phrase(self, text: str) -> bool:
        """Проверка на соответствие wake phrase"""
        if not text:
            return False
        
        # Проверяем все паттерны
        for pattern in self.patterns:
            if pattern.search(text):
                logger.info(f"Wake phrase обнаружена: '{text}'")
                return True
        
        return False
    
    def _listener_worker(self):
        """Основной цикл прослушивания"""
        frame_len = int(self.sample_rate * self.frame_duration)
        silence_frames_needed = int(self.silence_duration / self.frame_duration)
        
        # Буфер для накопления аудио
        audio_buffer = []
        silence_count = 0
        speaking = False
        
        try:
            # Открываем поток
            with sd.InputStream(
                device=self.mic_device,
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=frame_len,
                latency="low"
            ) as stream:
                
                logger.info("Voice Trigger слушает...")
                
                while not self.stop_event.is_set():
                    # Читаем аудио
                    audio_data, _ = stream.read(frame_len)
                    audio_data = audio_data.flatten()
                    
                    # VAD
                    if self._detect_speech(audio_data):
                        audio_buffer.append(audio_data)
                        speaking = True
                        silence_count = 0
                    else:
                        if speaking:
                            silence_count += 1
                            audio_buffer.append(audio_data)
                    
                    # Проверяем завершение речи
                    if speaking and silence_count >= silence_frames_needed:
                        if audio_buffer:
                            # Объединяем аудио
                            full_audio = np.concatenate(audio_buffer)
                            
                            # Транскрибируем
                            text = self._transcribe_audio(full_audio)
                            
                            # Проверяем wake phrase
                            if self._check_wake_phrase(text):
                                self._handle_trigger()
                            
                            # Очищаем буфер
                            audio_buffer.clear()
                            speaking = False
                            silence_count = 0
                    
                    # Ограничиваем размер буфера
                    if len(audio_buffer) > 50:  # ~12.5 секунд
                        audio_buffer = audio_buffer[-20:]
                        speaking = False
                        silence_count = 0
                    
                    time.sleep(0.01)  # Не нагружаем CPU
                    
        except Exception as e:
            logger.error(f"Ошибка в listener_worker: {e}")
        finally:
            logger.info("Voice Trigger остановлен")
    
    def _handle_trigger(self):
        """Обработка срабатывания триггера"""
        current_time = time.time()
        
        # Проверяем дебаунс
        if current_time - self.last_trigger_time < self.debounce_seconds:
            logger.info("Триггер проигнорирован (дебаунс)")
            return
        
        self.last_trigger_time = current_time
        self.is_triggered = True
        
        logger.info("🎯 WAKE PHRASE TRIGGERED!")
        
        # Выбираем случайную реакцию
        response = np.random.choice(self.trigger_responses)
        logger.info(f"Реакция: {response}")
        
        # Вызываем callback
        if self.response_callback:
            try:
                self.response_callback(response)
            except Exception as e:
                logger.error(f"Ошибка в response_callback: {e}")
    
    def start_listening(self):
        """Запуск прослушивания"""
        if self.is_listening:
            logger.warning("Voice Trigger уже слушает")
            return
        
        # Находим микрофон
        self.mic_device = self._find_microphone()
        if self.mic_device is None:
            logger.error("Не удалось найти микрофон")
            return
        
        # Запускаем поток
        self.stop_event.clear()
        self.listener_thread = threading.Thread(target=self._listener_worker, daemon=True)
        self.listener_thread.start()
        
        self.is_listening = True
        logger.info("Voice Trigger запущен")
    
    def stop_listening(self):
        """Остановка прослушивания"""
        if not self.is_listening:
            return
        
        self.stop_event.set()
        if self.listener_thread:
            self.listener_thread.join(timeout=2.0)
        
        self.is_listening = False
        logger.info("Voice Trigger остановлен")
    
    def get_status(self) -> dict:
        """Получение статуса"""
        return {
            "is_listening": self.is_listening,
            "is_triggered": self.is_triggered,
            "mic_device": self.mic_device,
            "wake_phrase": self.wake_phrase,
            "last_trigger": self.last_trigger_time,
            "whisper_loaded": self.whisper_model is not None
        }


# =============== ТЕСТИРОВАНИЕ ===============

def test_voice_trigger():
    """Тестирование Voice Trigger"""
    print("🧪 Тестирование Voice Trigger...")
    
    def test_callback(response):
        print(f"🎯 Триггер сработал! Реакция: {response}")
    
    # Создаем триггер
    trigger = VoiceTrigger(
        wake_phrase="мага запускай пора взрывать рынок",
        response_callback=test_callback
    )
    
    # Запускаем
    trigger.start_listening()
    
    print("🎙️ Скажите: 'Мага, запускай — пора взрывать рынок'")
    print("⏹️ Нажмите Ctrl+C для остановки")
    
    try:
        while True:
            time.sleep(1)
            status = trigger.get_status()
            if status["is_triggered"]:
                print(f"✅ Статус: {status}")
                break
    except KeyboardInterrupt:
        print("\n🛑 Остановка тестирования...")
    finally:
        trigger.stop_listening()


if __name__ == "__main__":
    test_voice_trigger()
