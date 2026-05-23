# PsySupport AI V1 Architecture Spec

**Document Type:** Product and Technical Architecture Spec
**Status:** Proposed
**Last Updated:** 2026-05-23

## Safety Goal

PsySupport AI V1 must provide supportive, non-clinical conversation while keeping safety routing deterministic, conservative, and auditable. The bot must never present itself as a doctor, psychologist, psychotherapist, psychiatrist, crisis hotline, diagnostic system, treatment provider, medical device, or replacement for professional human help.

The V1 architecture must preserve this order:

```text
Telegram Input
  -> Safety Router
  -> Intake and Topic Router
  -> User Profile and Memory
  -> Knowledge Retrieval
  -> Support Agent
  -> Output Safety Validator
  -> Telegram UX
```

If imminent or possible crisis risk is detected, the normal support flow stops before any LLM support response is generated.

## Product Goal

V1 should prove a safe support loop for one focused vertical: motivation and procrastination. The user experience should feel like a compact Telegram support conversation with optional voice input, adaptive onboarding, quick mood controls, and a small curated knowledge base. It should not feel like a symptom dashboard or a clinical intake form.

## Non-Goals

V1 does not implement diagnosis, treatment planning, medication guidance, emergency response, clinical assessment, therapist matching, insurance workflows, paid subscriptions, or a broad multi-topic content marketplace.

V1 does not attempt to fully solve every future topic. Anxiety, sadness, grief, burnout, negotiations, trading psychology, and business psychology remain compatible future verticals, but the first RAG loop should be proven with motivation and procrastination.

## Current Baseline

The current codebase already contains several V1 building blocks:

- Telegram polling bot with aiogram handlers.
- Text and voice input, including Telegram voice download, ffmpeg conversion, Groq STT, and LLM reply generation.
- Deterministic crisis detection before consent, onboarding, classifier, and support generation.
- Optional LLM safety classifier when `CLASSIFIER_MODEL` is configured.
- Deterministic intake classification with scenario and technique selection.
- Support pipeline with focused prompt construction, LLM generation, quality check, optional humanization rewrite, and deterministic output validation.
- User profile fields for onboarding personalization.
- Mood tracking, safety plan storage, feedback, and safety event recording.
- A small TF-IDF vector store for sadness support as an early local retrieval pattern.
- Scenario and technique YAML libraries with safety boundaries.

The next architecture step is not a broad rewrite. It is to formalize the target V1 flow and implement the missing pieces incrementally.

## Target Architecture

### 1. Telegram Input Layer

Responsibilities:

- Accept text messages.
- Accept Telegram voice messages and transcribe them before routing.
- Preserve the language of the user's current message for runtime responses.
- Keep command and menu UX compact.
- Avoid exposing implementation details to the user.

Input channels should produce one normalized internal payload:

```text
UserMessage(
  user_id,
  chat_id,
  channel="telegram",
  input_type="text" | "voice",
  text,
  detected_language,
  created_at
)
```

Voice transcription failures should produce a short, user-language retry message. They must not bypass safety routing.

### 2. Safety Router

Responsibilities:

- Run before consent, onboarding, mood note capture, safety plan capture, topic routing, RAG, and support generation.
- Detect possible crisis and imminent risk using deterministic rules first.
- Optionally call an LLM classifier only after deterministic checks and only when configured.
- Stop normal conversation for possible crisis or imminent risk.
- Record safety events without exposing raw identifiers in logs or reports.

Risk tiers:

```text
Tier 0: ordinary conversation
Tier 1: emotional distress without safety concern
Tier 2: elevated distress or passive death/disappearance wishes
Tier 3: possible crisis
Tier 4: imminent danger
```

Tier 3 and Tier 4 must not enter the normal support pipeline. Tier 2 may receive a short stabilizing response and gentle suggestion to seek human support if distress persists or worsens.

### 3. Intake and Topic Router

Responsibilities:

- Detect language from the current message, while allowing Telegram profile language as a weak fallback only.
- Classify the message into a topic and intent without diagnostic language.
- Select a safe response mode: general support, topic support, mood note, safety plan, onboarding, crisis route, or settings/menu action.
- Keep routing deterministic where possible.

For V1, add a motivation/procrastination topic family:

```text
Topic: motivation_procrastination
Intents:
  - stuck_starting
  - avoidance_loop
  - overwhelm
  - low_energy
  - fear_of_failure
  - perfectionism
  - task_clarification
```

