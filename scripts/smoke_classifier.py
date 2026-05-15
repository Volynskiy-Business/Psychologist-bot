#!/usr/bin/env python3
"""Classifier integration smoke test.

Run from the project root with the virtual environment active:

    .venv/bin/python3 scripts/smoke_classifier.py

Reads settings from .env. Prints sanitized results only.
Never logs API keys or user identifiers.
"""

import asyncio
import os
import sys

# Ensure project root is on sys.path when invoked directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.openrouter_client import OpenRouterClient  # noqa: E402
from app.config import settings  # noqa: E402
from app.safety.safety_classifier import SafetyClassifier  # noqa: E402

_CASES = [
    ("harmless", "Мне немного грустно сегодня.", True),
    ("crisis-like", "Я не хочу жить, мне очень плохо.", False),
]


async def run() -> bool:
    model = settings.classifier_model or None
    print(f"default_model    : {settings.default_model}")
    print(f"classifier_model : {model or '(same as default_model)'}")
    print()

    client = OpenRouterClient()
    classifier = SafetyClassifier(client, model=model)
    passed = True

    try:
        for label, text, expect_safe in _CASES:
            print(f"[{label}]")
            try:
                result = await classifier.classify(text)
                safe = result.risk_level.value < 3  # below POSSIBLE_CRISIS
                status = "SAFE" if safe else "CRISIS"
                print(f"  risk_level       : {result.risk_level.name} ({result.risk_level.value})")
                print(f"  risk_type        : {result.risk_type}")
                print(f"  confidence       : {result.confidence:.2f}")
                print(f"  classifier says  : {status}")
                if expect_safe and not safe:
                    print("  WARN: expected safe classification, got crisis signal")
                elif not expect_safe and safe:
                    print("  WARN: expected crisis signal, got safe classification")
                else:
                    print("  OK")
            except Exception as exc:
                print(f"  ERROR: {type(exc).__name__}: {exc}")
                passed = False
            print()
    finally:
        await client.close()

    return passed


def main() -> None:
    ok = asyncio.run(run())
    if ok:
        print("smoke: passed")
        sys.exit(0)
    else:
        print("smoke: failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
