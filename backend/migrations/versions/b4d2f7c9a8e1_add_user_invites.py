"""add user invites

Revision ID: b4d2f7c9a8e1
Revises: 7b1979250835
Create Date: 2026-06-10 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4d2f7c9a8e1"
down_revision: Union[str, Sequence[str], None] = "7b1979250835"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("invite_code", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("invited_by_user_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_users_invite_code"), "users", ["invite_code"], unique=True)
    op.create_index(op.f("ix_users_invited_by_user_id"), "users", ["invited_by_user_id"], unique=False)
    op.create_foreign_key(
        "fk_users_invited_by_user_id_users",
        "users",
        "users",
        ["invited_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_invited_by_user_id_users", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_invited_by_user_id"), table_name="users")
    op.drop_index(op.f("ix_users_invite_code"), table_name="users")
    op.drop_column("users", "invited_by_user_id")
    op.drop_column("users", "invite_code")