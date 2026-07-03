"""Add user contact aliases.

Revision ID: c8d1f4a7b9e2
Revises: e7c4b9a1d2f0
Create Date: 2026-07-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "c8d1f4a7b9e2"
down_revision = "e7c4b9a1d2f0"
branch_labels = None
depends_on = None


TABLE_NAME = "user_contact_aliases"


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
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("contact_user_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["contact_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_user_id",
            "contact_user_id",
            name="uq_user_contact_alias_owner_contact",
        ),
    )

    op.create_index(
        "ix_user_contact_aliases_id",
        TABLE_NAME,
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_user_contact_aliases_owner_user_id",
        TABLE_NAME,
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_contact_aliases_contact_user_id",
        TABLE_NAME,
        ["contact_user_id"],
        unique=False,
    )


def downgrade() -> None:
    if not _table_exists(TABLE_NAME):
        return

    index_names = [
        "ix_user_contact_aliases_contact_user_id",
        "ix_user_contact_aliases_owner_user_id",
        "ix_user_contact_aliases_id",
    ]

    for index_name in index_names:
        if _index_exists(TABLE_NAME, index_name):
            op.drop_index(index_name, table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)
