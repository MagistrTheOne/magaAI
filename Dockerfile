# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Устанавливаем playwright браузеры
RUN playwright install chromium

# Скачиваем NLTK данные
RUN python -c "import nltk; nltk.download('punkt')"

# Копируем код приложения
COPY . .

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1
ENV HEADLESS=1
ENV DISPLAY=""

# Открываем порт для health check
EXPOSE 8000

# Запускаем приложение
CMD ["python", "main.py"]
