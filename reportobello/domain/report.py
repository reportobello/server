from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(kw_only=True)
class Report:
    filename: str | None
    requested_version: int
    actual_version: int
    template_name: str
    started_at: datetime
    finished_at: datetime
    expires_at: datetime
    error_message: str | None = None
    data: str = ""
    data_type: str = "json"
    hash: str = ""

    @property
    def was_successful(self) -> bool:
        return self.error_message is None

    def as_json(self) -> dict[str, Any]:
        tmp = asdict(self)

        tmp["started_at"] = tmp.pop("started_at").isoformat()
        tmp["finished_at"] = tmp.pop("finished_at").isoformat()
        tmp["expires_at"] = tmp.pop("expires_at").isoformat()

        return tmp
