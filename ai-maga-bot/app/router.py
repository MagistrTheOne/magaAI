"""Telegram bot router with aiogram v3 handlers."""

import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.settings import settings
from app.services.mode import mode_manager, determine_response_mode, get_mode_description
from app.services.yandex_llm import complete_text
from app.services.yandex_tts import synthesize_speech
from app.services.yandex_stt import recognize_speech
from app.services.tg_utils import send_text_message, send_voice_message, download_voice_file, send_error_message
from app.schemas import UserMode
from app.commands.ux_commands import (
    handle_summary_command, handle_translate_command, handle_help_command,
    handle_help_callback, handle_help_back_callback
)
from app.observability.logging import app_logger

# Setup logging
logger = logging.getLogger(__name__)

# Create bot and dispatcher
bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()
router = Router()

# Register router
dp.include_router(router)


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    """Handle /start command."""
    user_id = message.from_user.id
    current_mode = mode_manager.get_user_mode(user_id)

    welcome_text = (
        "🤖 Привет! Я AI-Мага - ваш умный помощник.\n\n"
        f"Текущий режим: {get_mode_description(current_mode)}\n\n"
        "Команды:\n"
        "/mode auto|text|voice - переключить режим ответа\n"
        "/help - справка\n\n"
        "Просто напишите сообщение или отправьте голосовое!"
    )

    try:
        await send_text_message(bot, message.chat.id, welcome_text)
    except Exception as e:
        logger.error(f"Failed to send start message: {e}")


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    """Handle /help command."""
    await handle_help_command(message, bot, None)


@router.message(Command("summary"))
async def summary_handler(message: Message) -> None:
    """Handle /summary command."""
    await handle_summary_command(message, bot, None)


@router.message(Command("translate"))
async def translate_handler(message: Message) -> None:
    """Handle /translate command."""
    await handle_translate_command(message, bot, None)


@router.message(Command("mode"))
async def mode_handler(message: Message) -> None:
    """Handle /mode command."""
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 2:
        current_mode = mode_manager.get_user_mode(user_id)
        status_text = (
            f"Текущий режим: {current_mode.value}\n"
            f"{get_mode_description(current_mode)}\n\n"
            "Используйте: /mode auto|text|voice"
        )
        await send_text_message(bot, message.chat.id, status_text)
        return

    mode_arg = args[1].lower()

    try:
        if mode_arg == "auto":
            new_mode = UserMode.AUTO
        elif mode_arg == "text":
            new_mode = UserMode.TEXT
        elif mode_arg == "voice":
            new_mode = UserMode.VOICE
        else:
            await send_text_message(
                bot, message.chat.id,
                "❌ Неверный режим. Используйте: auto, text, voice"
            )
            return

        mode_manager.set_user_mode(user_id, new_mode)

        await send_text_message(
            bot, message.chat.id,
            f"✅ Режим изменён на: {new_mode.value}\n"
            f"{get_mode_description(new_mode)}"
        )

    except Exception as e:
        logger.error(f"Failed to handle mode command: {e}")
        await send_error_message(bot, message.chat.id, "Не удалось изменить режим")


@router.message(lambda message: message.voice is not None)
async def voice_handler(message: Message) -> None:
    """Handle voice messages."""
    user_id = message.from_user.id

    try:
        # Download voice file
        voice_data = await download_voice_file(bot, message.voice.file_id)

        # Check if STT is enabled
        if not settings.yandex_stt_enable:
            await send_text_message(
                bot, message.chat.id,
                "🎤 Голосовое сообщение получено, но STT отключён.\n"
                "Отправьте текст или включите STT в настройках.",
                reply_to_message_id=message.message_id
            )
            return

        # Recognize speech
        recognized_text = await recognize_speech(
            audio_data=voice_data,
            format="oggopus",
            language="ru-RU"
        )

        if not recognized_text:
            await send_text_message(
                bot, message.chat.id,
                "🎤 Не удалось распознать речь. Попробуйте ещё раз.",
                reply_to_message_id=message.message_id
            )
            return

        # Process with LLM
        ai_response = await complete_text(
            system_prompt="Ты полезный AI-ассистент. Отвечай кратко и по делу.",
            user_message=recognized_text
        )

        # Always respond with voice to voice messages
        audio_data = await synthesize_speech(ai_response)

        await send_voice_message(
            bot, message.chat.id,
            audio_data,
            reply_to_message_id=message.message_id
        )

    except Exception as e:
        logger.error(f"Failed to handle voice message: {e}")
        await send_error_message(
            bot, message.chat.id,
            "Не удалось обработать голосовое сообщение"
        )


@router.message()
async def message_handler(message: Message, state: FSMContext) -> None:
    """Handle text messages."""
    user_id = message.from_user.id
    text = message.text

    try:
        # Determine response mode
        response_mode = determine_response_mode(
            user_id=user_id,
            input_type="text",
            text_content=text
        )

        # Get AI response
        ai_response = await complete_text(
            system_prompt="Ты полезный AI-ассистент. Отвечай кратко и по делу.",
            user_message=text
        )

        if response_mode == "voice":
            # Generate and send voice response
            audio_data = await synthesize_speech(ai_response)
            await send_voice_message(
                bot, message.chat.id,
                audio_data,
                reply_to_message_id=message.message_id
            )
        else:
            # Send text response
            await send_text_message(
                bot, message.chat.id,
                ai_response,
                reply_to_message_id=message.message_id
            )

    except Exception as e:
        logger.error(f"Failed to handle text message: {e}")
        await send_error_message(
            bot, message.chat.id,
            "Не удалось обработать сообщение"
        )


async def set_webhook() -> None:
    """Set Telegram webhook on startup."""
    try:
        webhook_url = settings.webhook_url
        logger.info(f"Setting webhook to: {webhook_url}")

        # Set webhook
        result = await bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True
        )

        if result:
            logger.info("Webhook set successfully")
        else:
            logger.error("Failed to set webhook")

    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        raise


async def close_bot() -> None:
    """Close bot connection."""
    try:
        await bot.session.close()
        logger.info("Bot closed successfully")
    except Exception as e:
        logger.error(f"Failed to close bot: {e}")