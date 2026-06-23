from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.loan import Loan, LoanStatus
from app.models.loan_interest_ledger import LoanInterestLedger
from app.models.repayment import Repayment, RepaymentStatus
from app.models.user import User
from app.schemas.loan import LoanCreate, RepaymentCreate
from app.services.loan_balance_service import (
    allocate_repayment_interest_first,
    calculate_remaining_balance,
    normalize_money,
)
from app.services.telegram_notifications import (
    notify_loan_confirmed,
    notify_loan_created,
    notify_loan_paid,
    notify_loan_rejected,
    notify_repayment_confirmed,
    notify_repayment_rejected,
    notify_repayment_submitted,
)


def is_admin(user: User) -> bool:
    return user.role == "admin"


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


def is_user_in_telegram_network(
    db: Session,
    current_user: User,
    user: User,
) -> bool:
    result = db.execute(
        select(User)
    )

    users = result.scalars().all()

    connected_user_ids = get_connected_user_ids(
        users=users,
        current_user_id=current_user.id,
    )

    return user.id in connected_user_ids


def loan_with_users_query():
    return select(Loan).options(
        joinedload(Loan.lender),
        joinedload(Loan.borrower),
    )


def lock_loan_by_id(
    db: Session,
    loan_id: int,
):
    result = db.execute(
        select(Loan)
        .where(Loan.id == loan_id)
        .with_for_update()
    )

    return result.scalar_one_or_none()


def lock_repayment_by_id(
    db: Session,
    repayment_id: int,
):
    result = db.execute(
        select(Repayment)
        .where(Repayment.id == repayment_id)
        .with_for_update()
    )

    return result.scalar_one_or_none()


def attach_loan_users(
    db: Session,
    loan: Loan,
):
    loan.lender = db.get(User, loan.lender_id)
    loan.borrower = db.get(User, loan.borrower_id)

    return loan


def enrich_loan_with_balance(
    db: Session,
    loan: Loan,
):
    loan.remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    return loan


def calculate_pending_repayments_total(
    db: Session,
    loan: Loan,
) -> Decimal:
    result = db.execute(
        select(
            func.coalesce(
                func.sum(Repayment.amount),
                0,
            )
        ).where(
            Repayment.loan_id == loan.id,
            Repayment.status == RepaymentStatus.PENDING,
        )
    )

    return normalize_money(result.scalar_one())


def create_loan(
    db: Session,
    loan_data: LoanCreate,
    current_user: User,
) -> Loan:
    if loan_data.lender_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot create a loan request to yourself",
        )

    lender_result = db.execute(
        select(User).where(User.id == loan_data.lender_id)
    )

    lender = lender_result.scalar_one_or_none()

    if lender is None:
        raise HTTPException(
            status_code=404,
            detail="Lender not found",
        )

    if (
        not is_admin(current_user)
        and not is_user_in_telegram_network(
            db=db,
            current_user=current_user,
            user=lender,
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="Lender is not in your Telegram network",
        )

    loan = Loan(
        lender_id=lender.id,
        borrower_id=current_user.id,
        amount=loan_data.amount,
        annual_interest_rate=loan_data.annual_interest_rate,
        currency=loan_data.currency,
        description=loan_data.description,
        due_date=loan_data.due_date,
        status=LoanStatus.DRAFT,
    )

    db.add(loan)
    db.flush()

    loan.lender = lender
    loan.borrower = current_user
    loan.remaining_balance = loan.amount

    db.commit()

    notify_loan_created(
        loan=loan,
    )

    return loan


def get_user_loans(
    db: Session,
    current_user: User,
):
    query = loan_with_users_query()

    if is_admin(current_user):
        result = db.execute(
            query.order_by(Loan.id.desc())
        )
    else:
        result = db.execute(
            query.where(
                or_(
                    Loan.lender_id == current_user.id,
                    Loan.borrower_id == current_user.id,
                )
            ).order_by(Loan.id.desc())
        )

    loans = result.scalars().all()

    enriched_loans = []

    for loan in loans:
        enriched_loan = enrich_loan_with_balance(
            db=db,
            loan=loan,
        )

        enriched_loans.append(enriched_loan)

    return enriched_loans


def get_loan_by_id(
    db: Session,
    loan_id: int,
    current_user: User,
):
    result = db.execute(
        loan_with_users_query().where(
            Loan.id == loan_id
        )
    )

    loan = result.scalar_one_or_none()

    if loan is None:
        return None

    if is_admin(current_user):
        return enrich_loan_with_balance(
            db=db,
            loan=loan,
        )

    if (
        loan.lender_id != current_user.id
        and loan.borrower_id != current_user.id
    ):
        return None

    return enrich_loan_with_balance(
        db=db,
        loan=loan,
    )


def confirm_loan(
    db: Session,
    loan_id: int,
    current_user: User,
) -> Loan:
    loan = get_loan_by_id(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )

    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Loan not found",
        )

    if (
        not is_admin(current_user)
        and loan.lender_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Only lender can confirm this loan",
        )

    if loan.status != LoanStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Only draft loan can be confirmed",
        )

    loan.status = LoanStatus.ACTIVE
    loan.remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    db.commit()

    notify_loan_confirmed(
        loan=loan,
    )

    return loan


