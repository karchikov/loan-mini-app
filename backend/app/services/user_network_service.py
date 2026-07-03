from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from app.models.loan import Loan
from app.models.user import User
from app.models.user_contact_alias import UserContactAlias


def format_user_display_name(
    user: User,
    contact_alias: str | None = None,
) -> str:
    if contact_alias:
        return contact_alias

    name_parts = [
        user.first_name,
        user.last_name,
    ]
    full_name = " ".join(part for part in name_parts if part)

    if user.username:
        return f"{full_name or 'Пользователь'} (@{user.username})"

    return full_name or f"Пользователь #{user.id}"


def get_direct_contact_user_ids(
    db: Session,
    current_user: User,
) -> set[int]:
    contact_user_ids: set[int] = set()

    if current_user.invited_by_user_id is not None:
        contact_user_ids.add(current_user.invited_by_user_id)

    invited_users_result = db.execute(
        select(User.id).where(
            User.invited_by_user_id == current_user.id
        )
    )
    contact_user_ids.update(invited_users_result.scalars().all())

    loan_counterparties_result = db.execute(
        select(
            distinct(
                Loan.lender_id
            )
        ).where(
            Loan.borrower_id == current_user.id
        )
    )
    contact_user_ids.update(loan_counterparties_result.scalars().all())

    reverse_loan_counterparties_result = db.execute(
        select(
            distinct(
                Loan.borrower_id
            )
        ).where(
            Loan.lender_id == current_user.id
        )
    )
    contact_user_ids.update(
        reverse_loan_counterparties_result.scalars().all()
    )

    contact_user_ids.discard(current_user.id)

    return contact_user_ids


def can_user_access_contact(
    db: Session,
    current_user: User,
    contact_user_id: int,
) -> bool:
    if current_user.role == "admin":
        return current_user.id != contact_user_id

    return contact_user_id in get_direct_contact_user_ids(
        db=db,
        current_user=current_user,
    )


def get_contact_alias_map(
    db: Session,
    owner_user_id: int,
    contact_user_ids: list[int] | set[int],
) -> dict[int, str]:
    if not contact_user_ids:
        return {}

    result = db.execute(
        select(UserContactAlias).where(
            UserContactAlias.owner_user_id == owner_user_id,
            UserContactAlias.contact_user_id.in_(contact_user_ids),
        )
    )

    return {
        item.contact_user_id: item.alias
        for item in result.scalars().all()
    }


def build_contact_response(
    user: User,
    contact_alias: str | None = None,
) -> dict:
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "contact_alias": contact_alias,
        "display_name": format_user_display_name(
            user=user,
            contact_alias=contact_alias,
        ),
    }


def upsert_contact_alias(
    db: Session,
    owner_user_id: int,
    contact_user_id: int,
    alias: str | None,
) -> UserContactAlias | None:
    normalized_alias = (alias or "").strip()

    result = db.execute(
        select(UserContactAlias).where(
            UserContactAlias.owner_user_id == owner_user_id,
            UserContactAlias.contact_user_id == contact_user_id,
        )
    )
    contact_alias = result.scalar_one_or_none()

    if not normalized_alias:
        if contact_alias is not None:
            db.delete(contact_alias)
            db.commit()

        return None

    if contact_alias is None:
        contact_alias = UserContactAlias(
            owner_user_id=owner_user_id,
            contact_user_id=contact_user_id,
            alias=normalized_alias,
        )
        db.add(contact_alias)
    else:
        contact_alias.alias = normalized_alias

    db.commit()
    db.refresh(contact_alias)

    return contact_alias
