from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
    )

    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    first_name: Mapped[str] = mapped_column(
        String(255),
    )

    last_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="user",
        server_default="user",
    )

    loans_given = relationship(
        "Loan",
        foreign_keys="Loan.lender_id",
        back_populates="lender",
        cascade="all, delete-orphan",
    )

    loans_taken = relationship(
        "Loan",
        foreign_keys="Loan.borrower_id",
        back_populates="borrower",
        cascade="all, delete-orphan",
    )