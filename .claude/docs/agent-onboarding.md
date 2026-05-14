# Agent onboarding

If this is your first turn in this repo, do this in order.

## 1. Read the rules

- `CLAUDE.md` (root) — product identity, hard safety boundaries.
- `.claude/rules/safety.md` — mental-health rules.
- `.claude/rules/privacy.md` — PII / secrets / logging rules.
- `.claude/rules/repo-workflow.md` — branching, commits, PRs.
- `.claude/rules/output-contract.md` — response shape.

## 2. Orient quickly

- `app/safety/` — crisis detection + escalation.
- `app/ai/prompts/` — system prompts.
- `app/bot/handlers/` — Telegram handlers (`chat.py`, `start.py`,
  `mood.py`, `i18n.py`).
- `i18n/*.json` — localised copy.
- `knowledge_base/` — clinical reference.
- `tests/safety/` — regression guard.

Use the `repo-explorer` agent for any "where is X" question.

## 3. Pick the right helper

- Editing safety code? Use `prompt-edit-guard`, `crisis-copy-review`,
  `telegram-handler-review`, `tests-for-safety` skills as appropriate.
- Reviewing a diff? `safety-reviewer` first (if it touches safety),
  `code-reviewer` otherwise.
- Verifying? `test-runner`.

## 4. Stay in scope

- Smallest viable change.
- No drive-by refactors.
- No new dependencies without explicit instruction.
- Stop and surface, instead of pushing through, when a stop condition
  in `CLAUDE.md` fires.

## 5. Ship

- Branch: `<type>/<short-slug>`.
- PR description follows `.claude/rules/output-contract.md`.
- Never approve a PR — you’re not authorised to.
