# Repo workflow rules

## Branching

- Never commit directly to `main`.
- Branch names: `<type>/<short-slug>` — e.g. `fix/crisis-regex-ru`,
  `chore/claude-code-antigravity-pack`, `feat/mood-tracking-export`.
- Keep one logical change per branch.

## Commits

- Conventional-commit-ish prefixes: `feat:`, `fix:`, `chore:`, `docs:`,
  `refactor:`, `test:`, `ci:`, `perf:`.
- Subject ≤ 72 chars, imperative mood.
- Body explains *why*, not *what* (the diff already shows what).
- Reference issues when applicable.

## Pull requests

PR description must include:

1. **Diagnosis** — what was wrong / what the goal is.
2. **Changes** — bullet list of files touched and why.
3. **Verification** — exact commands run, and their results.
4. **Safety impact** — required whenever the change is in or near
   `app/safety/`, `app/ai/prompts/`, `i18n/`, `knowledge_base/`,
   or `tests/safety/`. State "None — change is in <area>" otherwise.
5. **Privacy impact** — required whenever logging, persistence,
   outbound calls, or user-data shapes change. State "None" otherwise.
6. **Risks / follow-ups** — anything deferred.

## Scope discipline

- Do not reformat files unrelated to the change.
- Do not rename modules, types, or public functions opportunistically.
- Do not add dependencies in unrelated PRs.
- Do not bundle "while I'm here" cleanups into a feature/fix PR.

## CI expectations

CI runs: `ruff` → `mypy` → `pytest` (with coverage) → `bandit` → docker build.
Do not weaken, skip, or `# noqa` past these without explicit instruction.

## Don’t

- Don’t force-push shared branches.
- Don’t rewrite history on `main`.
- Don’t `--no-verify` your way past hooks.
- Don’t approve your own PRs (and subagents must never approve any PR).
