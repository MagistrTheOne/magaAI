# Оптимизированный Dockerfile для Railway
FROM python:3.11-slim

# Устанавливаем только необходимые системные зависимости
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt первым для кэширования слоев
COPY requirements_v3.txt requirements.txt

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем только необходимые файлы
COPY telegram_bot_v3.py .
COPY brain/ brain/
COPY integrations/ integrations/
COPY services/ services/
COPY health_check.py .

# Создаем директории для данных
RUN mkdir -p storage data/rag_index

# Устанавливаем переменные окружения для Railway
ENV PYTHONUNBUFFERED=1
ENV HEADLESS=1
ENV DISPLAY=""
ENV PORT=8000

# Создаем пользователя для безопасности
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Открываем порт для health check
EXPOSE 8000

# Запускаем приложение
CMD ["python", "telegram_bot_v3.py"]
