# Privacy, PII, and secrets rules

## Secrets

- Never `cat`, `echo`, or otherwise print the contents of:
  - `.env`, `.env.local`, `.env.*` (except `.env.example`)
  - `*.pem`, `*.key`
  - anything under `secrets/`
  - `~/.ssh/*`, `~/.aws/credentials`
- Never commit real credentials, tokens, API keys, or webhook URLs.
- If a file *might* contain secrets, treat it as if it does.
- Reference `.env.example` for required variable names instead of opening
  `.env`.

## User data / PII

User messages to this bot can include highly sensitive disclosures
(mental health, abuse, suicidal ideation). Treat all user content as PII.

- Do not log raw user message text.
- Do not log Telegram user IDs, chat IDs, usernames, or message IDs in a
  form that ties them to message content.
- If structured logging is added, it must:
  - emit fields explicitly (no `**user_dict` style dumps),
  - hash or omit user identifiers when not strictly required,
  - never include message bodies or AI replies in logs by default.
- Do not send user content to third-party services beyond what the bot
  already uses (the configured LLM provider). Adding a new outbound
  destination is a stop-and-ask condition.

## Data at rest

- Database fields holding user text should not be replicated into logs,
  test fixtures, or sample data in the repo.
- If you need a fixture for tests, fabricate synthetic content — do not
  paste real conversations.

## When in doubt

If a change could increase the amount, scope, or retention of user data
captured, surface it explicitly in the PR description under a
**Privacy impact** heading.
