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
from app.orchestrator import get_orchestrator
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
        f"Привет! Я AI-Мага - ваш персональный ассистент.\n\n"
        f"Текущий режим: {current_mode}\n"
        f"{mode_description}\n\n"
        f"Команды:\n"
        f"• /mode auto|text|voice - изменить режим ответа\n"
        f"• /start - показать это сообщение\n\n"
        f"Просто напишите мне или отправьте голосовое сообщение!"
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
            f"Текущий режим: {current_mode}\n"
            f"{mode_description}\n\n"
            f"Доступные режимы:\n"
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
        error_text = "Неверный режим. Используйте: auto, text или voice"
        try:
            await send_text_message(bot, user_id, error_text)
        except TelegramError as e:
            logger.error(f"Ошибка отправки сообщения об ошибке режима: {e}")
        return
    
    # Устанавливаем новый режим
    set_user_mode(user_id, new_mode)
    mode_description = get_mode_description(new_mode)
    
    success_text = (
        f"Режим изменен на: {new_mode}\n"
        f"{mode_description}"
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
        # Получаем оркестратор
        orchestrator = await get_orchestrator()

        # Обрабатываем через оркестратор
        result = await orchestrator.process_message(user_id, text, "text")

        # Отправляем ответ в зависимости от типа
        if result.get("type") == "voice":
            await send_voice_message(bot, user_id, result["audio_data"], message.message_id)
            logger.info(f"Отправлен голосовой ответ пользователю {user_id}")
        elif result.get("type") == "audio":
            await send_audio_message(bot, user_id, result["audio_data"], message.message_id)
            logger.info(f"Отправлен аудио ответ пользователю {user_id}")
        else:
            await send_text_message(bot, user_id, result["text"], message.message_id)
            logger.info(f"Отправлен текстовый ответ пользователю {user_id}")

    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await send_error_message(bot, user_id, "Произошла ошибка", message.message_id)


@router.message(lambda message: message.photo is not None)
async def photo_handler(message: Message) -> None:
    """Обработчик фото сообщений."""
    user_id = message.from_user.id
    photo = message.photo[-1]  # Берем самое большое фото
    caption = message.caption

    logger.info(f"Получено фото от пользователя {user_id}")

    try:
        # Получаем оркестратор
        orchestrator = await get_orchestrator()

        # Скачиваем фото
        from app.services.tg_utils import download_voice_file
        # Используем тот же метод для скачивания файлов
        photo_data = await download_voice_file(bot, photo)

        # Сохраняем во временный файл
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_file.write(photo_data)
            temp_path = temp_file.name

        try:
            # Обрабатываем через оркестратор
            result = await orchestrator.process_image(user_id, temp_path, caption)

            # Отправляем ответ
            await send_text_message(bot, user_id, result["text"], message.message_id)

            logger.info(f"Фото обработано для пользователя {user_id}")

        finally:
            # Удаляем временный файл
            try:
                os.unlink(temp_path)
            except:
                pass

    except Exception as e:
        logger.error(f"Ошибка обработки фото: {e}")
        await send_error_message(bot, user_id, "Ошибка обработки фото", message.message_id)


@router.message(lambda message: message.document is not None)
async def document_handler(message: Message) -> None:
    """Обработчик документов (изображений)."""
    user_id = message.from_user.id
    document = message.document
    caption = message.caption

    # Проверяем, что это изображение
    if not document.mime_type or not document.mime_type.startswith('image/'):
        return  # Пропускаем не-изображения

    logger.info(f"Получен документ-изображение от пользователя {user_id}: {document.file_name}")

    try:
        # Получаем оркестратор
        orchestrator = await get_orchestrator()

        # Скачиваем документ
        from app.services.tg_utils import download_voice_file
        doc_data = await download_voice_file(bot, document)

        # Сохраняем во временный файл
        import tempfile
        import os
        ext = os.path.splitext(document.file_name or 'image.jpg')[1] or '.jpg'
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp_file:
            temp_file.write(doc_data)
            temp_path = temp_file.name

        try:
            # Обрабатываем через оркестратор
            result = await orchestrator.process_image(user_id, temp_path, caption)

            # Отправляем ответ
            await send_text_message(bot, user_id, result["text"], message.message_id)

            logger.info(f"Документ-изображение обработан для пользователя {user_id}")

        finally:
            # Удаляем временный файл
            try:
                os.unlink(temp_path)
            except:
                pass

    except Exception as e:
        logger.error(f"Ошибка обработки документа: {e}")
        await send_error_message(bot, user_id, "Ошибка обработки документа", message.message_id)


@router.message(lambda message: message.voice is not None)
async def voice_handler(message: Message) -> None:
    """Обработчик голосовых сообщений."""
    user_id = message.from_user.id
    voice = message.voice

    logger.info(f"Получено голосовое сообщение от {user_id}")

    try:
        # Получаем оркестратор
        orchestrator = await get_orchestrator()

        # Проверяем, включен ли STT
        if not settings.yandex_stt_enable:
            error_text = (
                "Голосовое сообщение получено, но STT отключен.\n"
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

        # Обрабатываем через оркестратор
        result = await orchestrator.process_message(user_id, recognized_text, "voice")

        # Отправляем ответ в зависимости от типа
        if result.get("type") == "voice":
            await send_voice_message(bot, user_id, result["audio_data"], message.message_id)
            logger.info(f"Отправлен голосовой ответ пользователю {user_id}")
        elif result.get("type") == "audio":
            await send_audio_message(bot, user_id, result["audio_data"], message.message_id)
            logger.info(f"Отправлен аудио ответ пользователю {user_id}")
        else:
            await send_text_message(bot, user_id, result["text"], message.message_id)
            logger.info(f"Отправлен текстовый ответ пользователю {user_id}")

    except Exception as e:
        logger.error(f"Ошибка при обработке голоса: {e}")
        await send_error_message(bot, user_id, "Ошибка обработки голоса", message.message_id)


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


# Zoom команды
@router.message(Command("zoom"))
async def zoom_handler(message: Message) -> None:
    """Обработчик команд Zoom."""
    user_id = message.from_user.id
    text = message.text or ""
    
    try:
        # Парсим команду
        parts = text.split()
        if len(parts) < 2:
            await send_text_message(bot, user_id,
                "Zoom команды:\n"
                "• /zoom join <meeting_id> [password] - присоединиться к встрече\n"
                "• /zoom create <topic> - создать встречу\n"
                "• /zoom mode <meeting_id> <silent|note_taker|cohost> - режим ИИ\n"
                "• /zoom mute <meeting_id> - заглушить ИИ\n"
                "• /zoom status [meeting_id] - статус встреч"
            )
            return
        
        command = parts[1].lower()
        orchestrator = await get_orchestrator()
        
        if command == "join":
            if len(parts) < 3:
                await send_text_message(bot, user_id, "Укажите ID встречи: /zoom join <meeting_id> [password]")
                return
            
            meeting_id = parts[2]
            password = parts[3] if len(parts) > 3 else None
            
            result = await orchestrator.zoom_join_meeting(user_id, meeting_id, password)
            
            if result["status"] == "success":
                join_url = result["data"]["join_url"]
                await send_text_message(bot, user_id, 
                    f"🔗 Ссылка для присоединения:\n{join_url}\n\n"
                    f"ID встречи: {meeting_id}\n"
                    f"Пароль: {result['data']['password'] or 'Не требуется'}"
                )
            else:
                await send_text_message(bot, user_id, f"Ошибка: {result['message']}")
        
        elif command == "create":
            if len(parts) < 3:
                await send_text_message(bot, user_id, "Укажите тему встречи: /zoom create <topic>")
                return
            
            topic = " ".join(parts[2:])
            result = await orchestrator.zoom_create_meeting(user_id, topic)
            
            if result["status"] == "success":
                meeting_data = result["data"]
                await send_text_message(bot, user_id,
                    f"Встреча создана!\n\n"
                    f"Тема: {meeting_data['topic']}\n"
                    f"ID: {meeting_data['id']}\n"
                    f"Ссылка: {meeting_data['join_url']}\n"
                    f"Пароль: {meeting_data.get('password', 'Не требуется')}"
                )
            else:
                await send_text_message(bot, user_id, f"Ошибка: {result['message']}")
        
        elif command == "mode":
            if len(parts) < 4:
                await send_text_message(bot, user_id,
                    "Укажите ID встречи и режим: /zoom mode <meeting_id> <silent|note_taker|cohost>")
                return
            
            meeting_id = parts[2]
            mode = parts[3]
            result = await orchestrator.zoom_set_meeting_mode(user_id, meeting_id, mode)
            
            if result["status"] == "success":
                await send_text_message(bot, user_id, f"Режим ИИ изменен на: {mode}")
            else:
                await send_text_message(bot, user_id, f"Ошибка: {result['message']}")
        
        elif command == "mute":
            if len(parts) < 3:
                await send_text_message(bot, user_id, "Укажите ID встречи: /zoom mute <meeting_id>")
                return
            
            meeting_id = parts[2]
            result = await orchestrator.zoom_mute_ai(user_id, meeting_id)
            
            if result["status"] == "success":
                await send_text_message(bot, user_id, "ИИ заглушен на встрече")
            else:
                await send_text_message(bot, user_id, f"Ошибка: {result['message']}")
        
        elif command == "status":
            meeting_id = parts[2] if len(parts) > 2 else None
            result = await orchestrator.zoom_get_status(user_id, meeting_id)
            
            if result["status"] == "success":
                if meeting_id:
                    # Статус конкретной встречи
                    status_data = result
                    await send_text_message(bot, user_id,
                        f"Статус встречи {meeting_id}:\n"
                        f"Профиль: {status_data['profile']}\n"
                        f"Заглушен: {'Да' if status_data['ai_muted'] else 'Нет'}\n"
                        f"Начало: {status_data.get('start_time', 'Неизвестно')}"
                    )
                else:
                    # Список активных встреч
                    meetings = result.get("active_meetings", [])
                    if meetings:
                        text = "Активные встречи:\n\n"
                        for meeting in meetings:
                            text += (
                                f"ID: {meeting['meeting_id']}\n"
                                f"Профиль: {meeting['profile']}\n"
                                f"Заглушен: {'Да' if meeting['ai_muted'] else 'Нет'}\n\n"
                            )
                        await send_text_message(bot, user_id, text)
                    else:
                        await send_text_message(bot, user_id, "Нет активных встреч")
            else:
                await send_text_message(bot, user_id, f"Ошибка: {result['message']}")
        
        else:
            await send_text_message(bot, user_id,
                "Неизвестная команда. Используйте /zoom для справки.")
    
    except Exception as e:
        logger.error(f"Ошибка обработки Zoom команды: {e}")
        await send_error_message(bot, user_id, "Произошла ошибка при обработке команды Zoom")
