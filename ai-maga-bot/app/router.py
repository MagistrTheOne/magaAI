"""
Telegram Bot router с обработчиками сообщений.
"""
import logging
from typing import Optional
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, Voice
from aiogram.filters import Command, CommandStart
from aiogram.exceptions import TelegramAPIError

from app.settings import settings
from app.services.mode import (
    get_user_mode, set_user_mode, determine_response_mode, get_mode_description
)
from app.services.yandex_llm import complete_text, YandexLLMError
from app.services.yandex_stt import recognize_speech, YandexSTTError
from app.services.tts import synthesize, TTSProviderError
from app.services.tg_utils import (
    send_text_message, send_voice_message, send_audio_message, send_error_message, 
    download_voice_file, TelegramError
)

logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()
router = Router()

# Регистрируем роутер в диспетчере
dp.include_router(router)


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    """Обработчик команды /start."""
    user_id = message.from_user.id
    current_mode = get_user_mode(user_id)
    mode_description = get_mode_description(current_mode)
    
    welcome_text = (
        f"🤖 Привет! Я AI-Мага - ваш персональный ассистент.\n\n"
        f"📋 Текущий режим: {current_mode}\n"
        f"💡 {mode_description}\n\n"
        f"🔧 Команды:\n"
        f"• /mode auto|text|voice - изменить режим ответа\n"
        f"• /start - показать это сообщение\n\n"
        f"💬 Просто напишите мне или отправьте голосовое сообщение!"
    )
    
    try:
        await send_text_message(bot, user_id, welcome_text)
        logger.info(f"Отправлено приветствие пользователю {user_id}")
    except TelegramError as e:
        logger.error(f"Ошибка отправки приветствия: {e}")


@router.message(Command("mode"))
async def mode_handler(message: Message) -> None:
    """Обработчик команды /mode."""
    user_id = message.from_user.id
    text = message.text or ""
    
    # Извлекаем режим из команды
    parts = text.split()
    if len(parts) < 2:
        # Показываем текущий режим
        current_mode = get_user_mode(user_id)
        mode_description = get_mode_description(current_mode)
        
        help_text = (
            f"📋 Текущий режим: {current_mode}\n"
            f"💡 {mode_description}\n\n"
            f"🔧 Доступные режимы:\n"
            f"• /mode auto - автоматический выбор\n"
            f"• /mode text - только текстовые ответы\n"
            f"• /mode voice - только голосовые ответы"
        )
        
        try:
            await send_text_message(bot, user_id, help_text)
        except TelegramError as e:
            logger.error(f"Ошибка отправки справки по режимам: {e}")
        return
    
    new_mode = parts[1].lower()
    if new_mode not in ["auto", "text", "voice"]:
        error_text = "❌ Неверный режим. Используйте: auto, text или voice"
        try:
            await send_text_message(bot, user_id, error_text)
        except TelegramError as e:
            logger.error(f"Ошибка отправки сообщения об ошибке режима: {e}")
        return
    
    # Устанавливаем новый режим
    set_user_mode(user_id, new_mode)
    mode_description = get_mode_description(new_mode)
    
    success_text = (
        f"✅ Режим изменен на: {new_mode}\n"
        f"💡 {mode_description}"
    )
    
    try:
        await send_text_message(bot, user_id, success_text)
        logger.info(f"Пользователь {user_id} изменил режим на {new_mode}")
    except TelegramError as e:
        logger.error(f"Ошибка отправки подтверждения смены режима: {e}")


@router.message()
async def message_handler(message: Message) -> None:
    """Обработчик текстовых сообщений."""
    user_id = message.from_user.id
    text = message.text or ""
    
    if not text.strip():
        return
    
    logger.info(f"Получено текстовое сообщение от {user_id}: {text[:100]}...")
    
    try:
        # Определяем режим ответа
        response_mode = determine_response_mode(user_id, "text", text)
        
        # Получаем ответ от LLM
        llm_response = await complete_text(
            system_prompt="Ты полезный AI-ассистент. Отвечай кратко и по делу на русском языке.",
            user_message=text
        )
        
        # Отправляем ответ в нужном формате
        if response_mode == "voice":
            # Синтезируем речь через фасад TTS
            tts_result = await synthesize(llm_response)
            
            if tts_result["type"] == "voice":
                await send_voice_message(bot, user_id, tts_result["data"], message.message_id)
                logger.info(f"Отправлен голосовой ответ пользователю {user_id}")
            else:
                await send_audio_message(bot, user_id, tts_result["data"], message.message_id)
                logger.info(f"Отправлен аудио ответ пользователю {user_id}")
        else:
            # Отправляем текст
            await send_text_message(bot, user_id, llm_response, message.message_id)
            logger.info(f"Отправлен текстовый ответ пользователю {user_id}")
            
    except YandexLLMError as e:
        logger.error(f"Ошибка LLM: {e}")
        await send_error_message(bot, user_id, "Ошибка при обработке запроса", message.message_id)
    except TTSProviderError as e:
        logger.error(f"Ошибка TTS: {e}")
        # Fallback на текстовый ответ
        try:
            await send_text_message(bot, user_id, llm_response, message.message_id)
        except:
            await send_error_message(bot, user_id, "Ошибка синтеза речи", message.message_id)
    except TelegramError as e:
        logger.error(f"Ошибка Telegram: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при обработке сообщения: {e}")
        await send_error_message(bot, user_id, "Произошла неожиданная ошибка", message.message_id)


