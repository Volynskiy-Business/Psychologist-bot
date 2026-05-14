# Skill: prompt-edit-guard

Use before editing any file under `app/ai/prompts/`.

## Checklist

1. The system prompt still forbids:
   - encouraging or instructing self-harm or suicide
   - harm to others
   - substance misuse
   - eating-disorder behaviours
2. The bot still identifies itself as a supportive companion, **not** a
   licensed therapist, and routes crises to professional help.
3. No new "roleplay", "developer mode", or "ignore previous instructions"
   surface is added.
4. Refusal style remains warm + redirecting, not cold + dismissive
   (so users in crisis don’t bounce off).
5. If the prompt is multilingual, the safety clauses are present in
   every language used.

## Output

If any check fails, stop the edit and report the specific clause that
would be weakened. Propose a minimal rewrite that preserves intent.
