# Agent Output Contract

This document defines how agents must report work.

## Implementation Report

Use this format after implementation tasks:

    ## Summary
    - What changed.

    ## Files Changed
    - path/to/file: reason.

    ## Verification
    - command: result.

    ## Risks / Notes
    - Remaining risks.
    - Assumptions.
    - Follow-up work.

## Audit Report

Use this format after audit tasks:

    # Project Audit Report

    ## Executive Summary

    ## Critical Issues

    ## High-Priority Issues

    ## Medium-Priority Issues

    ## Low-Priority Issues

    ## Safety Risks

    ## Security Risks

    ## Test Coverage Gaps

    ## Deployment Risks

    ## Documentation Gaps

    ## Recommended Implementation Plan

    ## Commands Run

    ## Commands Not Run and Why

## Language Rules

Developer-facing reports and explanations directed at the project owner must be written in Russian.

Do not switch to Ukrainian, English, or any other language based on Cyrillic detection, locale inference, or terminal environment.

Correct examples:
- "Бот работает. Последний запрос обработан без ошибок."
- "Изменения внесены в следующие файлы:"
- "Тесты прошли. Рафф чист."

Incorrect examples:
- "Бот живий..." (Ukrainian — not acceptable)
- "Твій план..." (Ukrainian — not acceptable)

Production artifacts (prompts, UX copy, docs, specs) must be written in English unless explicitly requested otherwise.

Reports must not include raw Telegram user IDs or bot update identifiers. Use redacted placeholders when referencing user-related log data.

## Verification Rules

Do not say:

- tests passed unless tests were run and passed;
- lint passed unless lint was run and passed;
- fixed unless the fix was implemented and verified;
- secure unless the checked scope is explicitly defined.

Prefer:

- Not verified; command was not run.
- Partially verified with targeted tests.
- Static review only.
- Blocked by missing dependency.
