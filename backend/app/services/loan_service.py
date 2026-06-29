from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import hmac
import secrets

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
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
from app.services.loan_event_log_service import record_loan_event
from app.services.telegram_notifications import (
    notify_funding_activation_code_regenerated,
    notify_loan_activated,
    notify_loan_created,
    notify_loan_funding_pending,
    notify_loan_paid,
    notify_loan_rejected,
    notify_repayment_confirmed,
    notify_repayment_rejected,
    notify_repayment_submitted,
)


FUNDING_ACTIVATION_CODE_LENGTH = 4
MAX_FUNDING_ACTIVATION_CODE_ATTEMPTS = 5


@dataclass
class FundingActivationCodeResult:
    loan: Loan
    activation_code: str


def is_admin(user: User) -> bool:
    return user.role == "admin"


def get_utc_today_date():
    return datetime.now(timezone.utc).date()


def get_due_date_utc_date(due_date):
    if due_date is None:
        return None

    if isinstance(due_date, datetime):
        normalized_due_date = due_date

        if normalized_due_date.tzinfo is None:
            normalized_due_date = normalized_due_date.replace(tzinfo=timezone.utc)

        return normalized_due_date.astimezone(timezone.utc).date()

    if isinstance(due_date, date):
        return due_date

    return None


def get_loan_due_date_utc_date(loan: Loan):
    return get_due_date_utc_date(loan.due_date)


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


def format_event_decimal(value) -> str:
    return str(normalize_money(value))


def validate_loan_due_date_not_in_past(due_date):
    due_date_utc_date = get_due_date_utc_date(due_date)

    if due_date_utc_date is None:
        return

    if due_date_utc_date < get_utc_today_date():
        raise HTTPException(
            status_code=400,
            detail="Нельзя создать заявку с прошедшей датой возврата",
        )


def is_expirable_loan_request(loan: Loan) -> bool:
    return loan.status in [
        LoanStatus.DRAFT,
        LoanStatus.FUNDING_PENDING,
    ]


def is_loan_request_expired(loan: Loan) -> bool:
    if not is_expirable_loan_request(loan):
        return False

    due_date = get_loan_due_date_utc_date(loan)

    if due_date is None:
        return False

    return due_date < get_utc_today_date()


