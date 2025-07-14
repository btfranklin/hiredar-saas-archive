"""
OpenAI client wrapper with centralised timeout, retry, and logging.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

import requests
from django.conf import settings  # type: ignore
from openai import APIError, OpenAI, RateLimitError, Timeout  # type: ignore
from tenacity import (  # type: ignore
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Exceptions that should trigger a retry
_RETRY_EXCEPTIONS = (
    APIError,
    RateLimitError,
    Timeout,
    requests.exceptions.RequestException,
)


@lru_cache(maxsize=1)
def _create_client() -> OpenAI:
    """Create (and cache) an OpenAI client instance."""
    api_key: str | None = getattr(settings, "OPENAI_API_KEY", None) or os.getenv(
        "OPENAI_API_KEY"
    )
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured in Django settings or environment"
        )
    logger.debug("Initialising OpenAI client")
    return OpenAI(api_key=api_key)


def get_client() -> OpenAI:
    """Return a singleton OpenAI client."""

    return _create_client()


# Shared retry decorator – exponential backoff up to 5 attempts (~15-second total)
_retry = retry(
    wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(_RETRY_EXCEPTIONS),
    reraise=True,
)


@_retry
def chat_complete(
    messages: list[dict[str, Any]],
    model: str,
    temperature: float = 0.7,
    timeout: int = 60,
    **kwargs: Any,
) -> str:
    """High-level convenience wrapper for Chat Completions.

    Returns the *content* field of the first choice.
    """

    client = get_client()
    logger.debug(
        "Calling OpenAI ChatCompletion | model=%s, messages=%d", model, len(messages)
    )

    completion = client.chat.completions.create(
        model=model,
        messages=messages,  # type: ignore[arg-type]
        temperature=temperature,
        timeout=timeout,
        **kwargs,
    )

    content = completion.choices[0].message.content
    if not isinstance(content, str):
        raise ValueError("Received non-string content from OpenAI response")

    return content


@_retry
def embed(
    texts: list[str],
    model: str | None = None,
    timeout: int = 60,
    **kwargs: Any,
) -> list[list[float]]:
    """Generate embeddings for a list of texts."""

    client = get_client()
    embed_model = model or getattr(
        settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
    )
    logger.debug(
        "Calling OpenAI Embeddings | model=%s, items=%d", embed_model, len(texts)
    )

    response = client.embeddings.create(
        model=embed_model,
        input=texts,  # type: ignore[arg-type]
        timeout=timeout,
        **kwargs,
    )

    return [record.embedding for record in response.data]
