"""Yandex LLM service using Foundation Models API."""

import httpx
import time
from typing import Optional
from app.settings import settings
from app.observability.metrics import metrics_collector
from app.observability.logging import llm_logger
from app.cache.lru_cache import response_cache


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
    start_time = time.time()
    
    # Check cache first
    cached_response = response_cache.get_llm_response(
        system_prompt, user_message, 
        temperature=temperature, max_tokens=max_tokens
    )
    if cached_response is not None:
        llm_logger.info("LLM cache hit", extra_fields={
            "cache_hit": True,
            "response_length": len(cached_response)
        })
        return cached_response
    
    llm_logger.info("LLM cache miss, making API request", extra_fields={
        "cache_hit": False,
        "user_message_length": len(user_message)
    })
    
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
            result = data["result"]["alternatives"][0]["message"]["text"].strip()
            
            # Cache the response
            response_cache.set_llm_response(
                system_prompt, user_message, result,
                temperature=temperature, max_tokens=max_tokens
            )
            
            # Record metrics
            duration = time.time() - start_time
            metrics_collector.record_llm_request("success", settings.yandex_llm_model, duration)
            
            llm_logger.info("LLM request successful", extra_fields={
                "duration_seconds": duration,
                "response_length": len(result)
            })
            
            return result

    except httpx.HTTPError as e:
        duration = time.time() - start_time
        metrics_collector.record_llm_request("error", settings.yandex_llm_model, duration)
        llm_logger.error(f"LLM HTTP error: {e}", extra_fields={"duration_seconds": duration})
        raise YandexLLMError(f"Yandex LLM API error: {e}")
    except (KeyError, IndexError) as e:
        duration = time.time() - start_time
        metrics_collector.record_llm_request("error", settings.yandex_llm_model, duration)
        llm_logger.error(f"LLM response format error: {e}", extra_fields={"duration_seconds": duration})
        raise YandexLLMError(f"Unexpected response format: {e}")
    except Exception as e:
        duration = time.time() - start_time
        metrics_collector.record_llm_request("error", settings.yandex_llm_model, duration)
        llm_logger.error(f"LLM unexpected error: {e}", extra_fields={"duration_seconds": duration})
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