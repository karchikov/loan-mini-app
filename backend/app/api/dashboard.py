from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User

from app.schemas.dashboard import DashboardResponse

from app.api.users import (
    get_available_lenders,
    get_my_history,
    get_my_summary,
)

from app.services.loan_service import get_user_loans


router = APIRouter(
    tags=["dashboard"]
)


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loans = get_user_loans(
        db=db,
        current_user=current_user,
    )

    summary = get_my_summary(
        db=db,
        current_user=current_user,
    )

    history = get_my_history(
        db=db,
        current_user=current_user,
    )

    available_lenders = get_available_lenders(
        db=db,
        current_user=current_user,
    )

    return DashboardResponse(
        user=current_user,
        loans=loans,
        summary=summary,
        history=history,
        available_lenders=available_lenders,
    )