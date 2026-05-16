"""Optional Langfuse tracing for LLM calls (compatible with langfuse>=3.0).

Activated only when LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY are set.
By default, message content is NOT sent to Langfuse (LANGFUSE_LOG_CONTENT=false).
Only performance metrics (model, tokens, latency) are recorded.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_client: Any = None
_initialized: bool = False


def _get_client() -> Any:
    global _client, _initialized
    if _initialized:
        return _client
    _initialized = True
    try:
        from app.config import settings  # late import avoids circular at module load

        if not (settings.langfuse_public_key and settings.langfuse_secret_key):
            return None
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key.get_secret_value(),
            host=settings.langfuse_host,
        )
        logger.info("stage=langfuse status=initialized host=%s", settings.langfuse_host)
    except ImportError:
        logger.warning("stage=langfuse status=package_missing; tracing disabled")
    except Exception:
        logger.exception("stage=langfuse status=init_failed; tracing disabled")
    return _client


def trace_generation(
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    name: str = "chat_completion",
    log_content: bool = False,
    input_messages: Optional[list] = None,
    output: Optional[str] = None,
    level: str = "DEFAULT",
) -> None:
    """Record one LLM generation. Silently no-ops if Langfuse is not configured."""
    client = _get_client()
    if client is None:
        return
    try:
        with client.start_as_current_observation(
            name=name,
            as_type="generation",
            model=model,
            input=input_messages if log_content else None,
            output=output if log_content else None,
            usage_details={
                "input": prompt_tokens,
                "output": completion_tokens,
            },
            metadata={"latency_ms": latency_ms},
            level=level,
            end_on_exit=True,
        ):
            pass
    except Exception:
        logger.exception("stage=langfuse status=trace_failed")
