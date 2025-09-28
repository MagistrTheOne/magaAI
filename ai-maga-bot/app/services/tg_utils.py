"""
Утилиты для работы с Telegram Bot API.
"""
import logging
from typing import Optional, Union
from aiogram import Bot
from aiogram.types import Message, Voice, InputFile
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)


class TelegramError(Exception):
    """Ошибка при работе с Telegram API."""
    """Вспомогательные функции для работы с Telegram."""
    pass


async def send_text_message(
    bot: Bot, 
    chat_id: int, 
    text: str,
    reply_to_message_id: Optional[int] = None
) -> Message:
    """
    Отправить текстовое сообщение.
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        text: Текст сообщения
        reply_to_message_id: ID сообщения для ответа
        
    Returns:
        Message: Отправленное сообщение
        
    Raises:
        TelegramError: При ошибке отправки
    """
    try:
        logger.debug(f"Отправляем текстовое сообщение в чат {chat_id}: {text[:50]}...")
        
        message = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_to_message_id=reply_to_message_id
        )
        
        logger.info(f"Текстовое сообщение отправлено в чат {chat_id}")
        return message
        
    except TelegramAPIError as e:
        logger.error(f"Ошибка Telegram API при отправке текста: {e}")
        raise TelegramError(f"Ошибка отправки текста: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке текста: {e}")
        raise TelegramError(f"Ошибка отправки текста: {e}")


async def send_voice_message(
    bot: Bot,
    chat_id: int,
    audio_data: bytes,
    reply_to_message_id: Optional[int] = None
) -> Message:
    """
    Отправить голосовое сообщение.
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        audio_data: Аудио данные (oggopus)
        reply_to_message_id: ID сообщения для ответа
        
    Returns:
        Message: Отправленное сообщение
        
    Raises:
        TelegramError: При ошибке отправки
    """
    try:
        logger.debug(f"Отправляем голосовое сообщение в чат {chat_id}: {len(audio_data)} байт")
        
        # Создаем InputFile из байтов
        voice_file = InputFile(
            io=audio_data,
            filename="voice.ogg",
            content_type="application/ogg"
        )
        
        message = await bot.send_voice(
            chat_id=chat_id,
            voice=voice_file,
            reply_to_message_id=reply_to_message_id
        )
        
        logger.info(f"Голосовое сообщение отправлено в чат {chat_id}")
        return message
        
    except TelegramAPIError as e:
        logger.error(f"Ошибка Telegram API при отправке голоса: {e}")
        raise TelegramError(f"Ошибка отправки голоса: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке голоса: {e}")
        raise TelegramError(f"Ошибка отправки голоса: {e}")


async def send_audio_message(
    bot: Bot,
    chat_id: int,
    audio_data: bytes,
    title: str = "AI Response",
    performer: str = "AI-Maga",
    reply_to_message_id: Optional[int] = None
) -> Message:
    """
    Отправить аудио сообщение (mp3).
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        audio_data: Аудио данные (mp3)
        title: Название аудио
        performer: Исполнитель
        reply_to_message_id: ID сообщения для ответа
        
    Returns:
        Message: Отправленное сообщение
        
    Raises:
        TelegramError: При ошибке отправки
    """
    try:
        logger.debug(f"Отправляем аудио сообщение в чат {chat_id}: {len(audio_data)} байт")
        
        # Создаем InputFile из байтов
        audio_file = InputFile(
            io=audio_data,
            filename="audio.mp3",
            content_type="audio/mpeg"
        )
        
        message = await bot.send_audio(
            chat_id=chat_id,
            audio=audio_file,
            title=title,
            performer=performer,
            reply_to_message_id=reply_to_message_id
        )
        
        logger.info(f"Аудио сообщение отправлено в чат {chat_id}")
        return message
        
    except TelegramAPIError as e:
        logger.error(f"Ошибка Telegram API при отправке аудио: {e}")
        raise TelegramError(f"Ошибка отправки аудио: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке аудио: {e}")
        raise TelegramError(f"Ошибка отправки аудио: {e}")


async def download_voice_file(bot: Bot, voice: Voice) -> bytes:
    """
    Скачать голосовой файл.
    
    Args:
        bot: Экземпляр бота
        voice: Объект голосового сообщения
        
    Returns:
        bytes: Аудио данные
        
    Raises:
        TelegramError: При ошибке скачивания
    """
    try:
        logger.debug(f"Скачиваем голосовой файл: {voice.file_id}")
        
        # Получаем информацию о файле
        file_info = await bot.get_file(voice.file_id)
        
        # Скачиваем файл
        file_data = await bot.download_file(file_info.file_path)
        
        if not file_data:
            raise TelegramError("Пустые данные файла")
        
        logger.debug(f"Голосовой файл скачан: {len(file_data)} байт")
        return file_data
        
    except TelegramAPIError as e:
        logger.error(f"Ошибка Telegram API при скачивании файла: {e}")
        raise TelegramError(f"Ошибка скачивания файла: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при скачивании файла: {e}")
        raise TelegramError(f"Ошибка скачивания файла: {e}")


async def send_error_message(
    bot: Bot,
    chat_id: int,
    error_text: str = "Произошла ошибка. Попробуйте позже.",
    reply_to_message_id: Optional[int] = None
) -> Message:
    """
    Отправить сообщение об ошибке.
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        error_text: Текст ошибки
        reply_to_message_id: ID сообщения для ответа
        
    Returns:
        Message: Отправленное сообщение
    """
    try:
        return await send_text_message(
            bot=bot,
            chat_id=chat_id,
            text=f"{error_text}",
            reply_to_message_id=reply_to_message_id
        )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение об ошибке: {e}")
        # Возвращаем None, так как это критическая ошибка
        return None
