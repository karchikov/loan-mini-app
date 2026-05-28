import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class LoanStatus(str, enum.Enum):
    DRAFT = "draft"
    WAITING_CONFIRMATION = "waiting_confirmation"
    ACTIVE = "active"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"
    REJECTED = "rejected"


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    lender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    borrower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="RUB",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[LoanStatus] = mapped_column(
        Enum(LoanStatus, name="loan_status"),
        nullable=False,
        default=LoanStatus.DRAFT,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    lender = relationship(
        "User",
        foreign_keys=[lender_id],
        back_populates="loans_given",
    )

    borrower = relationship(
        "User",
        foreign_keys=[borrower_id],
        back_populates="loans_taken",
    )

    repayments = relationship(
        "Repayment",
        back_populates="loan",
        cascade="all, delete-orphan",
    )