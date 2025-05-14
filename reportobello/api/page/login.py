import logging
import os
from typing import Annotated

from fastapi import APIRouter, Cookie, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from reportobello.api.limiter import limiter
from reportobello.config import IS_LIVE_SITE
from reportobello.infra.db import get_user_by_api_key

router = APIRouter()
logger = logging.getLogger("reportobello")

templates = Jinja2Templates(directory="templates")


@router.get("/login")
async def login_page(
    request: Request,
    err: Annotated[str | None, Cookie(alias="login_error_msg")] = None,
) -> HTMLResponse:
    ctx = {
        # TODO: find a less fragile way to do this
        "is_github_oauth_enabled": bool(os.getenv("REPORTOBELLO_GITHUB_OAUTH_CLIENT_ID")),
        "is_live_site": IS_LIVE_SITE,
        "error": err or "",
    }

    return templates.TemplateResponse(request, "login.html", context=ctx)


@router.post("/login")
@limiter.limit("10/minute")
async def post(request: Request, api_key: Annotated[str, Form()] = "") -> RedirectResponse:
    user = get_user_by_api_key(api_key)

    if not user:
        logger.info("login failed")

        return get_login_error_response()

    logger.info("user logged in", extra={"user": user.id})

    response = RedirectResponse("/survey" if user.is_setting_up_account else "/?refresh", status_code=302)

    response.set_cookie(
        key="api_key",
        value=user.api_key,
        secure=True,
        httponly=False,
        samesite="strict",
    )

    response.delete_cookie(
        key="login_error_msg",
        secure=True,
        httponly=True,
        samesite="strict",
        path="/login",
    )

    return response


def get_login_error_response() -> RedirectResponse:
    err = "Invalid API Key"

    response = RedirectResponse("/login", status_code=302)

    response.set_cookie(
        key="login_error_msg",
        value=err,
        expires=2,
        secure=True,
        httponly=True,
        samesite="strict",
        path="/login",
    )

    return response
