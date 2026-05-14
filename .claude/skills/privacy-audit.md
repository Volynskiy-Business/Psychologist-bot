# Skill: privacy-audit

Use when a change adds or modifies logging, persistence, outbound HTTP
calls, analytics, or anything that captures user data.

## Checklist

1. No raw user message text is logged.
2. No Telegram user/chat/message IDs are logged in a way that ties them
   to message content.
3. New persisted columns/fields are necessary and documented.
4. New outbound destinations (any host outside the existing LLM provider)
   are explicitly approved in the PR description.
5. Log records use structured fields, not `repr(dict)` / `**kwargs` dumps.
6. Test fixtures use synthetic content, not real conversation samples.

## Output

For each failed check, cite file:line and propose the minimal redaction
or structural fix. If a new outbound destination is being added without
approval, mark the change as **block**.
