#!/usr/bin/env python3
"""
Railway startup script for MAGA AI
"""
import os
import sys
import asyncio
from telegram_bot import MAGATelegramBot

# Устанавливаем headless режим
os.environ['HEADLESS'] = '1'
os.environ['DISPLAY'] = ''

def health_check():
    """Проверка здоровья для Railway"""
    return {"status": "healthy", "service": "maga-ai"}

async def main():
    """Основная функция запуска"""
    print("🚀 Starting MAGA AI on Railway...")

    try:
        # Создаем бота
        bot = MAGATelegramBot()

        print("✅ MAGA AI initialized successfully")
        print("🤖 Telegram bot ready")

        # Запускаем бота
        await bot.run()

    except Exception as e:
        print(f"❌ Error starting MAGA AI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Для health check
    if len(sys.argv) > 1 and sys.argv[1] == "--health":
        import json
        print(json.dumps(health_check()))
        sys.exit(0)

    # Запуск основного приложения
    asyncio.run(main())
