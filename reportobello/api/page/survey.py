import json
import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from reportobello.api.common import CurrentUser
from reportobello.infra.db import create_or_update_user, db

router = APIRouter()
logger = logging.getLogger("reportobello")

templates = Jinja2Templates(directory="templates")


@router.get("/survey")
async def get(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "survey.html", context={})


@router.post("/survey")
async def post(
    user: CurrentUser,
    features: Annotated[list[str], Form()],
    source: Annotated[str, Form()],
    source_other: Annotated[str | None, Form(alias="source-other")] = None,
) -> RedirectResponse:
    logger.info("survey completed", extra={"user": user.id})

    now = datetime.now(tz=UTC)

    data = {
        "source": source_other if source == "other" else source,
        "features": [f for f in features if f],
    }

    # TODO: move to db.py
    cursor = db.cursor()
    cursor.execute(
        """
INSERT INTO new_user_survey (owner_id, submitted_at, value)
VALUES (?, ?, ?)
ON CONFLICT DO UPDATE SET
    value=excluded.value,
    submitted_at=excluded.submitted_at;
""",
        [user.id, now.isoformat(), json.dumps(data, separators=(",", ":"))],
    )
    cursor.close()

    user.is_setting_up_account = False
    create_or_update_user(user)

    db.commit()

    return RedirectResponse("/", status_code=302)
