from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from reportobello.api.common import security
from reportobello.config import IS_LIVE_SITE
from reportobello.infra.db import get_all_templates_for_user

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/")
async def get(request: Request):  # type: ignore  # noqa: ANN201
    try:
        user = await security(request)

    except HTTPException:
        if IS_LIVE_SITE:
            return FileResponse("www/index.html", headers={"Vary": "Cookie"})

        return RedirectResponse("/login")

    rows = get_all_templates_for_user(user.id)

    # TODO: sort by most recently used
    ctx = {"templates": sorted(rows, key=lambda x: x.name)}

    return templates.TemplateResponse(request, "homepage.html", context=ctx, headers={"Vary": "Cookie"})
