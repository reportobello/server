import logging
import os
from typing import Annotated

from domin8 import tags as d
from fastapi import APIRouter, Cookie, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from reportobello.api.common import get_document
from reportobello.api.limiter import limiter
from reportobello.config import IS_LIVE_SITE
from reportobello.infra.db import get_user_by_api_key

router = APIRouter()
logger = logging.getLogger("reportobello")


@router.get("/login")
async def login_page(
    err: Annotated[str | None, Cookie(alias="login_error_msg")] = None
) -> HTMLResponse:
    doc = get_document("Login | Reportobello")

    # TODO: find a less fragile way to do this
    if os.getenv("REPORTOBELLO_GITHUB_OAUTH_CLIENT_ID"):
        login_with_github_button = d.a(
            d.button(
                "Login with GitHub",
                style="padding: 0.75em 1em; color: var(--white)",
                hx_disable_elt="this",
            ),
            href="/provider/github/authorize",
            hx_boost="false",
            style="width: fit-content; margin: auto",
        )

        login_with_github = (
            d.span("or", style="font-weight: bold"),
            login_with_github_button,
        )

    else:
        login_with_github = ()

    if IS_LIVE_SITE:
        legal_disclaimer = d.span(
            d.span("By using Reportobello you agree to our "),
            d.a(
                "Terms and Conditions",
                target="_blank",
                rel="noopener noreferrer",
                href="/terms",
                style="color: var(--black)",
            ),
            d.span("and"),
            d.a(
                "Privacy Policy",
                target="_blank",
                rel="noopener noreferrer",
                href="/privacy",
                style="color: var(--black)",
            ),
        )

    else:
        legal_disclaimer = ""

    page = d.main(
        d.form(
            d.h1("Reportobello", style="margin-bottom: 1.5em"),
            d.input_(
                name="api_key",
                type="password",
                minlength=1,
                placeholder="rpbl_YOUR_API_KEY",
                # TODO: style input box if text is invalid
                required=True,
                pattern="rpbl_[A-Za-z0-9_\\-]{43}",
                oninput="updateSubmitButton(this)",
            ),
            d.br(),
            d.button(
                "Login",
                _type="submit",
                style="margin: auto; padding: 0.75em 1em",
                _class="gray",
                disabled=True,
            ),
            d.p(err or "", style="color: var(--red)"),
            method="POST",
        ),
        *login_with_github,
        legal_disclaimer,
    )

    doc.add_raw_string("""

<style>
html, body {
    background: var(--teal) !important;
}

main {
    position: absolute;
    transform: translate(calc(50vw - 50% - 1em), calc(50vh - 50% - 1em));
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
    border: 2px solid var(--black);;
}

input {
    width: 25em;
    padding: 1em;
    background: #dfdfdf;
    margin-bottom: 2em;
    border-radius: 4px;
    color: var(--black);
    border: 2px solid var(--black);
}

nav {
    margin: 0;
    position: absolute;
}

nav a {
    color: var(--black);
    text-decoration: none;
    font-size: 1.5em;
    font-weight: bold;
}
</style>

<script>
function updateSubmitButton(element) {
    document.querySelector("button[type=submit]").disabled = !element.validity.valid;
}
</script>
""")

    doc.add(d.nav(d.a("Reportobello", href="/", hx_boost="false")))

    doc.add(page)

    return HTMLResponse(doc.render())


@router.post("/login")
@limiter.limit("10/minute")
async def post(request: Request, api_key: Annotated[str, Form()] = "") -> RedirectResponse:
    user = get_user_by_api_key(api_key)

    if not user:
        logger.info("login failed")

        return get_login_error_response()

    logger.info("user logged in", extra={"user": user.id})

    response = RedirectResponse("/survey" if user.is_setting_up_account else "/", status_code=302)

    response.set_cookie(
        key="api_key",
        value=user.api_key,
        secure=True,
        httponly=False,
        samesite="lax",
    )

    response.delete_cookie(
        key="login_error_msg",
        secure=True,
        httponly=True,
        samesite="lax",
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
        samesite="lax",
        path="/login",
    )

    return response
