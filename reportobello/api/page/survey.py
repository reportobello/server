import json
import logging
from datetime import UTC, datetime
from typing import Annotated

from domin8 import tags as d
from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from reportobello.api.common import CurrentUser, get_document
from reportobello.infra.db import create_or_update_user, db

router = APIRouter()

logger = logging.getLogger("reportobello")


@router.get("/survey")
async def get() -> HTMLResponse:
    doc = get_document("Onboarding Survey | Reportobello")

    doc.add_raw_string(
        """
<style>
main {
    position: absolute;
    transform: translate(calc(50vw - 50%), calc(50vh - 50%));
    padding-right: 0;
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: 3em;
}

form {
    display: flex;
    flex-direction: column;
    padding: 2em;
    background: #f0f0f0;
    border-radius: 4px;
    width: fit-content;
    margin: 0 auto;
    border: 2px solid var(--black);
    gap: 1em;
}

button[type=submit]:disabled {
    background: #959595 !important;
}

label[for=source] {
    cursor: normal;
}

fieldset, select {
    width: 25em;
    padding: 1em;
    background: #dfdfdf;
    margin-bottom: 1em;
    border-radius: 4px;
    color: var(--black);
    border: 2px solid var(--black);
}
</style>
"""
    )

    page = d.main(
        d.form(
            d.h1("One More Thing", style="margin-bottom: 1em"),
            d.label("How did you hear about us?", _for="source"),
            d.select(
                d.option("Please Select *", selected=True, disabled=True),
                d.option("Hacker News", value="hn"),
                d.option("Reddit", value="reddit"),
                d.option("GitHub", value="gh"),
                d.option("X/Twitter", value="x"),
                d.option("Word-of-mouth", value="wom"),
                d.option("Other", value="other"),
                name="source",
                id="source",
                style="width: 100% !important",
                required=True,
                onchange="showOtherIfNeeded(this)",
            ),
            d.input_(
                id="source-other",
                placeholder="Where did you hear about us?",
                name="source-other",
                style="margin: -0.5em 0 1em 0; height: 2em; display: none;",
            ),
            d.span("What feature(s) are you most interested in?"),
            d.fieldset(
                d.div(
                    d.input_(name="features", type="checkbox", id="pdf", value="pdf"),
                    d.label("PDF Generation", _for="pdf"),
                ),
                d.div(
                    d.input_(name="features", type="checkbox", id="bulk", value="bulk"),
                    d.label("Bulk PDF Generation", _for="bulk"),
                ),
                d.div(
                    d.input_(name="features", type="checkbox", id="ocr", value="ocr"),
                    d.label("PDF OCR", _for="ocr"),
                ),
                d.input_(placeholder="Other", name="features", style="margin: 0.5em 0 0 0"),
                style="display: flex; flex-direction: column; text-align: left",
            ),
            d.br(),
            d.button(
                "Finish",
                _type="submit",
                style="margin: auto; padding: 0.75em 1em",
                disabled=True,
            ),
            method="POST",
        ),
    )

    doc.add(page)

    doc.add_raw_string("""

<style>
html, body {
    background: var(--teal) !important;
}

fieldset div {
    display: flex;
    gap: 0.5em;
    cursor: pointer;
}

fieldset div * {
    cursor: pointer;
}

fieldset label {
    flex: 1;
    margin: auto;
}
</style>

<script>
function showOtherIfNeeded(element) {
    const other = document.getElementById("source-other");

    other.style.display = element.value == "other" ? "block" : "none";

    document.querySelector("button[type=submit]").disabled = false;
}
</script>
""")

    return HTMLResponse(doc.render())


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
