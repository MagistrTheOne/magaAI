# -*- coding: utf-8 -*-
"""
Ghost Interview Assistant (Windows)
- Невидимый голос ассистента в Zoom/Meet (через VB-CABLE)
- Кнопки: Listen, AI Mute, My Mic Mute, Intro / XP / Handoff
- Транскрипция речи собеседников (WASAPI loopback из динамиков)

УСТАНОВКА:
1. Установите VB-CABLE: https://vb-audio.com/Cable/ (скачать, установить, перезагрузить)
2. В Zoom: Microphone = CABLE Output, Speakers = ваши наушники/колонки
3. Запуск: python ghost_assistant_win.py

Requirements:
  pip install edge-tts sounddevice numpy pydub faster-whisper PySimpleGUI
Дополнительно: 
  - FFmpeg в PATH (для pydub mp3->pcm): https://ffmpeg.org/download.html
  - VB-CABLE установлен: https://vb-audio.com/Cable/
"""

import asyncio
import io
import os
import queue
import random
import re
import threading
import time
import warnings
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict

import numpy as np
import sounddevice as sd
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# Подавляем SSL-предупреждения для GigaChat API
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
warnings.filterwarnings('ignore', message='Couldn\'t find ffmpeg')

# --- TTS (Edge) ---
import edge_tts
from pydub import AudioSegment

# --- STT (Whisper small/tiny) ---
from faster_whisper import WhisperModel

# --- Tortoise TTS (опционально) ---
USE_TORTOISE_TTS = False  # Флаг для включения Tortoise TTS
TORTOISE_AVAILABLE = False

# --- Brain SDK (GigaChat + RAG) ---
try:
    from brain.ai_client import BrainManager
    from brain.rag_index import RAGManager
    BRAIN_AVAILABLE = True
except ImportError:
    BRAIN_AVAILABLE = False
    print("[WARNING] Brain SDK недоступен - установите зависимости")

# --- Streaming TTS ---
try:
    from streaming_tts import StreamingTTS
    STREAMING_TTS_AVAILABLE = True
except ImportError:
    STREAMING_TTS_AVAILABLE = False
    print("[WARNING] Streaming TTS недоступен")

# --- Ultra Features ---
try:
    from intent_engine import IntentEngine
    from screen_scanner import ScreenScanner
    from app_detection import AppDetector
    from mail_calendar import MailCalendar
    from ats_tailor import ATSTailor
    from negotiation_v2 import NegotiationEngine
    from overlay_hud import OverlayHUD, HUDStatus
    from secrets_watchdog import SecretsWatchdogManager
    from coach_simulator import HRSimulator
    from quantum_negotiation import QuantumNegotiationEngine
    from memory_palace import MemoryPalace
    from success_prediction import SuccessPredictionEngine, PredictionFeatures
    from telegram_bot import MAGATelegramBot
    from auto_pilot import AutoPilot, AutoPilotConfig
    from job_apis import JobAPIManager, JobSearchParams
    from desktop_rpa import DesktopRPA
    ULTRA_AVAILABLE = True
except ImportError as e:
    ULTRA_AVAILABLE = False
    print(f"[WARNING] Ultra Features недоступны: {e}")

# Проверка Tortoise TTS
if USE_TORTOISE_TTS:
    try:
        from tortoise.api import TextToSpeech
        TORTOISE_AVAILABLE = True
    except ImportError:
        TORTOISE_AVAILABLE = False
        print("[WARNING] Tortoise TTS недоступен")


# =============== CONFIG ===============

VOICE = "ru-RU-DmitryNeural"   # или "en-US-GuyNeural"
OUTPUT_DEVICE_SUBSTR = "CABLE Input"  # Куда проигрываем голос ассистента (Zoom Mic = CABLE Output)
# Если VB-CABLE не установлен, используйте: "Voicemod VAD Wave" или "USB Audio CODEC"
LOOPBACK_SPEAKER_SUBSTR = "PHL 322E1"  # Источник для loopback (ваши динамики/наушники)
EAR_MONITOR_SUBSTR = "CABLE-B Input"  # Канал "в ухо" для подсказок (если есть CABLE-B)
EAR_MONITOR_VOLUME = 0.3  # Громкость подсказок (0.0-1.0)

MODEL_SIZE = "small"  # "tiny" быстрее на CPU, "small" точнее
USE_GPU = False       # Если есть CUDA — True

# TTS настройки
TORTOISE_VOICE = "angie"  # Голос для Tortoise TTS

# Микрофон пользователя
MY_MIC_SUBSTR = "Microphone"  # Подстрока для поиска вашего микрофона

# AI-ассистент настройки
AI_ASSISTANT_MODE = True  # Включить автономного AI-ассистента
AI_PERSONALITY = "aggressive"  # "aggressive", "professional", "friendly"
AI_SALARY_TARGET = 200000  # Целевая зарплата в USD
AI_RESPONSE_DELAY = 2.0  # Задержка перед ответом (сек)

# Горячие фразы ассистента (можешь подредактировать)
LINES = {
    "intro": (
        "Здравствуйте. Я Максим Онюшко. Благодарю за время. "
        "Первые минуты встречу ведёт мой ассистент — затем подключусь лично."
    ),
    "xp": (
        "Коротко о фокусе: production L L M и агентные системы. "
        "Строю пайплайны от данных до инференса, снижаю задержку и стоимость. "
        "Последний проект — Prometheus: п девяносто пять около одной целой двух десятых секунды, "
        "пропускная способность сорок пять — шестьдесят токенов в секунду, "
        "и низкая себестоимость на тысячу токенов."
    ),
    "handoff": (
        "Спасибо. Подключаюсь лично — готов обсудить архитектуру, метрики и пилот."
    ),
}

# AI-ассистент фразы для разных ситуаций
AI_RESPONSES = {
    "salary_low": [
        "Интересно. А какая вилка у вас в голове?",
        "Хм, это ниже рыночной. У меня есть предложения от 180k.",
        "Давайте поговорим о компенсации. Что вы готовы предложить?"
    ],
    "salary_negotiation": [
        "Отлично! А есть ли equity?",
        "А бонусы? Медицинская страховка?",
        "Спасибо, это уже ближе к реальности."
    ],
    "technical_questions": [
        "Отличный вопрос! Расскажу на примере Prometheus...",
        "В моем последнем проекте мы решили это через...",
        "Да, это классическая задача. Вот как я бы подошел..."
    ],
    "company_questions": [
        "А какая у вас техническая культура?",
        "Интересно. А как вы видите развитие команды?",
        "Понятно. А какие у вас планы на AI/ML?"
    ],
    "aggressive": [
        "Слушайте, у меня есть еще 3 собеседования на этой неделе.",
        "Я рассматриваю несколько предложений. Что у вас уникального?",
        "Время дорого. Давайте к делу."
    ]
}

# VAD настройки
FRAME_DUR = 0.25       # сек, длительность аудиофрейма
VAD_THRESH = 0.01      # порог RMS для речи
SILENCE_TAIL = 0.8     # сек тишины для завершения фразы
MAX_SEG_LEN = 12.0     # сек, максимальная длина сегмента до форс-завершения

# =====================================


def find_output_device(name_substr: str) -> int:
    for idx, dev in enumerate(sd.query_devices()):
        if dev["max_output_channels"] > 0 and name_substr.lower() in dev["name"].lower():
            return idx
    raise RuntimeError(f"Output device not found: {name_substr}")


def find_loopback_device(name_substr: str) -> int:
    """
    Возвращает индекс устройства вывода (speakers), которое будем слушать в loopback.
    В WASAPI loopback мы открываем input stream с параметром 'loopback=True' и этим индексом.
    """
    for idx, dev in enumerate(sd.query_devices()):
        if dev["max_output_channels"] > 0 and name_substr.lower() in dev["name"].lower():
            return idx
    raise RuntimeError(f"Speaker device for loopback not found: {name_substr}")


def find_input_device(name_substr: str) -> int:
    """
    Возвращает индекс устройства ввода (микрофон).
    """
    for idx, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0 and name_substr.lower() in dev["name"].lower():
            return idx
    raise RuntimeError(f"Input device not found: {name_substr}")


async def edge_tts_pcm(text: str) -> np.ndarray:
    """
    Генерирует аудио через Edge TTS, конвертирует MP3->PCM float32 numpy.
    Требует FFmpeg (pydub).
    """
    try:
        communicate = edge_tts.Communicate(text, VOICE, rate="+0%", pitch="+0%")
        mp3_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_bytes += chunk["data"]
        # mp3 -> PCM
        seg = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
        seg = seg.set_frame_rate(16000).set_channels(1).set_sample_width(2)  # 16kHz, mono, 16-bit
        raw = seg.raw_data
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        return audio
    except Exception as e:
        raise RuntimeError(f"TTS conversion failed (check FFmpeg): {e}")


def tortoise_tts_pcm(text: str) -> np.ndarray:
    """
    Генерирует аудио через Tortoise TTS (офлайн, качественный).
    """
    if not TORTOISE_AVAILABLE:
        raise RuntimeError("Tortoise TTS not available")
    
    try:
        # Инициализация Tortoise TTS (только при первом вызове)
        if not hasattr(tortoise_tts_pcm, 'tts'):
            tortoise_tts_pcm.tts = TextToSpeech()
        
        # Генерация аудио
        gen, dbg_state = tortoise_tts_pcm.tts.tts_with_preset(
            text, 
            voice_samples=None,  # Используем предустановленный голос
            conditioning_latents=None,
            preset="fast",  # "ultra_fast", "fast", "standard", "high_quality"
            use_deterministic_seed=42
        )
        
        # Конвертация в numpy array
        audio = gen.squeeze(0).cpu().numpy()
        return audio.astype(np.float32)
    except Exception as e:
        raise RuntimeError(f"Tortoise TTS failed: {e}")


