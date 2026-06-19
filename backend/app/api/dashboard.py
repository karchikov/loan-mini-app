from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, load_only

from app.api.deps import get_current_user
from app.database import get_db
from app.models.loan import Loan, LoanStatus
from app.models.loan_interest_ledger import LoanInterestLedger
from app.models.repayment import Repayment, RepaymentStatus
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.schemas.user import UserHistoryItemResponse, UserSummaryResponse
from app.services.loan_balance_service import calculate_remaining_balance_from_values


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
        return Decimal("0.00")

    return Decimal(value)


def normalize_money(value: Decimal) -> Decimal:
    return to_decimal(value).quantize(Decimal("0.01"))


def format_user_name(user: User | None) -> str:
    if user is None:
        return "Пользователь"

    name = user.first_name or f"Пользователь #{user.id}"

    if user.username:
        return f"{name} (@{user.username})"

    return name


def get_connected_user_ids(
    users: list[User],
    current_user_id: int,
) -> set[int]:
    graph: dict[int, set[int]] = {}

    for user in users:
        graph.setdefault(user.id, set())

        if user.invited_by_user_id is not None:
            graph.setdefault(user.invited_by_user_id, set())
            graph[user.id].add(user.invited_by_user_id)
            graph[user.invited_by_user_id].add(user.id)

    visited = set()
    queue = [current_user_id]

    while queue:
        user_id = queue.pop(0)

        if user_id in visited:
            continue

        visited.add(user_id)

        for connected_user_id in graph.get(user_id, set()):
            if connected_user_id not in visited:
                queue.append(connected_user_id)

    return visited


def get_pending_repayments_by_loan_id(
    db: Session,
    loan_ids: list[int],
) -> dict[int, list[Repayment]]:
    if not loan_ids:
        return {}

    result = db.execute(
        select(Repayment)
        .where(
            Repayment.loan_id.in_(loan_ids),
            Repayment.status == RepaymentStatus.PENDING,
        )
        .order_by(
            Repayment.created_at.desc(),
            Repayment.id.desc(),
        )
    )

    pending_by_loan_id: dict[int, list[Repayment]] = {}

    for repayment in result.scalars().all():
        pending_by_loan_id.setdefault(
            repayment.loan_id,
            [],
        ).append(repayment)

    return pending_by_loan_id


def get_dashboard_loans(
    db: Session,
    current_user: User,
) -> list[Loan]:
    repayment_totals = (
        select(
            Repayment.loan_id.label("loan_id"),
            func.coalesce(
                func.sum(Repayment.principal_amount),
                0,
            ).label("principal_paid"),
        )
        .where(
            Repayment.status == RepaymentStatus.CONFIRMED,
        )
        .group_by(Repayment.loan_id)
        .subquery()
    )

    pending_repayment_totals = (
        select(
            Repayment.loan_id.label("loan_id"),
            func.count(Repayment.id).label("pending_repayments_count"),
            func.coalesce(
                func.sum(Repayment.amount),
                0,
            ).label("pending_repayments_total"),
        )
        .where(
            Repayment.status == RepaymentStatus.PENDING,
        )
        .group_by(Repayment.loan_id)
        .subquery()
    )

    interest_totals = (
        select(
            LoanInterestLedger.loan_id.label("loan_id"),
            func.coalesce(
                func.sum(
                    LoanInterestLedger.interest_amount
                    - LoanInterestLedger.paid_amount
                ),
                0,
            ).label("unpaid_interest"),
            func.max(
                LoanInterestLedger.accrual_date
            ).label("last_interest_accrual_date"),
        )
        .group_by(LoanInterestLedger.loan_id)
        .subquery()
    )

    query = (
        select(
            Loan,
            func.coalesce(
                repayment_totals.c.principal_paid,
                0,
            ).label("principal_paid"),
            func.coalesce(
                interest_totals.c.unpaid_interest,
                0,
            ).label("unpaid_interest"),
            interest_totals.c.last_interest_accrual_date.label(
                "last_interest_accrual_date"
            ),
            func.coalesce(
                pending_repayment_totals.c.pending_repayments_count,
                0,
            ).label("pending_repayments_count"),
            func.coalesce(
                pending_repayment_totals.c.pending_repayments_total,
                0,
            ).label("pending_repayments_total"),
        )
        .outerjoin(
            repayment_totals,
            repayment_totals.c.loan_id == Loan.id,
        )
        .outerjoin(
            interest_totals,
            interest_totals.c.loan_id == Loan.id,
        )
        .outerjoin(
            pending_repayment_totals,
            pending_repayment_totals.c.loan_id == Loan.id,
        )
        .options(
            load_only(
                Loan.id,
                Loan.lender_id,
                Loan.borrower_id,
                Loan.amount,
                Loan.annual_interest_rate,
                Loan.currency,
                Loan.description,
                Loan.status,
                Loan.created_at,
                Loan.updated_at,
            ),
            joinedload(Loan.lender).load_only(
                User.id,
                User.username,
                User.first_name,
            ),
            joinedload(Loan.borrower).load_only(
                User.id,
                User.username,
                User.first_name,
            ),
        )
        .order_by(Loan.id.desc())
    )

    if not is_admin(current_user):
        query = query.where(
            loan_belongs_to_user(current_user.id)
        )

    result = db.execute(query)

    rows = result.all()
    loan_ids = [loan.id for loan, *_ in rows]

    pending_repayments_by_loan_id = get_pending_repayments_by_loan_id(
        db=db,
        loan_ids=loan_ids,
    )

    loans = []

    for (
        loan,
        principal_paid,
        unpaid_interest,
        last_interest_accrual_date,
        pending_repayments_count,
        pending_repayments_total,
    ) in rows:
        principal_remaining = normalize_money(
            to_decimal(loan.amount) - to_decimal(principal_paid)
        )

        if principal_remaining < 0:
            principal_remaining = Decimal("0.00")

        unpaid_interest = normalize_money(
            unpaid_interest
        )

        loan.principal_remaining = principal_remaining
        loan.unpaid_interest = unpaid_interest
        loan.remaining_balance = calculate_remaining_balance_from_values(
            loan_amount=loan.amount,
            principal_paid=principal_paid,
            unpaid_interest=unpaid_interest,
        )
        loan.last_interest_accrual_date = last_interest_accrual_date

        loan.pending_repayments_count = int(
            pending_repayments_count or 0
        )

        loan.pending_repayments_total = normalize_money(
            pending_repayments_total
        )

        loan.pending_repayments = pending_repayments_by_loan_id.get(
            loan.id,
            [],
        )

        loans.append(loan)

    return loans


