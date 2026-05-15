# Operations Runbook — PsySupport AI

## Repeated "Сейчас я временно перегружен..." message

### What it means

The bot is returning the `chat.rate_limited` fallback for every user message. This means the safety classifier's OpenRouter provider is returning HTTP 429 (Too Many Requests).

The bot deliberately **fails closed**: when the classifier cannot confirm a message is safe, it stops the conversation rather than risk an unsafe reply.

### How to identify classifier 429

Look for these lines in the bot log (WARNING level):

```
stage=classifier error=rate_limited model=<model-name>
stage=classifier status=429 rate_limited; failing closed
```

### How to rotate CLASSIFIER_MODEL

1. Pick a different free model from openrouter.ai/models — choose one with a **separate quota pool** from `OPENROUTER_MODEL`.
2. Edit `.env`:
   ```
   CLASSIFIER_MODEL=<new-model-id>:free
   ```
3. Restart the bot process.
4. Run the classifier smoke test to confirm the new model responds:
   ```bash
   .venv/bin/python3 scripts/smoke_classifier.py
   ```

### When to switch from free models to a paid key

Switch to a paid OpenRouter key when:
- Free model quotas are exhausted daily (repeated 429s across multiple models)
- The bot needs to handle more than ~50 messages/day reliably
- High-stakes use requires consistent classifier availability

To switch: add billing on openrouter.ai, then remove the `:free` suffix from both `OPENROUTER_MODEL` and `CLASSIFIER_MODEL` in `.env`.

---

## Provider error reference

| Log label | Meaning | Action |
|---|---|---|
| `error=rate_limited` | HTTP 429 — quota exceeded | Rotate `CLASSIFIER_MODEL` (see above) |
| `error=auth_config` | HTTP 401/403 — bad API key | Verify `OPENROUTER_API_KEY` in `.env` |
| `error=timeout` | Request timed out | Check network; if persistent, rotate model |
| `error=network` | Cannot connect to OpenRouter | Check network/DNS; check openrouter.ai status |
| `error=parse_failed` | Classifier returned non-JSON | Usually transient; monitor frequency |

---

## Startup config check

At bot startup the log shows:

```
config: default_model=<model> classifier_model=<model or "(fallback to default_model)">
```

If `classifier_model=(fallback to default_model)`, both the classifier and the main chat share the same quota pool. Set `CLASSIFIER_MODEL` in `.env` to a different model to prevent quota contention.

---

## Classifier smoke test

Run outside Telegram to verify the classifier is reachable and responding:

```bash
.venv/bin/python3 scripts/smoke_classifier.py
```

Expected output on success:

```
default_model    : google/gemma-4-31b-it:free
classifier_model : qwen/qwen3-next-80b-a3b-instruct:free

[harmless]
  risk_level       : NO_RISK (0)
  ...
  OK

[crisis-like]
  risk_level       : POSSIBLE_CRISIS (3)
  ...
  OK

smoke: passed
```

If any case prints `ERROR:`, the provider is unreachable or rate-limited — rotate `CLASSIFIER_MODEL` and retry.
