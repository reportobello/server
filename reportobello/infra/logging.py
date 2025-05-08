import json
import logging
import logging.handlers
from typing import Any

empty_record = logging.LogRecord("", 0, "", 0, None, None, None, None, None)
reserved_log_names = empty_record.__dict__.keys()


class LogFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        self.default_msec_format = "%s.%03d"
        self.default_time_format = "%Y-%m-%dT%H:%M:%S"

        super().__init__(*args, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        super().format(record)

        metadata = {"lvl": record.levelname} | {
            k: v
            for k, v in record.__dict__.items()
            if k not in reserved_log_names
        }

        time = self.formatTime(record)

        return f"{time} {json.dumps(metadata, separators=(',', ':'))}"


def setup_logging() -> None:
    setup_uvicorn_logging()

    formatter = LogFormatter()

    logger = logging.getLogger("reportobello")
    logger.setLevel(logging.INFO)

    handler = logging.handlers.TimedRotatingFileHandler(filename="logs/logs", when="H")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def setup_uvicorn_logging() -> None:
    logger = logging.getLogger("uvicorn.default")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(handler)


def get_uvicorn_logging_config() -> dict[str, Any]:
    import uvicorn.config  # noqa: PLC0415

    log_config = uvicorn.config.LOGGING_CONFIG

    datefmt = "%Y-%m-%dT%H:%M:%S"
    formatters = log_config["formatters"]
    formatters["default"]["fmt"] = "%(asctime)s.%(msecs)03d %(levelprefix)s %(message)s"
    formatters["access"]["fmt"] = '%(asctime)s.%(msecs)03d %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'
    formatters["access"]["datefmt"] = datefmt
    formatters["default"]["datefmt"] = datefmt

    return log_config
