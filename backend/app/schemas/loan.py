from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict


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
    borrower_id: int
    amount: Decimal
    currency: str = "RUB"
    description: str | None = None
    due_date: datetime | None = None


class LoanCreate(LoanBase):
    pass


class RepaymentCreate(BaseModel):
    amount: Decimal


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

    amount: Decimal
    currency: str

    description: str | None
    due_date: datetime | None

    status: LoanStatus

    created_at: datetime
    updated_at: datetime

    remaining_balance: Decimal