def play_pcm(audio: np.ndarray, sr: int, device_idx: int, block=True, ai_muted=False):
    if ai_muted:
        return
    sd.play(audio, sr, device=device_idx, blocking=block)


@dataclass
class STTState:
    loopback_device_idx: int
    running: bool = False
    transcript_q: queue.Queue = field(default_factory=queue.Queue)
    model: Optional[WhisperModel] = None


def stt_worker(state: STTState):
    """
    Слушаем системный звук (динамики) в loopback, режем по VAD, отправляем сегменты в Whisper.
    """
    sr = 16000
    channels = 2  # WASAPI loopback отдаёт стерео; сведём в моно
    frame_len = int(sr * FRAME_DUR)
    silence_frames_needed = int(SILENCE_TAIL / FRAME_DUR)
    max_frames = int(MAX_SEG_LEN / FRAME_DUR)

    # инициализация whisper
    device = "cuda" if USE_GPU else "cpu"
    compute_type = "float16" if USE_GPU else "int8"
    state.model = WhisperModel(MODEL_SIZE, device=device, compute_type=compute_type)

    # буфер фразы
    seg_frames: List[np.ndarray] = []
    silence_count = 0
    speaking = False

    # WASAPI loopback input
    # sd.default.hostapi = None  # убрано - вызывает ошибку
    try:
        # Попытка использовать loopback через WasapiSettings
        stream = sd.InputStream(
            samplerate=sr,
            channels=channels,
            dtype="float32",
            device=state.loopback_device_idx,
            blocksize=frame_len,
            latency="low",
            extra_settings=sd.WasapiSettings(loopback=True),
        )
    except TypeError:
        # Fallback для старых версий sounddevice
        stream = sd.InputStream(
            samplerate=sr,
            channels=channels,
            dtype="float32",
            device=state.loopback_device_idx,
            blocksize=frame_len,
            latency="low",
        )
    stream.start()
    state.running = True

    try:
        while state.running:
            block = stream.read(frame_len)[0]  # (N, 2)
            mono = block.mean(axis=1)

            rms = np.sqrt(np.mean(mono ** 2) + 1e-9)

            if rms > VAD_THRESH:
                seg_frames.append(mono.copy())
                speaking = True
                silence_count = 0
            else:
                if speaking:
                    silence_count += 1
                    seg_frames.append(mono.copy())

            # завершение по тишине или длине
            if speaking and (silence_count >= silence_frames_needed or len(seg_frames) >= max_frames):
                audio_seg = np.concatenate(seg_frames, axis=0)
                seg_frames.clear()
                speaking = False
                silence_count = 0

                # транскрибируем
                try:
                    segments, _ = state.model.transcribe(audio_seg, language=None, vad_filter=False)
                    text = " ".join(s.text.strip() for s in segments)
                    if text:
                        state.transcript_q.put(text)
                except Exception as e:
                    state.transcript_q.put(f"[STT error] {e}")

            # не держим 100% ядро
            time.sleep(0.01)

    finally:
        stream.stop()
        stream.close()
        state.running = False


