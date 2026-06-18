"""add interest first repayment fields

Revision ID: 9f2b6c8d1a7e
Revises: 6752b66db2d1
Create Date: 2026-06-18 15:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f2b6c8d1a7e"
down_revision: Union[str, Sequence[str], None] = "6752b66db2d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "repayments",
        sa.Column(
            "interest_amount",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0.00",
        ),
    )

    op.add_column(
        "repayments",
        sa.Column(
            "principal_amount",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0.00",
        ),
    )

    op.execute(
        """
        UPDATE repayments
        SET
            interest_amount = 0.00,
            principal_amount = amount
        """
    )

    op.add_column(
        "loan_interest_ledger",
        sa.Column(
            "paid_amount",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0.00",
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "loan_interest_ledger",
        "paid_amount",
    )

    op.drop_column(
        "repayments",
        "principal_amount",
    )

    op.drop_column(
        "repayments",
        "interest_amount",
    )