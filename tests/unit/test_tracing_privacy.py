"""Privacy tests for Langfuse tracing anonymisation — TP-1 through TP-5."""


def test_anon_id_does_not_contain_raw_user_id() -> None:
    """TP-1: Anonymised user ID must not contain the raw Telegram user ID."""
    from app.bot.handlers.chat import _anon_stable_id

    telegram_user_id = 987654321
    result = _anon_stable_id(telegram_user_id, "tg_user")
    assert str(telegram_user_id) not in result


def test_anon_id_does_not_contain_raw_chat_id() -> None:
    """TP-2: Anonymised session ID must not contain the raw Telegram chat ID."""
    from app.bot.handlers.chat import _anon_stable_id

    telegram_chat_id = 123456789
    result = _anon_stable_id(telegram_chat_id, "tg_chat")
    assert str(telegram_chat_id) not in result


def test_anon_id_is_deterministic() -> None:
    """TP-3: Same input and namespace must always produce the same anonymised ID."""
    from app.bot.handlers.chat import _anon_stable_id

    telegram_id = 111222333
    assert _anon_stable_id(telegram_id, "tg_user") == _anon_stable_id(telegram_id, "tg_user")


def test_anon_id_differs_across_namespaces() -> None:
    """TP-4: Same numeric value in different namespaces must yield different IDs."""
    from app.bot.handlers.chat import _anon_stable_id

    value = 555666777
    assert _anon_stable_id(value, "tg_user") != _anon_stable_id(value, "tg_chat")


def test_tracing_context_no_ops_without_langfuse() -> None:
    """TP-5: tracing_context must be safely enterable when Langfuse is not configured."""
    from app.ai import tracing

    saved_initialized, saved_client = tracing._initialized, tracing._client
    tracing._initialized = True  # pretend already attempted, returned no client
    tracing._client = None
    try:
        ctx = tracing.tracing_context(session_id="s1", user_id="u1")
        with ctx:
            pass  # must not raise
    finally:
        tracing._initialized = saved_initialized
        tracing._client = saved_client
