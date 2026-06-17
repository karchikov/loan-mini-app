from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.user import UserShortResponse


ALLOWED_CURRENCIES = {
    "RUB",
    "USD",
    "USDT",
    "USDC",
}


class LoanStatus(str, Enum):
    DRAFT = "draft"
    WAITING_CONFIRMATION = "waiting_confirmation"
    ACTIVE = "active"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"
    REJECTED = "rejected"


class LoanBase(BaseModel):
    amount: Decimal = Field(
        gt=0,
        description="Loan amount must be greater than zero",
    )

    annual_interest_rate: Decimal = Field(
        ge=0,
        le=1000,
        description="Annual interest rate must be between 0 and 1000 percent",
    )

    currency: str = "RUB"
    description: str | None = None
    due_date: datetime | None = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        normalized_value = value.strip().upper()

        if normalized_value not in ALLOWED_CURRENCIES:
            raise ValueError(
                "Currency must be one of: RUB, USD, USDT, USDC"
            )

        return normalized_value


class LoanCreate(LoanBase):
    model_config = ConfigDict(extra="forbid")

    lender_id: int = Field(
        gt=0,
        description="Selected lender user id",
    )


class RepaymentCreate(BaseModel):
    amount: Decimal = Field(
        gt=0,
        description="Repayment amount must be greater than zero",
    )


class RepaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    loan_id: int
    amount: Decimal
    created_at: datetime


class LoanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int

    lender_id: int
    borrower_id: int

    lender: UserShortResponse
    borrower: UserShortResponse

    amount: Decimal
    annual_interest_rate: Decimal
    currency: str

    description: str | None
    due_date: datetime | None

    status: LoanStatus

    created_at: datetime
    updated_at: datetime

    remaining_balance: Decimal