"""Tests for OpenRouter client — retry behaviour and healthcheck."""

from unittest.mock import AsyncMock

import httpx
import pytest

from app.ai.openrouter_client import OpenRouterClient


def _make_http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(str(status_code), request=request, response=response)


@pytest.mark.asyncio
async def test_healthcheck() -> None:
    client = OpenRouterClient()
    result = await client.healthcheck()
    assert isinstance(result, bool)
    await client.close()


@pytest.mark.asyncio
async def test_http_429_not_retried() -> None:
    """R-1: HTTP 429 must raise immediately without retry (call_count == 1)."""
    client = OpenRouterClient()
    post_mock = AsyncMock(side_effect=_make_http_status_error(429))
    client.client.post = post_mock

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.chat_completion(messages=[{"role": "user", "content": "test"}])

    assert exc_info.value.response.status_code == 429
    assert post_mock.call_count == 1

    await client.close()
