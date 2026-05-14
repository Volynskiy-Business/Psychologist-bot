# Skill: telegram-handler-review

Use when editing files under `app/bot/handlers/` — especially
`chat.py`, `start.py`, `mood.py`, `i18n.py`.

## Checklist

1. Crisis branch precedence: when the safety pipeline flags a message,
   the handler returns the crisis response and does **not** also run the
   supportive/LLM path.
2. No raw user message text or Telegram identifiers are logged.
3. Errors are caught at the handler boundary so a crash doesn’t leave a
   user in a crisis flow without a reply.
4. i18n keys referenced exist in all locales the bot ships (or have a
   documented fallback).
5. Long-running calls (LLM, DB) are awaited correctly; no blocking calls
   in the event loop.
6. State transitions (FSM, if used) clean up on error.

## Output

Flag any failed check with file:line. Propose the smallest fix.
