from dataclasses import dataclass, field
from datetime import UTC, datetime

ApiKey = str
UserId = int


@dataclass
class User:
    id: UserId
    api_key: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    provider: str = "reportobello"
    provider_user_id: str = ""
    username: str = ""
    is_setting_up_account: bool = True
    email: str | None = None

    @property
    def is_demo_user(self) -> bool:
        return self.provider == "reportobello" and self.username == "demo"

    @property
    def is_admin(self) -> bool:
        return self.provider == "reportobello" and self.username == "admin"
