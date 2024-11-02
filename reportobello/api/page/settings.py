from domin8 import tags as d
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from reportobello.api.common import CurrentUser, get_document
from reportobello.api.page.svgs import ARROW_SVG, COPY_SVG

router = APIRouter()


@router.get("/settings")
async def settings(user: CurrentUser) -> HTMLResponse:
    html = get_document("Settings | Reportobello")

    html.add_raw_string(
"""
<script>
function copyApiKey() {
    const apiKey = document.getElementById("api-key").value;

    navigator.clipboard.writeText(apiKey).then(() => {
        document.getElementById("copy-success").style.display = "inline";
    });
}
</script>
"""
    )

    main = d.main(
        d.h1(
            d.div(
                ARROW_SVG,
                hx_get="/",
                hx_swap="outerHTML",
                hx_target="body",
                hx_push_url="true",
                style="height: 24px; margin: auto 0; cursor: pointer",
            ),
            d.span("Settings"),
            style="margin: 0; margin-bottom: 0.5em; display: flex; gap: 0.5em",
        ),
        d.h2("API Key", style="margin: 0"),
        d.div(
            d.div(
                d.input_(id="api-key", value=user.api_key, style="width: 12em; text-overflow: ellipsis"),
                d.div(
                    COPY_SVG,
                    onclick="copyApiKey()",
                    style="display: flex; margin: auto 0; cursor: pointer",
                ),
                d.span("Copied!", id="copy-success", style="display: none; font-style: italic; margin: auto 0"),
                style="display: flex; gap: 1em",
            ),
            style="display: flex; flex-direction: column; gap: 1em",
        ),
        style="display: flex; flex-direction: column; gap: 1em",
    )

    html.add(main)

    return HTMLResponse(html.render())