def reject_loan(
    db: Session,
    loan_id: int,
    current_user: User,
) -> Loan:
    loan = get_loan_by_id(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )

    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Loan not found",
        )

    if (
        not is_admin(current_user)
        and loan.lender_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Only lender can reject this loan",
        )

    if loan.status != LoanStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Only draft loan can be rejected",
        )

    loan.status = LoanStatus.REJECTED
    loan.remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    db.commit()

    notify_loan_rejected(
        loan=loan,
    )

    return loan


def mark_loan_as_paid(
    db: Session,
    loan_id: int,
    current_user: User,
) -> Loan:
    loan = lock_loan_by_id(
        db=db,
        loan_id=loan_id,
    )

    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Loan not found",
        )

    attach_loan_users(
        db=db,
        loan=loan,
    )

    if not is_admin(current_user):
        if (
            loan.lender_id != current_user.id
            and loan.borrower_id != current_user.id
        ):
            raise HTTPException(
                status_code=404,
                detail="Loan not found",
            )

        if loan.lender_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only lender can mark this loan as paid",
            )

    if loan.status not in [
        LoanStatus.ACTIVE,
        LoanStatus.PARTIALLY_PAID,
        LoanStatus.WAITING_CONFIRMATION,
    ]:
        raise HTTPException(
            status_code=400,
            detail="Only active loan can be marked as paid",
        )

    pending_repayments_total = calculate_pending_repayments_total(
        db=db,
        loan=loan,
    )

    if pending_repayments_total > 0:
        raise HTTPException(
            status_code=400,
            detail="Loan has pending repayments",
        )

    remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    if remaining_balance > 0:
        allocation = allocate_repayment_interest_first(
            db=db,
            loan=loan,
            payment_amount=remaining_balance,
        )

        repayment = Repayment(
            loan_id=loan.id,
            amount=allocation.total_amount,
            interest_amount=allocation.interest_amount,
            principal_amount=allocation.principal_amount,
            status=RepaymentStatus.CONFIRMED,
            submitted_by_user_id=current_user.id,
            confirmed_at=datetime.now(timezone.utc),
            confirmed_by_user_id=current_user.id,
        )

        db.add(repayment)

    loan.status = LoanStatus.PAID
    loan.updated_at = datetime.now(timezone.utc)
    loan.remaining_balance = Decimal("0.00")

    db.commit()

    notify_loan_paid(
        loan=loan,
    )

    return loan


def create_repayment(
    db: Session,
    loan_id: int,
    repayment_data: RepaymentCreate,
    current_user: User,
):
    loan = lock_loan_by_id(
        db=db,
        loan_id=loan_id,
    )

    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Loan not found",
        )

    attach_loan_users(
        db=db,
        loan=loan,
    )

    if not is_admin(current_user):
        if (
            loan.lender_id != current_user.id
            and loan.borrower_id != current_user.id
        ):
            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )

        if loan.borrower_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only borrower can repay this loan",
            )

    if loan.status not in [
        LoanStatus.ACTIVE,
        LoanStatus.PARTIALLY_PAID,
    ]:
        raise HTTPException(
            status_code=400,
            detail="Loan is not active",
        )

    payment_amount = normalize_money(repayment_data.amount)

    if payment_amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Repayment amount must be greater than zero",
        )

    remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    pending_repayments_total = calculate_pending_repayments_total(
        db=db,
        loan=loan,
    )

    available_for_new_repayment = normalize_money(
        remaining_balance - pending_repayments_total
    )

    if payment_amount > available_for_new_repayment:
        raise HTTPException(
            status_code=400,
            detail="Repayment amount exceeds available balance",
        )

    repayment = Repayment(
        loan_id=loan.id,
        amount=payment_amount,
        interest_amount=Decimal("0.00"),
        principal_amount=Decimal("0.00"),
        status=RepaymentStatus.PENDING,
        submitted_by_user_id=current_user.id,
    )

    db.add(repayment)
    db.flush()

    loan.updated_at = datetime.now(timezone.utc)
    loan.remaining_balance = remaining_balance

    db.commit()

    notify_repayment_submitted(
        loan=loan,
        repayment_id=repayment.id,
        payment_amount=payment_amount,
    )

    return loan


