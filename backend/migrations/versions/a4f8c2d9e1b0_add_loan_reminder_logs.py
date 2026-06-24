"""Add loan reminder logs table.

Revision ID: a4f8c2d9e1b0
Revises: 3e5a7c9d2f16
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "a4f8c2d9e1b0"
down_revision = "3e5a7c9d2f16"
branch_labels = None
depends_on = None


TABLE_NAME = "loan_reminder_logs"


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(index.get("name") == index_name for index in indexes)


def upgrade() -> None:
    if _table_exists(TABLE_NAME):
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("loan_id", sa.Integer(), nullable=False),
        sa.Column("reminder_type", sa.String(length=50), nullable=False),
        sa.Column("reminder_date", sa.Date(), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["loan_id"],
            ["loans.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "loan_id",
            "reminder_type",
            "reminder_date",
            name="uq_loan_reminder_log",
        ),
    )

    op.create_index(
        "ix_loan_reminder_logs_id",
        TABLE_NAME,
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_loan_reminder_logs_loan_id",
        TABLE_NAME,
        ["loan_id"],
        unique=False,
    )
    op.create_index(
        "ix_loan_reminder_logs_reminder_type",
        TABLE_NAME,
        ["reminder_type"],
        unique=False,
    )
    op.create_index(
        "ix_loan_reminder_logs_reminder_date",
        TABLE_NAME,
        ["reminder_date"],
        unique=False,
    )


def downgrade() -> None:
    if not _table_exists(TABLE_NAME):
        return

    index_names = [
        "ix_loan_reminder_logs_reminder_date",
        "ix_loan_reminder_logs_reminder_type",
        "ix_loan_reminder_logs_loan_id",
        "ix_loan_reminder_logs_id",
    ]

    for index_name in index_names:
        if _index_exists(TABLE_NAME, index_name):
            op.drop_index(index_name, table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)
