from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class File:
    filename: str
    hash: str
    size: int
    content_type: str | None = None
    uploaded_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
