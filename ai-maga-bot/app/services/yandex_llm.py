"""
Сервис для работы с Yandex Foundation Models (LLM).
"""
import logging
from typing import Optional
import httpx
from httpx import HTTPStatusError, TimeoutException

from app.settings import settings
from app.schemas import LLMRequest

logger = logging.getLogger(__name__)


class YandexLLMError(Exception):
    """Ошибка при работе с Yandex LLM."""
    pass


async def complete_text(
    system_prompt: str = "Ты полезный AI-ассистент. Отвечай кратко и по делу.",
    user_message: str = "",
    temperature: float = 0.3,
    max_tokens: int = 1200
) -> str:
    """
    Получить текстовый ответ от Yandex LLM.
    
    Args:
        system_prompt: Системный промпт
        user_message: Сообщение пользователя
        temperature: Температура генерации (0.0-1.0)
        max_tokens: Максимальное количество токенов
        
    Returns:
        str: Сгенерированный текст
        
    Raises:
        YandexLLMError: При ошибке API или сети
    """
    if not user_message.strip():
        raise YandexLLMError("Пустое сообщение пользователя")
    
    payload = {
        "modelUri": settings.yandex_llm_model,
        "completionOptions": {
            "temperature": temperature,
            "maxTokens": max_tokens
        },
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": user_message}
        ]
    }
    
    headers = {
        "Authorization": f"Api-Key {settings.yandex_api_key}",
        "x-folder-id": settings.yandex_folder_id,
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.debug(f"Отправляем запрос к Yandex LLM: {user_message[:100]}...")
            
            response = await client.post(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Извлекаем текст из первого альтернативного ответа
            if "result" in data and "alternatives" in data["result"]:
                alternatives = data["result"]["alternatives"]
                if alternatives and len(alternatives) > 0:
                    text = alternatives[0].get("message", {}).get("text", "").strip()
                    if text:
                        logger.debug(f"Получен ответ от LLM: {text[:100]}...")
                        return text
                    else:
                        raise YandexLLMError("Пустой ответ от LLM")
                else:
                    raise YandexLLMError("Нет альтернативных ответов от LLM")
            else:
                raise YandexLLMError(f"Неожиданная структура ответа: {data}")
                
    except HTTPStatusError as e:
        logger.error(f"HTTP ошибка при запросе к Yandex LLM: {e.response.status_code} - {e.response.text}")
        raise YandexLLMError(f"Ошибка API Yandex: {e.response.status_code}")
    except TimeoutException:
        logger.error("Таймаут при запросе к Yandex LLM")
        raise YandexLLMError("Таймаут при запросе к Yandex LLM")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при запросе к Yandex LLM: {e}")
        raise YandexLLMError(f"Ошибка при запросе к Yandex LLM: {e}")


async def complete_with_request(request: LLMRequest) -> str:
    """
    Получить текстовый ответ с использованием Pydantic модели.
    
    Args:
        request: Модель запроса к LLM
        
    Returns:
        str: Сгенерированный текст
    """
    return await complete_text(
        system_prompt=request.system_prompt,
        user_message=request.user_message,
        temperature=request.temperature,
        max_tokens=request.max_tokens
    )
