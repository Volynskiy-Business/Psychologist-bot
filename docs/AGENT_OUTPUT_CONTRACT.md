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
