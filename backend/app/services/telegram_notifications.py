import json
import logging
import urllib.error
import urllib.request
from decimal import Decimal
from typing import Any

from app.config import settings
from app.models.loan import Loan
from app.models.user import User

logger = logging.getLogger(__name__)


def format_money(amount: Decimal) -> str:
    value = amount.quantize(Decimal("1"))

    return f"{value:,.0f}".replace(",", " ")


def get_user_name(user: User | None) -> str:
    if user is None:
        return "Пользователь"

    if user.first_name:
        return user.first_name

    if user.username:
        return user.username

    return f"Пользователь #{user.id}"


def send_telegram_message(
    telegram_id: int | None,
    text: str,
) -> None:
    if telegram_id is None:
        return

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"

    payload: dict[str, Any] = {
        "chat_id": telegram_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
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
        logger.exception(
            "Telegram notification failed with HTTP error",
        )
    except urllib.error.URLError:
        logger.exception(
            "Telegram notification failed with URL error",
        )
    except Exception:
        logger.exception(
            "Telegram notification failed with unexpected error",
        )


def notify_loan_created(
    loan: Loan,
) -> None:
    lender_name = get_user_name(loan.lender)

    description = loan.description or "Без описания"

    text = (
        f"{lender_name} создал для вас займ\n"
        f"Сумма: {format_money(loan.amount)} ₽\n"
        f"Описание: {description}"
    )

    send_telegram_message(
        telegram_id=loan.borrower.telegram_id,
        text=text,
    )


def notify_loan_confirmed(
    loan: Loan,
) -> None:
    borrower_name = get_user_name(loan.borrower)

    text = (
        f"{borrower_name} подтвердил займ #{loan.id}\n"
        f"Сумма: {format_money(loan.amount)} ₽"
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=text,
    )


def notify_loan_rejected(
    loan: Loan,
) -> None:
    borrower_name = get_user_name(loan.borrower)

    text = f"{borrower_name} отклонил займ #{loan.id}"

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=text,
    )


def notify_partial_payment(
    loan: Loan,
    payment_amount: Decimal,
    remaining_balance: Decimal,
) -> None:
    text = (
        f"Поступил платёж по займу #{loan.id}\n"
        f"Сумма: {format_money(payment_amount)} ₽\n"
        f"Остаток: {format_money(remaining_balance)} ₽"
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=text,
    )

    send_telegram_message(
        telegram_id=loan.borrower.telegram_id,
        text=text,
    )


def notify_loan_paid(
    loan: Loan,
) -> None:
    text = f"Займ #{loan.id} полностью погашен"

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=text,
    )

    send_telegram_message(
        telegram_id=loan.borrower.telegram_id,
        text=text,
    )