def confirm_repayment(
    db: Session,
    loan_id: int,
    repayment_id: int,
    current_user: User,
) -> Loan:
    loan = lock_loan_by_id(
        db=db,
        loan_id=loan_id,
    )

    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Loan not found",
        )

    attach_loan_users(
        db=db,
        loan=loan,
    )

    repayment = lock_repayment_by_id(
        db=db,
        repayment_id=repayment_id,
    )

    if repayment is None or repayment.loan_id != loan.id:
        raise HTTPException(
            status_code=404,
            detail="Repayment not found",
        )

    if (
        not is_admin(current_user)
        and repayment.submitted_by_user_id == current_user.id
        and loan.borrower_id == current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Borrower cannot confirm own repayment",
        )

    if not is_admin(current_user):
        if (
            loan.lender_id != current_user.id
            and loan.borrower_id != current_user.id
        ):
            raise HTTPException(
                status_code=404,
                detail="Loan not found",
            )

        if loan.lender_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only lender can confirm repayment",
            )

    if repayment.status != RepaymentStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Only pending repayment can be confirmed",
        )

    remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    if repayment.amount > remaining_balance:
        raise HTTPException(
            status_code=400,
            detail="Repayment amount exceeds remaining balance",
        )

    allocation = allocate_repayment_interest_first(
        db=db,
        loan=loan,
        payment_amount=repayment.amount,
    )

    repayment.interest_amount = allocation.interest_amount
    repayment.principal_amount = allocation.principal_amount
    repayment.status = RepaymentStatus.CONFIRMED
    repayment.confirmed_at = datetime.now(timezone.utc)
    repayment.confirmed_by_user_id = current_user.id

    db.flush()

    new_remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    if new_remaining_balance <= 0:
        loan.status = LoanStatus.PAID
        loan.remaining_balance = Decimal("0.00")
    else:
        loan.status = LoanStatus.PARTIALLY_PAID
        loan.remaining_balance = new_remaining_balance

    loan.updated_at = datetime.now(timezone.utc)

    db.commit()

    notify_repayment_confirmed(
        loan=loan,
        payment_amount=repayment.amount,
        remaining_balance=loan.remaining_balance,
    )

    return loan


def reject_repayment(
    db: Session,
    loan_id: int,
    repayment_id: int,
    current_user: User,
) -> Loan:
    loan = lock_loan_by_id(
        db=db,
        loan_id=loan_id,
    )

    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Loan not found",
        )

    attach_loan_users(
        db=db,
        loan=loan,
    )

    repayment = lock_repayment_by_id(
        db=db,
        repayment_id=repayment_id,
    )

    if repayment is None or repayment.loan_id != loan.id:
        raise HTTPException(
            status_code=404,
            detail="Repayment not found",
        )

    if (
        not is_admin(current_user)
        and repayment.submitted_by_user_id == current_user.id
        and loan.borrower_id == current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Borrower cannot reject own repayment",
        )

    if not is_admin(current_user):
        if (
            loan.lender_id != current_user.id
            and loan.borrower_id != current_user.id
        ):
            raise HTTPException(
                status_code=404,
                detail="Loan not found",
            )

        if loan.lender_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only lender can reject repayment",
            )

    if repayment.status != RepaymentStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Only pending repayment can be rejected",
        )

    repayment.status = RepaymentStatus.REJECTED
    repayment.rejected_at = datetime.now(timezone.utc)
    repayment.rejected_by_user_id = current_user.id

    loan.updated_at = datetime.now(timezone.utc)
    loan.remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    db.commit()

    notify_repayment_rejected(
        loan=loan,
        payment_amount=repayment.amount,
    )

    return loan


def get_repayment_history(
    db: Session,
    loan_id: int,
    current_user: User,
):
    loan = get_loan_by_id(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )

    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Loan not found",
        )

    result = db.execute(
        select(Repayment)
        .where(
            Repayment.loan_id == loan.id
        )
        .order_by(
            Repayment.created_at.desc()
        )
    )

    return result.scalars().all()


def get_interest_ledger_history(
    db: Session,
    loan_id: int,
    current_user: User,
):
    loan = get_loan_by_id(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )

    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Loan not found",
        )

    result = db.execute(
        select(LoanInterestLedger)
        .where(
            LoanInterestLedger.loan_id == loan.id
        )
        .order_by(
            LoanInterestLedger.accrual_date.desc(),
            LoanInterestLedger.id.desc(),
        )
    )

    ledger_rows = result.scalars().all()

    history = []

    for ledger in ledger_rows:
        unpaid_interest_amount = normalize_money(
            ledger.interest_amount - ledger.paid_amount
        )

        if unpaid_interest_amount < 0:
            unpaid_interest_amount = Decimal("0.00")

        history.append(
            {
                "id": ledger.id,
                "loan_id": ledger.loan_id,
                "accrual_date": ledger.accrual_date,
                "principal_amount": ledger.principal_amount,
                "annual_interest_rate": ledger.annual_interest_rate,
                "interest_amount": ledger.interest_amount,
                "paid_amount": ledger.paid_amount,
                "unpaid_interest_amount": unpaid_interest_amount,
                "created_at": ledger.created_at,
            }
        )

    return history