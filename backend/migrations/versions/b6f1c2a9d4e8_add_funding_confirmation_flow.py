"""Add funding confirmation flow.

Revision ID: b6f1c2a9d4e8
Revises: a4f8c2d9e1b0
Create Date: 2026-06-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "b6f1c2a9d4e8"
down_revision = "a4f8c2d9e1b0"
branch_labels = None
depends_on = None


TABLE_NAME = "loans"


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = inspector.get_columns(table_name)

    return any(column.get("name") == column_name for column in columns)


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = inspector.get_indexes(table_name)

    return any(index.get("name") == index_name for index in indexes)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            sa.text(
                "ALTER TYPE loan_status ADD VALUE IF NOT EXISTS 'FUNDING_PENDING'"
            )
        )

    if not _column_exists(TABLE_NAME, "funding_activation_code_hash"):
        op.add_column(
            TABLE_NAME,
            sa.Column(
                "funding_activation_code_hash",
                sa.String(length=128),
                nullable=True,
            ),
        )

    if not _column_exists(TABLE_NAME, "funding_activation_code_generated_at"):
        op.add_column(
            TABLE_NAME,
            sa.Column(
                "funding_activation_code_generated_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )

    if not _column_exists(TABLE_NAME, "funding_activation_code_generated_by_user_id"):
        op.add_column(
            TABLE_NAME,
            sa.Column(
                "funding_activation_code_generated_by_user_id",
                sa.Integer(),
                sa.ForeignKey(
                    "users.id",
                    ondelete="SET NULL",
                ),
                nullable=True,
            ),
        )

    if not _column_exists(TABLE_NAME, "funding_activation_code_attempts"):
        op.add_column(
            TABLE_NAME,
            sa.Column(
                "funding_activation_code_attempts",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    if not _column_exists(TABLE_NAME, "lender_confirmed_at"):
        op.add_column(
            TABLE_NAME,
            sa.Column(
                "lender_confirmed_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )

    if not _column_exists(TABLE_NAME, "borrower_received_at"):
        op.add_column(
            TABLE_NAME,
            sa.Column(
                "borrower_received_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )

    if not _column_exists(TABLE_NAME, "borrower_received_by_user_id"):
        op.add_column(
            TABLE_NAME,
            sa.Column(
                "borrower_received_by_user_id",
                sa.Integer(),
                sa.ForeignKey(
                    "users.id",
                    ondelete="SET NULL",
                ),
                nullable=True,
            ),
        )

    if not _index_exists(
        TABLE_NAME,
        "ix_loans_funding_activation_code_generated_by_user_id",
    ):
        op.create_index(
            "ix_loans_funding_activation_code_generated_by_user_id",
            TABLE_NAME,
            ["funding_activation_code_generated_by_user_id"],
            unique=False,
        )

    if not _index_exists(
        TABLE_NAME,
        "ix_loans_borrower_received_by_user_id",
    ):
        op.create_index(
            "ix_loans_borrower_received_by_user_id",
            TABLE_NAME,
            ["borrower_received_by_user_id"],
            unique=False,
        )


def downgrade() -> None:
    if _index_exists(
        TABLE_NAME,
        "ix_loans_borrower_received_by_user_id",
    ):
        op.drop_index(
            "ix_loans_borrower_received_by_user_id",
            table_name=TABLE_NAME,
        )

    if _index_exists(
        TABLE_NAME,
        "ix_loans_funding_activation_code_generated_by_user_id",
    ):
        op.drop_index(
            "ix_loans_funding_activation_code_generated_by_user_id",
            table_name=TABLE_NAME,
        )

    columns = [
        "borrower_received_by_user_id",
        "borrower_received_at",
        "lender_confirmed_at",
        "funding_activation_code_attempts",
        "funding_activation_code_generated_by_user_id",
        "funding_activation_code_generated_at",
        "funding_activation_code_hash",
    ]

    for column_name in columns:
        if _column_exists(TABLE_NAME, column_name):
            op.drop_column(
                TABLE_NAME,
                column_name,
            )