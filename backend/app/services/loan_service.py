from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.loan import Loan, LoanStatus
from app.models.repayment import Repayment
from app.models.user import User
from app.schemas.loan import LoanCreate, RepaymentCreate


async def calculate_remaining_balance(
    db: AsyncSession,
    loan: Loan,
) -> Decimal:
    result = await db.execute(
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


async def enrich_loan_with_balance(
    db: AsyncSession,
    loan: Loan,
):
    loan.remaining_balance = await calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    return loan


async def create_loan(
    db: AsyncSession,
    loan_data: LoanCreate,
    current_user: User,
) -> Loan:
    if loan_data.borrower_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot create a loan to yourself",
        )

    borrower_result = await db.execute(
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
        lender_id=current_user.id,
        borrower_id=loan_data.borrower_id,
        amount=loan_data.amount,
        currency=loan_data.currency,
        description=loan_data.description,
        due_date=loan_data.due_date,
        status=LoanStatus.DRAFT,
    )

    db.add(loan)

    await db.commit()
    await db.refresh(loan)

    return await enrich_loan_with_balance(
        db=db,
        loan=loan,
    )


async def get_user_loans(
    db: AsyncSession,
    current_user: User,
):
    result = await db.execute(
        select(Loan).where(
            or_(
                Loan.lender_id == current_user.id,
                Loan.borrower_id == current_user.id,
            )
        )
    )

    loans = result.scalars().all()

    enriched_loans = []

    for loan in loans:
        enriched_loan = await enrich_loan_with_balance(
            db=db,
            loan=loan,
        )

        enriched_loans.append(enriched_loan)

    return enriched_loans


async def get_loan_by_id(
    db: AsyncSession,
    loan_id: int,
    current_user: User,
):
    result = await db.execute(
        select(Loan).where(
            Loan.id == loan_id
        )
    )

    loan = result.scalar_one_or_none()

    if loan is None:
        return None

    if (
        loan.lender_id != current_user.id
        and loan.borrower_id != current_user.id
    ):
        return None

    return await enrich_loan_with_balance(
        db=db,
        loan=loan,
    )


async def confirm_loan(
    db: AsyncSession,
    loan_id: int,
    current_user: User,
) -> Loan:
    loan = await get_loan_by_id(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )

    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Loan not found",
        )

    if loan.borrower_id != current_user.id:
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

    await db.commit()
    await db.refresh(loan)

    return await enrich_loan_with_balance(
        db=db,
        loan=loan,
    )


async def reject_loan(
    db: AsyncSession,
    loan_id: int,
    current_user: User,
) -> Loan:
    loan = await get_loan_by_id(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )

    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Loan not found",
        )

    if loan.borrower_id != current_user.id:
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

    await db.commit()
    await db.refresh(loan)

    return await enrich_loan_with_balance(
        db=db,
        loan=loan,
    )


async def mark_loan_as_paid(
    db: AsyncSession,
    loan_id: int,
    current_user: User,
) -> Loan:
    loan = await get_loan_by_id(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )

    if loan is None:
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

    remaining_balance = await calculate_remaining_balance(
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

    await db.commit()
    await db.refresh(loan)

    return await enrich_loan_with_balance(
        db=db,
        loan=loan,
    )


async def create_repayment(
    db: AsyncSession,
    loan_id: int,
    repayment_data: RepaymentCreate,
    current_user: User,
):
    result = await db.execute(
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

    paid_result = await db.execute(
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

    await db.commit()
    await db.refresh(loan)

    return await enrich_loan_with_balance(
        db=db,
        loan=loan,
    )


async def get_repayment_history(
    db: AsyncSession,
    loan_id: int,
    current_user: User,
):
    loan = await get_loan_by_id(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )

    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Loan not found",
        )

    result = await db.execute(
        select(Repayment)
        .where(
            Repayment.loan_id == loan.id
        )
        .order_by(
            Repayment.created_at.desc()
        )
    )

    return result.scalars().all()