"""UX commands for AI-Maga."""

import asyncio
from typing import Optional
from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.services.yandex_llm import complete_text
from app.observability.logging import app_logger


async def handle_summary_command(message: Message, bot: Bot, state: FSMContext):
    """Handle /summary command - generate brief summary."""
    try:
        # Get user message
        user_text = message.text.replace("/summary", "").strip()
        if not user_text:
            await message.answer(
                "📝 <b>Краткое изложение</b>\n\n"
                "Отправьте текст для краткого изложения.\n"
                "Пример: /summary Длинный текст для сжатия...",
                parse_mode="HTML"
            )
            return
        
        # Show typing indicator
        await bot.send_chat_action(message.chat.id, "typing")
        
        # Generate summary
        system_prompt = (
            "Ты эксперт по созданию кратких изложений. "
            "Создай краткое изложение текста, сохраняя ключевые моменты. "
            "Ответ должен быть в 2-3 предложениях."
        )
        
        summary = await complete_text(
            system_prompt=system_prompt,
            user_message=user_text,
            temperature=0.3,
            max_tokens=200
        )
        
        await message.answer(
            f"📝 <b>Краткое изложение:</b>\n\n{summary}",
            parse_mode="HTML"
        )
        
        app_logger.info("Summary command executed", extra_fields={
            "user_id": message.from_user.id,
            "text_length": len(user_text),
            "summary_length": len(summary)
        })
        
    except Exception as e:
        app_logger.error(f"Summary command error: {e}", extra_fields={
            "user_id": message.from_user.id
        })
        await message.answer("❌ Ошибка при создании изложения. Попробуйте позже.")


async def handle_translate_command(message: Message, bot: Bot, state: FSMContext):
    """Handle /translate command - translate text."""
    try:
        # Get user message
        user_text = message.text.replace("/translate", "").strip()
        if not user_text:
            await message.answer(
                "🌐 <b>Переводчик</b>\n\n"
                "Отправьте текст для перевода.\n"
                "Пример: /translate Hello world",
                parse_mode="HTML"
            )
            return
        
        # Show typing indicator
        await bot.send_chat_action(message.chat.id, "typing")
        
        # Detect language and translate
        system_prompt = (
            "Ты профессиональный переводчик. "
            "Определи язык текста и переведи его на русский, если он не на русском, "
            "или на английский, если он на русском. "
            "Ответь только переводом без дополнительных комментариев."
        )
        
        translation = await complete_text(
            system_prompt=system_prompt,
            user_message=user_text,
            temperature=0.1,
            max_tokens=300
        )
        
        await message.answer(
            f"🌐 <b>Перевод:</b>\n\n{translation}",
            parse_mode="HTML"
        )
        
        app_logger.info("Translate command executed", extra_fields={
            "user_id": message.from_user.id,
            "text_length": len(user_text),
            "translation_length": len(translation)
        })
        
    except Exception as e:
        app_logger.error(f"Translate command error: {e}", extra_fields={
            "user_id": message.from_user.id
        })
        await message.answer("❌ Ошибка при переводе. Попробуйте позже.")


async def handle_help_command(message: Message, bot: Bot, state: FSMContext):
    """Handle /help command with inline buttons."""
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Краткое изложение", callback_data="help_summary"),
                InlineKeyboardButton(text="🌐 Перевод", callback_data="help_translate")
            ],
            [
                InlineKeyboardButton(text="🎤 Голосовые команды", callback_data="help_voice"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="help_settings")
            ],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="help_stats"),
                InlineKeyboardButton(text="❓ Поддержка", callback_data="help_support")
            ]
        ])
        
        help_text = (
            "🤖 <b>AI-Магистр - Помощник</b>\n\n"
            "Доступные команды:\n"
            "• <code>/summary</code> - Краткое изложение текста\n"
            "• <code>/translate</code> - Перевод текста\n"
            "• <code>/mode auto|text|voice</code> - Режим ответов\n"
            "• <code>/start</code> - Начать работу\n\n"
            "Выберите категорию для подробной информации:"
        )
        
        await message.answer(help_text, parse_mode="HTML", reply_markup=keyboard)
        
        app_logger.info("Help command executed", extra_fields={
            "user_id": message.from_user.id
        })
        
    except Exception as e:
        app_logger.error(f"Help command error: {e}", extra_fields={
            "user_id": message.from_user.id
        })
        await message.answer("❌ Ошибка при показе справки.")


