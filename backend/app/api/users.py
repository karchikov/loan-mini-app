from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_admin
from app.database import get_db
from app.models.loan import Loan, LoanStatus
from app.models.repayment import Repayment
from app.models.user import User
from app.schemas.user import (
    UserHistoryItemResponse,
    UserRead,
    UserSummaryResponse,
)

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


def format_user_name(user: User | None) -> str:
    if user is None:
        return "Пользователь"

    name = user.first_name or f"User #{user.id}"

    if user.username:
        return f"{name} (@{user.username})"

    return name


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
            or_(
                Loan.borrower_id == current_user.id,
                Loan.lender_id == current_user.id,
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


@router.get(
    "/users/me/history",
    response_model=list[UserHistoryItemResponse],
)
def get_my_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    history = []

    loans_result = db.execute(
        select(Loan)
        .options(
            joinedload(Loan.lender),
            joinedload(Loan.borrower),
        )
        .where(
            or_(
                Loan.borrower_id == current_user.id,
                Loan.lender_id == current_user.id,
            )
        )
    )

    loans = loans_result.scalars().all()

    for loan in loans:
        borrower_name = format_user_name(loan.borrower)
        lender_name = format_user_name(loan.lender)

        history.append(
            UserHistoryItemResponse(
                id=f"loan-{loan.id}-created",
                type="loan_created",
                title="Создан займ",
                description=(
                    f"{borrower_name} получил займ "
                    f"от {lender_name}"
                ),
                amount=loan.amount,
                created_at=loan.created_at,
            )
        )

        if loan.status == LoanStatus.PAID:
            history.append(
                UserHistoryItemResponse(
                    id=f"loan-{loan.id}-paid",
                    type="loan_paid",
                    title="Займ погашен",
                    description=f"Займ #{loan.id} полностью погашен",
                    amount=loan.amount,
                    created_at=loan.updated_at,
                )
            )

        if loan.status == LoanStatus.REJECTED:
            history.append(
                UserHistoryItemResponse(
                    id=f"loan-{loan.id}-rejected",
                    type="loan_rejected",
                    title="Займ отклонён",
                    description=f"Займ #{loan.id} был отклонён",
                    amount=loan.amount,
                    created_at=loan.updated_at,
                )
            )

    repayments_result = db.execute(
        select(Repayment)
        .join(Loan)
        .where(
            or_(
                Loan.borrower_id == current_user.id,
                Loan.lender_id == current_user.id,
            )
        )
        .order_by(
            Repayment.created_at.desc()
        )
    )

    repayments = repayments_result.scalars().all()

    for repayment in repayments:
        history.append(
            UserHistoryItemResponse(
                id=f"repayment-{repayment.id}",
                type="repayment",
                title="Платёж по займу",
                description=f"Платёж по займу #{repayment.loan_id}",
                amount=repayment.amount,
                created_at=repayment.created_at,
            )
        )

    history.sort(
        key=lambda item: item.created_at,
        reverse=True,
    )

    return history[:30]


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