from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.loan import Loan, LoanStatus
from app.models.repayment import Repayment
from app.models.user import User
from app.schemas.loan import LoanCreate, RepaymentCreate


def is_admin(user: User) -> bool:
    return user.role == "admin"


def loan_with_users_query():
    return select(Loan).options(
        joinedload(Loan.lender),
        joinedload(Loan.borrower),
    )


def calculate_remaining_balance(
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
            Repayment.loan_id == loan.id
        )
    )

    total_paid = result.scalar_one()

    remaining = loan.amount - total_paid

    if remaining < 0:
        remaining = Decimal("0")

    return remaining


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
    lender_id = current_user.id

    if is_admin(current_user):
        if loan_data.lender_id is not None:
            lender_id = loan_data.lender_id

    if loan_data.borrower_id == lender_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot create a loan to yourself",
        )

    lender_result = db.execute(
        select(User).where(User.id == lender_id)
    )

    lender = lender_result.scalar_one_or_none()

    if lender is None:
        raise HTTPException(
            status_code=404,
            detail="Lender not found",
        )

    borrower_result = db.execute(
        select(User).where(
            User.id == loan_data.borrower_id
        )
    )

    borrower = borrower_result.scalar_one_or_none()

    if borrower is None:
        raise HTTPException(
            status_code=404,
            detail="Borrower not found",
        )

    loan = Loan(
        lender_id=lender_id,
        borrower_id=loan_data.borrower_id,
        amount=loan_data.amount,
        currency=loan_data.currency,
        description=loan_data.description,
        due_date=loan_data.due_date,
        status=LoanStatus.DRAFT,
    )

    db.add(loan)
    db.commit()
    db.refresh(loan)

    result = db.execute(
        loan_with_users_query().where(
            Loan.id == loan.id
        )
    )

    loan = result.scalar_one()

    return enrich_loan_with_balance(
        db=db,
        loan=loan,
    )


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
        and loan.borrower_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Only borrower can confirm this loan",
        )

    if loan.status != LoanStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Only draft loan can be confirmed",
        )

    loan.status = LoanStatus.ACTIVE

    db.commit()
    db.refresh(loan)

    return get_loan_by_id(
        db=db,
        loan_id=loan.id,
        current_user=current_user,
    )


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
        and loan.borrower_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Only borrower can reject this loan",
        )

    if loan.status != LoanStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Only draft loan can be rejected",
        )

    loan.status = LoanStatus.REJECTED

    db.commit()
    db.refresh(loan)

    return get_loan_by_id(
        db=db,
        loan_id=loan.id,
        current_user=current_user,
    )


def mark_loan_as_paid(
    db: Session,
    loan_id: int,
    current_user: User,
) -> Loan:
    result = db.execute(
        select(Loan)
        .where(Loan.id == loan_id)
        .with_for_update()
    )

    loan = result.scalar_one_or_none()

    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Loan not found",
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
    ]:
        raise HTTPException(
            status_code=400,
            detail="Only active loan can be marked as paid",
        )

    remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    if remaining_balance > 0:
        repayment = Repayment(
            loan_id=loan.id,
            amount=remaining_balance,
        )

        db.add(repayment)

    loan.status = LoanStatus.PAID

    db.commit()
    db.refresh(loan)

    return get_loan_by_id(
        db=db,
        loan_id=loan.id,
        current_user=current_user,
    )


def create_repayment(
    db: Session,
    loan_id: int,
    repayment_data: RepaymentCreate,
    current_user: User,
):
    result = db.execute(
        select(Loan)
        .where(Loan.id == loan_id)
        .with_for_update()
    )

    loan = result.scalar_one_or_none()

    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Loan not found",
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

    paid_result = db.execute(
        select(
            func.coalesce(
                func.sum(Repayment.amount),
                0,
            )
        ).where(
            Repayment.loan_id == loan.id
        )
    )

    total_paid = paid_result.scalar_one()

    remaining_balance = loan.amount - total_paid

    if repayment_data.amount > remaining_balance:
        raise HTTPException(
            status_code=400,
            detail="Repayment amount exceeds remaining balance",
        )

    repayment = Repayment(
        loan_id=loan.id,
        amount=repayment_data.amount,
    )

    db.add(repayment)

    new_remaining_balance = (
        remaining_balance - repayment_data.amount
    )

    if new_remaining_balance == 0:
        loan.status = LoanStatus.PAID
    else:
        loan.status = LoanStatus.PARTIALLY_PAID

    db.commit()
    db.refresh(loan)

    return get_loan_by_id(
        db=db,
        loan_id=loan.id,
        current_user=current_user,
    )


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