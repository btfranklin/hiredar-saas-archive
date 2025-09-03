"""
OpenAI client wrapper using the Responses API with centralised timeout, retry,
and logging.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any, Sequence

import requests
from django.conf import settings  # type: ignore
from openai import APIError, OpenAI, RateLimitError, Timeout  # type: ignore
from promptdown.types import ResponsesMessage  # type: ignore
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
    retry=retry_if_exception_type(_RETRY_EXCEPTIONS),  # type: ignore[arg-type]
    reraise=True,
)


@_retry
def get_llm_response(
    response_input: Sequence[ResponsesMessage],
    model: str,
    timeout: int = 60,
    reasoning_effort: str | None = None,
    **kwargs: Any,
) -> str:
    """High-level convenience wrapper for Responses API text generation.

    Returns the primary output text.
    """

    client = get_client()
    logger.debug(
        "Calling OpenAI Responses | model=%s, items=%d", model, len(response_input)
    )

    # Translate legacy max_tokens to Responses API parameter name.
    if "max_tokens" in kwargs and "max_output_tokens" not in kwargs:
        kwargs["max_output_tokens"] = kwargs.pop("max_tokens")

    client_with_timeout = client.with_options(timeout=timeout)

    request_kwargs: dict[str, Any] = {
        "model": model,
        "input": list(response_input),
    }

    if reasoning_effort:
        request_kwargs["reasoning"] = {"effort": reasoning_effort}

    # Merge any additional caller-supplied kwargs (e.g., response_format)
    request_kwargs.update(kwargs)

    response = client_with_timeout.responses.create(**request_kwargs)

    # Prefer SDK convenience when available
    content: Any = getattr(response, "output_text", None)
    if content is None:
        try:
            # Fallback to manual extraction
            content = response.output[0].content[0].text  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            raise ValueError("Unable to extract text from OpenAI response") from exc

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

    client_with_timeout = client.with_options(timeout=timeout)

    response = client_with_timeout.embeddings.create(
        model=embed_model,
        input=texts,  # type: ignore[arg-type]
        **kwargs,
    )

    return [record.embedding for record in response.data]
