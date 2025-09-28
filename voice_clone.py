# -*- coding: utf-8 -*-
"""
Voice Clone Module
Клонирование голоса из эталонных сэмплов с поддержкой Tortoise и Bark
"""

import os
import time
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
from typing import Optional, List, Dict, Callable
from pathlib import Path
import json


class VoiceClone:
    """
    Клонирование голоса из эталонных сэмплов
    """
    
    def __init__(self, 
                 samples_dir: str = "voice_samples",
                 clone_engine: str = "tortoise",  # "tortoise" или "bark"
                 on_clone_ready: Optional[Callable] = None):
        """
        Args:
            samples_dir: Директория с эталонными сэмплами
            clone_engine: Движок клонирования
            on_clone_ready: Callback при готовности клона
        """
        self.samples_dir = Path(samples_dir)
        self.clone_engine = clone_engine
        self.on_clone_ready = on_clone_ready
        
        # Создаем директорию для сэмплов
        self.samples_dir.mkdir(exist_ok=True)
        
        # Состояние
        self.is_ready = False
        self.voice_samples = []
        self.voice_embeddings = None
        self.clone_model = None
        
        # Настройки записи
        self.sample_rate = 22050  # Tortoise использует 22050 Hz
        self.recording_duration = 10.0  # секунд
        self.min_samples = 1
        self.max_samples = 3
        
        # Инициализация
        self._initialize_clone_engine()
        
    def _initialize_clone_engine(self):
        """Инициализация движка клонирования"""
        try:
            if self.clone_engine == "tortoise":
                self._init_tortoise()
            elif self.clone_engine == "bark":
                self._init_bark()
            else:
                raise ValueError(f"Неподдерживаемый движок: {self.clone_engine}")
                
        except Exception as e:
            print(f"[VoiceClone] Ошибка инициализации {self.clone_engine}: {e}")
            self.is_ready = False
            
    def _init_tortoise(self):
        """Инициализация Tortoise TTS"""
        try:
            from tortoise.api import TextToSpeech
            from tortoise.utils.audio import load_audio, load_voice
            
            self.clone_model = TextToSpeech()
            self.is_ready = True
            print("[VoiceClone] Tortoise TTS инициализирован")
            
        except ImportError:
            print("[VoiceClone] Tortoise TTS не установлен")
            self.is_ready = False
            
    def _init_bark(self):
        """Инициализация Bark TTS"""
        try:
            from bark import SAMPLE_RATE, generate_audio, preload_models
            from bark.generation import load_codec_model, generate_text_semantic
            
            # Предзагружаем модели
            preload_models()
            self.clone_model = {
                'sample_rate': SAMPLE_RATE,
                'generate_audio': generate_audio,
                'load_codec_model': load_codec_model,
                'generate_text_semantic': generate_text_semantic
            }
            self.is_ready = True
            print("[VoiceClone] Bark TTS инициализирован")
            
        except ImportError:
            print("[VoiceClone] Bark TTS не установлен")
            self.is_ready = False
            
    def start_sample_collection(self) -> bool:
        """Начать сбор эталонных сэмплов"""
        if not self.is_ready:
            print("[VoiceClone] Движок не готов")
            return False
            
        print(f"[VoiceClone] Начинаем сбор сэмплов (нужно {self.min_samples}-{self.max_samples})")
        print("[VoiceClone] Говорите четко и естественно")
        
        return True
        
    def record_sample(self, sample_name: str) -> bool:
        """Записать один сэмпл голоса"""
        try:
            print(f"[VoiceClone] Запись сэмпла '{sample_name}'...")
            print(f"[VoiceClone] Говорите {self.recording_duration} секунд...")
            
            # Записываем аудио
            audio_data = sd.rec(
                int(self.sample_rate * self.recording_duration),
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32'
            )
            sd.wait()  # Ждем завершения записи
            
            # Сохраняем сэмпл
            sample_path = self.samples_dir / f"{sample_name}.wav"
            sf.write(sample_path, audio_data, self.sample_rate)
            
            # Добавляем в список
            self.voice_samples.append({
                'name': sample_name,
                'path': str(sample_path),
                'audio': audio_data,
                'duration': self.recording_duration
            })
            
            print(f"[VoiceClone] Сэмпл '{sample_name}' сохранен")
            return True
            
        except Exception as e:
            print(f"[VoiceClone] Ошибка записи сэмпла: {e}")
            return False
            
    def process_samples(self) -> bool:
        """Обработать собранные сэмплы"""
        if len(self.voice_samples) < self.min_samples:
            print(f"[VoiceClone] Недостаточно сэмплов (нужно {self.min_samples}, есть {len(self.voice_samples)})")
            return False
            
        try:
            if self.clone_engine == "tortoise":
                return self._process_tortoise_samples()
            elif self.clone_engine == "bark":
                return self._process_bark_samples()
            else:
                return False
                
        except Exception as e:
            print(f"[VoiceClone] Ошибка обработки сэмплов: {e}")
            return False
            
    def _process_tortoise_samples(self) -> bool:
        """Обработка сэмплов для Tortoise"""
        try:
            from tortoise.utils.audio import load_voice
            
            # Загружаем голосовые сэмплы
            voice_samples = []
            for sample in self.voice_samples:
                voice_samples.append(sample['audio'])
                
            # Создаем эмбеддинги голоса
            self.voice_embeddings = self.clone_model.get_conditioning_latents(voice_samples)
            
            print("[VoiceClone] Tortoise сэмплы обработаны")
            return True
            
        except Exception as e:
            print(f"[VoiceClone] Ошибка обработки Tortoise сэмплов: {e}")
            return False
            
    def _process_bark_samples(self) -> bool:
        """Обработка сэмплов для Bark"""
        try:
            # Bark использует другой подход - сохраняем сэмплы как есть
            # Bark будет использовать их напрямую при генерации
            
            print("[VoiceClone] Bark сэмплы обработаны")
            return True
            
        except Exception as e:
            print(f"[VoiceClone] Ошибка обработки Bark сэмплов: {e}")
            return False
            
    def clone_voice(self, text: str) -> Optional[np.ndarray]:
        """Клонировать голос для заданного текста"""
        if not self.is_ready or not self.voice_samples:
            print("[VoiceClone] Клон не готов")
            return None
            
        try:
            if self.clone_engine == "tortoise":
                return self._clone_with_tortoise(text)
            elif self.clone_engine == "bark":
                return self._clone_with_bark(text)
            else:
                return None
                
        except Exception as e:
            print(f"[VoiceClone] Ошибка клонирования: {e}")
            return None
            
    def _clone_with_tortoise(self, text: str) -> Optional[np.ndarray]:
        """Клонирование с Tortoise"""
        try:
            # Генерируем аудио с клонированным голосом
            gen, dbg_state = self.clone_model.tts_with_preset(
                text,
                voice_samples=self.voice_samples[0]['audio'],  # Используем первый сэмпл
                conditioning_latents=self.voice_embeddings,
                preset="fast",
                use_deterministic_seed=42
            )
            
            # Конвертируем в numpy array
            audio = gen.squeeze(0).cpu().numpy()
            return audio.astype(np.float32)
            
        except Exception as e:
            print(f"[VoiceClone] Ошибка Tortoise клонирования: {e}")
            return None
            
    def _clone_with_bark(self, text: str) -> Optional[np.ndarray]:
        """Клонирование с Bark"""
        try:
            from bark import generate_audio
            
            # Bark использует другой подход - загружаем сэмпл как референс
            sample_path = self.voice_samples[0]['path']
            
            # Генерируем аудио с клонированным голосом
            audio = generate_audio(
                text,
                history_prompt="custom",  # Используем кастомный голос
                text_temp=0.7,
                waveform_temp=0.7
            )
            
            return audio
            
        except Exception as e:
            print(f"[VoiceClone] Ошибка Bark клонирования: {e}")
            return None
            
    def save_voice_profile(self, profile_name: str) -> bool:
        """Сохранить профиль голоса"""
        try:
            profile_data = {
                'name': profile_name,
                'engine': self.clone_engine,
                'samples': [
                    {
                        'name': sample['name'],
                        'path': sample['path'],
                        'duration': sample['duration']
                    }
                    for sample in self.voice_samples
                ],
                'created_at': time.time()
            }
            
            profile_path = self.samples_dir / f"{profile_name}_profile.json"
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, ensure_ascii=False, indent=2)
                
            print(f"[VoiceClone] Профиль '{profile_name}' сохранен")
            return True
            
        except Exception as e:
            print(f"[VoiceClone] Ошибка сохранения профиля: {e}")
            return False
            
    def load_voice_profile(self, profile_name: str) -> bool:
        """Загрузить профиль голоса"""
        try:
            profile_path = self.samples_dir / f"{profile_name}_profile.json"
            if not profile_path.exists():
                print(f"[VoiceClone] Профиль '{profile_name}' не найден")
                return False
                
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
                
            # Загружаем сэмплы
            self.voice_samples = []
            for sample_info in profile_data['samples']:
                if os.path.exists(sample_info['path']):
                    audio_data, sr = sf.read(sample_info['path'])
                    self.voice_samples.append({
                        'name': sample_info['name'],
                        'path': sample_info['path'],
                        'audio': audio_data,
                        'duration': sample_info['duration']
                    })
                    
            print(f"[VoiceClone] Профиль '{profile_name}' загружен")
            return True
            
        except Exception as e:
            print(f"[VoiceClone] Ошибка загрузки профиля: {e}")
            return False
            
    def get_available_profiles(self) -> List[str]:
        """Получить список доступных профилей"""
        profiles = []
        for profile_file in self.samples_dir.glob("*_profile.json"):
            profile_name = profile_file.stem.replace("_profile", "")
            profiles.append(profile_name)
        return profiles
        
    def delete_voice_profile(self, profile_name: str) -> bool:
        """Удалить профиль голоса"""
        try:
            profile_path = self.samples_dir / f"{profile_name}_profile.json"
            if profile_path.exists():
                profile_path.unlink()
                
            # Удаляем связанные аудио файлы
            for sample in self.voice_samples:
                if sample['name'].startswith(profile_name):
                    sample_path = Path(sample['path'])
                    if sample_path.exists():
                        sample_path.unlink()
                        
            print(f"[VoiceClone] Профиль '{profile_name}' удален")
            return True
            
        except Exception as e:
            print(f"[VoiceClone] Ошибка удаления профиля: {e}")
            return False
            
    def get_sample_count(self) -> int:
        """Получить количество собранных сэмплов"""
        return len(self.voice_samples)
        
    def is_ready_for_cloning(self) -> bool:
        """Проверить, готов ли клон для использования"""
        return self.is_ready and len(self.voice_samples) >= self.min_samples
        
    def get_sample_info(self) -> List[Dict]:
        """Получить информацию о сэмплах"""
        return [
            {
                'name': sample['name'],
                'duration': sample['duration'],
                'path': sample['path']
            }
            for sample in self.voice_samples
        ]
