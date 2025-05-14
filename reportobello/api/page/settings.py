from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from reportobello.api.common import CurrentUser

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/settings")
async def settings(request: Request, user: CurrentUser) -> HTMLResponse:
    return templates.TemplateResponse(request, "settings.html", context={"user": user})
