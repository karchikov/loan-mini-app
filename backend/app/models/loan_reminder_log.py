from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LoanReminderLog(Base):
    __tablename__ = "loan_reminder_logs"

    __table_args__ = (
        UniqueConstraint(
            "loan_id",
            "reminder_type",
            "reminder_date",
            name="uq_loan_reminder_log",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    loan_id: Mapped[int] = mapped_column(
        ForeignKey("loans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reminder_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    reminder_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )