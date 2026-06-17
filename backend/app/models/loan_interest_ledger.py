import enum
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class LoanInterestLedger(Base):
    __tablename__ = "loan_interest_ledger"

    __table_args__ = (
        UniqueConstraint(
            "loan_id",
            "accrual_date",
            name="uq_loan_interest_ledger_loan_date",
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

    accrual_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    principal_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    annual_interest_rate: Mapped[Decimal] = mapped_column(
        Numeric(7, 2),
        nullable=False,
    )

    interest_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    loan = relationship(
        "Loan",
        backref="interest_ledgers",
    )