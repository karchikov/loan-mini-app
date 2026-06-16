from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.database import get_db
from app.models.loan import Loan, LoanStatus
from app.models.repayment import Repayment
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.schemas.user import UserHistoryItemResponse, UserSummaryResponse


router = APIRouter(
    tags=["dashboard"]
)


ACTIVE_LOAN_STATUSES = [
    LoanStatus.ACTIVE,
    LoanStatus.PARTIALLY_PAID,
]


def is_admin(user: User) -> bool:
    return user.role == "admin"


def loan_belongs_to_user(user_id: int):
    return or_(
        Loan.lender_id == user_id,
        Loan.borrower_id == user_id,
    )


def to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")

    return Decimal(value)


def format_user_name(user: User | None) -> str:
    if user is None:
        return "\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c"

    name = user.first_name or f"User #{user.id}"

    if user.username:
        return f"{name} (@{user.username})"

    return name


def get_dashboard_loans(
    db: Session,
    current_user: User,
) -> list[Loan]:
    repayment_totals = (
        select(
            Repayment.loan_id.label("loan_id"),
            func.coalesce(
                func.sum(Repayment.amount),
                0,
            ).label("total_paid"),
        )
        .group_by(Repayment.loan_id)
        .subquery()
    )

    query = (
        select(
            Loan,
            func.coalesce(
                repayment_totals.c.total_paid,
                0,
            ).label("total_paid"),
        )
        .outerjoin(
            repayment_totals,
            repayment_totals.c.loan_id == Loan.id,
        )
        .options(
            joinedload(Loan.lender),
            joinedload(Loan.borrower),
        )
        .order_by(Loan.id.desc())
    )

    if not is_admin(current_user):
        query = query.where(
            loan_belongs_to_user(current_user.id)
        )

    result = db.execute(query)

    loans = []

    for loan, total_paid in result.all():
        remaining_balance = loan.amount - to_decimal(total_paid)

        if remaining_balance < 0:
            remaining_balance = Decimal("0")

        loan.remaining_balance = remaining_balance
        loans.append(loan)

    return loans


def get_dashboard_summary(
    db: Session,
    current_user: User,
) -> UserSummaryResponse:
    result = db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            Loan.borrower_id == current_user.id,
                            Loan.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("my_debts"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Loan.lender_id == current_user.id,
                            Loan.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("owed_to_me"),
            func.count(Loan.id).label("active_loans_count"),
        ).where(
            Loan.status.in_(ACTIVE_LOAN_STATUSES),
            loan_belongs_to_user(current_user.id),
        )
    )

    row = result.one()

    my_debts = to_decimal(row.my_debts)
    owed_to_me = to_decimal(row.owed_to_me)

    return UserSummaryResponse(
        my_debts=my_debts,
        owed_to_me=owed_to_me,
        balance=owed_to_me - my_debts,
        active_loans_count=row.active_loans_count,
    )


def get_dashboard_repayments_history(
    db: Session,
    current_user: User,
) -> list[Repayment]:
    result = db.execute(
        select(Repayment)
        .join(Loan)
        .where(
            loan_belongs_to_user(current_user.id)
        )
        .order_by(
            Repayment.created_at.desc()
        )
        .limit(30)
    )

    return result.scalars().all()


def get_dashboard_available_lenders(
    db: Session,
    current_user: User,
) -> list[User]:
    network_conditions = [
        User.invited_by_user_id == current_user.id,
    ]

    if current_user.invited_by_user_id is not None:
        network_conditions.append(
            User.id == current_user.invited_by_user_id
        )

    result = db.execute(
        select(User)
        .where(
            User.id != current_user.id,
            or_(*network_conditions),
        )
        .order_by(
            User.first_name.asc(),
            User.id.asc(),
        )
    )

    return result.scalars().all()


def build_dashboard_history(
    loans: list[Loan],
    repayments: list[Repayment],
    current_user: User,
) -> list[UserHistoryItemResponse]:
    history = []
    user_loans = [
        loan
        for loan in loans
        if (
            loan.borrower_id == current_user.id
            or loan.lender_id == current_user.id
        )
    ]

    for loan in user_loans:
        borrower_name = format_user_name(loan.borrower)
        lender_name = format_user_name(loan.lender)

        history.append(
            UserHistoryItemResponse(
                id=f"loan-{loan.id}-created",
                type="loan_created",
                title=(
                    "\u0421\u043e\u0437\u0434\u0430\u043d\u0430 "
                    "\u0437\u0430\u044f\u0432\u043a\u0430 "
                    "\u043d\u0430 \u0437\u0430\u0439\u043c"
                ),
                description=(
                    f"{borrower_name} "
                    "\u0437\u0430\u043f\u0440\u043e\u0441\u0438\u043b "
                    "\u0437\u0430\u0439\u043c \u0443 "
                    f"{lender_name}"
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
                    title=(
                        "\u0417\u0430\u0439\u043c "
                        "\u043f\u043e\u0433\u0430\u0448\u0435\u043d"
                    ),
                    description=(
                        "\u0417\u0430\u0439\u043c "
                        f"#{loan.id}"
                        " \u043f\u043e\u043b\u043d\u043e\u0441\u0442\u044c\u044e "
                        "\u043f\u043e\u0433\u0430\u0448\u0435\u043d"
                    ),
                    amount=loan.amount,
                    created_at=loan.updated_at,
                )
            )

        if loan.status == LoanStatus.REJECTED:
            history.append(
                UserHistoryItemResponse(
                    id=f"loan-{loan.id}-rejected",
                    type="loan_rejected",
                    title=(
                        "\u0417\u0430\u0439\u043c "
                        "\u043e\u0442\u043a\u043b\u043e\u043d\u0451\u043d"
                    ),
                    description=(
                        "\u0417\u0430\u0439\u043c "
                        f"#{loan.id}"
                        " \u0431\u044b\u043b "
                        "\u043e\u0442\u043a\u043b\u043e\u043d\u0451\u043d"
                    ),
                    amount=loan.amount,
                    created_at=loan.updated_at,
                )
            )

    for repayment in repayments:
        history.append(
            UserHistoryItemResponse(
                id=f"repayment-{repayment.id}",
                type="repayment",
                title=(
                    "\u041f\u043b\u0430\u0442\u0451\u0436 "
                    "\u043f\u043e \u0437\u0430\u0439\u043c\u0443"
                ),
                description=(
                    "\u041f\u043b\u0430\u0442\u0451\u0436 "
                    "\u043f\u043e \u0437\u0430\u0439\u043c\u0443 "
                    f"#{repayment.loan_id}"
                ),
                amount=repayment.amount,
                created_at=repayment.created_at,
            )
        )

    history.sort(
        key=lambda item: item.created_at,
        reverse=True,
    )

    return history[:30]


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loans = get_dashboard_loans(
        db=db,
        current_user=current_user,
    )

    summary = get_dashboard_summary(
        db=db,
        current_user=current_user,
    )

    repayments = get_dashboard_repayments_history(
        db=db,
        current_user=current_user,
    )

    history = build_dashboard_history(
        loans=loans,
        repayments=repayments,
        current_user=current_user,
    )

    available_lenders = get_dashboard_available_lenders(
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
