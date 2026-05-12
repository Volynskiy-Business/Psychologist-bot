#!/usr/bin/env bash
set -euo pipefail

export BOT_TOKEN="${BOT_TOKEN:-dummy-test-bot-token}"
export OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-dummy-test-openrouter-key}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./test.db}"
export OPENROUTER_MODEL="${OPENROUTER_MODEL:-deepseek/deepseek-chat}"
export APP_ENV="${APP_ENV:-test}"
export LOG_LEVEL="${LOG_LEVEL:-debug}"

pytest -q
