"""Make safety_events.telegram_user_id nullable for data deletion.

Revision ID: 002
Revises: 001
Create Date: 2026-05-15

Privacy: delete_user_data() intentionally nullifies this column so that no
direct Telegram identifier survives a user's right-to-erasure request.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "safety_events",
        "telegram_user_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )


def downgrade() -> None:
    # WARNING: this downgrade will fail if any rows have telegram_user_id = NULL.
    # Rows are intentionally nullified by delete_user_data() to honour the right
    # to erasure.  Manually back-fill or remove NULL rows before downgrading.
    op.alter_column(
        "safety_events",
        "telegram_user_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