async def handle_help_callback(callback_query, bot: Bot):
    """Handle help callback queries."""
    try:
        data = callback_query.data
        user_id = callback_query.from_user.id
        
        if data == "help_summary":
            text = (
                "📝 <b>Краткое изложение</b>\n\n"
                "Создает краткое изложение длинного текста.\n\n"
                "<b>Использование:</b>\n"
                "<code>/summary Ваш длинный текст здесь...</code>\n\n"
                "<b>Пример:</b>\n"
                "<code>/summary Искусственный интеллект — это технология...</code>"
            )
        elif data == "help_translate":
            text = (
                "🌐 <b>Переводчик</b>\n\n"
                "Переводит текст между русским и английским языками.\n\n"
                "<b>Использование:</b>\n"
                "<code>/translate Текст для перевода</code>\n\n"
                "<b>Пример:</b>\n"
                "<code>/translate Hello world</code>\n"
                "<code>/translate Привет мир</code>"
            )
        elif data == "help_voice":
            text = (
                "🎤 <b>Голосовые команды</b>\n\n"
                "Отправьте голосовое сообщение для получения ответа голосом.\n"
                "Или добавьте 🔊 в текстовое сообщение для голосового ответа.\n\n"
                "<b>Режимы:</b>\n"
                "• <code>auto</code> - Автоматический выбор\n"
                "• <code>voice</code> - Всегда голос\n"
                "• <code>text</code> - Всегда текст"
            )
        elif data == "help_settings":
            text = (
                "⚙️ <b>Настройки</b>\n\n"
                "Управление режимами работы бота.\n\n"
                "<b>Команды:</b>\n"
                "• <code>/mode auto</code> - Автоматический режим\n"
                "• <code>/mode voice</code> - Голосовой режим\n"
                "• <code>/mode text</code> - Текстовый режим"
            )
        elif data == "help_stats":
            text = (
                "📊 <b>Статистика</b>\n\n"
                "Информация о работе бота и метриках.\n\n"
                "Используйте команду <code>/metrics</code> для просмотра статистики."
            )
        elif data == "help_support":
            text = (
                "❓ <b>Поддержка</b>\n\n"
                "Если у вас возникли проблемы:\n"
                "• Проверьте правильность команд\n"
                "• Убедитесь, что бот имеет доступ к сообщениям\n"
                "• Попробуйте перезапустить бота командой <code>/start</code>"
            )
        else:
            text = "❓ Неизвестная команда справки."
        
        await callback_query.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="help_back")]
            ])
        )
        
        await callback_query.answer()
        
        app_logger.info("Help callback executed", extra_fields={
            "user_id": user_id,
            "callback_data": data
        })
        
    except Exception as e:
        app_logger.error(f"Help callback error: {e}", extra_fields={
            "user_id": callback_query.from_user.id,
            "callback_data": callback_query.data
        })
        await callback_query.answer("❌ Ошибка при обработке запроса.")


async def handle_help_back_callback(callback_query, bot: Bot):
    """Handle help back callback."""
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Краткое изложение", callback_data="help_summary"),
                InlineKeyboardButton(text="🌐 Перевод", callback_data="help_translate")
            ],
            [
                InlineKeyboardButton(text="🎤 Голосовые команды", callback_data="help_voice"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="help_settings")
            ],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="help_stats"),
                InlineKeyboardButton(text="❓ Поддержка", callback_data="help_support")
            ]
        ])
        
        help_text = (
            "🤖 <b>AI-Магистр - Помощник</b>\n\n"
            "Доступные команды:\n"
            "• <code>/summary</code> - Краткое изложение текста\n"
            "• <code>/translate</code> - Перевод текста\n"
            "• <code>/mode auto|text|voice</code> - Режим ответов\n"
            "• <code>/start</code> - Начать работу\n\n"
            "Выберите категорию для подробной информации:"
        )
        
        await callback_query.message.edit_text(
            help_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        await callback_query.answer()
        
    except Exception as e:
        app_logger.error(f"Help back callback error: {e}", extra_fields={
            "user_id": callback_query.from_user.id
        })
        await callback_query.answer("❌ Ошибка при возврате к справке.")
