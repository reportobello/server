import asyncio
import logging
from datetime import datetime, timezone

from opentelemetry import trace
from reportobello.config import PDF_ARTIFACT_DIR

from reportobello.infra.db import db


tracer = trace.get_tracer("reportobello")
logger = logging.getLogger("reportobello")


TASK_DELAY_IN_SECONDS = 60

_background_task = None


def periodically_remove_expired_data() -> None:
    async def loop() -> None:
        while True:
            with tracer.start_as_current_span("remove expired files") as span:
                remove_expired_files(span)

            await asyncio.sleep(TASK_DELAY_IN_SECONDS)

    global _background_task
    _background_task = asyncio.create_task(loop())


def remove_expired_files(span: trace.Span) -> None:
    now = datetime.now(tz=timezone.utc).isoformat()

    sql = """
SELECT id, filename
FROM reports
WHERE filename IS NOT NULL AND ? > expires_at
"""

    cursor = db.cursor()
    rows = cursor.execute(sql, [now]).fetchall()
    cursor.close()

    count = len(rows)

    span.set_attribute(key="files_deleted", value=count)

    if count == 0:
        return

    logger.info("deleting files", extra={"count": count})

    for row in rows:
        (PDF_ARTIFACT_DIR / row["filename"]).unlink(missing_ok=True)

    # This is safe because the "id" field is an integer, which cannot contain strings
    inner = ','.join(str(int(row["id"])) for row in rows)

    cursor = db.cursor()
    cursor.execute(f"UPDATE reports SET filename=NULL WHERE id IN ({inner})")
    db.commit()
    cursor.close()
