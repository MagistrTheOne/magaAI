# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UVICORN_WORKERS=1

# Минимальные зависимости для работы
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Опциональная установка ffmpeg для конвертации аудио
# Раскомментируйте следующие строки, если нужна конвертация MP3 в OGG/OPUS:
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     ffmpeg \
#   && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем код приложения
COPY app ./app

# Открываем порт
EXPOSE 8080

# Запускаем приложение
CMD ["python", "-m", "app.main"]
