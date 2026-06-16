from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.loan import LoanStatus
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


class DashboardLoanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int

    lender_id: int
    borrower_id: int

    lender: UserShortResponse
    borrower: UserShortResponse

    amount: Decimal
    description: str | None
    status: LoanStatus
    remaining_balance: Decimal


class DashboardResponse(BaseModel):
    user: DashboardUserResponse
    loans: list[DashboardLoanResponse]
    summary: UserSummaryResponse
    history: list[UserHistoryItemResponse]
    available_lenders: list[DashboardAvailableLenderResponse]
