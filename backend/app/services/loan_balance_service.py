from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.loan import Loan
from app.models.loan_interest_ledger import LoanInterestLedger
from app.models.repayment import Repayment, RepaymentStatus


@dataclass(frozen=True)
class RepaymentAllocation:
    total_amount: Decimal
    interest_amount: Decimal
    principal_amount: Decimal


def to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0.00")

    return Decimal(value)


def normalize_money(value: Decimal) -> Decimal:
    return to_decimal(value).quantize(Decimal("0.01"))


def calculate_remaining_balance_from_values(
    loan_amount,
    principal_paid,
    unpaid_interest,
) -> Decimal:
    remaining = (
        to_decimal(loan_amount)
        - to_decimal(principal_paid)
        + to_decimal(unpaid_interest)
    )

    if remaining < 0:
        return Decimal("0.00")

    return normalize_money(remaining)


def calculate_principal_paid(
    db: Session,
    loan: Loan,
) -> Decimal:
    result = db.execute(
        select(
            func.coalesce(
                func.sum(Repayment.principal_amount),
                0,
            )
        ).where(
            Repayment.loan_id == loan.id,
            Repayment.status == RepaymentStatus.CONFIRMED,
        )
    )

    return normalize_money(result.scalar_one())


def calculate_principal_remaining(
    db: Session,
    loan: Loan,
) -> Decimal:
    principal_paid = calculate_principal_paid(
        db=db,
        loan=loan,
    )

    remaining = to_decimal(loan.amount) - principal_paid

    if remaining < 0:
        return Decimal("0.00")

    return normalize_money(remaining)


def calculate_unpaid_interest(
    db: Session,
    loan: Loan,
) -> Decimal:
    result = db.execute(
        select(
            func.coalesce(
                func.sum(
                    LoanInterestLedger.interest_amount
                    - LoanInterestLedger.paid_amount
                ),
                0,
            )
        ).where(
            LoanInterestLedger.loan_id == loan.id
        )
    )

    unpaid_interest = to_decimal(result.scalar_one())

    if unpaid_interest < 0:
        return Decimal("0.00")

    return normalize_money(unpaid_interest)


def calculate_remaining_balance(
    db: Session,
    loan: Loan,
) -> Decimal:
    principal_remaining = calculate_principal_remaining(
        db=db,
        loan=loan,
    )

    unpaid_interest = calculate_unpaid_interest(
        db=db,
        loan=loan,
    )

    remaining = principal_remaining + unpaid_interest

    if remaining < 0:
        return Decimal("0.00")

    return normalize_money(remaining)


def get_unpaid_interest_ledgers(
    db: Session,
    loan: Loan,
) -> list[LoanInterestLedger]:
    result = db.execute(
        select(LoanInterestLedger)
        .where(
            LoanInterestLedger.loan_id == loan.id,
            LoanInterestLedger.interest_amount
            > LoanInterestLedger.paid_amount,
        )
        .order_by(
            LoanInterestLedger.accrual_date.asc(),
            LoanInterestLedger.id.asc(),
        )
        .with_for_update()
    )

    return result.scalars().all()


def allocate_repayment_interest_first(
    db: Session,
    loan: Loan,
    payment_amount: Decimal,
) -> RepaymentAllocation:
    payment_amount = normalize_money(payment_amount)

    if payment_amount <= 0:
        raise ValueError("Payment amount must be greater than zero")

    remaining_payment = payment_amount
    interest_paid = Decimal("0.00")

    ledgers = get_unpaid_interest_ledgers(
        db=db,
        loan=loan,
    )

    for ledger in ledgers:
        unpaid_for_ledger = normalize_money(
            ledger.interest_amount - ledger.paid_amount
        )

        if unpaid_for_ledger <= 0:
            continue

        if remaining_payment <= 0:
            break

        amount_to_interest = min(
            remaining_payment,
            unpaid_for_ledger,
        )

        ledger.paid_amount = normalize_money(
            ledger.paid_amount + amount_to_interest
        )

        interest_paid = normalize_money(
            interest_paid + amount_to_interest
        )

        remaining_payment = normalize_money(
            remaining_payment - amount_to_interest
        )

    principal_remaining = calculate_principal_remaining(
        db=db,
        loan=loan,
    )

    principal_paid = min(
        remaining_payment,
        principal_remaining,
    )

    principal_paid = normalize_money(principal_paid)

    return RepaymentAllocation(
        total_amount=payment_amount,
        interest_amount=interest_paid,
        principal_amount=principal_paid,
    )