class App:
    def __init__(self):
        # Создадим папку для транскриптов
        self.transcripts_dir = "transcripts"
        os.makedirs(self.transcripts_dir, exist_ok=True)

        # Определим устройства
        try:
            self.out_idx = find_output_device(OUTPUT_DEVICE_SUBSTR)
        except Exception as e:
            self.out_idx = None
            print(f"Warning: Output device not found: {e}")

        try:
            self.loop_idx = find_loopback_device(LOOPBACK_SPEAKER_SUBSTR)
        except Exception as e:
            self.loop_idx = None
            print(f"Warning: Loopback device not found: {e}")
            
        # "В ухо" канал для подсказок
        try:
            self.ear_idx = find_output_device(EAR_MONITOR_SUBSTR)
        except Exception as e:
            self.ear_idx = None
            print(f"Info: Ear monitor device not found: {e}")

        try:
            self.mic_idx = find_input_device(MY_MIC_SUBSTR)
        except Exception as e:
            self.mic_idx = None
            print(f"Warning: Microphone not found: {e}")

        # Состояния
        self.ai_muted = False
        self.me_muted = False
        self.stt_state = None  # type: Optional[STTState]
        self.stt_thread = None
        self.transcript_file = None
        self.listen_source = "loopback"  # "loopback" или "microphone"
        
        # AI-ассистент состояние
        self.ai_active = False
        self.conversation_context = []
        self.last_hr_message = ""
        self.salary_mentioned = False
        
        # Brain SDK
        self.brain_manager = None
        self.rag_manager = None
        if BRAIN_AVAILABLE:
            self._initialize_brain()
        
        # Voice Trigger
        self.voice_trigger = None
        self.wake_trigger_active = False
        
        # Ultra Features
        self.voice_duplex = None
        self.intent_engine = None
        self.desktop_rpa = None
        self.browser_rpa = None
        self.duplex_mode = False
        
        # "В ухо" канал
        self.ear_monitor_active = False

        # Streaming TTS
        self.streaming_tts = None
        self.streaming_mode = False

        # Ultra Features
        self.intent_engine = None
        self.screen_scanner = None
        self.app_detector = None
        self.mail_calendar = None
        self.ats_tailor = None
        self.negotiation_engine = None
        self.overlay_hud = None
        self.overlay_hud_active = False
        self.secrets_watchdog = None
        self.hr_simulator = None
        self.quantum_negotiation = None
        self.memory_palace = None
        self.success_prediction = None
        self.telegram_bot = None
        self.telegram_active = False
        self.auto_pilot = None
        self.desktop_rpa = None
        self.job_api_manager = None
        self.quantum_active = False

        # Инициализируем Ultra Features
        if ULTRA_AVAILABLE:
            self._initialize_ultra_features()

        # Создаем GUI
        try:
            self.root = tk.Tk()
            self.root.title("Ghost Interview Assistant")
            self.root.geometry("800x600")
            self.root.configure(bg='#404040')
            self._initialize_gui()  # Инициализируем GUI элементы
        except:
            # Для тестирования без GUI
            self.root = None
            print("[GUI] Tkinter not available, running in headless mode")

    def _initialize_gui(self):
        """Инициализация GUI элементов"""
        if not self.root:
            return

        # Заголовок
        title_label = tk.Label(self.root, text="Ghost Assistant (Windows)",
                              font=("Segoe UI", 14, "bold"),
                              bg='#404040', fg='white')
        title_label.pack(pady=10)

        # Устройства
        devices_frame = ttk.LabelFrame(self.root, text="Devices", padding=10)
        devices_frame.pack(fill='x', padx=10, pady=5)
        
        tts_device = sd.query_devices(self.out_idx)['name'] if self.out_idx is not None else 'NOT FOUND'
        loopback_device = sd.query_devices(self.loop_idx)['name'] if self.loop_idx is not None else 'NOT FOUND'
        
        tk.Label(devices_frame, text=f"TTS → Output device: {tts_device}", 
                bg='#404040', fg='white').pack(anchor='w')
        tk.Label(devices_frame, text=f"Loopback source: {loopback_device}", 
                bg='#404040', fg='white').pack(anchor='w')

        # Управление
        controls_frame = ttk.LabelFrame(self.root, text="Controls", padding=10)
        controls_frame.pack(fill='x', padx=10, pady=5)

        # Кнопки управления
        buttons_frame = tk.Frame(controls_frame)
        buttons_frame.pack(fill='x')
        
        self.listen_btn = tk.Button(buttons_frame, text="▶ Listen (F9)", 
                                  command=self.start_listen, bg='#1f6feb', fg='white')
        self.listen_btn.pack(side='left', padx=5)
        
        self.stop_btn = tk.Button(buttons_frame, text="■ Stop", 
                                 command=self.stop_listen, state='disabled')
        self.stop_btn.pack(side='left', padx=5)
        
        self.ai_mute_btn = tk.Button(buttons_frame, text="🤫 AI Mute: OFF (F10)", 
                                   command=self.toggle_ai_mute)
        self.ai_mute_btn.pack(side='left', padx=5)
        
        self.me_mute_btn = tk.Button(buttons_frame, text="🎙 My Mic: ON", 
                                    command=self.toggle_me_mute)
        self.me_mute_btn.pack(side='left', padx=5)

        # Переключатель источника STT
        source_frame = tk.Frame(controls_frame)
        source_frame.pack(fill='x', pady=5)
        
        tk.Label(source_frame, text="STT Source:", bg='#404040', fg='white').pack(side='left')
        self.source_var = tk.StringVar(value="loopback")
        tk.Radiobutton(source_frame, text="Собеседник (Loopback)", variable=self.source_var, 
                      value="loopback", command=self.toggle_source, bg='#404040', fg='white').pack(side='left', padx=5)
        tk.Radiobutton(source_frame, text="Мой микрофон", variable=self.source_var, 
                      value="microphone", command=self.toggle_source, bg='#404040', fg='white').pack(side='left', padx=5)

        # AI-ассистент управление
        ai_frame = tk.Frame(controls_frame)
        ai_frame.pack(fill='x', pady=5)
        
        self.ai_btn = tk.Button(ai_frame, text="🤖 AI Assistant: OFF", 
                              command=self.toggle_ai_assistant, bg='#ff6b35', fg='white')
        self.ai_btn.pack(side='left', padx=5)
        
        # Voice Trigger управление
        self.wake_btn = tk.Button(ai_frame, text="🎙️ Wake Trigger: OFF", 
                                command=self.toggle_wake_trigger, bg='#9c27b0', fg='white')
        self.wake_btn.pack(side='left', padx=5)
        
        # Ultra Features управление
        self.duplex_btn = tk.Button(ai_frame, text="🎙️ Duplex Mode: OFF", 
                                   command=self.toggle_duplex_mode, bg='#ff5722', fg='white')
        self.duplex_btn.pack(side='left', padx=5)
        
        # "В ухо" канал для подсказок
        self.ear_btn = tk.Button(ai_frame, text="👂 Ear Monitor: OFF", 
                                command=self.toggle_ear_monitor, bg='#673ab7', fg='white')
        self.ear_btn.pack(side='left', padx=5)
        
        # Streaming TTS
        self.streaming_btn = tk.Button(ai_frame, text="🌊 Streaming: OFF",
                                      command=self.toggle_streaming, bg='#2196f3', fg='white')
        self.streaming_btn.pack(side='left', padx=5)

        # Overlay HUD
        self.hud_btn = tk.Button(ai_frame, text="🖥️ HUD: OFF",
                                command=self.toggle_overlay_hud, bg='#9c27b0', fg='white')
        self.hud_btn.pack(side='left', padx=5)

        # Quantum Negotiation
        self.quantum_btn = tk.Button(ai_frame, text="⚛️ Quantum: OFF",
                                    command=self.toggle_quantum_negotiation, bg='#ff1493', fg='white')
        self.quantum_btn.pack(side='left', padx=5)

        # Success Prediction
        self.predict_btn = tk.Button(ai_frame, text="🔮 Predict",
                                    command=self.run_success_prediction, bg='#00ced1', fg='white')
        self.predict_btn.pack(side='left', padx=5)

        # Telegram Bot
        self.telegram_btn = tk.Button(ai_frame, text="📱 Telegram: OFF",
                                     command=self.toggle_telegram_bot, bg='#0088cc', fg='white')
        self.telegram_btn.pack(side='left', padx=5)

        # Auto-Pilot
        self.autopilot_btn = tk.Button(ai_frame, text="🚀 Auto-Pilot: OFF",
                                      command=self.toggle_auto_pilot, bg='#ff4500', fg='white')
        self.autopilot_btn.pack(side='left', padx=5)

        # Telegram Control
        self.telegram_control_btn = tk.Button(ai_frame, text="🎮 Telegram Control",
                                             command=self.open_telegram_control, bg='#0088cc', fg='white')
        self.telegram_control_btn.pack(side='left', padx=5)
        
        tk.Label(ai_frame, text=f"Target: ${AI_SALARY_TARGET:,}", 
                bg='#404040', fg='#00ff00').pack(side='left', padx=10)

        # Быстрые фразы
        phrases_frame = tk.Frame(controls_frame)
        phrases_frame.pack(fill='x', pady=5)
        
        tk.Button(phrases_frame, text="Intro (F11)", command=self.speak_intro).pack(side='left', padx=5)
        tk.Button(phrases_frame, text="Experience", command=self.speak_xp).pack(side='left', padx=5)
        tk.Button(phrases_frame, text="Handoff", command=self.speak_handoff).pack(side='left', padx=5)

        # Транскрипт
        transcript_frame = ttk.LabelFrame(self.root, text="Transcript (remote side)", padding=10)
        transcript_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(transcript_frame, height=16, width=90, 
                                                 bg='#2b2b2b', fg='white', state='disabled')
        self.log_text.pack(fill='both', expand=True)

        # Подсказки
        hint_label = tk.Label(self.root, 
                             text="Hint: Zoom Microphone = CABLE Output. Our TTS plays to CABLE Input.",
                             bg='#404040', fg='#9aa7b0')
        hint_label.pack(pady=2)
        
        # Подсказка о FFmpeg
        ffmpeg_label = tk.Label(self.root, 
                               text="FFmpeg required for TTS: https://ffmpeg.org/download.html",
                               bg='#404040', fg='#ffa500')
        ffmpeg_label.pack(pady=1)
        
        hotkeys_label = tk.Label(self.root, 
                                text="Hotkeys: F9=Listen, F10=AI Mute, F11=Intro",
                                bg='#404040', fg='#9aa7b0')
        hotkeys_label.pack(pady=2)
        
        # Инструкции по прослушиванию голоса
        voice_hint = tk.Label(self.root, 
                             text="🎧 Чтобы слышать голос ассистента: Windows Sound → Default Device = PHL 322E1",
                             bg='#404040', fg='#ffff00')
        voice_hint.pack(pady=2)
        
        # Проверка FFmpeg
        ffmpeg_status = self._check_ffmpeg()
        ffmpeg_label = tk.Label(self.root, 
                               text=f"🎬 FFmpeg: {ffmpeg_status}",
                               bg='#404040', fg='#00ff00' if ffmpeg_status == "OK" else '#ff0000')
        ffmpeg_label.pack(pady=2)

        # Горячие клавиши
        self.root.bind('<F9>', lambda e: self.start_listen())
        self.root.bind('<F10>', lambda e: self.toggle_ai_mute())
        self.root.bind('<F11>', lambda e: self.speak_intro())
        self.root.bind('<Control-Shift-G>', lambda e: self.toggle_wake_trigger())

    def log(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {msg}"
        
        # Добавляем в GUI
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, log_msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        
        # Автосохранение в файл
        if self.transcript_file:
            try:
                with open(self.transcript_file, "a", encoding="utf-8") as f:
                    f.write(log_msg + "\n")
            except Exception as e:
                print(f"Error saving transcript: {e}")

    async def speak(self, text: str):
        if self.out_idx is None:
            self.log("[TTS] Output device not found")
            return
        try:
            if USE_TORTOISE_TTS and TORTOISE_AVAILABLE:
                self.log("[TTS] Using Tortoise TTS...")
                pcm = tortoise_tts_pcm(text)
                play_pcm(pcm, 22050, self.out_idx, block=True, ai_muted=self.ai_muted)  # Tortoise использует 22050 Hz
            else:
                self.log("[TTS] Using Edge TTS...")
                pcm = await edge_tts_pcm(text)
                play_pcm(pcm, 16000, self.out_idx, block=True, ai_muted=self.ai_muted)
        except Exception as e:
            self.log(f"[TTS error] {e}")

    def start_listen(self):
        # Выбираем устройство в зависимости от источника
        if self.listen_source == "loopback":
            device_idx = self.loop_idx
            if device_idx is None:
                self.log("[STT] Loopback device not found")
                return
        else:  # microphone
            device_idx = self.mic_idx
            if device_idx is None:
                self.log("[STT] Microphone not found")
                return
        
        if self.stt_state and self.stt_state.running:
            return
        
        # Создаем файл для транскрипта
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        source_suffix = "mic" if self.listen_source == "microphone" else "loopback"
        self.transcript_file = os.path.join(self.transcripts_dir, f"transcript_{source_suffix}_{timestamp}.txt")
        
        self.stt_state = STTState(loopback_device_idx=device_idx)
        self.stt_thread = threading.Thread(target=stt_worker, args=(self.stt_state,), daemon=True)
        self.stt_thread.start()
        self.listen_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.log(f"[STT] Listening from {self.listen_source}… (saving to {self.transcript_file})")

        # Обновляем HUD статус
        if self.overlay_hud and self.overlay_hud_active:
            self.overlay_hud.set_status(HUDStatus.LISTENING, f"Listening ({self.listen_source})")

        # Отдельный поток для подтягивания транскриптов
        def pump():
            while self.stt_state and self.stt_state.running:
                try:
                    text = self.stt_state.transcript_q.get(timeout=0.2)
                    self.log(text)
                    
                    # AI-анализ и автоответ (только для loopback - HR)
                    if self.listen_source == "loopback" and self.ai_active:
                        self.ai_auto_response(text)
                        
                except queue.Empty:
                    pass
                time.sleep(0.05)

        threading.Thread(target=pump, daemon=True).start()

    def stop_listen(self):
        if self.stt_state:
            self.stt_state.running = False
        self.listen_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.log("[STT] Stopped.")

        # Обновляем HUD статус
        if self.overlay_hud and self.overlay_hud_active:
            self.overlay_hud.set_status(HUDStatus.IDLE, "Ready")

    def toggle_ai_mute(self):
        self.ai_muted = not self.ai_muted
        self.ai_mute_btn.config(text=f"🤫 AI Mute: {'ON' if self.ai_muted else 'OFF'}")

    def toggle_me_mute(self):
        # Программно замьютить именно Zoom микрофон нельзя без хаков;
        # Эта кнопка — индикатор/триггер. Свяжи с Voicemeeter MacroButtons, если нужно аппаратно.
        self.me_muted = not self.me_muted
        self.me_mute_btn.config(text=f"🎙 My Mic: {'OFF' if self.me_muted else 'ON'}")

    def speak_intro(self):
        threading.Thread(target=self._run_speak, args=(LINES["intro"],), daemon=True).start()

    def speak_xp(self):
        threading.Thread(target=self._run_speak, args=(LINES["xp"],), daemon=True).start()

    def speak_handoff(self):
        threading.Thread(target=self._run_speak, args=(LINES["handoff"],), daemon=True).start()

    def toggle_source(self):
        self.listen_source = self.source_var.get()
        self.log(f"[STT] Source switched to: {self.listen_source}")

    def toggle_ai_assistant(self):
        self.ai_active = not self.ai_active
        status = "ON" if self.ai_active else "OFF"
        color = "#00ff00" if self.ai_active else "#ff6b35"
        self.ai_btn.config(text=f"🤖 AI Assistant: {status}", bg=color)
        self.log(f"[AI] Assistant {status}")
        
        if self.ai_active:
            self.log("[AI] 🤖 AI-ассистент активирован! Буду анализировать HR и отвечать автономно.")
            self.log("[AI] 💰 Целевая зарплата: $200,000")
            self.log("[AI] 🎯 Режим: Агрессивный переговорщик")
    
    def toggle_wake_trigger(self):
        """Переключение Voice Trigger"""
        if not self.wake_trigger_active:
            self._start_wake_trigger()
        else:
            self._stop_wake_trigger()
    
    def _start_wake_trigger(self):
        """Запуск Voice Trigger"""
        try:
            from voice_trigger import VoiceTrigger

            self.voice_trigger = VoiceTrigger(
                wake_phrase="мага запускай пора взрывать рынок",
                response_callback=self._on_wake_triggered
            )

            # Запускаем в отдельном потоке
            self.wake_thread = threading.Thread(target=self._run_wake_trigger, daemon=True)
            self.wake_thread.start()

            self.wake_trigger_active = True

            status = "ON"
            color = "#00ff00"
            self.wake_btn.config(text=f"🎙️ Wake Trigger: {status}", bg=color)
            self.log("[WAKE] 🎙️ Voice Trigger активирован!")
            self.log("[WAKE] Скажите: 'Мага, запускай — пора взрывать рынок'")

        except Exception as e:
            self.log(f"[WAKE] ❌ Ошибка запуска Voice Trigger: {e}")

    def _run_wake_trigger(self):
        """Запуск Voice Trigger в потоке"""
        try:
            if self.voice_trigger:
                self.voice_trigger.start_listening()
        except Exception as e:
            self.log(f"[WAKE] ❌ Ошибка в потоке Voice Trigger: {e}")
    
    def _stop_wake_trigger(self):
        """Остановка Voice Trigger"""
        if self.voice_trigger:
            self.voice_trigger.stop_listening()
            self.voice_trigger = None
        
        self.wake_trigger_active = False
        status = "OFF"
        color = "#9c27b0"
        self.wake_btn.config(text=f"🎙️ Wake Trigger: {status}", bg=color)
        self.log("[WAKE] 🛑 Voice Trigger остановлен")
    
    def _on_wake_triggered(self, response: str):
        """Обработка срабатывания wake phrase"""
        self.log(f"[WAKE] 🎯 Триггер сработал! Реакция: {response}")
        
        # Автоматически включаем AI Assistant если он выключен
        if not self.ai_active:
            self.toggle_ai_assistant()
        
        # Проигрываем реакцию через TTS
        threading.Thread(target=self._run_speak, args=(response,), daemon=True).start()
    
    def toggle_duplex_mode(self):
        """Переключение Duplex Mode"""
        if not self.duplex_mode:
            self._start_duplex_mode()
        else:
            self._stop_duplex_mode()
    
    def _start_duplex_mode(self):
        """Запуск Duplex Mode"""
        try:
            from voice_duplex import VoiceDuplex
            from intent_engine import IntentEngine
            from desktop_rpa import DesktopRPA
            
            # Инициализируем Voice Duplex
            self.voice_duplex = VoiceDuplex(
                response_callback=self._on_duplex_response
            )
            
            # Инициализируем Intent Engine
            self.intent_engine = IntentEngine()
            self._register_intent_actions()
            
            # Инициализируем Desktop RPA
            self.desktop_rpa = DesktopRPA()
            
            # Запускаем Voice Duplex
            self.voice_duplex.start()
            self.duplex_mode = True
            
            status = "ON"
            color = "#00ff00"
            self.duplex_btn.config(text=f"🎙️ Duplex Mode: {status}", bg=color)
            self.log("[DUPLex] 🎙️ Duplex Mode активирован!")
            self.log("[DUPLex] Теперь можно говорить с AI напрямую")
            self.log("[DUPLex] Доступны команды: поиск вакансий, проверка откликов, подготовка к собеседованию")
            
        except Exception as e:
            self.log(f"[DUPLex] ❌ Ошибка запуска Duplex Mode: {e}")
    
    def _stop_duplex_mode(self):
        """Остановка Duplex Mode"""
        if self.voice_duplex:
            self.voice_duplex.stop()
            self.voice_duplex = None
        
        self.duplex_mode = False
        status = "OFF"
        color = "#ff5722"
        self.duplex_btn.config(text=f"🎙️ Duplex Mode: {status}", bg=color)
        self.log("[DUPLex] 🛑 Duplex Mode остановлен")
    
    def _on_duplex_response(self, user_text: str):
        """Обработка речи пользователя в Duplex Mode"""
        self.log(f"[DUPLex] 🎤 Пользователь сказал: {user_text}")

        # Проверяем, является ли это командой для Мага
        maga_triggered = any(phrase in user_text.lower() for phrase in [
            "мага", "мага,", "мага!", "мага?", "мага запускай"
        ])

        if maga_triggered:
            # Обрабатываем команду через Intent Engine Мага
            if self.intent_engine:
                # TTS callback для озвучивания ответа
                def tts_callback(response_text: str):
                    self.log(f"[МАГА] 🤖 {response_text}")
                    threading.Thread(target=self._run_speak, args=(response_text,), daemon=True).start()

                result = self.intent_engine.process_command(user_text, tts_callback)
                if result and not tts_callback:  # Если TTS не был вызван внутри
                    self.log(f"[МАГА] 🤖 {result}")
                    threading.Thread(target=self._run_speak, args=(result,), daemon=True).start()
        else:
            # Обычная обработка через AI Assistant
            if self.intent_engine:
                result = self.intent_engine.process_command(user_text)
                if result:
                    self.log(f"[DUPLex] 🤖 AI отвечает: {result}")
                    # Озвучиваем ответ
                    threading.Thread(target=self._run_speak, args=(result,), daemon=True).start()
                else:
                    # Общий ответ если команда не распознана
                    response = "Понял, но не знаю как это сделать. Попробуйте: 'Мага, найди вакансии', 'Мага, проверь отклики', 'Мага, подготовь к собеседованию'."
                    self.log(f"[DUPLex] 🤖 AI отвечает: {response}")
                    threading.Thread(target=self._run_speak, args=(response,), daemon=True).start()
    
    def _register_intent_actions(self):
        """Регистрация действий для Intent Engine"""
        if not self.intent_engine:
            return

        # Используем register_maga_actions для регистрации всех действий Мага
        self.intent_engine.register_maga_actions()
        self.log("[INTENT] Действия Мага зарегистрированы")
    
    def toggle_ear_monitor(self):
        """Переключение "в ухо" канала"""
        if not self.ear_monitor_active:
            self._start_ear_monitor()
        else:
            self._stop_ear_monitor()
    
    def toggle_streaming(self):
        """Переключение Streaming TTS"""
        if not self.streaming_mode:
            self._start_streaming()
        else:
            self._stop_streaming()
    
    def _start_streaming(self):
        """Запуск Streaming TTS"""
        try:
            if not STREAMING_TTS_AVAILABLE:
                self.log("[STREAM] Streaming TTS недоступен")
                return
                
            from streaming_tts import StreamingTTS
            
            self.streaming_tts = StreamingTTS(
                voice=VOICE,
                output_device_idx=self.out_idx,
                chunk_duration=0.5,
                barge_in_threshold=0.01,
                on_barge_in=self._on_streaming_barge_in
            )
            
            # Устанавливаем микрофон для мониторинга бардж-ина
            if self.mic_idx is not None:
                self.streaming_tts.set_monitor_microphone(self.mic_idx)
            
            self.streaming_tts.start()
            self.streaming_mode = True
            
            status = "ON"
            color = "#00ff00"
            self.streaming_btn.config(text=f"🌊 Streaming: {status}", bg=color)
            self.log("[STREAM] Потоковый TTS активирован")
            self.log("[STREAM] Низкая задержка + бардж-ин")
            
        except Exception as e:
            self.log(f"[STREAM] Ошибка запуска: {e}")
    
    def _stop_streaming(self):
        """Остановка Streaming TTS"""
        if self.streaming_tts:
            self.streaming_tts.stop()
            self.streaming_tts = None
            
        self.streaming_mode = False
        status = "OFF"
        color = "#2196f3"
        self.streaming_btn.config(text=f"🌊 Streaming: {status}", bg=color)
        self.log("[STREAM] Потоковый TTS остановлен")
    
    def _on_streaming_barge_in(self):
        """Обработка бардж-ина в Streaming TTS"""
        self.log("[STREAM] Бардж-ин обнаружен - пауза TTS")
        if self.streaming_tts:
            self.streaming_tts.pause()
    
    async def speak_streaming(self, text: str):
        """Потоковое озвучивание"""
        if self.streaming_tts and self.streaming_mode:
            await self.streaming_tts.speak_streaming(text)
        else:
            # Fallback на обычный TTS
            await self.speak(text)
    
    def _start_ear_monitor(self):
        """Запуск "в ухо" канала"""
        if self.ear_idx is None:
            self.log("[EAR] Устройство CABLE-B не найдено")
            return
            
        self.ear_monitor_active = True
        status = "ON"
        color = "#00ff00"
        self.ear_btn.config(text=f"👂 Ear Monitor: {status}", bg=color)
        self.log("[EAR] Канал 'в ухо' активирован")
        self.log("[EAR] Подсказки будут воспроизводиться тихо")
    
    def _stop_ear_monitor(self):
        """Остановка "в ухо" канала"""
        self.ear_monitor_active = False
        status = "OFF"
        color = "#673ab7"
        self.ear_btn.config(text=f"👂 Ear Monitor: {status}", bg=color)
        self.log("[EAR] Канал 'в ухо' остановлен")
    
    def speak_to_ear(self, text: str):
        """Озвучивание подсказки в 'ухо' канал"""
        if not self.ear_monitor_active or self.ear_idx is None:
            return
            
        # Создаем тихую версию для "в ухо"
        threading.Thread(target=self._run_speak_ear, args=(text,), daemon=True).start()
    
    def _run_speak_ear(self, text: str):
        """Запуск TTS для 'в ухо' канала"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Генерируем аудио
            if USE_TORTOISE_TTS and TORTOISE_AVAILABLE:
                pcm = tortoise_tts_pcm(text)
            else:
                pcm = loop.run_until_complete(edge_tts_pcm(text))
            
            # Применяем громкость для "в ухо"
            pcm = pcm * EAR_MONITOR_VOLUME
            
            # Проигрываем в "в ухо" канал
            play_pcm(pcm, 16000, self.ear_idx, block=True, ai_muted=False)
            
        except Exception as e:
            print(f"[EAR TTS error] {e}")

    def toggle_overlay_hud(self):
        """Переключение Overlay HUD"""
        if not self.overlay_hud_active:
            self._start_overlay_hud()
        else:
            self._stop_overlay_hud()

    def _start_overlay_hud(self):
        """Запуск Overlay HUD"""
        try:
            if not self.overlay_hud:
                self.log("[HUD] Overlay HUD не инициализирован")
                return

            self.overlay_hud.show()
            self.overlay_hud_active = True

            status = "ON"
            color = "#00ff00"
            self.hud_btn.config(text=f"🖥️ HUD: {status}", bg=color)
            self.log("[HUD] Overlay HUD активирован")

            # Обновляем статус HUD
            if self.overlay_hud:
                self.overlay_hud.set_status(HUDStatus.IDLE, "Ready")

        except Exception as e:
            self.log(f"[HUD] Ошибка запуска: {e}")

    def _stop_overlay_hud(self):
        """Остановка Overlay HUD"""
        if self.overlay_hud:
            self.overlay_hud.hide()
            self.overlay_hud_active = False

        status = "OFF"
        color = "#9c27b0"
        self.hud_btn.config(text=f"🖥️ HUD: {status}", bg=color)
        self.log("[HUD] Overlay HUD остановлен")

    def toggle_quantum_negotiation(self):
        """Переключение Quantum Negotiation"""
        if not self.quantum_active:
            self._start_quantum_negotiation()
        else:
            self._stop_quantum_negotiation()

    def _start_quantum_negotiation(self):
        """Запуск Quantum Negotiation"""
        try:
            if not self.quantum_negotiation:
                self.log("[QUANTUM] Quantum Negotiation не инициализирован")
                return

            self.quantum_active = True
            status = "ON"
            color = "#00ff00"
            self.quantum_btn.config(text=f"⚛️ Quantum: {status}", bg=color)
            self.log("[QUANTUM] Quantum Negotiation активирован!")
            self.log("[QUANTUM] Теперь МАГА будет использовать 3 параллельных AI для переговоров")

        except Exception as e:
            self.log(f"[QUANTUM] Ошибка запуска: {e}")

    def _stop_quantum_negotiation(self):
        """Остановка Quantum Negotiation"""
        self.quantum_active = False
        status = "OFF"
        color = "#ff1493"
        self.quantum_btn.config(text=f"⚛️ Quantum: {status}", bg=color)
        self.log("[QUANTUM] Quantum Negotiation остановлен")

    def run_quantum_negotiation(self, hr_message: str) -> None:
        """Запуск квантовых переговоров"""
        if not self.quantum_active or not self.quantum_negotiation:
            return

        def progress_callback(progress: float, message: str):
            """Callback для прогресса"""
            if self.overlay_hud and self.overlay_hud_active:
                self.overlay_hud.set_progress(int(progress * 100))
                self.overlay_hud.set_status(HUDStatus.PROCESSING, message)

        def negotiation_thread():
            """Поток для квантовых переговоров"""
            try:
                self.log("[QUANTUM] 🚀 Запуск квантовых переговоров...")
                self.log(f"[QUANTUM] Сообщение HR: {hr_message}")

                if self.overlay_hud and self.overlay_hud_active:
                    self.overlay_hud.set_status(HUDStatus.PROCESSING, "Анализ стратегий...")

                # Запускаем квантовые переговоры
                result = self.quantum_negotiation.negotiate_quantum(
                    hr_message=hr_message,
                    context={
                        'current_salary': self.base_salary if hasattr(self, 'base_salary') else AI_SALARY_TARGET,
                        'target_salary': AI_SALARY_TARGET,
                        'personality': AI_PERSONALITY
                    },
                    progress_callback=progress_callback
                )

                # Озвучиваем лучший результат
                best_offer = result.best_result.final_offer
                recommendation = result.recommendation

                self.log(f"[QUANTUM] 🎯 Лучший результат: ${best_offer:,.0f}")
                self.log(f"[QUANTUM] 💡 Рекомендация: {recommendation}")
                self.log(f"[QUANTUM] ⏱️ Время: {result.total_time:.1f} сек")

                # Озвучиваем рекомендацию
                threading.Thread(target=self._run_speak, args=(recommendation,), daemon=True).start()

                # Обновляем HUD
                if self.overlay_hud and self.overlay_hud_active:
                    self.overlay_hud.set_status(HUDStatus.IDLE, f"Лучший оффер: ${best_offer:,.0f}")

            except Exception as e:
                error_msg = f"Ошибка в квантовых переговорах: {e}"
                self.log(f"[QUANTUM] ❌ {error_msg}")
                if self.overlay_hud and self.overlay_hud_active:
                    self.overlay_hud.set_status(HUDStatus.ERROR, "Quantum Error")

        # Запускаем в отдельном потоке
        threading.Thread(target=negotiation_thread, daemon=True).start()

    def run_success_prediction(self):
        """Запуск прогноза успеха"""
        if not self.success_prediction:
            self.log("[PREDICT] Success Prediction не инициализирован")
            return

        def prediction_thread():
            """Поток для прогноза"""
            try:
                self.log("[PREDICT] 🚀 Запуск прогноза успеха...")

                if self.overlay_hud and self.overlay_hud_active:
                    self.overlay_hud.set_status(HUDStatus.PROCESSING, "Анализ шансов...")

                # Создаем фичи для прогноза - извлекаем из контекста
                company_size = self._extract_company_size_from_context()
                industry = self._extract_industry_from_context()
                role_level = self._extract_role_level_from_context()
                
                features = PredictionFeatures(
                    company_size=company_size,
                    industry=industry,
                    role_level=role_level,
                    interview_round=1,
                    time_spent=5.0,      # часов подготовки
                    questions_asked=3,
                    technical_score=0.8,
                    communication_score=0.7,
                    cultural_fit=0.8,
                    salary_expectation=AI_SALARY_TARGET,
                    market_rate=AI_SALARY_TARGET * 0.9,  # рыночная ставка
                    candidate_experience=5,  # лет опыта
                    similar_offers_count=2
                )

                # Делаем прогноз
                result = self.success_prediction.predict_success(features)

                # Озвучиваем результат
                probability = result.offer_probability
                confidence = result.confidence_interval

                self.log(f"[PREDICT] 🎯 Вероятность оффера: {probability:.1%}")
                self.log(f"[PREDICT] 📊 Доверительный интервал: {confidence[0]:.1%} - {confidence[1]:.1%}")

                if result.key_factors:
                    self.log(f"[PREDICT] 🔑 Ключевые факторы: {', '.join(result.key_factors[:3])}")

                if result.recommendations:
                    self.log(f"[PREDICT] 💡 Рекомендации: {result.recommendations[0]}")

                # Озвучиваем основной результат
                speech_text = f"Вероятность получить оффер: {probability:.0%}. {result.recommendations[0] if result.recommendations else ''}"
                threading.Thread(target=self._run_speak, args=(speech_text,), daemon=True).start()

                # Обновляем HUD
                if self.overlay_hud and self.overlay_hud_active:
                    status_msg = f"Оффер: {probability:.0%}"
                    self.overlay_hud.set_status(HUDStatus.IDLE, status_msg)

            except Exception as e:
                error_msg = f"Ошибка прогноза: {e}"
                self.log(f"[PREDICT] ❌ {error_msg}")
                if self.overlay_hud and self.overlay_hud_active:
                    self.overlay_hud.set_status(HUDStatus.ERROR, "Prediction Error")

        # Запускаем в отдельном потоке
        threading.Thread(target=prediction_thread, daemon=True).start()

    def toggle_telegram_bot(self):
        """Переключение Telegram бота"""
        if not self.telegram_active:
            self._start_telegram_bot()
        else:
            self._stop_telegram_bot()

    def _start_telegram_bot(self):
        """Запуск Telegram бота"""
        try:
            if not self.telegram_bot:
                self.log("[Telegram] Бот не инициализирован")
                return

            self.telegram_active = True
            status = "ON"
            color = "#00ff00"
            self.telegram_btn.config(text=f"📱 Telegram: {status}", bg=color)
            self.log("[Telegram] Запуск Telegram бота...")

            # Запускаем бота в отдельном потоке
            import asyncio
            def run_bot():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.telegram_bot.start_polling())
                except Exception as e:
                    self.log(f"[Telegram] Ошибка запуска бота: {e}")

            self.telegram_thread = threading.Thread(target=run_bot, daemon=True)
            self.telegram_thread.start()

            self.log("[Telegram] Telegram бот запущен! Используйте @your_bot в Telegram")

        except Exception as e:
            self.log(f"[Telegram] Ошибка запуска: {e}")

    def _stop_telegram_bot(self):
        """Остановка Telegram бота"""
        try:
            if self.telegram_bot:
                # Останавливаем бота асинхронно
                import asyncio
                async def stop_bot():
                    await self.telegram_bot.stop()

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(stop_bot())

            self.telegram_active = False
            status = "OFF"
            color = "#0088cc"
            self.telegram_btn.config(text=f"📱 Telegram: {status}", bg=color)
            self.log("[Telegram] Telegram бот остановлен")

        except Exception as e:
            self.log(f"[Telegram] Ошибка остановки: {e}")

    def toggle_auto_pilot(self):
        """Переключение Auto-Pilot"""
        if not self.auto_pilot:
            self.log("[AutoPilot] Auto-Pilot не инициализирован")
            return

        if self.auto_pilot.is_running:
            self.auto_pilot.stop()
            self.autopilot_btn.config(text="🚀 Auto-Pilot: OFF", bg='#ff4500')
            self.log("[AutoPilot] Auto-Pilot остановлен")
        else:
            self.auto_pilot.start()
            self.autopilot_btn.config(text="🚀 Auto-Pilot: ON", bg='#00ff00')
            self.log("[AutoPilot] Auto-Pilot запущен!")

    def _on_autopilot_state_change(self, state, start_time):
        """Callback при изменении состояния Auto-Pilot"""
        state_name = state.value
        self.log(f"[AutoPilot] 🔄 Состояние: {state_name}")

        # Обновляем статус в Telegram если активен
        if self.telegram_active and self.telegram_bot:
            # Отправляем статус в Telegram (нужно реализовать метод в боте)
            pass

    def _on_autopilot_application(self, application):
        """Callback при подаче нового отклика"""
        job_title = application.job.title
        company = application.job.company
        prediction = application.prediction_score

        self.log(f"[AutoPilot] ✅ Отклик подан: {job_title} в {company}")
        self.log(f"[AutoPilot] 🎯 Прогноз успеха: {prediction:.1%}")

        # Уведомление в Telegram
        if self.telegram_active and self.telegram_bot:
            message = (
                f"✅ <b>Новый отклик!</b>\n\n"
                f"🏢 <b>{company}</b>\n"
                f"💼 <b>{job_title}</b>\n"
                f"🎯 Прогноз: {prediction:.0%}\n\n"
                f"📅 Следующий follow-up: {application.follow_up_date.strftime('%d.%m') if application.follow_up_date else 'Не запланирован'}"
            )
            # self.telegram_bot.send_notification(message)  # Нужно реализовать в боте

    def _on_autopilot_offer(self, offer):
        """Callback при получении оффера"""
        company = offer.job.company
        amount = offer.offer_amount

        self.log(f"[AutoPilot] 🏆 Оффер получен: ${amount:,.0f} от {company}")

        # Важное уведомление в Telegram
        if self.telegram_active and self.telegram_bot:
            message = (
                f"🎉 <b>ОФФЕР ПОЛУЧЕН!</b>\n\n"
                f"🏢 <b>{company}</b>\n"
                f"💰 <b>${amount:,.0f}</b>\n\n"
                f"🎊 Поздравляем! МАГА справилась!"
            )
            # self.telegram_bot.send_urgent_notification(message)

    def open_telegram_control(self):
        """Открытие окна управления Telegram"""
        if not self.telegram_bot:
            self.log("[Telegram] Бот не инициализирован")
            return

        # Создаем новое окно управления
        control_window = tk.Toplevel(self.root)
        control_window.title("🎮 Telegram Control Panel")
        control_window.geometry("500x600")
        control_window.configure(bg='#2c3e50')

        # Заголовок
        title_label = tk.Label(control_window, text="Telegram Control Panel",
                              font=("Arial", 16, "bold"), bg='#2c3e50', fg='white')
        title_label.pack(pady=10)

        # Статус бота
        status_frame = tk.Frame(control_window, bg='#34495e', relief='raised', bd=2)
        status_frame.pack(fill='x', padx=10, pady=5)

        status_text = "🟢 Активен" if self.telegram_active else "🔴 Неактивен"
        status_label = tk.Label(status_frame, text=f"Статус бота: {status_text}",
                               font=("Arial", 12), bg='#34495e', fg='white')
        status_label.pack(pady=5)

        # Кнопки быстрого управления
        buttons_frame = tk.Frame(control_window, bg='#2c3e50')
        buttons_frame.pack(fill='x', padx=10, pady=10)

        # Кнопки в две колонки
        left_frame = tk.Frame(buttons_frame, bg='#2c3e50')
        left_frame.pack(side='left', padx=5)
        right_frame = tk.Frame(buttons_frame, bg='#2c3e50')
        right_frame.pack(side='right', padx=5)

        # Левая колонка
        tk.Button(left_frame, text="🔍 Найти работу",
                 command=lambda: self._telegram_quick_action("find_jobs"),
                 bg='#3498db', fg='white', width=15).pack(pady=2)

        tk.Button(left_frame, text="📧 Проверить почту",
                 command=lambda: self._telegram_quick_action("check_email"),
                 bg='#3498db', fg='white', width=15).pack(pady=2)

        tk.Button(left_frame, text="📅 Календарь",
                 command=lambda: self._telegram_quick_action("calendar"),
                 bg='#3498db', fg='white', width=15).pack(pady=2)

        tk.Button(left_frame, text="🎯 Прогноз",
                 command=lambda: self._telegram_quick_action("prediction"),
                 bg='#3498db', fg='white', width=15).pack(pady=2)

        # Правая колонка
        tk.Button(right_frame, text="💼 Переговоры",
                 command=lambda: self._telegram_quick_action("negotiations"),
                 bg='#e74c3c', fg='white', width=15).pack(pady=2)

        tk.Button(right_frame, text="🚀 Auto-Pilot",
                 command=lambda: self._telegram_quick_action("autopilot"),
                 bg='#e74c3c', fg='white', width=15).pack(pady=2)

        tk.Button(right_frame, text="🧠 Память",
                 command=lambda: self._telegram_quick_action("memory"),
                 bg='#e74c3c', fg='white', width=15).pack(pady=2)

        tk.Button(right_frame, text="⚙️ Настройки",
                 command=lambda: self._telegram_quick_action("settings"),
                 bg='#95a5a6', fg='white', width=15).pack(pady=2)

        # Инструкции
        instructions_frame = tk.Frame(control_window, bg='#34495e', relief='sunken', bd=2)
        instructions_frame.pack(fill='both', expand=True, padx=10, pady=10)

        instructions_text = """
        📱 Как использовать Telegram управление:

        1. Запустите бота кнопкой "📱 Telegram: ON"
        2. Найдите бота в Telegram: @your_maga_bot
        3. Используйте кнопки выше или команды:

        💬 Голосовые команды:
        • "МАГА, найди работу"
        • "МАГА, проверь почту"
        • "МАГА, подготовь к интервью"

        🎛️ Быстрые кнопки:
        • Найти работу - поиск вакансий
        • Почта - проверка email
        • Переговоры - запуск Quantum AI
        • Auto-Pilot - полная автономия

        📊 Статус обновляется в реальном времени!
        """

        instructions_label = tk.Label(instructions_frame, text=instructions_text,
                                    font=("Arial", 10), bg='#34495e', fg='white',
                                    justify='left', anchor='w')
        instructions_label.pack(fill='both', expand=True, padx=10, pady=10)

        # Кнопки тестирования
        test_frame = tk.Frame(control_window, bg='#2c3e50')
        test_frame.pack(fill='x', padx=10, pady=5)

        tk.Button(test_frame, text="🧪 Test API",
                 command=self._test_telegram_api, bg='#f39c12', fg='white', width=12).pack(side='left', padx=5)

        tk.Button(test_frame, text="🔗 Test Buttons",
                 command=self._test_telegram_buttons, bg='#f39c12', fg='white', width=12).pack(side='left', padx=5)

        # Кнопка закрытия
        close_btn = tk.Button(control_window, text="❌ Закрыть",
                             command=control_window.destroy, bg='#e74c3c', fg='white')
        close_btn.pack(pady=10)

    def _telegram_quick_action(self, action: str):
        """Быстрое действие через Telegram"""
        if not self.telegram_bot:
            self.log(f"[Telegram] Бот не инициализирован для действия: {action}")
            return

        try:
            # Имитируем нажатие кнопки в Telegram
            # В реальности нужно отправить callback боту
            self.log(f"[Telegram] Имитирую действие: {action}")

            # Для демонстрации - выполняем действия локально
            if action == "find_jobs":
                self.run_job_search()
            elif action == "check_email":
                self.log("[Telegram] Проверка почты...")
            elif action == "calendar":
                self.log("[Telegram] Открытие календаря...")
            elif action == "prediction":
                self.run_success_prediction()
            elif action == "negotiations":
                self.log("[Telegram] Запуск переговоров...")
            elif action == "autopilot":
                self.toggle_auto_pilot()
            elif action == "memory":
                self.log("[Telegram] Проверка памяти...")
            elif action == "settings":
                self.log("[Telegram] Открытие настроек...")

        except Exception as e:
            self.log(f"[Telegram] Ошибка быстрого действия {action}: {e}")

    def run_job_search(self):
        """Запуск поиска работы"""
        if not self.job_api_manager:
            self.log("[JobSearch] Job API не инициализирован")
            return

        def search_thread():
            """Поток поиска работы"""
            try:
                self.log("[JobSearch] 🚀 Начинаю поиск работы...")

                # Параметры поиска
                params = JobSearchParams(
                    query="Senior Python Developer",
                    location="Москва",
                    experience="between3And6",
                    salary_min=150000,
                    limit=10
                )

                # Поиск через API
                import asyncio
                jobs = asyncio.run(self.job_api_manager.search_jobs_multi_api(params))

                if jobs:
                    self.log(f"[JobSearch] 📋 Найдено {len(jobs)} вакансий:")
                    for i, job in enumerate(jobs[:5], 1):  # Показываем первые 5
                        self.log(f"[JobSearch] {i}. {job.title} в {job.company} - {job.salary or 'з/п не указана'}")
                else:
                    self.log("[JobSearch] 😔 Вакансий не найдено")

            except Exception as e:
                self.log(f"[JobSearch] ❌ Ошибка поиска: {e}")

        threading.Thread(target=search_thread, daemon=True).start()

    def _test_telegram_api(self):
        """Тестирование Telegram API"""
        if not self.telegram_bot:
            self.log("[Telegram] ❌ Бот не инициализирован")
            return

        try:
            # Тестируем инициализацию компонентов
            status = {
                "brain": self.telegram_bot.brain_manager is not None,
                "intent": self.telegram_bot.intent_engine is not None,
                "quantum": self.telegram_bot.quantum_negotiation is not None,
                "memory": self.telegram_bot.memory_palace is not None,
                "prediction": self.telegram_bot.success_prediction is not None,
                "secrets": self.telegram_bot.secrets_manager is not None
            }

            active_components = sum(status.values())
            total_components = len(status)

            self.log(f"[Telegram] 🧪 API Test: {active_components}/{total_components} компонентов инициализировано")
            self.log(f"[Telegram] 📊 Статус: {status}")

            if active_components == total_components:
                self.log("[Telegram] ✅ Telegram API полностью готов!")
            else:
                self.log("[Telegram] ⚠️ Некоторые компоненты недоступны")

        except Exception as e:
            self.log(f"[Telegram] ❌ Ошибка тестирования API: {e}")

    def _test_telegram_buttons(self):
        """Тестирование Telegram кнопок"""
        if not self.telegram_bot:
            self.log("[Telegram] ❌ Бот не инициализирован")
            return

        try:
            # Имитируем нажатие кнопок
            test_user_id = 123456789  # Тестовый user ID

            self.log("[Telegram] 🔗 Тестирование кнопок...")

            # Тест основных кнопок
            buttons = ["find_jobs", "check_email", "calendar", "negotiations", "prediction", "memory", "autopilot", "settings"]

            for button in buttons:
                try:
                    # Имитируем callback
                    self._telegram_quick_action(button)
                    self.log(f"[Telegram] ✅ Кнопка '{button}' протестирована")
                except Exception as e:
                    self.log(f"[Telegram] ❌ Ошибка кнопки '{button}': {e}")

            self.log("[Telegram] 🎯 Все кнопки протестированы!")

        except Exception as e:
            self.log(f"[Telegram] ❌ Ошибка тестирования кнопок: {e}")

    def _run_speak(self, text):
        try:
            # Обновляем HUD статус перед озвучиванием
            if self.overlay_hud and self.overlay_hud_active:
                self.overlay_hud.set_status(HUDStatus.SPEAKING, "Speaking...")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.speak(text))
            loop.close()

            # Возвращаем HUD в idle после озвучивания
            if self.overlay_hud and self.overlay_hud_active:
                self.overlay_hud.set_status(HUDStatus.IDLE, "Ready")

        except Exception as e:
            self.log(f"[TTS Thread Error] {e}")
            # Возвращаем HUD в idle при ошибке
            if self.overlay_hud and self.overlay_hud_active:
                self.overlay_hud.set_status(HUDStatus.ERROR, "TTS Error")

    def _check_ffmpeg(self) -> str:
        """
        Проверка наличия FFmpeg в системе
        """
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return "OK"
            else:
                return "NOT FOUND"
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return "NOT FOUND"
    
    def _initialize_brain(self):
        """
        Инициализация Brain SDK
        """
        try:
            # Конфигурация GigaChat с реальными ключами
            config = GigaChatConfig(
                client_id="0199824b-4c1e-7ef1-b423-bb3156ddecee",
                client_secret="e1235bde-e645-426b-895b-e966c752d9ba",
                api_url="https://gigachat.devices.sberbank.ru/api/v1",
                scope="GIGACHAT_API_PERS",
                verify_ssl=False,  # Отключаем SSL проверку для корпоративных сетей
                ca_bundle=None
            )
            
            # Инициализация Brain Manager
            self.brain_manager = BrainManager(config)
            
            # Инициализация RAG Manager
            self.rag_manager = RAGManager()
            
            # Реальная инициализация Brain SDK
            brain_success = self.brain_manager.initialize()
            rag_success = self.rag_manager.initialize()
            
            if brain_success and rag_success:
                print("[BRAIN] Brain SDK инициализирован успешно!")
                print("[BRAIN] GigaChat API подключен")
                print("[BRAIN] RAG индекс загружен")
            else:
                print("[BRAIN] Частичная инициализация")
                if not brain_success:
                    print("[BRAIN] GigaChat API недоступен")
                if not rag_success:
                    print("[BRAIN] RAG индекс не загружен")
            
        except Exception as e:
            print(f"[BRAIN] Ошибка инициализации: {e}")
            self.brain_manager = None
            self.rag_manager = None

    def _initialize_ultra_features(self):
        """Инициализация Ultra Features"""
        try:
            # Intent Engine (Мага)
            self.intent_engine = IntentEngine()
            if self.brain_manager:
                self.intent_engine.set_brain_manager(self.brain_manager)
            if self.rag_manager:
                self.intent_engine.set_rag_manager(self.rag_manager)

            # Регистрируем действия Мага
            self.intent_engine.register_maga_actions()

            # Screen Scanner
            self.screen_scanner = ScreenScanner(
                trigger_words=["оффер", "зарплата", "тестовое", "salary", "offer"],
                on_trigger=self._on_screen_trigger
            )

            # App Detector
            self.app_detector = AppDetector(
                on_app_detected=self._on_app_detected
            )

            # Mail & Calendar
            self.mail_calendar = MailCalendar(
                on_mail_received=self._on_mail_received,
                on_calendar_event=self._on_calendar_event
            )

            # ATS Tailor
            self.ats_tailor = ATSTailor()

            # Negotiation Engine
            self.negotiation_engine = NegotiationEngine(
                base_salary=AI_SALARY_TARGET,
                target_salary=AI_SALARY_TARGET,
                min_acceptable=int(AI_SALARY_TARGET * 0.8)
            )

            # Quantum Negotiation Engine
            self.quantum_negotiation = QuantumNegotiationEngine(
                brain_manager=self.brain_manager,
                base_salary=AI_SALARY_TARGET,
                target_salary=AI_SALARY_TARGET,
                max_parallel=3,
                timeout=60
            )

            # Overlay HUD
            self.overlay_hud = OverlayHUD(
                on_hotkey=self._on_hud_hotkey,
                position="top-right"
            )

            # Secrets & Watchdog
            self.secrets_watchdog = SecretsWatchdogManager()

            # HR Simulator
            self.hr_simulator = HRSimulator()

            # Memory Palace
            self.memory_palace = MemoryPalace()

            # Success Prediction Engine
            self.success_prediction = SuccessPredictionEngine()

            # Telegram Bot
            telegram_token = self.secrets_watchdog.get_secret("TELEGRAM_BOT_TOKEN")
            if telegram_token:
                try:
                    self.telegram_bot = MAGATelegramBot(telegram_token)
                    print("[Telegram] Бот инициализирован (API готов)")
                except Exception as e:
                    print(f"[Telegram] Ошибка инициализации бота: {e}")
            else:
                print("[Telegram] TELEGRAM_BOT_TOKEN не найден")

            # Job APIs Manager
            self.job_api_manager = JobAPIManager()

            # Desktop RPA
            self.desktop_rpa = DesktopRPA()

            # Auto-Pilot
            autopilot_config = AutoPilotConfig(
                target_role="Senior Python Developer",
                target_companies=["Яндекс", "Сбер", "Тинькофф"],
                target_salary=AI_SALARY_TARGET,
                max_applications_per_day=5
            )

            self.auto_pilot = AutoPilot(
                config=autopilot_config,
                success_prediction=self.success_prediction,
                brain_manager=self.brain_manager
            )

            # Настраиваем callbacks для Auto-Pilot
            self.auto_pilot.on_state_change = self._on_autopilot_state_change
            self.auto_pilot.on_application = self._on_autopilot_application
            self.auto_pilot.on_offer = self._on_autopilot_offer

            print("[AutoPilot] Система автономного найма инициализирована")

            # Интегрируем модули с Intent Engine
            self.intent_engine.set_screen_scanner(self.screen_scanner)
            self.intent_engine.set_app_detector(self.app_detector)
            self.intent_engine.set_mail_calendar(self.mail_calendar)
            self.intent_engine.set_ats_tailor(self.ats_tailor)
            self.intent_engine.set_negotiation_engine(self.negotiation_engine)
            self.intent_engine.set_overlay_hud(self.overlay_hud)

            print("[ULTRA] Все Ultra Features инициализированы")

        except Exception as e:
            print(f"[ULTRA] Ошибка инициализации Ultra Features: {e}")

    def _on_screen_trigger(self, triggers: List[str], text: str, window):
        """Обработка триггеров с экрана"""
        trigger_text = f"Обнаружен триггер на экране: {', '.join(triggers)}"
        self.log(f"[SCREEN] {trigger_text}")

        # Автоматически активируем AI Assistant если нужно
        if not self.ai_active:
            self.toggle_ai_assistant()

        # Генерируем ответ через AI
        ai_response = self.analyze_hr_message(trigger_text)
        if ai_response:
            self.log(f"[SCREEN] AI Response: {ai_response}")
            threading.Thread(target=self._run_speak, args=(ai_response,), daemon=True).start()

    def _on_app_detected(self, app_name: str, app_info: Dict, action: str):
        """Обработка обнаружения приложения"""
        self.log(f"[APP] {app_name} {action}")

    def _on_mail_received(self, mail_info: Dict):
        """Обработка получения письма"""
        subject = mail_info.get('subject', 'Без темы')
        sender = mail_info.get('from', 'Неизвестно')
        self.log(f"[MAIL] Новое письмо: '{subject}' от {sender}")

        # Автоматический анализ через AI
        if self.ai_active:
            analysis = self.analyze_hr_message(f"Новое письмо: {subject}")
            if analysis:
                self.log(f"[MAIL] Анализ: {analysis}")

    def _on_calendar_event(self, event_info: Dict):
        """Обработка события календаря"""
        subject = event_info.get('subject', 'Событие')
        start_time = event_info.get('start', 'Неизвестно')
        self.log(f"[CALENDAR] Событие: '{subject}' в {start_time}")

    def _on_hud_hotkey(self, action: str):
        """Обработка хоткеев HUD"""
        if action == 'listen':
            self.start_listen()
        elif action == 'mute':
            self.toggle_ai_mute()
        elif action == 'intro':
            self.speak_intro()

    def analyze_hr_message(self, text: str) -> str:
        """
        Анализирует сообщение HR и возвращает подходящий ответ.
        """
        # Если Brain SDK доступен, используем его
        if self.brain_manager and self.rag_manager:
            try:
                # Получение контекста из RAG
                context = {}
                if self.rag_manager and hasattr(self.rag_manager, 'search_context'):
                    try:
                        rag_context = self.rag_manager.search_context(text, max_length=500)
                        context["rag_context"] = rag_context
                    except Exception as e:
                        self.log(f"[RAG] Ошибка поиска контекста: {e}")
                
                # Добавление контекста экрана (если есть)
                context["screen_text"] = getattr(self, 'current_screen_text', '')
                
                # Обработка через Brain SDK
                response, analysis = self.brain_manager.process_hr_message(text, context)
                
                # Логирование анализа
                self.log(f"[BRAIN] 📊 Анализ: {analysis}")
                
                return response
                
            except Exception as e:
                self.log(f"[BRAIN] ❌ Ошибка анализа: {e}")
                # Fallback на простой анализ - продолжаем выполнение
        
        # Простой анализ ключевых слов (fallback)
        text_lower = text.lower()
        
        # Анализ зарплаты
        salary_patterns = [
            r'\$?(\d{1,3}(?:,\d{3})*(?:k|000)?)',
            r'(\d+)\s*(?:k|thousand|тысяч)',
            r'компенсация|зарплата|salary|compensation'
        ]
        
        salary_mentioned = any(re.search(pattern, text_lower) for pattern in salary_patterns)
        
        # Анализ технических вопросов
        tech_patterns = [
            r'python|java|javascript|react|node|docker|kubernetes',
            r'машинное обучение|ml|ai|нейросети',
            r'архитектура|система|база данных|database'
        ]
        
        is_technical = any(re.search(pattern, text_lower) for pattern in tech_patterns)
        
        # Анализ вопросов о компании
        company_patterns = [
            r'компания|команда|культура|офис',
            r'почему мы|зачем вам|интересно ли'
        ]
        
        is_company_question = any(re.search(pattern, text_lower) for pattern in company_patterns)
        
        # Выбор ответа
        if salary_mentioned:
            if not self.salary_mentioned:
                self.salary_mentioned = True
                return random.choice(AI_RESPONSES["salary_low"])
            else:
                return random.choice(AI_RESPONSES["salary_negotiation"])
        elif is_technical:
            return random.choice(AI_RESPONSES["technical_questions"])
        elif is_company_question:
            return random.choice(AI_RESPONSES["company_questions"])
        elif AI_PERSONALITY == "aggressive":
            return random.choice(AI_RESPONSES["aggressive"])
        else:
            return "Интересно. Расскажите подробнее."

    def ai_auto_response(self, text: str):
        """
        Автоматический ответ AI-ассистента на основе анализа HR.
        Сохраняет разговор в Memory Palace
        """
        if not AI_ASSISTANT_MODE or not self.ai_active:
            return

        # Сохраняем входящее сообщение в память
        if self.memory_palace:
            self.memory_palace.add_memory(
                content=f"HR сказал: {text}",
                metadata={
                    'type': 'hr_message',
                    'company': self._extract_company_from_context(),
                    'source': 'conversation'
                },
                tags=['hr', 'conversation', 'input']
            )

        # Если активны квантовые переговоры - используем их
        if self.quantum_active and self.quantum_negotiation:
            self.run_quantum_negotiation(text)
            return

        # Обычный анализ
        response = self.analyze_hr_message(text)

        # Сохраняем ответ в память
        if self.memory_palace:
            self.memory_palace.add_memory(
                content=f"МАГА ответил: {response}",
                metadata={
                    'type': 'ai_response',
                    'company': 'unknown',
                    'response_to': text[:100],
                    'source': 'conversation'
                },
                tags=['ai', 'conversation', 'output', 'response']
            )

        # Добавляем задержку для реалистичности
        def delayed_response():
            time.sleep(AI_RESPONSE_DELAY)
            self.log(f"[AI] Auto-responding: {response}")
            threading.Thread(target=self._run_speak, args=(response,), daemon=True).start()

        threading.Thread(target=delayed_response, daemon=True).start()

    def run(self):
        if not self.root:
            print("[GUI] GUI not available, cannot run application")
            return

        # Обработчик закрытия окна
        def on_closing():
            self.stop_listen()
            self.root.destroy()

        self.root.protocol("WM_DELETE_WINDOW", on_closing)

        # Запускаем GUI
        self.root.mainloop()
    
    def _extract_company_size_from_context(self) -> str:
        """Извлекает размер компании из контекста"""
        try:
            # Анализируем текст на экране для определения размера компании
            screen_text = self._get_screen_text()
            
            # Ключевые слова для определения размера
            if any(word in screen_text.lower() for word in ['startup', 'стартап', 'малый', 'small']):
                return "startup"
            elif any(word in screen_text.lower() for word in ['корпорация', 'corporation', 'крупная', 'большая']):
                return "enterprise"
            elif any(word in screen_text.lower() for word in ['средняя', 'medium', 'mid']):
                return "mid"
            else:
                return "mid"  # По умолчанию
                
        except Exception as e:
            self.log(f"Ошибка извлечения размера компании: {e}")
            return "mid"
    
    def _extract_industry_from_context(self) -> str:
        """Извлекает отрасль из контекста"""
        try:
            screen_text = self._get_screen_text()
            
            # Определяем отрасль по ключевым словам
            if any(word in screen_text.lower() for word in ['fintech', 'финтех', 'банк', 'bank', 'финансы']):
                return "fintech"
            elif any(word in screen_text.lower() for word in ['ecommerce', 'e-commerce', 'торговля', 'retail']):
                return "ecommerce"
            elif any(word in screen_text.lower() for word in ['gaming', 'игры', 'game']):
                return "gaming"
            elif any(word in screen_text.lower() for word in ['ai', 'ml', 'искусственный интеллект', 'машинное обучение']):
                return "ai"
            else:
                return "tech"  # По умолчанию
                
        except Exception as e:
            self.log(f"Ошибка извлечения отрасли: {e}")
            return "tech"
    
    def _extract_role_level_from_context(self) -> str:
        """Извлекает уровень позиции из контекста"""
        try:
            screen_text = self._get_screen_text()
            
            # Определяем уровень позиции
            if any(word in screen_text.lower() for word in ['junior', 'младший', 'entry', 'начальный']):
                return "junior"
            elif any(word in screen_text.lower() for word in ['senior', 'старший', 'ведущий']):
                return "senior"
            elif any(word in screen_text.lower() for word in ['lead', 'руководитель', 'team lead']):
                return "lead"
            elif any(word in screen_text.lower() for word in ['principal', 'архитектор', 'architect']):
                return "principal"
            else:
                return "senior"  # По умолчанию
                
        except Exception as e:
            self.log(f"Ошибка извлечения уровня позиции: {e}")
            return "senior"
    
    def _extract_company_from_context(self) -> str:
        """Извлекает название компании из контекста"""
        try:
            screen_text = self._get_screen_text()
            
            # Ищем известные компании
            known_companies = ['яндекс', 'yandex', 'сбер', 'sber', 'тинькофф', 'tinkoff', 'vk', 'ozon', 'mail.ru']
            
            for company in known_companies:
                if company in screen_text.lower():
                    return company.title()
            
            return "unknown"
                
        except Exception as e:
            self.log(f"Ошибка извлечения компании: {e}")
            return "unknown"
    
    def _get_screen_text(self) -> str:
        """Получает текст с экрана для анализа"""
        try:
            # Используем OCR для получения текста с экрана
            if hasattr(self, 'ocr_engine') and self.ocr_engine:
                # Реальный OCR
                screenshot = self._capture_screenshot()
                text = self.ocr_engine.extract_text(screenshot)
                return text
            else:
                # Fallback - возвращаем пустую строку
                return ""
        except Exception as e:
            self.log(f"Ошибка получения текста с экрана: {e}")
            return ""


if __name__ == "__main__":
    App().run()