The router must not infer mental disorders from procrastination, fatigue, avoidance, low mood, or anxiety. It should describe observable user goals and states only.

### 4. User Profile and Memory

Responsibilities:

- Store stable, low-risk personalization fields from onboarding: display name, language preference, region, user gender when provided, consultant presentation preference, and onboarding completion.
- Store lightweight product memory, not sensitive clinical memory.
- Keep short-term conversation history capped.
- Avoid storing secrets, raw crisis content beyond required safety event audit fields, or unnecessary sensitive details.

Recommended V1 memory fields:

```text
profile:
  display_name
  preferred_language
  region
  user_gender
  consultant_gender
  onboarding_completed

support_preferences:
  prefers_voice
  preferred_response_length
  preferred_style

topic_memory:
  active_topic
  current_goal_label
  last_selected_micro_step
  last_mood_score
```

Memory must be used to reduce repetition and make the bot warmer, not to create clinical profiles or diagnostic conclusions.

### 5. Knowledge Retrieval

Responsibilities:

- Retrieve curated self-help content by topic, language, and safety tier.
- Keep source material short, structured, and safe for direct prompt injection.
- Return no content for crisis tiers that must be handled by safety protocols.
- Prefer local deterministic retrieval first, then upgrade to a vector database when content volume justifies it.

Recommended V1 content shape:

```yaml
id: motivation_start_tiny_step
topic: motivation_procrastination
language: en
safety_tier_max: 2
title: Tiny next step
intent_tags:
  - stuck_starting
  - overwhelm
technique_family: behavioral_activation
user_situation: "The user wants to start but feels blocked or overwhelmed."
support_move: "Help the user choose one action small enough to do in two minutes."
bot_boundary: "Frame this as optional self-help, not treatment."
contraindications:
  - imminent_risk
  - active_self_harm
prompt_snippet: "Invite the user to choose one tiny action that reduces friction, such as opening the document, writing one sentence, or setting a two-minute timer."
```

Initial retrieval can use a local YAML library plus TF-IDF or simple tag scoring. Qdrant or pgvector should wait until the curated library grows enough that local search becomes limiting.

### 6. Support Agent

Responsibilities:

- Generate a short supportive response in the language of the current user message.
- Use only the selected topic, intent, technique, user profile, recent conversation, and retrieved safe snippets.
- Keep the response non-clinical, conversational, and specific.
- Offer at most one micro-step or exercise at a time.
- Ask at most one gentle question.
- Avoid Markdown in normal Telegram chat unless a specific menu or structured flow needs it.

For motivation/procrastination, the support agent should usually follow:

```text
Reflect the user's concrete situation.
Name the friction without diagnosing it.
Offer one tiny next step or choice.
Invite a brief response or action.
```

Example safe behavior:

```text
It sounds like the task has become too heavy to approach all at once. Let's make it smaller: open the file or note where this task lives, and do nothing else for two minutes. If that feels possible, tell me what the first visible piece of the task is.
```

The support agent must not claim to cure procrastination, treat anxiety, diagnose ADHD, provide therapy, or replace a coach, clinician, or crisis service.

### 7. Output Safety Validator

Responsibilities:

- Run after every generated or rewritten support response.
- Block identity claims, diagnosis, treatment claims, medication instructions, self-harm encouragement, crisis minimization, and emergency-delay language.
- Return a safe fallback message when output is blocked.
- Log only block reason and safe metadata.

The validator should remain deterministic for the final send/no-send decision. LLM-based validation can be added as a secondary signal, but it must not be the only output gate.

### 8. Telegram UX

Responsibilities:

- Keep the first screen focused on actual use, not a long educational menu.
- Use compact mood buttons and a small main menu.
- Let users type or speak naturally.
- Let the bot infer topic and intent through conversation.
- Keep onboarding adaptive and short.

Recommended V1 menu:

```text
Talk
Voice message
Mood check
Small step
Safety plan
Settings
```

The "Small step" entry point should route to the motivation/procrastination vertical. It should ask one lightweight question only when needed, such as "What are you trying to start or continue?"

## Motivation and Procrastination Vertical

### Scope

V1 should support users who feel stuck, avoid a task, feel overwhelmed, cannot start, lose motivation, or keep delaying something important.

### Safety Boundary

