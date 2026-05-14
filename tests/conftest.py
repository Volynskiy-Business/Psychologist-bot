"""Shared pytest configuration.

Sets minimal env vars so ``app.config.Settings`` can instantiate during test
collection without requiring a real ``.env`` file or live secrets.
"""

import os

os.environ.setdefault("BOT_TOKEN", "test-bot-token")
os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
