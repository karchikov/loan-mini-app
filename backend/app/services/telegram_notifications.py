from html import escape
import json
import logging
import urllib.error
import urllib.request
from decimal import Decimal
from typing import Any
from urllib.parse import quote

from app.config import settings
from app.models.loan import Loan
from app.models.user import User

logger = logging.getLogger(__name__)


def format_money(amount: Decimal) -> str:
    value = amount.quantize(Decimal("0.01"))

    return f"{value:,.2f}".replace(",", " ")


def format_date(value) -> str:
    if value is None:
        return "не указана"

    date_value = value.date() if hasattr(value, "date") else value

    return date_value.strftime("%d.%m.%Y")


def get_user_name(user: User | None) -> str:
    if user is None:
        return "Пользователь"

    if user.first_name:
        return escape(user.first_name)

    if user.username:
        return escape(user.username)

    return f"Пользователь #{user.id}"


def build_mini_app_url(
    start_param: str | None = None,
) -> str | None:
    bot_username = settings.TELEGRAM_BOT_USERNAME

    if not bot_username:
        return None

    normalized_bot_username = bot_username.lstrip("@")

    if settings.TELEGRAM_MINI_APP_SHORT_NAME:
        mini_app_name = settings.TELEGRAM_MINI_APP_SHORT_NAME.strip("/")
        base_url = f"https://t.me/{normalized_bot_username}/{mini_app_name}"
    else:
        base_url = f"https://t.me/{normalized_bot_username}"

    if not start_param:
        return base_url

    encoded_start_param = quote(
        start_param,
        safe="",
    )

    return f"{base_url}?startapp={encoded_start_param}"


def build_open_loan_keyboard(
    loan_id: int,
) -> dict[str, Any] | None:
    mini_app_url = build_mini_app_url(
        start_param=f"loan_{loan_id}",
    )

    if not mini_app_url:
        return None

    return {
        "inline_keyboard": [
            [
                {
                    "text": "Открыть приложение",
                    "url": mini_app_url,
                },
            ],
        ],
    }


def append_open_loan_button(
    reply_markup: dict[str, Any],
    loan_id: int,
) -> dict[str, Any]:
    mini_app_url = build_mini_app_url(
        start_param=f"loan_{loan_id}",
    )

    if not mini_app_url:
        return reply_markup

    keyboard_rows = [
        list(row)
        for row in reply_markup.get("inline_keyboard", [])
    ]

    keyboard_rows.append(
        [
            {
                "text": "Открыть приложение",
                "url": mini_app_url,
            },
        ]
    )

    return {
        "inline_keyboard": keyboard_rows,
    }


