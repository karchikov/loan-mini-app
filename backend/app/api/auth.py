from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginResponse
from app.services.auth import create_access_token
from app.services.telegram_auth import validate_telegram_init_data

router = APIRouter(prefix="/auth", tags=["auth"])


def apply_invite_if_needed(
    db: Session,
    user: User,
    telegram_id: int,
    start_param: str | None,
) -> None:
    if not start_param:
        return

    if user.invited_by_user_id is not None:
        return

    inviter_result = db.execute(
        select(User).where(User.invite_code == start_param)
    )

    inviter = inviter_result.scalar_one_or_none()

    if inviter is None:
        return

    if inviter.telegram_id == telegram_id:
        return

    user.invited_by_user_id = inviter.id


@router.post("/dev-login", response_model=LoginResponse)
def dev_login(
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    db: Session = Depends(get_db),
):
    if not settings.ENABLE_DEV_LOGIN:
        raise HTTPException(
            status_code=404,
            detail="Not found",
        )

    result = db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name or "Dev",
            last_name=last_name,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(
        data={"sub": str(user.id)}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/telegram", response_model=LoginResponse)
def telegram_login(
    init_data: str,
    db: Session = Depends(get_db),
):
    try:
        telegram_user = validate_telegram_init_data(init_data)

    except Exception as error:
        raise HTTPException(
            status_code=401,
            detail=str(error),
        )

    telegram_id = telegram_user["id"]
    start_param = telegram_user.get("start_param")

    result = db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_user["id"],
            username=telegram_user.get("username"),
            first_name=telegram_user.get("first_name", "Telegram"),
            last_name=telegram_user.get("last_name"),
        )

        apply_invite_if_needed(
            db=db,
            user=user,
            telegram_id=telegram_id,
            start_param=start_param,
        )

        db.add(user)

    else:
        user.username = telegram_user.get("username")
        user.first_name = telegram_user.get(
            "first_name",
            user.first_name,
        )
        user.last_name = telegram_user.get("last_name")

        apply_invite_if_needed(
            db=db,
            user=user,
            telegram_id=telegram_id,
            start_param=start_param,
        )

    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        data={"sub": str(user.id)}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }