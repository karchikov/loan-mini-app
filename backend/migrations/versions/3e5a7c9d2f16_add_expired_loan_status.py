"""add expired loan status

Revision ID: 3e5a7c9d2f16
Revises: d8f3a2b7c9e1
Create Date: 2026-06-23 18:17:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "3e5a7c9d2f16"
down_revision: Union[str, Sequence[str], None] = "d8f3a2b7c9e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE loan_status ADD VALUE IF NOT EXISTS 'EXPIRED'"
    )


def downgrade() -> None:
    pass
