from datetime import date, datetime
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
    FUNDING_PENDING = "funding_pending"
    ACTIVE = "active"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class RepaymentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
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
    due_date: datetime = Field(
        description="Loan due date is required",
    )

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


class LoanActivationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activation_code: str = Field(
        min_length=4,
        max_length=4,
        description="4-digit funding activation code",
    )

    @field_validator("activation_code")
    @classmethod
    def validate_activation_code(cls, value: str) -> str:
        normalized_value = value.strip()

        if len(normalized_value) != 4 or not normalized_value.isdigit():
            raise ValueError("Activation code must contain exactly 4 digits")

        return normalized_value


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
    interest_amount: Decimal
    principal_amount: Decimal
    status: RepaymentStatus
    submitted_by_user_id: int | None = None
    confirmed_at: datetime | None = None
    confirmed_by_user_id: int | None = None
    rejected_at: datetime | None = None
    rejected_by_user_id: int | None = None
    created_at: datetime


class LoanInterestLedgerResponse(BaseModel):
    id: int
    loan_id: int
    accrual_date: date
    principal_amount: Decimal
    annual_interest_rate: Decimal
    interest_amount: Decimal
    paid_amount: Decimal
    unpaid_interest_amount: Decimal
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

    lender_confirmed_at: datetime | None = None
    funding_activation_code_generated_at: datetime | None = None
    funding_activation_code_generated_by_user_id: int | None = None
    funding_activation_code_attempts: int = 0
    borrower_received_at: datetime | None = None
    borrower_received_by_user_id: int | None = None

    created_at: datetime
    updated_at: datetime

    remaining_balance: Decimal


class LoanFundingActivationCodeResponse(BaseModel):
    loan: LoanResponse
    activation_code: str = Field(
        min_length=4,
        max_length=4,
        description="4-digit funding activation code. Returned only once.",
    )