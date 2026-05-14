#!/usr/bin/env bash
# PreToolUse hook for Bash. Blocks high-risk commands.
# Reads Claude Code hook JSON from stdin; exits 2 with a stderr reason to block.
# Safe no-op on malformed input or unrelated tools.

set -u

input="$(cat || true)"
[ -z "${input}" ] && exit 0

# Extract tool_input.command without depending on jq.
# Match: "command":"...."  (single-line value).
cmd="$(printf '%s' "$input" \
  | tr -d '\n' \
  | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\(\([^"\\]\|\\.\)*\)".*/\1/p')"

# If we couldn't parse a command, do nothing.
[ -z "${cmd:-}" ] && exit 0

block() {
  # $1 = short reason
  printf 'blocked by risky-bash-block: %s\n' "$1" 1>&2
  exit 2
}

# Normalised lowercase copy for matching.
lc="$(printf '%s' "$cmd" | tr '[:upper:]' '[:lower:]')"

# 1) Reading .env (but .env.example is fine).
case "$lc" in
  *cat*.env|*cat*.env\ *|*' .env'*|*'<.env'*|*'< .env'*)
    case "$lc" in
      *.env.example*) ;;
      *) block "reads .env / dotenv file" ;;
    esac
    ;;
esac
# Generic dotenv read patterns.
if printf '%s' "$lc" | grep -Eq '(^|[^a-z0-9_])(cat|less|more|head|tail|bat|xxd|od|strings)([[:space:]]+-[a-z]+)*[[:space:]]+\.env(\.[a-z0-9_-]+)?([[:space:]]|$)'; then
  case "$lc" in
    *.env.example*) ;;
    *) block "reads .env / dotenv file" ;;
  esac
fi

# 2) Reading real secrets.
if printf '%s' "$lc" | grep -Eq '(^|[^a-z0-9_])(cat|less|more|head|tail|bat|xxd|od|strings|cp|mv|scp|rsync)[[:space:]]+[^|;]*\.(pem|key|p12|pfx)([[:space:]]|$)'; then
  block "reads private key material"
fi
if printf '%s' "$lc" | grep -Eq '(^|[^a-z0-9_])(cat|less|more|head|tail|cp|mv|scp|rsync)[[:space:]]+[^|;]*secrets/'; then
  block "reads files under secrets/"
fi
if printf '%s' "$lc" | grep -Eq '~/\.ssh/|/\.ssh/id_|~/\.aws/credentials|/\.aws/credentials'; then
  block "reads SSH or AWS credentials"
fi

# 3) Git force push.
if printf '%s' "$lc" | grep -Eq 'git[[:space:]]+push([[:space:]]+[^|;]*)?(--force([^-]|$)|[[:space:]]-f([[:space:]]|$))'; then
  block "git force push"
fi

# 4) Hard reset / destructive history rewrite.
if printf '%s' "$lc" | grep -Eq 'git[[:space:]]+reset[[:space:]]+--hard'; then
  block "git reset --hard"
fi
if printf '%s' "$lc" | grep -Eq 'git[[:space:]]+filter-branch|git[[:space:]]+clean[[:space:]]+-fdx'; then
  block "destructive git history operation"
fi

# 5) rm -rf on sensitive paths.
if printf '%s' "$lc" | grep -Eq 'rm[[:space:]]+(-[a-z]*r[a-z]*f[a-z]*|-rf|-fr)[[:space:]]+[^|;]*(\.git|/|~|\.|app|tests|i18n|knowledge_base|\.claude)([[:space:]]|/|$)'; then
  block "rm -rf on sensitive path"
fi

# 6) Curl|sh / wget|sh remote execution.
if printf '%s' "$lc" | grep -Eq '(curl|wget)[[:space:]]+[^|;]+\|[[:space:]]*(sh|bash|zsh)([[:space:]]|$)'; then
  block "remote pipe-to-shell execution"
fi

exit 0
