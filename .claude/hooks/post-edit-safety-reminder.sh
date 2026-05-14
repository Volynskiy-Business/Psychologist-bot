#!/usr/bin/env bash
# PostToolUse hook for Edit | Write | MultiEdit.
# Prints a concise reminder to stderr when a safety-sensitive path is touched.
# Never blocks. Safe no-op on malformed input.

set -u

input="$(cat || true)"
[ -z "${input}" ] && exit 0

# Extract tool_input.file_path; fall back to file_paths array elements.
path="$(printf '%s' "$input" \
  | tr -d '\n' \
  | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\(\([^"\\]\|\\.\)*\)".*/\1/p')"

if [ -z "${path:-}" ]; then
  # MultiEdit may use edits[].file_path; pull the first occurrence.
  path="$(printf '%s' "$input" \
    | tr -d '\n' \
    | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\(\([^"\\]\|\\.\)*\)".*/\1/p' \
    | head -n1)"
fi

[ -z "${path:-}" ] && exit 0

# Match safety-sensitive areas. Use case-insensitive plain substring checks.
remind=""
case "$path" in
  *app/safety/*)            remind="safety pipeline" ;;
  *app/ai/prompts/*)        remind="LLM prompts" ;;
  *app/bot/handlers/*)      remind="Telegram handler" ;;
  *i18n/*.json)             remind="localised copy (check crisis_* / safety_* keys)" ;;
  *knowledge_base/*)        remind="clinical reference content" ;;
  *tests/safety/*)          remind="safety tests" ;;
esac

if [ -n "$remind" ]; then
  printf '[safety-reminder] touched %s — affects %s. Re-check .claude/rules/safety.md and consider running tests/safety.\n' "$path" "$remind" 1>&2
fi

exit 0