@router.message(lambda message: message.voice is not None)
async def voice_handler(message: Message) -> None:
    """Обработчик голосовых сообщений."""
    user_id = message.from_user.id
    voice = message.voice
    
    logger.info(f"Получено голосовое сообщение от {user_id}")
    
    try:
        # Проверяем, включен ли STT
        if not settings.yandex_stt_enable:
            error_text = (
                "🎤 Голосовое сообщение получено, но STT отключен.\n"
                "Отправьте текстовое сообщение или включите STT в настройках."
            )
            await send_text_message(bot, user_id, error_text, message.message_id)
            return
        
        # Скачиваем голосовой файл
        audio_data = await download_voice_file(bot, voice)
        
        # Распознаем речь
        recognized_text = await recognize_speech(audio_data)
        
        if not recognized_text.strip():
            await send_text_message(bot, user_id, "Не удалось распознать речь", message.message_id)
            return
        
        logger.info(f"Распознан текст: {recognized_text[:100]}...")
        
        # Получаем ответ от LLM
        llm_response = await complete_text(
            system_prompt="Ты полезный AI-ассистент. Отвечай кратко и по делу на русском языке.",
            user_message=recognized_text
        )
        
        # Определяем режим ответа (для голоса всегда голос)
        response_mode = determine_response_mode(user_id, "voice")
        
        # Отправляем ответ
        if response_mode == "voice":
            # Синтезируем речь через фасад TTS
            tts_result = await synthesize(llm_response)
            
            if tts_result["type"] == "voice":
                await send_voice_message(bot, user_id, tts_result["data"], message.message_id)
                logger.info(f"Отправлен голосовой ответ пользователю {user_id}")
            else:
                await send_audio_message(bot, user_id, tts_result["data"], message.message_id)
                logger.info(f"Отправлен аудио ответ пользователю {user_id}")
        else:
            await send_text_message(bot, user_id, llm_response, message.message_id)
            logger.info(f"Отправлен текстовый ответ пользователю {user_id}")
            
    except YandexSTTError as e:
        logger.error(f"Ошибка STT: {e}")
        await send_error_message(bot, user_id, "Ошибка распознавания речи", message.message_id)
    except YandexLLMError as e:
        logger.error(f"Ошибка LLM: {e}")
        await send_error_message(bot, user_id, "Ошибка при обработке запроса", message.message_id)
    except TTSProviderError as e:
        logger.error(f"Ошибка TTS: {e}")
        # Fallback на текстовый ответ
        try:
            await send_text_message(bot, user_id, llm_response, message.message_id)
        except:
            await send_error_message(bot, user_id, "Ошибка синтеза речи", message.message_id)
    except TelegramError as e:
        logger.error(f"Ошибка Telegram: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при обработке голоса: {e}")
        await send_error_message(bot, user_id, "Произошла неожиданная ошибка", message.message_id)


async def set_webhook() -> None:
    """Установить webhook для бота."""
    try:
        webhook_url = settings.webhook_url
        secret_token = settings.telegram_webhook_secret
        
        logger.info(f"Устанавливаем webhook: {webhook_url}")
        
        await bot.set_webhook(
            url=webhook_url,
            secret_token=secret_token
        )
        
        logger.info("Webhook установлен успешно")
        
    except TelegramAPIError as e:
        logger.error(f"Ошибка установки webhook: {e}")
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при установке webhook: {e}")
        raise


async def close_bot() -> None:
    """Закрыть соединение с ботом."""
    try:
        await bot.session.close()
        logger.info("Соединение с ботом закрыто")
    except Exception as e:
        logger.error(f"Ошибка при закрытии соединения с ботом: {e}")
