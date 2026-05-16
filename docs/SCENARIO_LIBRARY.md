# Scenario and Technique Library

## What This Is

PsySupport AI uses two YAML libraries — scenarios and techniques — to structure its emotional support responses. These libraries drive a deterministic intake pipeline that classifies each user message and selects an appropriate response pattern before any LLM call.

This document explains what the libraries are, their safety boundaries, and what still requires external validation.

## Scenario Library (`app/ai/scenarios/library.yaml`)

A scenario is a named emotional situation with a defined response pattern. When a user sends a message, the intake agent scores it against each scenario's `emotion_signals` and selects the best match.

Each scenario defines:

- `emotion_signals` — keywords that indicate this scenario
- `risk_signals` — phrases that elevate risk tier within this scenario
- `risk_ceiling` — the maximum risk tier this scenario is appropriate for
- `recommended_techniques` — ordered list of technique IDs safe for this scenario
- `response_shape` — the structural pattern the LLM response should follow
- `do_rules` / `dont_rules` — behavioral constraints injected into the system prompt
- `escalation_rules` — conditions that require escalation to higher risk handling

### Current Scenarios (19)

**Ordinary support scenarios:**
- `sadness_grief` — sadness, grief, general loss
- `anxiety` — worry, panic, fear
- `anger` — frustration, conflict, rage
- `loneliness` — isolation, disconnection
- `exhaustion` — burnout, depletion, no energy
- `guilt_shame` — self-blame, shame, guilt
- `loss_of_meaning` — apathy, meaninglessness, existential crisis
- `uncertainty` — loss of control, chaos, confusion

**Life-event scenarios:**
- `breakup_divorce` — romantic separation, divorce
- `death_of_loved_one` — bereavement, mourning
- `job_loss` — career crisis, unemployment
- `financial_loss` — debt, financial crisis
- `serious_illness_or_disability` — chronic illness, disability, chronic pain

**Safety redirect scenarios (no techniques):**
- `passive_death_thoughts` — passive wish to not exist; redirects to human support
- `possible_self_harm` — active self-harm signals; redirects to crisis support
- `imminent_danger` — immediate physical danger; redirects to emergency services

**Boundary scenarios:**
- `diagnosis_request` — declines diagnosis, explains why, offers referral
- `medication_question` — declines medication advice, refers to prescribing doctor
- `general_support` — fallback when no specific scenario matches

### Risk Tier System

The pipeline assigns one of five risk tiers (0–4) to each message:

| Tier | Meaning | Handled by |
|------|---------|------------|
| 0 | No emotional distress | General pipeline |
| 1 | Emotional distress, no safety concern | General pipeline |
| 2 | Elevated distress: hopelessness, severe isolation | Pipeline with crisis section |
| 3 | Possible self-harm (handled upstream) | Crisis detector before pipeline |
| 4 | Imminent danger (handled upstream) | Crisis detector before pipeline |

The crisis detector runs before the pipeline. Tier 3/4 messages never reach the support pipeline.

## Technique Library (`app/ai/techniques/library.yaml`)

A technique is a brief, evidence-informed self-help tool. When a scenario is matched, the pipeline selects the first technique from `recommended_techniques` whose `risk_ceiling` is at or above the detected risk tier. The technique's instructions and boundary are injected into the system prompt.

Each technique defines:

- `evidence_base` — the theoretical framework (DBT, ACT, CBT, etc.)
- `risk_ceiling` — maximum risk tier at which this technique is appropriate
- `emotion_states` — emotional contexts where this technique is useful
- `instructions` — what the bot should suggest to the user
- `contraindications` — situations where this technique should not be used
- `bot_usage_boundary` — explicit statement of what the bot can and cannot do with this technique

### Current Techniques (27)

Organized by primary framework: DBT, Self-Compassion (Neff), CBT/Behavioral, Grief Work, Neuroscience/Somatic, Sensory Grounding, ACT, NVC, Social Psychology, Mindfulness, Positive Psychology, Solution-Focused.

Full list: `labeling_dbt`, `self_compassion_neff`, `behavioral_activation`, `permission_to_grieve`, `physiological_sigh`, `grounding_54321`, `worry_scheduling`, `accepting_uncertainty_act`, `physical_discharge`, `stop_pause`, `validate_need`, `i_statement_nvc`, `micro_contact`, `common_humanity_act`, `mindful_self_presence`, `minimum_dose`, `check_basic_needs`, `resource_inventory`, `letter_to_friend_cbt`, `guilt_vs_shame`, `reparative_action`, `normalize_apathy`, `values_compass_act`, `action_without_motivation`, `circles_of_influence`, `next_small_step`, `body_grounding`.

## Safety Boundaries

The scenario and technique libraries are designed for **emotional support and psychological self-help**, not clinical treatment.

The bot:
- does not diagnose any condition
- does not prescribe, recommend, or comment on medication
- does not claim to treat any mental health condition
- does not promise specific outcomes or recovery
- does not replace professional psychological or psychiatric care
- always refers users to human professionals when risk is elevated

Techniques are framed as optional self-help invitations, not therapeutic interventions. The `bot_usage_boundary` field on each technique makes this explicit.

## Evidence Status

The libraries are **evidence-informed**, not evidence-validated for this specific deployment.

The theoretical frameworks referenced (DBT, ACT, CBT, NVC, Neff's self-compassion, somatic approaches) are established in clinical psychology literature. However:

- No randomized controlled trials have been conducted on this specific bot's use of these techniques
- The `evidence_base` field names the source framework only — it is not a citation to a specific study
- The bot's adaptation of these techniques for a text-based, asynchronous, non-clinical context has not been independently validated
- Individual response quality depends on the LLM's generation and the user's specific situation

Future work should:
- Add specific source citations to each technique's `evidence_base`
- Add `evidence_level` metadata (e.g., well-established, emerging, framework-based)
- Conduct user research on whether technique delivery feels appropriate and helpful
- Have a qualified psychologist review the scenario playbooks and technique instructions

## What This Library Does Not Cover

- Crisis intervention (handled by the crisis detector, not the pipeline)
- Clinical assessment or diagnosis
- Treatment planning
- Session-based therapy
- Medication management
- Emergency response

For crisis handling, see `app/safety/crisis_detector.py` and `app/safety/safety_protocols.py`.
