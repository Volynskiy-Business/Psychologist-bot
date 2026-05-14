# Skill: crisis-copy-review

Use before/while editing any `crisis_*`, `safety_*`, or hotline-related
key in `i18n/*.json` or content in `knowledge_base/crisis_safety_plan.md`.

## Checklist

1. The new copy still names emergency services or hotlines in that locale.
2. The new copy still includes the disclaimer that this bot is **not** a
   substitute for emergency services.
3. The new copy does not soften urgency (no "if you want to" where the
   original said "please reach out now").
4. No reduction in length that drops a key piece of information
   (hotline number, instruction, disclaimer).
5. Key parity with `ru.json` is preserved — no `crisis_*` key silently
   dropped from a locale.
6. JSON is valid (`python3 -m json.tool`).

## Output

If any check fails, **do not save the edit**. Surface the issue with the
exact key + locale and propose a safer rewrite.
