from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginResponse
from app.services.auth import create_access_token
from app.services.telegram_auth import (
    validate_telegram_init_data,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/dev-login", response_model=LoginResponse)
async def dev_login(
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )

        db.add(user)

        await db.commit()

        await db.refresh(user)

    access_token = create_access_token(
        data={"sub": str(user.id)}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/telegram", response_model=LoginResponse)
async def telegram_login(
    init_data: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        telegram_user = validate_telegram_init_data(
            init_data
        )

    except Exception as error:
        raise HTTPException(
            status_code=401,
            detail=str(error),
        )

    telegram_id = telegram_user["id"]

    result = await db.execute(
        select(User).where(
            User.telegram_id == telegram_id
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_user["id"],
            username=telegram_user.get("username"),
            first_name=telegram_user.get(
                "first_name",
                "Telegram",
            ),
            last_name=telegram_user.get(
                "last_name"
            ),
        )

        db.add(user)

    else:
        user.username = telegram_user.get(
            "username"
        )

        user.first_name = telegram_user.get(
            "first_name",
            user.first_name,
        )

        user.last_name = telegram_user.get(
            "last_name"
        )

    await db.commit()

    await db.refresh(user)

    access_token = create_access_token(
        data={"sub": str(user.id)}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }