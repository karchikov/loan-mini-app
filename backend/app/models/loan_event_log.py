from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LoanEventLog(Base):
    __tablename__ = "loan_event_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    loan_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    actor_user_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    actor_role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    old_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    new_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    telegram_id_snapshot: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    username_snapshot: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    first_name_snapshot: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    event_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )

    previous_event_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    event_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


Index(
    "ix_loan_event_logs_actor_user_id",
    LoanEventLog.actor_user_id,
)

Index(
    "ix_loan_event_logs_event_type",
    LoanEventLog.event_type,
)

Index(
    "ix_loan_event_logs_previous_event_hash",
    LoanEventLog.previous_event_hash,
)

Index(
    "ix_loan_event_logs_event_hash",
    LoanEventLog.event_hash,
    unique=True,
)

Index(
    "ix_loan_event_logs_loan_created_at",
    LoanEventLog.loan_id,
    LoanEventLog.created_at,
)