# Output contract

Every non-trivial response and PR description should follow this shape.
Skip sections that don’t apply, but keep the order.

## 1. Diagnosis

- State, in 1–3 bullets, what the current code/state actually is.
- Cite paths and lines: `app/safety/classifier.py:42`.
- Distinguish observed facts from assumptions.

## 2. Plan

- The smallest viable change that achieves the goal.
- Concrete numbered steps. No vague "improve X".
- Call out anything intentionally out of scope.

## 3. Changes

- List files touched and the purpose of each change.
- Prefer diffs over prose where it makes the change clearer.

## 4. Verification

- Exact commands run, and their actual results.
- If a command was not run, say so — never imply coverage you didn’t do.
- For UI-adjacent changes (bot replies, i18n copy), describe the manual
  check.

## 5. Safety impact

Required when the change touches or could affect:

- `app/safety/`
- `app/ai/prompts/`
- crisis-related copy in `i18n/*.json` or `knowledge_base/`
- `tests/safety/`

State "None — change is isolated to <area>" otherwise. Don’t omit the
heading; absence is itself information.

## 6. Privacy impact

Required when logging, persistence, outbound calls, or the shape of user
data changes. Otherwise state "None".

## 7. Risks / follow-ups

- Anything deferred, especially safety-adjacent.
- Add to `.claude/docs/v2-backlog.md` if it’s a real follow-up.

## Style

- Terse. Bullets over paragraphs.
- File:line citations over vague references.
- Don’t restate the user’s prompt back at them.
- Don’t invent verification you didn’t run.
