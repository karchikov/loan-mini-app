from datetime import datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.loan import Loan, LoanStatus


def get_today_start_utc() -> datetime:
    today_utc = datetime.now(timezone.utc).date()

    return datetime.combine(
        today_utc,
        time.min,
        tzinfo=timezone.utc,
    )


def process_expired_draft_loans(db: Session) -> int:
    today_start_utc = get_today_start_utc()

    result = db.execute(
        select(Loan)
        .where(
            Loan.status.in_(
                [
                    LoanStatus.DRAFT,
                    LoanStatus.FUNDING_PENDING,
                ]
            ),
            Loan.due_date.is_not(None),
            Loan.due_date < today_start_utc,
        )
        .with_for_update(skip_locked=True)
    )

    loans = result.scalars().all()

    if not loans:
        return 0

    now_utc = datetime.now(timezone.utc)

    for loan in loans:
        loan.status = LoanStatus.EXPIRED
        loan.updated_at = now_utc

    db.commit()

    return len(loans)