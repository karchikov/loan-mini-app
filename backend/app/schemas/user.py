from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class UserShortResponse(BaseModel):
    id: int
    username: str | None = None
    first_name: str | None = None

    model_config = {
        "from_attributes": True
    }


class UserRead(BaseModel):
    id: int
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    role: str = "user"

    model_config = {
        "from_attributes": True
    }


class UserNetworkRead(BaseModel):
    id: int
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    contact_alias: str | None = None
    display_name: str | None = None

    model_config = {
        "from_attributes": True
    }


class UserContactAliasUpdate(BaseModel):
    alias: str | None = Field(
        default=None,
        max_length=255,
    )


class UserSummaryResponse(BaseModel):
    my_debts: Decimal
    owed_to_me: Decimal
    balance: Decimal
    active_loans_count: int


class UserInviteResponse(BaseModel):
    invite_code: str
    invite_link: str


class UserHistoryItemResponse(BaseModel):
    id: str
    type: str
    title: str
    description: str
    amount: Decimal | None = None
    created_at: datetime
