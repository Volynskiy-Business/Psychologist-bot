# v2 backlog — known issues & follow-ups

Tracked here so future agents/contributors don’t re-discover them.
Move items into issues/PRs as they’re worked.

## Known bugs

- **`app/bot/handlers/chat.py:58` — system prompt / model content wiring.**
  A pre-existing issue around how the system prompt is composed and
  passed to the model. Out of scope for the Claude Code pack PR;
  needs its own focused fix + test.

## Safety coverage gaps

- **Classifier / protocol tests.** Expand `tests/safety/` to cover:
  - positive + negative cases for each detection pattern,
  - precedence (crisis branch wins over supportive branch),
  - per-locale response shape.

- **i18n key parity test.** Add a test asserting that every locale in
  `i18n/*.json` defines the same `crisis_*` / `safety_*` keys (or
  documents the omission).

- **Deterministic crisis patterns for non-RU shipped languages.**
  Either add language-specific patterns for `da`, `de`, `en`, `fr`,
  `no`, `pt`, or explicitly document that crisis detection is RU-only
  and the bot falls back to a safe locale otherwise.

## Observability

- **Scrubbed structured logging.** Add a logging utility that:
  - emits structured fields,
  - never logs raw user message text,
  - hashes/omits Telegram identifiers tied to message content.

## Tooling

- **Pre-commit hook** running `ruff` and `pytest tests/safety` on
  staged changes that touch `app/` or `i18n/`.

## Process

- **PR template** mirroring `.claude/rules/output-contract.md`
  (Diagnosis / Changes / Verification / Safety impact / Privacy
  impact / Risks).
