"""add annual interest rate to loans

Revision ID: c2f4a9d8e6b1
Revises: b4d2f7c9a8e1
Create Date: 2026-06-17 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2f4a9d8e6b1"
down_revision: Union[str, Sequence[str], None] = "b4d2f7c9a8e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "loans",
        sa.Column(
            "annual_interest_rate",
            sa.Numeric(7, 2),
            nullable=False,
            server_default="0.00",
        ),
    )


def downgrade() -> None:
    op.drop_column("loans", "annual_interest_rate")