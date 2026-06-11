import logging
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.loan import Loan, LoanStatus
from app.models.loan_reminder_log import LoanReminderLog
from app.models.repayment import Repayment
from app.services.telegram_notifications import format_money, send_telegram_message

logger = logging.getLogger(__name__)


REMINDER_BEFORE_7 = "before_7"
REMINDER_BEFORE_3 = "before_3"
REMINDER_BEFORE_1 = "before_1"
REMINDER_DUE_TODAY = "due_today"
REMINDER_OVERDUE_DAILY = "overdue_daily"


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
    remaining_balance = loan.amount - total_paid

    if remaining_balance < 0:
        return Decimal("0")

    return remaining_balance


def get_reminder_type(
    loan: Loan,
    today: date,
) -> str | None:
    if loan.due_date is None:
        return None

    due_date = loan.due_date.date()
    days_delta = (due_date - today).days

    if days_delta == 7:
        return REMINDER_BEFORE_7

    if days_delta == 3:
        return REMINDER_BEFORE_3

    if days_delta == 1:
        return REMINDER_BEFORE_1

    if days_delta == 0:
        return REMINDER_DUE_TODAY

    if days_delta < 0:
        return REMINDER_OVERDUE_DAILY

    return None


def reminder_already_sent(
    db: Session,
    loan_id: int,
    reminder_type: str,
    reminder_date: date,
) -> bool:
    result = db.execute(
        select(LoanReminderLog).where(
            LoanReminderLog.loan_id == loan_id,
            LoanReminderLog.reminder_type == reminder_type,
            LoanReminderLog.reminder_date == reminder_date,
        )
    )

    return result.scalar_one_or_none() is not None


def create_reminder_log(
    db: Session,
    loan_id: int,
    reminder_type: str,
    reminder_date: date,
) -> None:
    reminder_log = LoanReminderLog(
        loan_id=loan_id,
        reminder_type=reminder_type,
        reminder_date=reminder_date,
    )

    db.add(reminder_log)


def build_reminder_text(
    loan: Loan,
    remaining_balance: Decimal,
    today: date,
) -> str:
    due_date = loan.due_date.date()
    days_delta = (due_date - today).days

    if days_delta > 0:
        timing_text = f"До срока возврата осталось дней: {days_delta}"
        title = "Напоминание о возврате займа"
    elif days_delta == 0:
        timing_text = "Сегодня срок возврата займа"
        title = "Сегодня срок возврата займа"
    else:
        timing_text = f"Просрочка дней: {abs(days_delta)}"
        title = "Просрочка по займу"

    return (
        f"{title} #{loan.id}\n\n"
        f"Сумма займа: {format_money(loan.amount)} {loan.currency}\n"
        f"Остаток долга: {format_money(remaining_balance)} {loan.currency}\n"
        f"{timing_text}"
    )


def send_loan_reminder(
    loan: Loan,
    text: str,
) -> None:
    send_telegram_message(
        telegram_id=loan.borrower.telegram_id,
        text=text,
    )

    if loan.lender.telegram_id != loan.borrower.telegram_id:
        send_telegram_message(
            telegram_id=loan.lender.telegram_id,
            text=text,
        )


def process_loan_reminders(
    db: Session,
) -> int:
    today = datetime.now(timezone.utc).date()

    result = db.execute(
        select(Loan)
        .options(
            joinedload(Loan.lender),
            joinedload(Loan.borrower),
        )
        .where(
            Loan.due_date.is_not(None),
            Loan.status.in_(
                [
                    LoanStatus.ACTIVE,
                    LoanStatus.PARTIALLY_PAID,
                    LoanStatus.OVERDUE,
                ]
            ),
        )
        .order_by(Loan.id.asc())
    )

    loans = result.scalars().all()

    sent_count = 0

    for loan in loans:
        reminder_type = get_reminder_type(
            loan=loan,
            today=today,
        )

        if reminder_type is None:
            continue

        already_sent = reminder_already_sent(
            db=db,
            loan_id=loan.id,
            reminder_type=reminder_type,
            reminder_date=today,
        )

        if already_sent:
            continue

        remaining_balance = calculate_remaining_balance(
            db=db,
            loan=loan,
        )

        if remaining_balance <= 0:
            continue

        text = build_reminder_text(
            loan=loan,
            remaining_balance=remaining_balance,
            today=today,
        )

        send_loan_reminder(
            loan=loan,
            text=text,
        )

        create_reminder_log(
            db=db,
            loan_id=loan.id,
            reminder_type=reminder_type,
            reminder_date=today,
        )

        sent_count += 1

    db.commit()

    logger.warning(
        "Loan reminders processed. Sent count: %s",
        sent_count,
    )

    return sent_count