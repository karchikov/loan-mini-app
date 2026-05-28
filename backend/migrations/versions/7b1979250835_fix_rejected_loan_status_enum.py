"""fix rejected loan status enum

Revision ID: 7b1979250835
Revises: a70b7e3d17de
Create Date: 2026-05-27 13:41:39.167498
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "7b1979250835"

down_revision: Union[str, Sequence[str], None] = "a70b7e3d17de"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE loan_status ADD VALUE IF NOT EXISTS 'REJECTED'"
    )


def downgrade() -> None:
    pass