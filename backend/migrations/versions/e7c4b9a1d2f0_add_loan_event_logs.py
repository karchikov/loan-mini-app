"""Add loan event logs.

Revision ID: e7c4b9a1d2f0
Revises: b6f1c2a9d4e8
Create Date: 2026-06-29
"""

from alembic import op


revision = "e7c4b9a1d2f0"
down_revision = "b6f1c2a9d4e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS loan_event_logs (
            id BIGSERIAL PRIMARY KEY,
            loan_id INTEGER NOT NULL,
            actor_user_id INTEGER NULL,
            actor_role VARCHAR(50) NULL,
            event_type VARCHAR(100) NOT NULL,
            old_status VARCHAR(50) NULL,
            new_status VARCHAR(50) NULL,
            telegram_id_snapshot BIGINT NULL,
            username_snapshot VARCHAR(255) NULL,
            first_name_snapshot VARCHAR(255) NULL,
            ip_address VARCHAR(100) NULL,
            user_agent TEXT NULL,
            metadata JSONB NULL,
            previous_event_hash VARCHAR(64) NULL,
            event_hash VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_loan_event_logs_actor_user_id
        ON loan_event_logs (actor_user_id);
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_loan_event_logs_event_type
        ON loan_event_logs (event_type);
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_loan_event_logs_previous_event_hash
        ON loan_event_logs (previous_event_hash);
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_loan_event_logs_event_hash
        ON loan_event_logs (event_hash);
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_loan_event_logs_loan_created_at
        ON loan_event_logs (loan_id, created_at);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS loan_event_logs;")