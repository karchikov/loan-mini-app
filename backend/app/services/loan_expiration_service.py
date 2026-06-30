from datetime import date, datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.loan import Loan, LoanStatus
from app.services.loan_event_log_service import record_loan_event
from app.services.telegram_notifications import notify_loan_expired


def get_today_start_utc() -> datetime:
    today_utc = datetime.now(timezone.utc).date()

    return datetime.combine(
        today_utc,
        time.min,
        tzinfo=timezone.utc,
    )


def format_event_datetime(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc).isoformat()

    if isinstance(value, date):
        return value.isoformat()

    return str(value)


def process_expired_draft_loans(db: Session) -> int:
    today_start_utc = get_today_start_utc()

    result = db.execute(
        select(Loan)
        .options(
            joinedload(Loan.lender),
            joinedload(Loan.borrower),
        )
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
    expired_loans: list[tuple[Loan, str]] = []

    for loan in loans:
        old_status = loan.status
        old_status_value = getattr(old_status, "value", str(old_status))

        loan.status = LoanStatus.EXPIRED
        loan.updated_at = now_utc
        loan.funding_activation_code_hash = None

        record_loan_event(
            db=db,
            loan=loan,
            actor=None,
            event_type="loan_expired",
            old_status=old_status,
            new_status=LoanStatus.EXPIRED,
            metadata={
                "due_date": format_event_datetime(loan.due_date),
                "expired_at": format_event_datetime(now_utc),
                "source": "scheduler",
            },
        )

        expired_loans.append(
            (
                loan,
                old_status_value,
            )
        )

    db.commit()

    for loan, old_status_value in expired_loans:
        notify_loan_expired(
            loan=loan,
            previous_status=old_status_value,
        )

    return len(loans)