def expire_loan_request_if_needed(
    db: Session,
    loan: Loan,
    actor: User | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> bool:
    if not is_loan_request_expired(loan):
        return False

    old_status = loan.status
    now_utc = datetime.now(timezone.utc)

    loan.status = LoanStatus.EXPIRED
    loan.updated_at = now_utc
    loan.funding_activation_code_hash = None
    loan.remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    record_loan_event(
        db=db,
        loan=loan,
        actor=actor,
        event_type="loan_expired",
        old_status=old_status,
        new_status=LoanStatus.EXPIRED,
        metadata={
            "due_date": format_event_datetime(loan.due_date),
            "expired_at": format_event_datetime(now_utc),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.commit()

    return True


def is_draft_loan_expired(loan: Loan) -> bool:
    return loan.status == LoanStatus.DRAFT and is_loan_request_expired(loan)


def expire_draft_loan_if_needed(
    db: Session,
    loan: Loan,
    actor: User | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> bool:
    if loan.status != LoanStatus.DRAFT:
        return False

    return expire_loan_request_if_needed(
        db=db,
        loan=loan,
        actor=actor,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def generate_funding_activation_code() -> str:
    max_value = 10 ** FUNDING_ACTIVATION_CODE_LENGTH

    return f"{secrets.randbelow(max_value):0{FUNDING_ACTIVATION_CODE_LENGTH}d}"


def build_funding_activation_code_hash(
    loan_id: int,
    activation_code: str,
) -> str:
    message = f"{loan_id}:{activation_code}".encode("utf-8")
    secret_key = settings.SECRET_KEY.encode("utf-8")

    return hmac.new(
        secret_key,
        message,
        hashlib.sha256,
    ).hexdigest()


def verify_funding_activation_code(
    loan: Loan,
    activation_code: str,
) -> bool:
    if not loan.funding_activation_code_hash:
        return False

    expected_hash = build_funding_activation_code_hash(
        loan_id=loan.id,
        activation_code=activation_code,
    )

    return hmac.compare_digest(
        expected_hash,
        loan.funding_activation_code_hash,
    )


def set_funding_activation_code(
    loan: Loan,
    current_user: User,
) -> str:
    activation_code = generate_funding_activation_code()
    now_utc = datetime.now(timezone.utc)

    loan.funding_activation_code_hash = build_funding_activation_code_hash(
        loan_id=loan.id,
        activation_code=activation_code,
    )
    loan.funding_activation_code_generated_at = now_utc
    loan.funding_activation_code_generated_by_user_id = current_user.id
    loan.funding_activation_code_attempts = 0
    loan.updated_at = now_utc

    return activation_code


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
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Loan:
    validate_loan_due_date_not_in_past(loan_data.due_date)

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

    record_loan_event(
        db=db,
        loan=loan,
        actor=current_user,
        event_type="loan_created",
        old_status=None,
        new_status=LoanStatus.DRAFT,
        metadata={
            "amount": format_event_decimal(loan.amount),
            "annual_interest_rate": format_event_decimal(loan.annual_interest_rate),
            "currency": loan.currency,
            "due_date": format_event_datetime(loan.due_date),
            "borrower_id": loan.borrower_id,
            "lender_id": loan.lender_id,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

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
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> FundingActivationCodeResult:
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

    if (
        not is_admin(current_user)
        and loan.lender_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Only lender can confirm this loan",
        )

    if loan.status == LoanStatus.EXPIRED:
        raise HTTPException(
            status_code=400,
            detail="Loan request expired and cannot be confirmed",
        )

    if loan.status != LoanStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Only draft loan can be confirmed",
        )

    if expire_draft_loan_if_needed(
        db=db,
        loan=loan,
        actor=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    ):
        raise HTTPException(
            status_code=400,
            detail="Loan request expired and cannot be confirmed",
        )

    old_status = loan.status
    now_utc = datetime.now(timezone.utc)

    loan.status = LoanStatus.FUNDING_PENDING
    loan.lender_confirmed_at = now_utc
    loan.updated_at = now_utc

    activation_code = set_funding_activation_code(
        loan=loan,
        current_user=current_user,
    )

    loan.remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    record_loan_event(
        db=db,
        loan=loan,
        actor=current_user,
        event_type="lender_funding_confirmed",
        old_status=old_status,
        new_status=LoanStatus.FUNDING_PENDING,
        metadata={
            "lender_confirmed_at": format_event_datetime(now_utc),
            "confirmation_text": (
                "Кредитор подтвердил готовность передать денежные средства "
                "заемщику вне приложения."
            ),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    record_loan_event(
        db=db,
        loan=loan,
        actor=current_user,
        event_type="funding_activation_code_generated",
        old_status=LoanStatus.FUNDING_PENDING,
        new_status=LoanStatus.FUNDING_PENDING,
        metadata={
            "code_length": FUNDING_ACTIVATION_CODE_LENGTH,
            "generated_at": format_event_datetime(
                loan.funding_activation_code_generated_at
            ),
            "generated_by_user_id": current_user.id,
            "attempts_reset": True,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.commit()

    notify_loan_funding_pending(
        loan=loan,
        activation_code=activation_code,
    )

    return FundingActivationCodeResult(
        loan=loan,
        activation_code=activation_code,
    )


def regenerate_funding_activation_code(
    db: Session,
    loan_id: int,
    current_user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> FundingActivationCodeResult:
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

    if (
        not is_admin(current_user)
        and loan.lender_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Only lender can regenerate activation code",
        )

    if loan.status != LoanStatus.FUNDING_PENDING:
        raise HTTPException(
            status_code=400,
            detail="Activation code can be regenerated only for funding pending loan",
        )

    if expire_loan_request_if_needed(
        db=db,
        loan=loan,
        actor=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    ):
        raise HTTPException(
            status_code=400,
            detail="Loan request expired and activation code cannot be regenerated",
        )

    activation_code = set_funding_activation_code(
        loan=loan,
        current_user=current_user,
    )

    loan.remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    record_loan_event(
        db=db,
        loan=loan,
        actor=current_user,
        event_type="funding_activation_code_regenerated",
        old_status=LoanStatus.FUNDING_PENDING,
        new_status=LoanStatus.FUNDING_PENDING,
        metadata={
            "code_length": FUNDING_ACTIVATION_CODE_LENGTH,
            "generated_at": format_event_datetime(
                loan.funding_activation_code_generated_at
            ),
            "generated_by_user_id": current_user.id,
            "attempts_reset": True,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.commit()

    notify_funding_activation_code_regenerated(
        loan=loan,
        activation_code=activation_code,
    )

    return FundingActivationCodeResult(
        loan=loan,
        activation_code=activation_code,
    )


def complete_funding_activation(
    db: Session,
    loan: Loan,
    current_user: User,
    confirmation_method: str,
    activation_method: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Loan:
    old_status = loan.status
    now_utc = datetime.now(timezone.utc)

    loan.status = LoanStatus.ACTIVE
    loan.borrower_received_at = now_utc
    loan.borrower_received_by_user_id = current_user.id
    loan.funding_activation_code_hash = None
    loan.updated_at = now_utc
    loan.remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    record_loan_event(
        db=db,
        loan=loan,
        actor=current_user,
        event_type="borrower_money_received_confirmed",
        old_status=old_status,
        new_status=LoanStatus.ACTIVE,
        metadata={
            "borrower_received_at": format_event_datetime(now_utc),
            "confirmation_method": confirmation_method,
            "confirmation_text": (
                "Заемщик подтвердил фактическое получение денежных средств "
                "от кредитора вне приложения."
            ),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    record_loan_event(
        db=db,
        loan=loan,
        actor=current_user,
        event_type="loan_activated",
        old_status=old_status,
        new_status=LoanStatus.ACTIVE,
        metadata={
            "activated_at": format_event_datetime(now_utc),
            "activation_method": activation_method,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.commit()

    notify_loan_activated(
        loan=loan,
    )

    return loan


def get_funding_pending_loan_for_activation(
    db: Session,
    loan_id: int,
    current_user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
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

    if (
        not is_admin(current_user)
        and loan.borrower_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Only borrower can activate this loan",
        )

    if loan.status == LoanStatus.EXPIRED:
        raise HTTPException(
            status_code=400,
            detail="Loan request expired and cannot be activated",
        )

    if loan.status != LoanStatus.FUNDING_PENDING:
        raise HTTPException(
            status_code=400,
            detail="Only funding pending loan can be activated",
        )

    if expire_loan_request_if_needed(
        db=db,
        loan=loan,
        actor=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    ):
        raise HTTPException(
            status_code=400,
            detail="Loan request expired and cannot be activated",
        )

    return loan


def activate_loan_by_borrower_confirmation(
    db: Session,
    loan_id: int,
    current_user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Loan:
    loan = get_funding_pending_loan_for_activation(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return complete_funding_activation(
        db=db,
        loan=loan,
        current_user=current_user,
        confirmation_method="simple_button",
        activation_method="borrower_confirmation_without_code",
        ip_address=ip_address,
        user_agent=user_agent,
    )


def activate_loan(
    db: Session,
    loan_id: int,
    activation_code: str,
    current_user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Loan:
    loan = get_funding_pending_loan_for_activation(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not loan.funding_activation_code_hash:
        raise HTTPException(
            status_code=400,
            detail="Activation code is not available. Ask lender to generate a new code",
        )

    if loan.funding_activation_code_attempts >= MAX_FUNDING_ACTIVATION_CODE_ATTEMPTS:
        raise HTTPException(
            status_code=400,
            detail="Activation code is locked. Ask lender to generate a new code",
        )

    normalized_activation_code = activation_code.strip()

    if not verify_funding_activation_code(
        loan=loan,
        activation_code=normalized_activation_code,
    ):
        loan.funding_activation_code_attempts += 1
        loan.updated_at = datetime.now(timezone.utc)

        db.commit()

        attempts_left = (
            MAX_FUNDING_ACTIVATION_CODE_ATTEMPTS
            - loan.funding_activation_code_attempts
        )

        if attempts_left <= 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid activation code. Code is locked after too many attempts. Ask lender to generate a new code",
            )

        raise HTTPException(
            status_code=400,
            detail=f"Invalid activation code. Attempts left: {attempts_left}",
        )

    return complete_funding_activation(
        db=db,
        loan=loan,
        current_user=current_user,
        confirmation_method="funding_activation_code",
        activation_method="borrower_confirmation_with_code",
        ip_address=ip_address,
        user_agent=user_agent,
    )


def reject_loan(
    db: Session,
    loan_id: int,
    current_user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
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

    if loan.status == LoanStatus.EXPIRED:
        raise HTTPException(
            status_code=400,
            detail="Loan request expired and cannot be rejected",
        )

    if loan.status != LoanStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Only draft loan can be rejected",
        )

    if expire_draft_loan_if_needed(
        db=db,
        loan=loan,
        actor=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    ):
        raise HTTPException(
            status_code=400,
            detail="Loan request expired and cannot be rejected",
        )

    old_status = loan.status
    now_utc = datetime.now(timezone.utc)

    loan.status = LoanStatus.REJECTED
    loan.updated_at = now_utc
    loan.remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    record_loan_event(
        db=db,
        loan=loan,
        actor=current_user,
        event_type="loan_rejected",
        old_status=old_status,
        new_status=LoanStatus.REJECTED,
        metadata={
            "rejected_at": format_event_datetime(now_utc),
        },
        ip_address=ip_address,
        user_agent=user_agent,
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
    ip_address: str | None = None,
    user_agent: str | None = None,
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

    old_status = loan.status

    remaining_balance = calculate_remaining_balance(
        db=db,
        loan=loan,
    )

    repayment = None

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
        db.flush()

    now_utc = datetime.now(timezone.utc)

    loan.status = LoanStatus.PAID
    loan.updated_at = now_utc
    loan.remaining_balance = Decimal("0.00")

    record_loan_event(
        db=db,
        loan=loan,
        actor=current_user,
        event_type="loan_paid",
        old_status=old_status,
        new_status=LoanStatus.PAID,
        metadata={
            "paid_at": format_event_datetime(now_utc),
            "remaining_balance_before": format_event_decimal(remaining_balance),
            "repayment_id": repayment.id if repayment else None,
            "source": "mark_loan_as_paid",
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

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
    ip_address: str | None = None,
    user_agent: str | None = None,
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

    record_loan_event(
        db=db,
        loan=loan,
        actor=current_user,
        event_type="repayment_submitted",
        old_status=loan.status,
        new_status=loan.status,
        metadata={
            "repayment_id": repayment.id,
            "amount": format_event_decimal(payment_amount),
            "remaining_balance_before": format_event_decimal(remaining_balance),
            "pending_repayments_total_before": format_event_decimal(
                pending_repayments_total
            ),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

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
    ip_address: str | None = None,
    user_agent: str | None = None,
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

    old_status = loan.status

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

    record_loan_event(
        db=db,
        loan=loan,
        actor=current_user,
        event_type="repayment_confirmed",
        old_status=old_status,
        new_status=loan.status,
        metadata={
            "repayment_id": repayment.id,
            "amount": format_event_decimal(repayment.amount),
            "interest_amount": format_event_decimal(repayment.interest_amount),
            "principal_amount": format_event_decimal(repayment.principal_amount),
            "remaining_balance_before": format_event_decimal(remaining_balance),
            "remaining_balance_after": format_event_decimal(loan.remaining_balance),
            "confirmed_at": format_event_datetime(repayment.confirmed_at),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if loan.status == LoanStatus.PAID:
        record_loan_event(
            db=db,
            loan=loan,
            actor=current_user,
            event_type="loan_paid",
            old_status=old_status,
            new_status=LoanStatus.PAID,
            metadata={
                "paid_at": format_event_datetime(loan.updated_at),
                "repayment_id": repayment.id,
                "source": "repayment_confirmation",
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

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
    ip_address: str | None = None,
    user_agent: str | None = None,
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

    record_loan_event(
        db=db,
        loan=loan,
        actor=current_user,
        event_type="repayment_rejected",
        old_status=loan.status,
        new_status=loan.status,
        metadata={
            "repayment_id": repayment.id,
            "amount": format_event_decimal(repayment.amount),
            "rejected_at": format_event_datetime(repayment.rejected_at),
        },
        ip_address=ip_address,
        user_agent=user_agent,
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
