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
    value = amount.quantize(Decimal("0.01"))

    return f"{value:,.2f}".replace(",", " ")


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
    reply_markup: dict[str, Any] | None = None,
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

    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

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
        logger.exception("Telegram notification failed with HTTP error")
    except urllib.error.URLError:
        logger.exception("Telegram notification failed with URL error")
    except Exception:
        logger.exception("Telegram notification failed with unexpected error")


def build_loan_request_keyboard(
    loan_id: int,
) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {
                    "text": "Подтвердить",
                    "callback_data": f"loan:confirm:{loan_id}",
                },
                {
                    "text": "Отклонить",
                    "callback_data": f"loan:reject:{loan_id}",
                },
            ],
        ],
    }


def build_mark_paid_keyboard(
    loan_id: int,
) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {
                    "text": "Подтвердить закрытие",
                    "callback_data": f"loan:mark_paid:{loan_id}",
                },
            ],
        ],
    }


def notify_loan_created(
    loan: Loan,
) -> None:
    borrower_name = get_user_name(loan.borrower)

    text = (
        f"Новый запрос займа #{loan.id}\n\n"
        f"Заёмщик: {borrower_name}\n"
        f"Сумма: {format_money(loan.amount)} {loan.currency}\n\n"
        f"Вы можете подтвердить или отклонить заявку прямо здесь."
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=text,
        reply_markup=build_loan_request_keyboard(
            loan_id=loan.id,
        ),
    )


def notify_loan_confirmed(
    loan: Loan,
) -> None:
    lender_name = get_user_name(loan.lender)

    text = (
        f"Заявка на займ #{loan.id} подтверждена.\n\n"
        f"Кредитор: {lender_name}\n"
        f"Сумма: {format_money(loan.amount)} {loan.currency}"
    )

    send_telegram_message(
        telegram_id=loan.borrower.telegram_id,
        text=text,
    )


def notify_loan_rejected(
    loan: Loan,
) -> None:
    lender_name = get_user_name(loan.lender)

    text = (
        f"Заявка на займ #{loan.id} отклонена.\n\n"
        f"Кредитор: {lender_name}"
    )

    send_telegram_message(
        telegram_id=loan.borrower.telegram_id,
        text=text,
    )


def notify_partial_payment(
    loan: Loan,
    payment_amount: Decimal,
    remaining_balance: Decimal,
) -> None:
    borrower_name = get_user_name(loan.borrower)

    text = (
        f"Поступил частичный платёж по займу #{loan.id}\n\n"
        f"Заёмщик: {borrower_name}\n"
        f"Платёж: {format_money(payment_amount)} {loan.currency}\n"
        f"Остаток: {format_money(remaining_balance)} {loan.currency}"
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=text,
    )

    if loan.borrower.telegram_id != loan.lender.telegram_id:
        send_telegram_message(
            telegram_id=loan.borrower.telegram_id,
            text=text,
        )


def notify_final_repayment_submitted(
    loan: Loan,
    payment_amount: Decimal,
) -> None:
    borrower_name = get_user_name(loan.borrower)

    lender_text = (
        f"Заёмщик сообщил о полном погашении займа #{loan.id}\n\n"
        f"Заёмщик: {borrower_name}\n"
        f"Последний платёж: {format_money(payment_amount)} {loan.currency}\n\n"
        f"Подтвердите закрытие займа, если деньги получены."
    )

    borrower_text = (
        f"Последний платёж по займу #{loan.id} отправлен.\n\n"
        f"Платёж: {format_money(payment_amount)} {loan.currency}\n"
        f"Займ ожидает подтверждения закрытия кредитором."
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=lender_text,
        reply_markup=build_mark_paid_keyboard(
            loan_id=loan.id,
        ),
    )

    if loan.borrower.telegram_id != loan.lender.telegram_id:
        send_telegram_message(
            telegram_id=loan.borrower.telegram_id,
            text=borrower_text,
        )


def notify_loan_paid(
    loan: Loan,
) -> None:
    text = (
        f"Займ #{loan.id} закрыт.\n\n"
        f"Кредитор подтвердил полное погашение."
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=text,
    )

    if loan.borrower.telegram_id != loan.lender.telegram_id:
        send_telegram_message(
            telegram_id=loan.borrower.telegram_id,
            text=text,
        )