"""Telegram utility functions for sending messages and voice."""

from typing import Optional
from aiogram import Bot
from aiogram.types import Message
from app.schemas import TTSRequest


class TelegramError(Exception):
    """Exception for Telegram API errors."""
    pass


async def send_text_message(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_to_message_id: Optional[int] = None
) -> Message:
    """
    Send text message to Telegram chat.

    Args:
        bot: Telegram bot instance
        chat_id: Chat ID to send to
        text: Text to send
        reply_to_message_id: Message ID to reply to

    Returns:
        Sent message

    Raises:
        TelegramError: If sending fails
    """
    try:
        return await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_to_message_id=reply_to_message_id
        )
    except Exception as e:
        raise TelegramError(f"Failed to send text message: {e}")


async def send_voice_message(
    bot: Bot,
    chat_id: int,
    audio_data: bytes,
    reply_to_message_id: Optional[int] = None,
    duration: Optional[int] = None
) -> Message:
    """
    Send voice message to Telegram chat.

    Args:
        bot: Telegram bot instance
        chat_id: Chat ID to send to
        audio_data: Audio data as bytes
        reply_to_message_id: Message ID to reply to
        duration: Voice duration in seconds

    Returns:
        Sent message

    Raises:
        TelegramError: If sending fails
    """
    try:
        # Create input file from bytes
        from aiogram.types import BufferedInputFile

        voice_file = BufferedInputFile(
            file=audio_data,
            filename="voice.ogg"
        )

        return await bot.send_voice(
            chat_id=chat_id,
            voice=voice_file,
            duration=duration,
            reply_to_message_id=reply_to_message_id
        )
    except Exception as e:
        raise TelegramError(f"Failed to send voice message: {e}")


async def download_voice_file(bot: Bot, voice_file_id: str) -> bytes:
    """
    Download voice file from Telegram.

    Args:
        bot: Telegram bot instance
        voice_file_id: File ID of the voice message

    Returns:
        Voice file content as bytes

    Raises:
        TelegramError: If download fails
    """
    try:
        file = await bot.get_file(voice_file_id)
        file_path = file.file_path

        # Download file content
        file_content = await bot.download_file(file_path)
        return file_content.read()

    except Exception as e:
        raise TelegramError(f"Failed to download voice file: {e}")


async def send_error_message(
    bot: Bot,
    chat_id: int,
    error_text: str = "Произошла ошибка. Попробуйте позже.",
    reply_to_message_id: Optional[int] = None
) -> Message:
    """
    Send error message to Telegram chat.

    Args:
        bot: Telegram bot instance
        chat_id: Chat ID to send to
        error_text: Error text to send
        reply_to_message_id: Message ID to reply to

    Returns:
        Sent message
    """
    try:
        return await send_text_message(
            bot=bot,
            chat_id=chat_id,
            text=f"❌ {error_text}",
            reply_to_message_id=reply_to_message_id
        )
    except Exception:
        # Fallback if even error message fails
        return None