"""SQLAlchemy ORM models."""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RiskLevel(enum.IntEnum):
    NO_RISK = 0
    MILD_DISTRESS = 1
    ELEVATED_DISTRESS = 2
    POSSIBLE_CRISIS = 3
    IMMINENT_RISK = 4


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="ru")
    region: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    style_preference: Mapped[str] = mapped_column(String(32), default="soft")
    consent_given: Mapped[bool] = mapped_column(default=False)
    consent_accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    mood_entries: Mapped[list["MoodEntry"]] = relationship(back_populates="user")
    messages: Mapped[list["Message"]] = relationship(back_populates="user")
    safety_events: Mapped[list["SafetyEvent"]] = relationship(back_populates="user")


class MoodEntry(Base):
    __tablename__ = "mood_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    mood_score: Mapped[int] = mapped_column(Integer)  # -5..+5
    anxiety_score: Mapped[int] = mapped_column(Integer)  # 0..10
    energy_score: Mapped[int] = mapped_column(Integer)  # 0..10
    sleep_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    main_emotion: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    trigger: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thought: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_done: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="mood_entries")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user / assistant / system
    content: Mapped[str] = mapped_column(Text)
    model_used: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="messages")


class SafetyEvent(Base):
    __tablename__ = "safety_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), index=True, nullable=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel))
    risk_type: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)
    requires_crisis_response: Mapped[bool] = mapped_column(default=False)
    requires_professional_referral: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="safety_events")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ModelCall(Base):
    __tablename__ = "model_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[str] = mapped_column(String(128))
    latency_ms: Mapped[int] = mapped_column(Integer)
    prompt_tokens: Mapped[int] = mapped_column(Integer)
    completion_tokens: Mapped[int] = mapped_column(Integer)
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
