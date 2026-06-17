from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.loan import Loan, LoanStatus
from app.models.loan_interest_ledger import LoanInterestLedger
from app.services.loan_service import calculate_remaining_balance


def calculate_daily_interest(
    principal: Decimal,
    annual_rate: Decimal,
) -> Decimal:
    if principal <= 0 or annual_rate <= 0:
        return Decimal("0.00")

    daily = (principal * annual_rate / Decimal("100")) / Decimal("365")

    return daily.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def process_daily_interest_accrual(db: Session) -> int:
    today = date.today()

    loans_result = db.execute(
        select(Loan).where(
            Loan.status.in_(
                [
                    LoanStatus.ACTIVE,
                    LoanStatus.PARTIALLY_PAID,
                ]
            )
        )
    )

    loans = loans_result.scalars().all()

    created = 0

    for loan in loans:
        principal = calculate_remaining_balance(db=db, loan=loan)

        if principal <= 0:
            continue

        interest_amount = calculate_daily_interest(
            principal=principal,
            annual_rate=loan.annual_interest_rate,
        )

        if interest_amount <= 0:
            continue

        ledger = LoanInterestLedger(
            loan_id=loan.id,
            accrual_date=today,
            principal_amount=principal,
            annual_interest_rate=loan.annual_interest_rate,
            interest_amount=interest_amount,
        )

        db.add(ledger)

        try:
            db.commit()
            created += 1
        except IntegrityError:
            db.rollback()
            continue

    return created