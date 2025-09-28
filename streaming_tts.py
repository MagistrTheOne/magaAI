# -*- coding: utf-8 -*-
"""
Streaming TTS Module
Потоковая генерация и проигрывание TTS с низкой задержкой и бардж-ином
"""

import asyncio
import io
import queue
import threading
import time
from typing import Optional, Callable, List
import numpy as np
import sounddevice as sd
import edge_tts
from pydub import AudioSegment


class StreamingTTS:
    """
    Потоковый TTS с чанками и бардж-ином
    """
    
    def __init__(self, 
                 voice: str = "ru-RU-DmitryNeural",
                 output_device_idx: int = None,
                 chunk_duration: float = 0.5,
                 barge_in_threshold: float = 0.01,
                 on_barge_in: Optional[Callable] = None):
        """
        Args:
            voice: Голос для TTS
            output_device_idx: Индекс выходного устройства
            chunk_duration: Длительность чанка в секундах
            barge_in_threshold: Порог для бардж-ина
            on_barge_in: Callback при бардж-ине
        """
        self.voice = voice
        self.output_device_idx = output_device_idx
        self.chunk_duration = chunk_duration
        self.barge_in_threshold = barge_in_threshold
        self.on_barge_in = on_barge_in
        
        # Состояние
        self.is_playing = False
        self.is_paused = False
        self.audio_queue = queue.Queue()
        self.playback_thread = None
        self.monitor_thread = None
        self.stop_event = threading.Event()
        
        # Бардж-ин мониторинг
        self.monitor_mic_idx = None
        self.monitor_active = False
        
    def set_output_device(self, device_idx: int):
        """Установить выходное устройство"""
        self.output_device_idx = device_idx
        
    def set_monitor_microphone(self, mic_idx: int):
        """Установить микрофон для мониторинга бардж-ина"""
        self.monitor_mic_idx = mic_idx
        
    def start(self):
        """Запуск потокового TTS"""
        if self.is_playing:
            return
            
        self.is_playing = True
        self.stop_event.clear()
        
        # Запуск потока воспроизведения
        self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self.playback_thread.start()
        
        # Запуск мониторинга бардж-ина
        if self.monitor_mic_idx is not None:
            self.monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
            self.monitor_thread.start()
            
    def stop(self):
        """Остановка потокового TTS"""
        self.is_playing = False
        self.stop_event.set()
        
        # Очистка очереди
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
                
        # Ожидание завершения потоков
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=1.0)
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
            
    def pause(self):
        """Пауза воспроизведения"""
        self.is_paused = True
        
    def resume(self):
        """Возобновление воспроизведения"""
        self.is_paused = False
        
    async def speak_streaming(self, text: str):
        """Потоковое озвучивание текста"""
        if not self.is_playing:
            return
            
        try:
            # Генерируем аудио чанками
            communicate = edge_tts.Communicate(text, self.voice, rate="+0%", pitch="+0%")
            
            async for chunk in communicate.stream():
                if chunk["type"] == "audio" and not self.stop_event.is_set():
                    # Конвертируем MP3 в PCM
                    pcm = self._mp3_to_pcm(chunk["data"])
                    if pcm is not None:
                        self.audio_queue.put(pcm)
                        
        except Exception as e:
            print(f"[StreamingTTS] Ошибка генерации: {e}")
            
    def _mp3_to_pcm(self, mp3_data: bytes) -> Optional[np.ndarray]:
        """Конвертация MP3 в PCM"""
        try:
            seg = AudioSegment.from_file(io.BytesIO(mp3_data), format="mp3")
            seg = seg.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            raw = seg.raw_data
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            return audio
        except Exception as e:
            print(f"[StreamingTTS] Ошибка конвертации: {e}")
            return None
            
    def _playback_worker(self):
        """Поток воспроизведения аудио"""
        while self.is_playing and not self.stop_event.is_set():
            try:
                # Получаем чанк из очереди
                audio_chunk = self.audio_queue.get(timeout=0.1)
                
                # Проверяем паузу
                if self.is_paused:
                    time.sleep(0.1)
                    continue
                    
                # Воспроизводим чанк
                if self.output_device_idx is not None:
                    sd.play(audio_chunk, 16000, device=self.output_device_idx, blocking=True)
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[StreamingTTS] Ошибка воспроизведения: {e}")
                
    def _monitor_worker(self):
        """Поток мониторинга бардж-ина"""
        if self.monitor_mic_idx is None:
            return
            
        try:
            # Настройки мониторинга
            sr = 16000
            frame_len = int(sr * self.chunk_duration)
            
            stream = sd.InputStream(
                samplerate=sr,
                channels=1,
                dtype="float32",
                device=self.monitor_mic_idx,
                blocksize=frame_len,
                latency="low"
            )
            stream.start()
            
            while self.is_playing and not self.stop_event.is_set():
                try:
                    block = stream.read(frame_len)[0]
                    rms = np.sqrt(np.mean(block ** 2) + 1e-9)
                    
                    # Проверяем порог бардж-ина
                    if rms > self.barge_in_threshold:
                        self._handle_barge_in()
                        
                except Exception as e:
                    print(f"[StreamingTTS] Ошибка мониторинга: {e}")
                    
            stream.stop()
            stream.close()
            
        except Exception as e:
            print(f"[StreamingTTS] Ошибка инициализации мониторинга: {e}")
            
    def _handle_barge_in(self):
        """Обработка бардж-ина"""
        if self.on_barge_in:
            self.on_barge_in()
        else:
            # По умолчанию - пауза
            self.pause()
            
    def get_queue_size(self) -> int:
        """Получить размер очереди"""
        return self.audio_queue.qsize()
        
    def is_queue_empty(self) -> bool:
        """Проверить, пуста ли очередь"""
        return self.audio_queue.empty()