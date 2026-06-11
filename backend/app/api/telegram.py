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
    ),
) -> None:
    if not settings.TELEGRAM_WEBHOOK_SECRET:
        return

    if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
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