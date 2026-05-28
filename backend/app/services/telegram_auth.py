import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.config import settings


def validate_telegram_init_data(init_data: str) -> dict:
    parsed_data = dict(parse_qsl(init_data))

    received_hash = parsed_data.pop("hash", None)

    if not received_hash:
        raise ValueError("Telegram hash missing")

    auth_date = parsed_data.get("auth_date")

    if not auth_date:
        raise ValueError("auth_date missing")

    auth_timestamp = int(auth_date)

    current_timestamp = int(time.time())

    if (
        current_timestamp - auth_timestamp
        > settings.TELEGRAM_AUTH_EXPIRE_SECONDS
    ):
        raise ValueError("Telegram auth expired")

    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(parsed_data.items())
    )

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=settings.BOT_TOKEN.encode(),
        digestmod=hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if calculated_hash != received_hash:
        raise ValueError("Invalid Telegram signature")

    user_data = json.loads(parsed_data["user"])

    return user_data