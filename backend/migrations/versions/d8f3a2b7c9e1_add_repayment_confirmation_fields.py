"""add repayment confirmation fields

Revision ID: d8f3a2b7c9e1
Revises: 9f2b6c8d1a7e
Create Date: 2026-06-19 18:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d8f3a2b7c9e1"
down_revision: Union[str, Sequence[str], None] = "9f2b6c8d1a7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


repayment_status_enum = postgresql.ENUM(
    "pending",
    "confirmed",
    "rejected",
    name="repayment_status",
)


def upgrade() -> None:
    bind = op.get_bind()

    repayment_status_enum.create(
        bind,
        checkfirst=True,
    )

    op.add_column(
        "repayments",
        sa.Column(
            "status",
            repayment_status_enum,
            nullable=False,
            server_default="confirmed",
        ),
    )

    op.alter_column(
        "repayments",
        "status",
        server_default="pending",
    )

    op.add_column(
        "repayments",
        sa.Column(
            "submitted_by_user_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
    )

    op.add_column(
        "repayments",
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "repayments",
        sa.Column(
            "confirmed_by_user_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
    )

    op.add_column(
        "repayments",
        sa.Column(
            "rejected_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "repayments",
        sa.Column(
            "rejected_by_user_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_repayments_status",
        "repayments",
        ["status"],
    )

    op.create_index(
        "ix_repayments_submitted_by_user_id",
        "repayments",
        ["submitted_by_user_id"],
    )

    op.create_index(
        "ix_repayments_confirmed_by_user_id",
        "repayments",
        ["confirmed_by_user_id"],
    )

    op.create_index(
        "ix_repayments_rejected_by_user_id",
        "repayments",
        ["rejected_by_user_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(
        "ix_repayments_rejected_by_user_id",
        table_name="repayments",
    )

    op.drop_index(
        "ix_repayments_confirmed_by_user_id",
        table_name="repayments",
    )

    op.drop_index(
        "ix_repayments_submitted_by_user_id",
        table_name="repayments",
    )

    op.drop_index(
        "ix_repayments_status",
        table_name="repayments",
    )

    op.drop_column(
        "repayments",
        "rejected_by_user_id",
    )

    op.drop_column(
        "repayments",
        "rejected_at",
    )

    op.drop_column(
        "repayments",
        "confirmed_by_user_id",
    )

    op.drop_column(
        "repayments",
        "confirmed_at",
    )

    op.drop_column(
        "repayments",
        "submitted_by_user_id",
    )

    op.drop_column(
        "repayments",
        "status",
    )

    repayment_status_enum.drop(
        bind,
        checkfirst=True,
    )