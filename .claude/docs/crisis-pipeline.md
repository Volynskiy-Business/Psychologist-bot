# Crisis pipeline (overview)

This is a high-level map. Read the code for ground truth; this doc just
points you to the right files.

## Entry points

- Incoming Telegram messages land in `app/bot/handlers/chat.py`
  (and friends in the same directory).
- `chat.py` is responsible for routing each message through the safety
  pipeline before any supportive / LLM path runs.

## Detection

- Lives under `app/safety/`.
- Conceptually: classify a message → decide whether it’s a crisis →
  decide which protocol applies.

## Response

- Crisis responses pull copy from `i18n/<locale>.json` (`crisis_*`,
  `safety_*`, hotline keys).
- Background reference: `knowledge_base/crisis_safety_plan.md`,
  `cbt.md`, `dbt_skills.md`, `mindfulness.md`.

## Invariants

- A flagged message must take the crisis branch **and not** also
  produce a generic supportive reply.
- Every shipped locale must define the crisis keys, or the bot must
  fall back deterministically to a locale that does.
- `app/ai/prompts/` system prompts must keep the harmful-content
  refusals intact regardless of persona / language.

## Tests

- `tests/safety/` is the regression guard. Adding new detection
  patterns or response paths means adding tests there.

## Open items

See `.claude/docs/v2-backlog.md` for known gaps and follow-ups.
