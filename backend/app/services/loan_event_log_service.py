from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.loan import Loan
from app.models.loan_event_log import LoanEventLog
from app.models.user import User


def normalize_status(status) -> str | None:
    if status is None:
        return None

    return getattr(status, "value", str(status))


def get_actor_role(
    loan: Loan,
    actor: User | None,
) -> str | None:
    if actor is None:
        return None

    if actor.role == "admin":
        return "admin"

    if loan.borrower_id == actor.id:
        return "borrower"

    if loan.lender_id == actor.id:
        return "lender"

    return actor.role or "user"


def get_latest_event_hash(
    db: Session,
    loan_id: int,
) -> str | None:
    result = db.execute(
        select(LoanEventLog.event_hash)
        .where(LoanEventLog.loan_id == loan_id)
        .order_by(LoanEventLog.id.desc())
        .limit(1)
    )

    return result.scalar_one_or_none()


def build_event_hash(payload: dict[str, Any]) -> str:
    serialized_payload = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    return hashlib.sha256(
        serialized_payload.encode("utf-8")
    ).hexdigest()


def build_hash_payload(
    *,
    loan_id: int,
    actor_user_id: int | None,
    actor_role: str | None,
    event_type: str,
    old_status: str | None,
    new_status: str | None,
    telegram_id_snapshot: int | None,
    username_snapshot: str | None,
    first_name_snapshot: str | None,
    ip_address: str | None,
    user_agent: str | None,
    metadata: dict[str, Any] | None,
    previous_event_hash: str | None,
    created_at: datetime,
) -> dict[str, Any]:
    return {
        "loan_id": loan_id,
        "actor_user_id": actor_user_id,
        "actor_role": actor_role,
        "event_type": event_type,
        "old_status": old_status,
        "new_status": new_status,
        "telegram_id_snapshot": telegram_id_snapshot,
        "username_snapshot": username_snapshot,
        "first_name_snapshot": first_name_snapshot,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "metadata": metadata or {},
        "previous_event_hash": previous_event_hash,
        "created_at": created_at.isoformat(),
    }


def record_loan_event(
    *,
    db: Session,
    loan: Loan,
    actor: User | None,
    event_type: str,
    old_status=None,
    new_status=None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> LoanEventLog:
    created_at = datetime.now(timezone.utc)
    actor_role = get_actor_role(
        loan=loan,
        actor=actor,
    )

    previous_event_hash = get_latest_event_hash(
        db=db,
        loan_id=loan.id,
    )

    actor_user_id = actor.id if actor else None
    telegram_id_snapshot = actor.telegram_id if actor else None
    username_snapshot = actor.username if actor else None
    first_name_snapshot = actor.first_name if actor else None

    old_status_value = normalize_status(old_status)
    new_status_value = normalize_status(new_status)

    hash_payload = build_hash_payload(
        loan_id=loan.id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        event_type=event_type,
        old_status=old_status_value,
        new_status=new_status_value,
        telegram_id_snapshot=telegram_id_snapshot,
        username_snapshot=username_snapshot,
        first_name_snapshot=first_name_snapshot,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {},
        previous_event_hash=previous_event_hash,
        created_at=created_at,
    )

    event = LoanEventLog(
        loan_id=loan.id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        event_type=event_type,
        old_status=old_status_value,
        new_status=new_status_value,
        telegram_id_snapshot=telegram_id_snapshot,
        username_snapshot=username_snapshot,
        first_name_snapshot=first_name_snapshot,
        ip_address=ip_address,
        user_agent=user_agent,
        event_metadata=metadata or {},
        previous_event_hash=previous_event_hash,
        event_hash=build_event_hash(hash_payload),
        created_at=created_at,
    )

    db.add(event)
    db.flush()

    return event