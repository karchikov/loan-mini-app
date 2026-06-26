from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.loan import LoanStatus, RepaymentStatus
from app.schemas.user import (
    UserHistoryItemResponse,
    UserShortResponse,
    UserSummaryResponse,
)


class DashboardUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str | None = None
    first_name: str | None = None
    role: str = "user"


class DashboardAvailableLenderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class DashboardPendingRepaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    loan_id: int
    amount: Decimal
    status: RepaymentStatus
    submitted_by_user_id: int | None = None
    created_at: datetime


class DashboardLoanResponse(BaseModel):
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
    status: LoanStatus

    created_at: datetime
    updated_at: datetime
    due_date: date | datetime | None = None

    lender_confirmed_at: datetime | None = None
    funding_activation_code_generated_at: datetime | None = None
    funding_activation_code_generated_by_user_id: int | None = None
    funding_activation_code_attempts: int = 0
    borrower_received_at: datetime | None = None
    borrower_received_by_user_id: int | None = None

    principal_remaining: Decimal = Decimal("0.00")
    unpaid_interest: Decimal = Decimal("0.00")
    remaining_balance: Decimal

    last_interest_accrual_date: date | None = None

    pending_repayments_count: int = 0
    pending_repayments_total: Decimal = Decimal("0.00")
    pending_repayments: list[DashboardPendingRepaymentResponse] = Field(
        default_factory=list
    )


class DashboardResponse(BaseModel):
    user: DashboardUserResponse
    loans: list[DashboardLoanResponse]
    summary: UserSummaryResponse
    history: list[UserHistoryItemResponse]
    available_lenders: list[DashboardAvailableLenderResponse]