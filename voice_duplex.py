# -*- coding: utf-8 -*-
"""
Voice Duplex - Двусторонний голосовой диалог
TTS↔STT с бардж-ином и приватным каналом "в ухо"
"""

import asyncio
import io
import threading
import time
import queue
from datetime import datetime
from typing import Optional, Callable, Dict, Any
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
import edge_tts
from pydub import AudioSegment
from loguru import logger


class VoiceDuplex:
    """
    Двусторонний голосовой диалог с AI
    - TTS → пользователь (основной канал)
    - STT ← пользователь (микрофон)
    - "В ухо" канал для приватных подсказок
    - Бардж-ин: авто-пауза TTS при речи пользователя
    """
    
    def __init__(self, 
                 main_output_device: Optional[int] = None,
                 ear_output_device: Optional[int] = None,
                 mic_input_device: Optional[int] = None,
                 response_callback: Optional[Callable] = None):
        """
        Инициализация дуплекс-голоса
        
        Args:
            main_output_device: Основной выход (CABLE Input для собеседований)
            ear_output_device: "В ухо" канал (CABLE-B или отдельные наушники)
            mic_input_device: Микрофон пользователя
            response_callback: Функция для обработки распознанной речи
        """
        self.main_output_device = main_output_device
        self.ear_output_device = ear_output_device
        self.mic_input_device = mic_input_device
        self.response_callback = response_callback
        
        # Состояние
        self.is_active = False
        self.is_speaking = False
        self.is_user_speaking = False
        self.tts_queue = queue.Queue()
        self.stt_queue = queue.Queue()
        
        # Потоки
        self.tts_thread = None
        self.stt_thread = None
        self.ear_thread = None
        self.stop_event = threading.Event()
        
        # Настройки
        self.sample_rate = 16000
        self.frame_duration = 0.1  # 100ms для быстрого отклика
        self.vad_threshold = 0.015  # Порог для детекции речи пользователя
        self.barge_in_threshold = 0.02  # Порог для бардж-ина
        
        # STT модель
        self.whisper_model = None
        self._init_whisper()
        
        # Бардж-ин состояние
        self.barge_in_active = True
        self.tts_paused = False
        self.user_speech_buffer = []
        
        logger.info("Voice Duplex инициализирован")
    
    def _init_whisper(self):
        """Инициализация Whisper для STT"""
        try:
            self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
            logger.info("Whisper модель загружена для дуплекс-режима")
        except Exception as e:
            logger.error(f"Ошибка загрузки Whisper: {e}")
            self.whisper_model = None
    
    def _find_devices(self):
        """Поиск аудио устройств"""
        devices = sd.query_devices()
        
        # Поиск основного выхода (CABLE Input)
        if self.main_output_device is None:
            for idx, device in enumerate(devices):
                if device["max_output_channels"] > 0 and "cable" in device["name"].lower():
                    self.main_output_device = idx
                    logger.info(f"Найден основной выход: {device['name']}")
                    break
        
        # Поиск "в ухо" канала (CABLE-B или альтернативный)
        if self.ear_output_device is None:
            for idx, device in enumerate(devices):
                if device["max_output_channels"] > 0 and ("cable-b" in device["name"].lower() or 
                                                         "ear" in device["name"].lower()):
                    self.ear_output_device = idx
                    logger.info(f"Найден 'в ухо' канал: {device['name']}")
                    break
        
        # Поиск микрофона
        if self.mic_input_device is None:
            for idx, device in enumerate(devices):
                if device["max_input_channels"] > 0 and ("microphone" in device["name"].lower() or 
                                                       "mic" in device["name"].lower()):
                    self.mic_input_device = idx
                    logger.info(f"Найден микрофон: {device['name']}")
                    break
    
    def _detect_user_speech(self, audio: np.ndarray) -> bool:
        """Детекция речи пользователя для бардж-ина"""
        rms = np.sqrt(np.mean(audio ** 2) + 1e-9)
        return rms > self.vad_threshold
    
    def _detect_barge_in(self, audio: np.ndarray) -> bool:
        """Детекция бардж-ина (пользователь перебивает AI)"""
        rms = np.sqrt(np.mean(audio ** 2) + 1e-9)
        return rms > self.barge_in_threshold
    
    def _stt_worker(self):
        """STT рабочий поток"""
        frame_len = int(self.sample_rate * self.frame_duration)
        silence_frames_needed = int(0.5 / self.frame_duration)  # 0.5 сек тишины
        
        audio_buffer = []
        silence_count = 0
        speaking = False
        
        try:
            with sd.InputStream(
                device=self.mic_input_device,
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=frame_len,
                latency="low"
            ) as stream:
                
                logger.info("STT слушает микрофон...")
                
                while not self.stop_event.is_set():
                    # Читаем аудио
                    audio_data, _ = stream.read(frame_len)
                    audio_data = audio_data.flatten()
                    
                    # Детекция речи пользователя
                    if self._detect_user_speech(audio_data):
                        audio_buffer.append(audio_data)
                        speaking = True
                        silence_count = 0
                        
                        # Проверяем бардж-ин
                        if self.barge_in_active and self.is_speaking:
                            if self._detect_barge_in(audio_data):
                                logger.info("🎤 Бардж-ин: пользователь перебивает")
                                self._pause_tts()
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
                            if text:
                                self.stt_queue.put(text)
                                logger.info(f"🎤 Пользователь сказал: {text}")
                            
                            # Очищаем буфер
                            audio_buffer.clear()
                            speaking = False
                            silence_count = 0
                    
                    # Ограничиваем размер буфера
                    if len(audio_buffer) > 100:  # ~10 секунд
                        audio_buffer = audio_buffer[-50:]
                        speaking = False
                        silence_count = 0
                    
                    time.sleep(0.01)
                    
        except Exception as e:
            logger.error(f"Ошибка в STT worker: {e}")
    
    def _transcribe_audio(self, audio: np.ndarray) -> str:
        """Транскрипция аудио"""
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
            return text.strip()
        except Exception as e:
            logger.error(f"Ошибка транскрипции: {e}")
            return ""
    
    def _tts_worker(self):
        """TTS рабочий поток"""
        logger.info("TTS worker запущен")
        
        while not self.stop_event.is_set():
            try:
                # Получаем текст для озвучивания
                text = self.tts_queue.get(timeout=1.0)
                
                if text:
                    self._speak_text(text)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Ошибка в TTS worker: {e}")
    
    def _speak_text(self, text: str):
        """Озвучивание текста"""
        if not text:
            return
        
        try:
            self.is_speaking = True
            logger.info(f"🔊 AI говорит: {text}")
            
            # Генерируем аудио через Edge TTS
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                audio_data = loop.run_until_complete(self._generate_tts_audio(text))
                
                # Проигрываем на основном выходе
                if self.main_output_device is not None:
                    sd.play(audio_data, self.sample_rate, device=self.main_output_device, blocking=True)
                
            finally:
                loop.close()
            
            self.is_speaking = False
            
        except Exception as e:
            logger.error(f"Ошибка озвучивания: {e}")
            self.is_speaking = False
    
    async def _generate_tts_audio(self, text: str) -> np.ndarray:
        """Генерация TTS аудио"""
        try:
            communicate = edge_tts.Communicate(text, "ru-RU-DmitryNeural", rate="+0%", pitch="+0%")
            mp3_bytes = b""
            
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_bytes += chunk["data"]
            
            # Конвертируем MP3 в PCM
            seg = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
            seg = seg.set_frame_rate(self.sample_rate).set_channels(1).set_sample_width(2)
            raw = seg.raw_data
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            
            return audio
            
        except Exception as e:
            logger.error(f"Ошибка генерации TTS: {e}")
            return np.array([])
    
    def _ear_worker(self):
        """Рабочий поток для "в ухо" канала"""
        logger.info("'В ухо' канал запущен")
        
        while not self.stop_event.is_set():
            try:
                # Получаем приватные подсказки
                if not self.stt_queue.empty():
                    user_text = self.stt_queue.get_nowait()
                    
                    # Анализируем и генерируем подсказку
                    hint = self._generate_ear_hint(user_text)
                    if hint and self.ear_output_device is not None:
                        self._speak_ear_hint(hint)
                
                time.sleep(0.1)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Ошибка в ear worker: {e}")
    
    def _generate_ear_hint(self, user_text: str) -> str:
        """Генерация подсказки "в ухо" на основе речи пользователя"""
        # Простая логика подсказок (можно заменить на AI)
        hints = {
            "зарплата": "💡 Спроси про equity и бонусы",
            "опыт": "💡 Расскажи про Prometheus проект",
            "компания": "💡 Узнай про техническую культуру",
            "время": "💡 Предложи конкретные даты",
            "удаленка": "💡 Уточни гибридный режим"
        }
        
        user_lower = user_text.lower()
        for keyword, hint in hints.items():
            if keyword in user_lower:
                return hint
        
        return ""
    
    def _speak_ear_hint(self, hint: str):
        """Озвучивание подсказки "в ухо" (тише)"""
        try:
            # Генерируем аудио с пониженной громкостью
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                audio_data = loop.run_until_complete(self._generate_tts_audio(hint))
                
                # Понижаем громкость для "в ухо"
                audio_data = audio_data * 0.3  # 30% громкости
                
                # Проигрываем на "в ухо" канале
                if self.ear_output_device is not None:
                    sd.play(audio_data, self.sample_rate, device=self.ear_output_device, blocking=True)
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Ошибка озвучивания подсказки: {e}")
    
    def _pause_tts(self):
        """Пауза TTS при бардж-ине"""
        self.tts_paused = True
        logger.info("⏸️ TTS приостановлен (бардж-ин)")
    
    def _resume_tts(self):
        """Возобновление TTS"""
        self.tts_paused = False
        logger.info("▶️ TTS возобновлен")
    
    def speak(self, text: str, ear_hint: str = ""):
        """Добавить текст в очередь для озвучивания"""
        if text:
            self.tts_queue.put(text)
        
        if ear_hint:
            self.tts_queue.put(f"[ПОДСКАЗКА] {ear_hint}")
    
    def start(self):
        """Запуск дуплекс-режима"""
        if self.is_active:
            logger.warning("Voice Duplex уже активен")
            return
        
        # Находим устройства
        self._find_devices()
        
        if self.main_output_device is None:
            logger.error("Основной выход не найден")
            return
        
        if self.mic_input_device is None:
            logger.error("Микрофон не найден")
            return
        
        # Запускаем потоки
        self.stop_event.clear()
        
        # STT поток
        self.stt_thread = threading.Thread(target=self._stt_worker, daemon=True)
        self.stt_thread.start()
        
        # TTS поток
        self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self.tts_thread.start()
        
        # "В ухо" поток
        if self.ear_output_device is not None:
            self.ear_thread = threading.Thread(target=self._ear_worker, daemon=True)
            self.ear_thread.start()
        
        self.is_active = True
        logger.info("🎙️ Voice Duplex активирован")
    
    def stop(self):
        """Остановка дуплекс-режима"""
        if not self.is_active:
            return
        
        self.stop_event.set()
        
        # Ждем завершения потоков
        if self.stt_thread:
            self.stt_thread.join(timeout=2.0)
        if self.tts_thread:
            self.tts_thread.join(timeout=2.0)
        if self.ear_thread:
            self.ear_thread.join(timeout=2.0)
        
        self.is_active = False
        logger.info("🛑 Voice Duplex остановлен")
    
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса"""
        return {
            "is_active": self.is_active,
            "is_speaking": self.is_speaking,
            "is_user_speaking": self.is_user_speaking,
            "barge_in_active": self.barge_in_active,
            "tts_paused": self.tts_paused,
            "main_output": self.main_output_device,
            "ear_output": self.ear_output_device,
            "mic_input": self.mic_input_device
        }


# =============== ТЕСТИРОВАНИЕ ===============

def test_voice_duplex():
    """Тестирование Voice Duplex"""
    print("🧪 Тестирование Voice Duplex...")
    
    def test_callback(text):
        print(f"🎤 Получена речь: {text}")
        return f"Понял: {text}"
    
    duplex = VoiceDuplex(response_callback=test_callback)
    
    # Запускаем
    duplex.start()
    
    print("🎙️ Дуплекс-режим активен")
    print("💬 Говорите с AI, он будет отвечать")
    print("🎧 Подсказки будут в 'в ухо' канале")
    print("⏹️ Нажмите Ctrl+C для остановки")
    
    try:
        # Тестовое озвучивание
        duplex.speak("Привет! Я готов к диалогу.")
        time.sleep(2)
        duplex.speak("Скажите что-нибудь, и я отвечу.")
        
        # Ждем
        while True:
            time.sleep(1)
            status = duplex.get_status()
            if not status["is_active"]:
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Остановка тестирования...")
    finally:
        duplex.stop()


if __name__ == "__main__":
    test_voice_duplex()
