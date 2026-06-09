from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.database import get_db
from app.models.loan import Loan, LoanStatus
from app.models.user import User
from app.schemas.user import UserRead, UserSummaryResponse

router = APIRouter(tags=["users"])


ACTIVE_LOAN_STATUSES = [
    LoanStatus.ACTIVE,
    LoanStatus.PARTIALLY_PAID,
]


def calculate_sum(
    db: Session,
    user_id: int,
    column,
):
    result = db.execute(
        select(
            func.coalesce(
                func.sum(Loan.amount),
                0,
            )
        ).where(
            column == user_id,
            Loan.status.in_(ACTIVE_LOAN_STATUSES),
        )
    )

    value = result.scalar_one()

    return Decimal(value)


@router.get("/me", response_model=UserRead)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.get("/users/me/summary", response_model=UserSummaryResponse)
def get_my_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    my_debts = calculate_sum(
        db=db,
        user_id=current_user.id,
        column=Loan.borrower_id,
    )

    owed_to_me = calculate_sum(
        db=db,
        user_id=current_user.id,
        column=Loan.lender_id,
    )

    active_loans_count_result = db.execute(
        select(
            func.count(Loan.id)
        ).where(
            Loan.status.in_(ACTIVE_LOAN_STATUSES),
            (
                (Loan.borrower_id == current_user.id)
                | (Loan.lender_id == current_user.id)
            ),
        )
    )

    active_loans_count = active_loans_count_result.scalar_one()

    return UserSummaryResponse(
        my_debts=my_debts,
        owed_to_me=owed_to_me,
        balance=owed_to_me - my_debts,
        active_loans_count=active_loans_count,
    )


@router.get("/users", response_model=list[UserRead])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = db.execute(
        select(User)
        .where(User.id != current_user.id)
        .order_by(User.id.asc())
    )

    return result.scalars().all()