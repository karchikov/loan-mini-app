from secrets import compare_digest
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services.telegram_callback_service import handle_telegram_callback

router = APIRouter(
    prefix="/telegram",
    tags=["telegram"],
)


def verify_telegram_secret(
    x_telegram_bot_api_secret_token: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
) -> None:
    if not settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Telegram webhook secret is not configured",
        )

    if not x_telegram_bot_api_secret_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing Telegram webhook secret",
        )

    if not compare_digest(
        x_telegram_bot_api_secret_token,
        settings.TELEGRAM_WEBHOOK_SECRET,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Telegram webhook secret",
        )


@router.post("/webhook")
def telegram_webhook(
    update: dict[str, Any],
    db: Session = Depends(get_db),
    _: None = Depends(verify_telegram_secret),
):
    return handle_telegram_callback(
        db=db,
        update=update,
    )