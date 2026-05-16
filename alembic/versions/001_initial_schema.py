"""Initial schema — all tables.

Revision ID: 001
Revises:
Create Date: 2026-05-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_risklevel = sa.Enum(
    "NO_RISK",
    "MILD_DISTRESS",
    "ELEVATED_DISTRESS",
    "POSSIBLE_CRISIS",
    "IMMINENT_RISK",
    name="risklevel",
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(128), nullable=True),
        sa.Column("first_name", sa.String(128), nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="ru"),
        sa.Column("region", sa.String(64), nullable=True),
        sa.Column("style_preference", sa.String(32), nullable=False, server_default="soft"),
        sa.Column("consent_given", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("consent_accepted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "mood_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("mood_score", sa.Integer(), nullable=False),
        sa.Column("anxiety_score", sa.Integer(), nullable=False),
        sa.Column("energy_score", sa.Integer(), nullable=False),
        sa.Column("sleep_hours", sa.Float(), nullable=True),
        sa.Column("main_emotion", sa.String(64), nullable=True),
        sa.Column("trigger", sa.Text(), nullable=True),
        sa.Column("thought", sa.Text(), nullable=True),
        sa.Column("action_done", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mood_entries_user_id", "mood_entries", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_used", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_user_id", "messages", ["user_id"])

    op.create_table(
        "safety_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("risk_level", _risklevel, nullable=False),
        sa.Column("risk_type", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("requires_crisis_response", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_professional_referral", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_safety_events_user_id", "safety_events", ["user_id"])
    op.create_index("ix_safety_events_telegram_user_id", "safety_events", ["telegram_user_id"])
    op.create_index("ix_safety_events_created_at", "safety_events", ["created_at"])

    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_user_id", "feedback", ["user_id"])

    op.create_table(
        "model_calls",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_id", sa.String(128), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("model_calls")
    op.drop_index("ix_feedback_user_id", table_name="feedback")
    op.drop_table("feedback")
    op.drop_index("ix_safety_events_created_at", table_name="safety_events")
    op.drop_index("ix_safety_events_telegram_user_id", table_name="safety_events")
    op.drop_index("ix_safety_events_user_id", table_name="safety_events")
    op.drop_table("safety_events")
    op.drop_index("ix_messages_user_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_mood_entries_user_id", table_name="mood_entries")
    op.drop_table("mood_entries")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
    _risklevel.drop(op.get_bind(), checkfirst=True)