The vertical must not treat procrastination as a disorder. It must not diagnose ADHD, depression, anxiety disorder, burnout, trauma, or executive dysfunction. If the user asks for diagnosis, the bot should decline diagnosis and suggest speaking with a qualified professional.

### Technique Families

Allowed V1 technique families:

- Behavioral activation: one small doable action.
- Implementation intentions: "When X, I will do Y for Z minutes."
- Friction reduction: make the first action easier.
- Values clarification: connect the task to a personal reason.
- Self-compassion: reduce shame without excusing harmful avoidance.
- Problem-solving: clarify the next visible obstacle.

### Initial Content Set

Create 8 to 12 curated knowledge entries:

- Tiny next step.
- Two-minute start.
- Friction audit.
- If-then plan.
- Task slicing.
- Shame spiral interruption.
- Perfectionism softening.
- Energy-aware action.
- Values reminder.
- Reward after action.
- Re-entry after falling behind.
- Ask for help.

Each entry should define intent tags, safety tier ceiling, contraindications, and a prompt snippet.

## Multilingual and Voice Strategy

Runtime responses must follow the language of the user's current message. For mixed-language messages, the bot should answer in the dominant language or mirror the user's final clear request.

Voice input should be treated as another input mode, not a separate support mode:

```text
Telegram voice -> download -> ffmpeg conversion -> STT -> normalized text -> Safety Router -> normal flow
```

STT provider choice should remain configurable. Groq STT is currently working. Future local Whisper or other providers should share the same provider interface and must not change safety routing.

## Data and Storage

V1 can use existing PostgreSQL tables for users, mood entries, feedback, safety events, and safety plans. New storage should be minimal.

Likely future tables:

```text
knowledge_entries
  id
  topic
  language
  safety_tier_max
  title
  intent_tags
  technique_family
  user_situation
  support_move
  bot_boundary
  contraindications
  prompt_snippet
  created_at
  updated_at

topic_memory
  id
  user_id
  active_topic
  current_goal_label
  last_selected_micro_step
  updated_at
```

For V1 proof of concept, local YAML can be used before adding database tables.

## Observability

Log structured metadata for:

- input type: text or voice;
- transcript length, not transcript content;
- safety tier and route;
- topic and intent;
- selected knowledge entry IDs;
- selected model;
- output validation block reason;
- response success or failure.

Do not log raw Telegram identifiers, full user messages, secrets, API keys, database URLs, or sensitive chat content.

## Verification Strategy

Minimum checks for V1 implementation:

- Unit tests for motivation/procrastination routing.
- Unit tests for knowledge entry loading and safety tier filtering.
- Unit tests proving Tier 3 and Tier 4 never reach the support agent.
- Unit tests for diagnosis and medication boundary requests.
- Output validation regression tests for clinical self-description claims.
- Golden dialogue tests for motivation/procrastination in Russian and English.
- Voice smoke test proving transcript text enters the same safety pipeline.

Manual checks:

- Normal procrastination message.
- Ambiguous low-energy message.
- Diagnosis request about procrastination or ADHD.
- Medication question.
- Passive death wish.
- Possible crisis.
- Imminent risk.

## Implementation Sequence

1. Add motivation/procrastination scenarios and techniques to the existing YAML libraries.
2. Add routing regression tests for the new topic and intent signals.
3. Add a local curated knowledge library for the vertical.
4. Add a small retrieval function that filters by topic, language, intent tags, and risk tier.
5. Inject retrieved snippets into the support prompt.
6. Add golden dialogue tests for Russian and English responses.
7. Add compact Telegram entry point copy for "Small step".
8. Run targeted safety tests and output validation tests.
9. Only after the local loop works, evaluate whether Qdrant or pgvector is needed.

## Regression Risks

- Over-routing normal procrastination into clinical or crisis language.
- Under-routing passive or active self-harm signals hidden inside productivity complaints.
- Prompt snippets increasing response length or making the bot sound like a therapist.
- Voice transcription errors changing safety meaning.
- Memory fields becoming too sensitive or too clinical.
- RAG snippets bypassing scenario and technique safety ceilings.

## Before and After Behavior

Before this spec, the repository had working pieces of the safe support pipeline, but no single V1 architecture document tying safety routing, topic routing, memory, retrieval, support generation, validation, Telegram UX, voice, and the first knowledge vertical together.

After this spec, implementation can proceed in small verified increments against one product loop: motivation/procrastination support with safe retrieval and compact Telegram UX.
