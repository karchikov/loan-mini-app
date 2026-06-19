from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.loan import Loan, LoanStatus
from app.models.repayment import Repayment
from app.models.user import User
from app.schemas.loan import LoanCreate, RepaymentCreate
from app.services.loan_balance_service import (
    allocate_repayment_interest_first,
    calculate_remaining_balance,
)
from app.services.telegram_notifications import (
    notify_final_repayment_submitted,
    notify_loan_confirmed,
    notify_loan_created,
    notify_loan_paid,
    notify_loan_rejected,
    notify_partial_payment,
)


def is_admin(user: User) -> bool:
    return user.role == "admin"


def is_user_in_telegram_network(
    current_user: User,
    user: User,
) -> bool:
    return (
        user.invited_by_user_id == current_user.id
        or current_user.invited_by_user_id == user.id
    )


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

    if not is_user_in_telegram_network(
        current_user=current_user,
        user=lender,
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

    remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    if loan.status == LoanStatus.WAITING_CONFIRMATION:
        if remaining_balance > 0:
            raise HTTPException(
                status_code=400,
                detail="Loan still has remaining balance",
            )
    else:
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
            )

            db.add(repayment)

    loan.status = LoanStatus.PAID
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

    if repayment_data.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Repayment amount must be greater than zero",
        )

    remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    if repayment_data.amount > remaining_balance:
        raise HTTPException(
            status_code=400,
            detail="Repayment amount exceeds remaining balance",
        )

    allocation = allocate_repayment_interest_first(
        db=db,
        loan=loan,
        payment_amount=repayment_data.amount,
    )

    repayment = Repayment(
        loan_id=loan.id,
        amount=allocation.total_amount,
        interest_amount=allocation.interest_amount,
        principal_amount=allocation.principal_amount,
    )

    db.add(repayment)
    db.flush()

    new_remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    if new_remaining_balance <= 0:
        loan.status = LoanStatus.WAITING_CONFIRMATION
    else:
        loan.status = LoanStatus.PARTIALLY_PAID

    loan.remaining_balance = new_remaining_balance

    db.commit()

    if new_remaining_balance <= 0:
        notify_final_repayment_submitted(
            loan=loan,
            payment_amount=repayment_data.amount,
        )
    else:
        notify_partial_payment(
            loan=loan,
            payment_amount=repayment_data.amount,
            remaining_balance=new_remaining_balance,
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