def get_dashboard_summary(
    loans: list[Loan],
    current_user: User,
) -> UserSummaryResponse:
    my_debts = Decimal("0.00")
    owed_to_me = Decimal("0.00")
    active_loans_count = 0

    for loan in loans:
        if loan.status not in ACTIVE_LOAN_STATUSES:
            continue

        if (
            loan.borrower_id != current_user.id
            and loan.lender_id != current_user.id
        ):
            continue

        active_loans_count += 1

        if loan.borrower_id == current_user.id:
            my_debts += loan.remaining_balance

        if loan.lender_id == current_user.id:
            owed_to_me += loan.remaining_balance

    return UserSummaryResponse(
        my_debts=normalize_money(my_debts),
        owed_to_me=normalize_money(owed_to_me),
        balance=normalize_money(owed_to_me - my_debts),
        active_loans_count=active_loans_count,
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
    query = (
        select(User)
        .options(
            load_only(
                User.id,
                User.username,
                User.first_name,
                User.last_name,
                User.invited_by_user_id,
            )
        )
        .where(
            User.id != current_user.id
        )
        .order_by(
            User.first_name.asc(),
            User.id.asc(),
        )
    )

    result = db.execute(query)
    all_users = result.scalars().all()

    if is_admin(current_user):
        return all_users

    connected_user_ids = get_connected_user_ids(
        users=all_users + [current_user],
        current_user_id=current_user.id,
    )

    return [
        user
        for user in all_users
        if user.id in connected_user_ids
    ]


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
                title="Создана заявка на займ",
                description=(
                    f"{borrower_name} запросил "
                    f"займ у {lender_name}"
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
                    description=(
                        f"Займ #{loan.id} полностью погашен"
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
                    title="Займ отклонен",
                    description=(
                        f"Займ #{loan.id} был отклонен"
                    ),
                    amount=loan.amount,
                    created_at=loan.updated_at,
                )
            )

    for repayment in repayments:
        if repayment.status == RepaymentStatus.PENDING:
            title = "Платеж ожидает подтверждения"
        elif repayment.status == RepaymentStatus.REJECTED:
            title = "Платеж отклонен"
        else:
            title = "Платеж по займу"

        history.append(
            UserHistoryItemResponse(
                id=f"repayment-{repayment.id}",
                type="repayment",
                title=title,
                description=(
                    f"Платеж по займу #{repayment.loan_id}"
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
        loans=loans,
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