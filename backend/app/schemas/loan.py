from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserShortResponse


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

    currency: str = "RUB"
    description: str | None = None
    due_date: datetime | None = None


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
    currency: str

    description: str | None
    due_date: datetime | None

    status: LoanStatus

    created_at: datetime
    updated_at: datetime

    remaining_balance: Decimal