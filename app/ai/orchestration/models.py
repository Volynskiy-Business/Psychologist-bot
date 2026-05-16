"""Pydantic models for the multi-agent support pipeline."""

from enum import IntEnum
from typing import Optional

from pydantic import BaseModel


class RiskTier(IntEnum):
    TIER_0 = 0  # ordinary conversation — no emotional distress
    TIER_1 = 1  # emotional distress, no safety concern
    TIER_2 = 2  # elevated distress: hopelessness, isolation, severe overwhelm
    TIER_3 = 3  # possible self-harm or danger (handled upstream by crisis detector)
    TIER_4 = 4  # imminent danger — plan, means, inability to stay safe (crisis detector)


class IntakeResult(BaseModel):
    language: str
    detected_emotion: str
    intensity: float  # 0.0–1.0
    scenario_id: str
    risk_tier: RiskTier
    risk_signals: list[str]


class ScenarioData(BaseModel):
    id: str
    title: str
    emotion_signals: list[str]
    risk_signals: list[str]
    risk_ceiling: int
    recommended_techniques: list[str]
    response_shape: str
    do_rules: list[str]
    dont_rules: list[str]
    contraindications: list[str]
    escalation_rules: list[str]
    knowledge_snippets: list[str] = []


class TechniqueData(BaseModel):
    id: str
    title: str
    evidence_base: str
    risk_ceiling: int
    emotion_states: list[str]
    instructions: str
    contraindications: list[str]
    bot_usage_boundary: Optional[str] = None


class PipelineResult(BaseModel):
    content: str
    is_safe: bool
    block_reason: Optional[str]
    scenario_id: Optional[str]
    technique_id: Optional[str]
    risk_tier: RiskTier
    intake_language: str
