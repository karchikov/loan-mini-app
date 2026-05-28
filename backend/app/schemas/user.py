from pydantic import BaseModel


class UserRead(BaseModel):
    id: int
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None

    model_config = {
        "from_attributes": True
    }