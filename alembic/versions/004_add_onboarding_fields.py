"""Add onboarding profile fields to users table.

Revision ID: 004
Revises: 003
Create Date: 2026-05-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("gender", sa.String(32), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "consultant_gender",
            sa.String(32),
            nullable=False,
            server_default="female",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed")
    op.drop_column("users", "consultant_gender")
    op.drop_column("users", "gender")
    op.drop_column("users", "display_name")
