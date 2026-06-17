"""add loan interest ledger

Revision ID: 6752b66db2d1
Revises: c2f4a9d8e6b1
Create Date: 2026-06-17 21:01:33.191393
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6752b66db2d1"
down_revision: Union[str, Sequence[str], None] = "c2f4a9d8e6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "loan_interest_ledger",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("loan_id", sa.Integer(), sa.ForeignKey("loans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("accrual_date", sa.Date(), nullable=False),
        sa.Column("principal_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("annual_interest_rate", sa.Numeric(7, 2), nullable=False),
        sa.Column("interest_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "loan_id",
            "accrual_date",
            name="uq_loan_interest_ledger_loan_date",
        ),
    )

    op.create_index(
        "ix_loan_interest_ledger_loan_id",
        "loan_interest_ledger",
        ["loan_id"],
    )

    op.create_index(
        "ix_loan_interest_ledger_accrual_date",
        "loan_interest_ledger",
        ["accrual_date"],
    )


def downgrade() -> None:
    op.drop_table("loan_interest_ledger")