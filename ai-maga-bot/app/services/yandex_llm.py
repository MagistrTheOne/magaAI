"""Yandex LLM service using Foundation Models API."""

import httpx
from typing import Optional
from app.settings import settings


class YandexLLMError(Exception):
    """Exception for Yandex LLM errors."""
    pass


async def complete_text(
    system_prompt: str = "You are a helpful AI assistant. Answer briefly and to the point.",
    user_message: str = "",
    temperature: float = 0.3,
    max_tokens: int = 1200
) -> str:
    """
    Complete text using Yandex Foundation Models.

    Args:
        system_prompt: System message for the LLM
        user_message: User message to complete
        temperature: Temperature for generation (0.0-1.0)
        max_tokens: Maximum tokens to generate

    Returns:
        Generated text response

    Raises:
        YandexLLMError: If the API call fails
    """
    payload = {
        "modelUri": settings.yandex_llm_model,
        "completionOptions": {
            "temperature": temperature,
            "maxTokens": max_tokens,
        },
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": user_message},
        ],
    }

    headers = {
        "Authorization": f"Api-Key {settings.yandex_api_key}",
        "x-folder-id": settings.yandex_folder_id,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            return data["result"]["alternatives"][0]["message"]["text"].strip()

    except httpx.HTTPError as e:
        raise YandexLLMError(f"Yandex LLM API error: {e}")
    except (KeyError, IndexError) as e:
        raise YandexLLMError(f"Unexpected response format: {e}")
    except Exception as e:
        raise YandexLLMError(f"Unexpected error: {e}")


async def complete_with_request(request: "LLMRequest") -> str:
    """
    Complete text using LLMRequest model.

    Args:
        request: LLMRequest instance

    Returns:
        Generated text response
    """
    return await complete_text(
        system_prompt=request.system_prompt,
        user_message=request.user_message,
        temperature=request.temperature,
        max_tokens=request.max_tokens
    )