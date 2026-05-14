# CLAUDE.md — Psychologist Bot

> Operational instructions for Claude Code / Antigravity working on this repo.
> Keep responses tight, surgical, and aligned with the safety surfaces below.

## Product identity

A Telegram bot (aiogram 3) that provides supportive, CBT/DBT-informed
conversations. **It is not a therapist and not a substitute for emergency
services.** Users in distress must always be routed to professional/local
emergency help.

## Hard mental-health safety boundaries (non-negotiable)

1. **Never** generate content that could be interpreted as encouraging,
   instructing, or romanticising self-harm, suicide, harm to others, or
   substance misuse — in any language, persona, or “roleplay” framing.
2. **Never** weaken or bypass the crisis detection / safety reply pipeline in
   `app/safety/` or the prompts in `app/ai/prompts/`. Treat these as
   load-bearing.
3. **Never** remove or soften the crisis copy in `i18n/*.json` (`crisis_*`,
   `safety_*` keys) or in `knowledge_base/crisis_safety_plan.md`.
4. **Never** disable, mock, or skip tests under `tests/safety/`.
5. Preserve emergency numbers, hotline references, and "this bot is not a
   substitute for emergency services" disclaimers wherever they appear.
6. If a change *might* affect detection, response, or escalation behaviour,
   stop and surface the risk in your PR description before merging.

## Karpathy-inspired working rules

- **Think before coding.** State the goal, the smallest viable change, and
  what could go wrong — *then* edit.
- **Simplicity first.** Prefer the smallest diff that solves the problem.
  Avoid speculative abstractions, new dependencies, or refactors outside the
  task.
- **Surgical changes.** Touch only what the task requires. No drive-by
  reformatting in files unrelated to the change.
- **Goal-driven execution.** If a step isn’t moving the goal forward, stop
  and re-plan instead of grinding.
- **Verify what you claim.** Only assert that tests/lints pass if you
  actually ran them.

## Safety surface map

| Area | Path | Why it matters |
| --- | --- | --- |
| Crisis detection & protocols | `app/safety/` | Classification + escalation logic |
| LLM prompts / personas | `app/ai/prompts/` | Defines bot behaviour and refusals |
| User-facing handlers | `app/bot/handlers/chat.py`, `start.py`, `mood.py`, `i18n.py` | Where copy and flow are wired |
| Localised copy | `i18n/{da,de,en,fr,no,pt,ru}.json` | Crisis & support strings |
| Clinical reference | `knowledge_base/{cbt,dbt_skills,mindfulness,crisis_safety_plan}.md` | Grounding for replies |
| Safety tests | `tests/safety/` | Regression guardrail — must keep passing |

## Privacy & secrets (summary)

- Never read, print, commit, or echo real secrets. `.env.example` is safe;
  `.env*` is not.
- Do not log raw user messages, identifiers, or message IDs. If logging is
  added, it must be scrubbed/structured (see `.claude/rules/privacy.md`).
- Do not exfiltrate data to third-party services without explicit approval.
- See `.claude/rules/privacy.md` for the full rule set.

## Stop conditions — abort and ask the human

Stop and request review instead of proceeding when:

- A change would touch `app/safety/`, `app/ai/prompts/`, or `tests/safety/`
  semantics.
- Crisis copy or emergency references would be removed, reworded
  significantly, or dropped from any locale.
- A dependency, model provider, or external network call would be added.
- You are about to disable a test, lint rule, type check, or CI step.
- A migration / destructive DB change is implied.
- You can’t reproduce a verification step the PR claims.

## Stack & verification (read-only summary)

- Python 3.11 / 3.12, aiogram 3, pydantic v2, sqlalchemy async, httpx, redis.
- Tooling: ruff, mypy, pytest (+coverage), bandit. Docker build in CI.
- CI runs: ruff → mypy → pytest+cov → bandit → docker build. Don’t weaken
  these without explicit instruction.

## Scoped rules and docs

- `.claude/rules/safety.md` — mental-health safety guardrails in detail
- `.claude/rules/privacy.md` — PII / secrets / logging rules
- `.claude/rules/repo-workflow.md` — branching, commits, PRs, scope discipline
- `.claude/rules/output-contract.md` — how to structure replies and PRs
- `.claude/docs/agent-onboarding.md` — start here when first invoked
- `.claude/docs/crisis-pipeline.md` — how the safety flow is wired
- `.claude/docs/v2-backlog.md` — known issues and follow-ups

## Output contract (short form)

Every non-trivial response should include:

1. **Diagnosis** — what the code/state actually is, with file:line refs.
2. **Plan** — smallest viable change, listed as concrete steps.
3. **Changes** — diffs or file lists, scoped to the plan.
4. **Verification** — exact commands run and their result. Don’t claim
   coverage you didn’t execute.
5. **Risks / follow-ups** — anything deferred, especially safety-adjacent.

Full version: `.claude/rules/output-contract.md`.