def send_telegram_message(
    telegram_id: int | None,
    text: str,
    reply_markup: dict[str, Any] | None = None,
) -> bool:
    if telegram_id is None:
        logger.warning("Telegram notification skipped: telegram_id is missing")

        return False

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"

    payload: dict[str, Any] = {
        "chat_id": telegram_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "disable_notification": False,
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

        logger.info(
            "Telegram notification sent: telegram_id=%s",
            telegram_id,
        )

        return True
    except urllib.error.HTTPError as error:
        error_body = ""

        try:
            error_body = error.read().decode("utf-8")[:1000]
        except Exception:
            error_body = "<failed to read Telegram error body>"

        logger.exception(
            "Telegram notification failed with HTTP error: "
            "telegram_id=%s status=%s reason=%s body=%s",
            telegram_id,
            error.code,
            error.reason,
            error_body,
        )
    except urllib.error.URLError as error:
        logger.exception(
            "Telegram notification failed with URL error: telegram_id=%s reason=%s",
            telegram_id,
            error.reason,
        )
    except Exception:
        logger.exception(
            "Telegram notification failed with unexpected error: telegram_id=%s",
            telegram_id,
        )

    return False


def build_loan_request_keyboard(
    loan_id: int,
) -> dict[str, Any]:
    reply_markup = {
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

    return append_open_loan_button(
        reply_markup=reply_markup,
        loan_id=loan_id,
    )


def build_mark_paid_keyboard(
    loan_id: int,
) -> dict[str, Any]:
    reply_markup = {
        "inline_keyboard": [
            [
                {
                    "text": "Подтвердить закрытие",
                    "callback_data": f"loan:mark_paid:{loan_id}",
                },
            ],
        ],
    }

    return append_open_loan_button(
        reply_markup=reply_markup,
        loan_id=loan_id,
    )


def build_repayment_confirmation_keyboard(
    loan_id: int,
    repayment_id: int,
) -> dict[str, Any]:
    reply_markup = {
        "inline_keyboard": [
            [
                {
                    "text": "Подтвердить платеж",
                    "callback_data": f"repayment:confirm:{repayment_id}",
                },
                {
                    "text": "Отклонить платеж",
                    "callback_data": f"repayment:reject:{repayment_id}",
                },
            ],
        ],
    }

    return append_open_loan_button(
        reply_markup=reply_markup,
        loan_id=loan_id,
    )


def notify_loan_created(
    loan: Loan,
) -> None:
    borrower_name = get_user_name(loan.borrower)
    lender_name = get_user_name(loan.lender)

    lender_text = (
        f"Новый запрос займа #{loan.id}\n\n"
        f"Заемщик: {borrower_name}\n"
        f"Сумма: {format_money(loan.amount)} {loan.currency}\n\n"
        f"Вы можете подтвердить или отклонить заявку прямо здесь."
    )

    borrower_text = (
        f"Заявка на займ #{loan.id} отправлена кредитору.\n\n"
        f"Кредитор: {lender_name}\n"
        f"Сумма: {format_money(loan.amount)} {loan.currency}\n\n"
        f"Ожидается действие кредитора."
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=lender_text,
        reply_markup=build_loan_request_keyboard(
            loan_id=loan.id,
        ),
    )

    if loan.borrower.telegram_id != loan.lender.telegram_id:
        send_telegram_message(
            telegram_id=loan.borrower.telegram_id,
            text=borrower_text,
            reply_markup=build_open_loan_keyboard(
                loan_id=loan.id,
            ),
        )


def notify_loan_funding_pending(
    loan: Loan,
    activation_code: str,
) -> None:
    borrower_name = get_user_name(loan.borrower)
    lender_name = get_user_name(loan.lender)

    lender_text = (
        f"Вы подтвердили готовность передать средства по займу #{loan.id}.\n\n"
        f"Заемщик: {borrower_name}\n"
        f"Сумма: {format_money(loan.amount)} {loan.currency}\n\n"
        f"После фактической передачи денежных средств вне приложения заемщик "
        f"должен подтвердить получение в приложении.\n"
        f"Кодовый вариант доступен в приложении как усиленное подтверждение."
    )

    borrower_text = (
        f"Кредитор подтвердил готовность передать средства по займу #{loan.id}.\n\n"
        f"Кредитор: {lender_name}\n"
        f"Сумма: {format_money(loan.amount)} {loan.currency}\n\n"
        f"После фактического получения денежных средств вне приложения "
        f"подтвердите получение в карточке займа."
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=lender_text,
        reply_markup=build_open_loan_keyboard(
            loan_id=loan.id,
        ),
    )

    if loan.borrower.telegram_id != loan.lender.telegram_id:
        send_telegram_message(
            telegram_id=loan.borrower.telegram_id,
            text=borrower_text,
            reply_markup=build_open_loan_keyboard(
                loan_id=loan.id,
            ),
        )


def notify_funding_activation_code_regenerated(
    loan: Loan,
    activation_code: str,
) -> None:
    borrower_name = get_user_name(loan.borrower)

    text = (
        f"Сгенерирован новый код усиленного подтверждения по займу #{loan.id}.\n\n"
        f"Заемщик: {borrower_name}\n"
        f"Сумма: {format_money(loan.amount)} {loan.currency}\n\n"
        f"Новый код: <b>{activation_code}</b>\n\n"
        f"Старый код больше не действует. Кодовый сценарий остается резервным."
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=text,
        reply_markup=build_open_loan_keyboard(
            loan_id=loan.id,
        ),
    )


def notify_loan_activated(
    loan: Loan,
) -> None:
    borrower_name = get_user_name(loan.borrower)
    lender_name = get_user_name(loan.lender)

    lender_text = (
        f"Займ #{loan.id} активирован.\n\n"
        f"Заемщик: {borrower_name}\n"
        f"Сумма: {format_money(loan.amount)} {loan.currency}\n\n"
        f"Заемщик подтвердил фактическое получение денежных средств вне приложения."
    )

    borrower_text = (
        f"Вы подтвердили фактическое получение средств по займу #{loan.id}.\n\n"
        f"Кредитор: {lender_name}\n"
        f"Сумма: {format_money(loan.amount)} {loan.currency}\n\n"
        f"Займ переведен в статус активного."
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=lender_text,
        reply_markup=build_open_loan_keyboard(
            loan_id=loan.id,
        ),
    )

    if loan.borrower.telegram_id != loan.lender.telegram_id:
        send_telegram_message(
            telegram_id=loan.borrower.telegram_id,
            text=borrower_text,
            reply_markup=build_open_loan_keyboard(
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
        reply_markup=build_open_loan_keyboard(
            loan_id=loan.id,
        ),
    )


def notify_loan_rejected(
    loan: Loan,
) -> None:
    borrower_name = get_user_name(loan.borrower)
    lender_name = get_user_name(loan.lender)

    lender_text = (
        f"Вы отклонили заявку на займ #{loan.id}.\n\n"
        f"Заемщик: {borrower_name}\n"
        f"Сумма: {format_money(loan.amount)} {loan.currency}"
    )

    borrower_text = (
        f"Заявка на займ #{loan.id} отклонена.\n\n"
        f"Кредитор: {lender_name}\n"
        f"Сумма: {format_money(loan.amount)} {loan.currency}"
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=lender_text,
        reply_markup=build_open_loan_keyboard(
            loan_id=loan.id,
        ),
    )

    if loan.borrower.telegram_id != loan.lender.telegram_id:
        send_telegram_message(
            telegram_id=loan.borrower.telegram_id,
            text=borrower_text,
            reply_markup=build_open_loan_keyboard(
                loan_id=loan.id,
            ),
        )


def notify_loan_expired(
    loan: Loan,
    previous_status: str | None = None,
) -> None:
    borrower_name = get_user_name(loan.borrower)
    lender_name = get_user_name(loan.lender)
    due_date_text = format_date(loan.due_date)

    if previous_status == "funding_pending":
        reason_text = "подтверждение получения не было завершено до срока возврата"
    else:
        reason_text = "заявка не была подтверждена до срока возврата"

    lender_text = (
        f"Срок заявки по займу #{loan.id} истек.\n\n"
        f"Заемщик: {borrower_name}\n"
        f"Сумма: {format_money(loan.amount)} {loan.currency}\n"
        f"Дата возврата: {due_date_text}\n\n"
        f"Причина: {reason_text}."
    )

    borrower_text = (
        f"Срок заявки по займу #{loan.id} истек.\n\n"
        f"Кредитор: {lender_name}\n"
        f"Сумма: {format_money(loan.amount)} {loan.currency}\n"
        f"Дата возврата: {due_date_text}\n\n"
        f"Причина: {reason_text}."
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=lender_text,
        reply_markup=build_open_loan_keyboard(
            loan_id=loan.id,
        ),
    )

    if loan.borrower.telegram_id != loan.lender.telegram_id:
        send_telegram_message(
            telegram_id=loan.borrower.telegram_id,
            text=borrower_text,
            reply_markup=build_open_loan_keyboard(
                loan_id=loan.id,
            ),
        )


def notify_repayment_submitted(
    loan: Loan,
    repayment_id: int,
    payment_amount: Decimal,
) -> None:
    borrower_name = get_user_name(loan.borrower)

    lender_text = (
        f"Заемщик отправил платеж по займу #{loan.id}.\n\n"
        f"Заемщик: {borrower_name}\n"
        f"Платеж: {format_money(payment_amount)} {loan.currency}\n\n"
        f"Остаток займа пока не уменьшен. Подтвердите платеж, если деньги получены."
    )

    borrower_text = (
        f"Платеж по займу #{loan.id} отправлен на подтверждение.\n\n"
        f"Платеж: {format_money(payment_amount)} {loan.currency}\n"
        f"Остаток займа уменьшится только после подтверждения кредитором."
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=lender_text,
        reply_markup=build_repayment_confirmation_keyboard(
            loan_id=loan.id,
            repayment_id=repayment_id,
        ),
    )

    if loan.borrower.telegram_id != loan.lender.telegram_id:
        send_telegram_message(
            telegram_id=loan.borrower.telegram_id,
            text=borrower_text,
            reply_markup=build_open_loan_keyboard(
                loan_id=loan.id,
            ),
        )


def notify_repayment_confirmed(
    loan: Loan,
    payment_amount: Decimal,
    remaining_balance: Decimal,
) -> None:
    text = (
        f"Платеж по займу #{loan.id} подтвержден.\n\n"
        f"Платеж: {format_money(payment_amount)} {loan.currency}\n"
        f"Остаток: {format_money(remaining_balance)} {loan.currency}"
    )

    reply_markup = build_open_loan_keyboard(
        loan_id=loan.id,
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=text,
        reply_markup=reply_markup,
    )

    if loan.borrower.telegram_id != loan.lender.telegram_id:
        send_telegram_message(
            telegram_id=loan.borrower.telegram_id,
            text=text,
            reply_markup=reply_markup,
        )


def notify_repayment_rejected(
    loan: Loan,
    payment_amount: Decimal,
) -> None:
    borrower_name = get_user_name(loan.borrower)
    lender_name = get_user_name(loan.lender)

    lender_text = (
        f"Вы отклонили платеж по займу #{loan.id}.\n\n"
        f"Заемщик: {borrower_name}\n"
        f"Платеж: {format_money(payment_amount)} {loan.currency}\n"
        f"Остаток займа не изменился."
    )

    borrower_text = (
        f"Платеж по займу #{loan.id} отклонен.\n\n"
        f"Кредитор: {lender_name}\n"
        f"Платеж: {format_money(payment_amount)} {loan.currency}\n"
        f"Остаток займа не изменился."
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=lender_text,
        reply_markup=build_open_loan_keyboard(
            loan_id=loan.id,
        ),
    )

    if loan.borrower.telegram_id != loan.lender.telegram_id:
        send_telegram_message(
            telegram_id=loan.borrower.telegram_id,
            text=borrower_text,
            reply_markup=build_open_loan_keyboard(
                loan_id=loan.id,
            ),
        )


def notify_partial_payment(
    loan: Loan,
    payment_amount: Decimal,
    remaining_balance: Decimal,
) -> None:
    borrower_name = get_user_name(loan.borrower)

    text = (
        f"Поступил частичный платеж по займу #{loan.id}\n\n"
        f"Заемщик: {borrower_name}\n"
        f"Платеж: {format_money(payment_amount)} {loan.currency}\n"
        f"Остаток: {format_money(remaining_balance)} {loan.currency}"
    )

    reply_markup = build_open_loan_keyboard(
        loan_id=loan.id,
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=text,
        reply_markup=reply_markup,
    )

    if loan.borrower.telegram_id != loan.lender.telegram_id:
        send_telegram_message(
            telegram_id=loan.borrower.telegram_id,
            text=text,
            reply_markup=reply_markup,
        )


def notify_final_repayment_submitted(
    loan: Loan,
    payment_amount: Decimal,
) -> None:
    borrower_name = get_user_name(loan.borrower)

    lender_text = (
        f"Заемщик сообщил о полном погашении займа #{loan.id}\n\n"
        f"Заемщик: {borrower_name}\n"
        f"Последний платеж: {format_money(payment_amount)} {loan.currency}\n\n"
        f"Подтвердите закрытие займа, если деньги получены."
    )

    borrower_text = (
        f"Последний платеж по займу #{loan.id} отправлен.\n\n"
        f"Платеж: {format_money(payment_amount)} {loan.currency}\n"
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
            reply_markup=build_open_loan_keyboard(
                loan_id=loan.id,
            ),
        )


def notify_loan_paid(
    loan: Loan,
) -> None:
    text = (
        f"Займ #{loan.id} закрыт.\n\n"
        f"Кредитор подтвердил полное погашение."
    )

    reply_markup = build_open_loan_keyboard(
        loan_id=loan.id,
    )

    send_telegram_message(
        telegram_id=loan.lender.telegram_id,
        text=text,
        reply_markup=reply_markup,
    )

    if loan.borrower.telegram_id != loan.lender.telegram_id:
        send_telegram_message(
            telegram_id=loan.borrower.telegram_id,
            text=text,
            reply_markup=reply_markup,
        )
