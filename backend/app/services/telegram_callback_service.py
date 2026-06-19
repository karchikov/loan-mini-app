import json
import logging
import urllib.error
import urllib.request
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.repayment import Repayment
from app.models.user import User
from app.services.loan_service import (
    confirm_loan,
    confirm_repayment,
    mark_loan_as_paid,
    reject_loan,
    reject_repayment,
)

logger = logging.getLogger(__name__)


def answer_callback_query(
    callback_query_id: str,
    text: str,
    show_alert: bool = False,
) -> None:
    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/answerCallbackQuery"

    payload: dict[str, Any] = {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": show_alert,
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=5,
        ) as response:
            response.read()
    except urllib.error.HTTPError:
        logger.exception("Telegram answerCallbackQuery failed with HTTP error")
    except urllib.error.URLError:
        logger.exception("Telegram answerCallbackQuery failed with URL error")
    except Exception:
        logger.exception("Telegram answerCallbackQuery failed with unexpected error")


def edit_message_reply_markup(
    chat_id: int,
    message_id: int,
) -> None:
    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/editMessageReplyMarkup"

    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reply_markup": {
            "inline_keyboard": [],
        },
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=5,
        ) as response:
            response.read()
    except urllib.error.HTTPError:
        logger.exception("Telegram editMessageReplyMarkup failed with HTTP error")
    except urllib.error.URLError:
        logger.exception("Telegram editMessageReplyMarkup failed with URL error")
    except Exception:
        logger.exception("Telegram editMessageReplyMarkup failed with unexpected error")


def get_user_by_telegram_id(
    db: Session,
    telegram_id: int,
) -> User | None:
    result = db.execute(
        select(User).where(
            User.telegram_id == telegram_id
        )
    )

    return result.scalar_one_or_none()


def get_repayment_by_id(
    db: Session,
    repayment_id: int,
) -> Repayment | None:
    result = db.execute(
        select(Repayment).where(
            Repayment.id == repayment_id
        )
    )

    return result.scalar_one_or_none()


def parse_callback_data(
    callback_data: str,
) -> tuple[str, str, int]:
    parts = callback_data.split(":")

    if len(parts) != 3:
        raise ValueError("Invalid callback data format")

    entity, action, raw_object_id = parts

    if entity not in [
        "loan",
        "repayment",
    ]:
        raise ValueError("Unsupported callback entity")

    object_id = int(raw_object_id)

    return entity, action, object_id


def handle_loan_callback(
    db: Session,
    action: str,
    loan_id: int,
    user: User,
) -> str:
    if action == "confirm":
        confirm_loan(
            db=db,
            loan_id=loan_id,
            current_user=user,
        )

        return "Займ подтвержден."

    if action == "reject":
        reject_loan(
            db=db,
            loan_id=loan_id,
            current_user=user,
        )

        return "Заявка отклонена."

    if action == "mark_paid":
        mark_loan_as_paid(
            db=db,
            loan_id=loan_id,
            current_user=user,
        )

        return "Закрытие займа подтверждено."

    raise ValueError("Unsupported loan callback action")


def handle_repayment_callback(
    db: Session,
    action: str,
    repayment_id: int,
    user: User,
) -> str:
    repayment = get_repayment_by_id(
        db=db,
        repayment_id=repayment_id,
    )

    if repayment is None:
        raise HTTPException(
            status_code=404,
            detail="Repayment not found",
        )

    if action == "confirm":
        confirm_repayment(
            db=db,
            loan_id=repayment.loan_id,
            repayment_id=repayment.id,
            current_user=user,
        )

        return "Платеж подтвержден."

    if action == "reject":
        reject_repayment(
            db=db,
            loan_id=repayment.loan_id,
            repayment_id=repayment.id,
            current_user=user,
        )

        return "Платеж отклонен."

    raise ValueError("Unsupported repayment callback action")


def handle_telegram_callback(
    db: Session,
    update: dict[str, Any],
) -> dict[str, str]:
    callback_query = update.get("callback_query")

    if not callback_query:
        return {
            "status": "ignored",
        }

    callback_query_id = callback_query.get("id")
    callback_data = callback_query.get("data")
    telegram_user = callback_query.get("from") or {}
    telegram_id = telegram_user.get("id")

    message = callback_query.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    message_id = message.get("message_id")

    if not callback_query_id:
        return {
            "status": "ignored",
        }

    if not callback_data or telegram_id is None:
        answer_callback_query(
            callback_query_id=callback_query_id,
            text="Не удалось обработать действие.",
            show_alert=True,
        )

        return {
            "status": "invalid_callback",
        }

    user = get_user_by_telegram_id(
        db=db,
        telegram_id=int(telegram_id),
    )

    if user is None:
        answer_callback_query(
            callback_query_id=callback_query_id,
            text="Пользователь не найден. Откройте приложение через Telegram.",
            show_alert=True,
        )

        return {
            "status": "user_not_found",
        }

    try:
        entity, action, object_id = parse_callback_data(
            callback_data=callback_data,
        )

        if entity == "loan":
            answer_text = handle_loan_callback(
                db=db,
                action=action,
                loan_id=object_id,
                user=user,
            )
        elif entity == "repayment":
            answer_text = handle_repayment_callback(
                db=db,
                action=action,
                repayment_id=object_id,
                user=user,
            )
        else:
            raise ValueError("Unsupported callback entity")

        if chat_id is not None and message_id is not None:
            edit_message_reply_markup(
                chat_id=int(chat_id),
                message_id=int(message_id),
            )

        answer_callback_query(
            callback_query_id=callback_query_id,
            text=answer_text,
            show_alert=False,
        )

        return {
            "status": "ok",
        }

    except HTTPException as error:
        db.rollback()

        answer_callback_query(
            callback_query_id=callback_query_id,
            text=str(error.detail),
            show_alert=True,
        )

        return {
            "status": "business_error",
        }

    except Exception:
        db.rollback()

        logger.exception("Telegram callback processing failed")

        answer_callback_query(
            callback_query_id=callback_query_id,
            text="Не удалось выполнить действие.",
            show_alert=True,
        )

        return {
            "status": "error",
        }