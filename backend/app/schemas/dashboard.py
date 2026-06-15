from app.schemas.loan import LoanResponse
from app.schemas.user import (
    UserHistoryItemResponse,
    UserNetworkRead,
    UserRead,
    UserSummaryResponse,
)

from pydantic import BaseModel


class DashboardResponse(BaseModel):
    user: UserRead
    loans: list[LoanResponse]
    summary: UserSummaryResponse
    history: list[UserHistoryItemResponse]
    available_lenders: list[UserNetworkRead]