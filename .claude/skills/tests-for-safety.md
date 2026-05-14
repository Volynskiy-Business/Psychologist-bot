# Skill: tests-for-safety

Use whenever a change touches `app/safety/`, `app/ai/prompts/`,
crisis copy in `i18n/*.json`, or the crisis branch in
`app/bot/handlers/chat.py`.

## What to add

1. **Detection tests.** For new or modified patterns/classifier logic,
   add positive cases (must trigger) and negative cases (must not
   trigger), in `tests/safety/`.
2. **Response tests.** Assert that the crisis response includes the
   hotline / emergency disclaimer for the target locale.
3. **Precedence tests.** Assert that when the safety pipeline flags a
   message, the supportive/LLM path is **not** also invoked.
4. **i18n parity.** If you added/removed a `crisis_*` key, add a parity
   test ensuring all shipped locales define it.

## Rules

- Tests must be deterministic. No real network, no real LLM.
- Use synthetic fixtures — no real user conversations.
- If a test is hard to write because the code is tangled, prefer
  refactoring the code over weakening the assertion.

## Output

List the new/changed tests by name, what they assert, and the command
that runs them.
