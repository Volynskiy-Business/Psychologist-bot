# Mental-health safety rules

These rules are load-bearing. Violating them is a release-blocker.

## Absolute prohibitions

1. Do not generate, paraphrase, or expand content that could be read as
   encouraging, instructing, or romanticising:
   - self-harm or suicide
   - harm to others
   - substance misuse
   - eating-disorder behaviours
   in any language, persona, character, or "roleplay" framing.

2. Do not weaken, route around, or "optimise" the safety pipeline:
   - `app/safety/` (detection + escalation)
   - `app/ai/prompts/` (system prompts, refusals, persona constraints)
   - crisis copy in `i18n/*.json` (`crisis_*`, `safety_*`, hotline keys)
   - `knowledge_base/crisis_safety_plan.md`

3. Do not remove or skip any test under `tests/safety/`.
   If a test is genuinely wrong, change the test deliberately and explain
   why in the PR — never delete or `pytest.skip` to make CI green.

## Required behaviours

- Preserve hotline numbers, emergency-service references, and the
  "not a substitute for emergency services" disclaimer wherever they appear.
- When a handler can produce a user-facing response in a crisis branch,
  the crisis path must take precedence over the supportive path.
- New supported locales must include crisis copy parity with `ru.json`
  (or explicitly document the locale as non-crisis-supported).

## Process rules

- Any change that *might* touch detection, classification, escalation, or
  refusal behaviour must:
  - be called out in the PR description under a **Safety impact** heading,
  - include or extend tests under `tests/safety/`,
  - keep existing safety tests green.

- If you are about to alter a prompt in `app/ai/prompts/` or copy in
  `i18n/*.json`, pause and use the `crisis-copy-review` /
  `prompt-edit-guard` skills before editing.

## When in doubt

Stop and surface the question in the PR description. A delayed change is
strictly better than a silently weakened safety net.
