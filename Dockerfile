# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем системные зависимости для Railway
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    tesseract-ocr \
    tesseract-ocr-rus \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libxss1 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    libgtk-3-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt первым для кэширования слоев
COPY requirements_v3.txt requirements.txt

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Устанавливаем playwright браузеры для headless режима
RUN playwright install chromium --with-deps

# Скачиваем NLTK данные
RUN python -c "import nltk; nltk.download('punkt')"

# Копируем код приложения
COPY . .

# Устанавливаем переменные окружения для Railway
ENV PYTHONUNBUFFERED=1
ENV HEADLESS=1
ENV DISPLAY=""
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Создаем пользователя для безопасности
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Открываем порт для health check
EXPOSE 8000

# Запускаем приложение
CMD ["python", "telegram_bot_v3.py"]
