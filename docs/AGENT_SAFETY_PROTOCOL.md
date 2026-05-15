# Agent Safety Protocol

This document governs safety-sensitive work in PsySupport AI.

## Product Boundary

PsySupport AI provides emotional support and psychological self-help conversations.

It must not present itself as:

- a doctor;
- a licensed therapist;
- a crisis hotline;
- a medical device;
- a diagnostic system;
- a treatment provider.

## Non-Negotiable Rules

The bot must never:

- diagnose;
- claim to treat mental health conditions;
- provide medication advice;
- provide self-harm, suicide, violence, or evasion instructions;
- minimize crisis signals;
- continue normal supportive chat when imminent risk is detected.

## Safety-Sensitive Areas

Treat these as safety-sensitive:

- crisis detection;
- risk classification;
- safety protocols;
- system prompts;
- Telegram bot onboarding;
- help messages;
- disclaimers;
- mental-health copy;
- emergency or crisis guidance;
- README/product claims.

## Required Change Protocol

Before changing safety-sensitive areas:

1. state the safety goal;
2. identify current behavior;
3. identify the smallest safe change;
4. list likely regression risks;
5. implement only the required change;
6. verify normal, ambiguous, possible-crisis, and imminent-risk cases where practical;
7. document before/after behavior.

## Copy Rules

Use language that is:

- calm;
- supportive;
- non-clinical;
- clear;
- non-judgmental;
- honest about limitations.

Avoid:

- therapeutic authority claims;
- diagnostic wording;
- promises of outcomes;
- exaggerated reassurance;
- language that delays urgent human help;
- engagement-driven copy in crisis contexts.

## Crisis Handling Principle

When risk is high, safety beats conversational continuity.

The bot should stop normal support flow and provide short, clear guidance toward immediate human support or emergency resources appropriate to the user context.
