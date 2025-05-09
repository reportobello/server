import json
from typing import Annotated

from domin8 import document  # type: ignore
from dominate.dom_tag import dom_tag
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer

from reportobello.domain.user import User
from reportobello.infra.db import get_user_by_api_key


def get_document(title: str) -> dom_tag:
    html = document(title=title)

    html["lang"] = "en"

    html.head.add_raw_string("""
<meta name="viewport" content="width=device-width, initial-scale=1" />

<script src="/www/node_modules/htmx.org/dist/htmx.min.js?v=2.0.3"></script>

<link rel="icon" href="/www/favicon.ico">

<script>
function utcNormalize(e) {
    for (const element of document.querySelectorAll("[data-utc-localize]")) {
        element.innerText = new Date(element.dataset.utcLocalize).toLocaleString();
    }
}
addEventListener("DOMContentLoaded", utcNormalize);
addEventListener("htmx:load", utcNormalize);

function getCookie(name) {
    return document.cookie.split(";").map(x => x.split("=")).filter(x => x[0].trim() === name)?.[0]?.[1];
}
</script>

<style>
@font-face {
  font-face: JetBrains;
  src: url('/www/jetbrains.ttf');
}

@font-face {
  font-face: JetBrains;
  font-weight: bold;
  src: url('/www/jetbrains-bold.ttf');
}

:root {
    --red: #ff2929;
    --green: #85ff40;
    --blue: #0034ff;
    --yellow: #fffc40;
    --teal: #5afccb;
    --black: #171717;
    --white: #f9f9f9;
}

* {
    font-family: JetBrains, monospace;
    color: var(--black);
}

html {
    margin: 0;
    width: 100vw;
    height: 100vh;
    font-size: 12px;
}

body {
    margin: 1em;
    width: calc(100vw - 2em);
    height: calc(100vh - 2em);
}

html, body {
    padding: 0;
    background: var(--white);
}

a {
    color: var(--blue);
    text-underline-position: under;
}
.fg-red { color: var(--red); }
.fg-green { color: var(--green); }
.fg-blue { color: var(--blue); }
.fg-yellow { color: var(--yellow); }

.red { background: var(--red); }
.green { background: var(--green); }
.blue { background: var(--blue); }
.yellow { background: var(--yellow); }

summary {
    cursor: pointer;
}

button {
    color: var(--white);
    background: var(--black);
    padding: 4px 1em;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background 300ms;
}

button.green {
    color: var(--black);
    background: var(--green);
}

button.outline {
    color: var(--black);
    background: var(--white);
    border: 2px solid var(--black);
}

.red-outline {
    color: var(--red);
    background: transparent;
    border: 2px solid var(--red);
}

button:disabled {
    cursor: not-allowed !important;
    background: #dbdbdb !important;
}

input {
    border: none;
}

input, textarea {
    background: var(--white);
    padding: 4px 6px;
    border-radius: 4px;
    border: 2px solid var(--black);
    color: var(--black);
}

.chip {
    padding: 0.25em 0.5em;
    margin: -0.25em -0.5em;
    border-radius: 4px;
}

input[type=checkbox], input[type=radio], label {
    cursor: pointer;
}

input[type=checkbox]:disabled, input[type=radio]:disabled, input:disabled+label {
    cursor: not-allowed;
}
</style>
""")

    html.body.attributes["hx-boost"] = "true"

    return html


class CustomAuthorizer(HTTPBearer):
    def __init__(self, **kwargs) -> None:  # type: ignore  # noqa: ANN003
        kwargs["auto_error"] = False

        super().__init__(**kwargs)

    async def __call__(self, request: Request) -> User:  # type: ignore
        # check if we have already called this function for the given request
        user = getattr(request.state, "user", ...)

        if user is ...:
            user = await self._get_user(request)

            request.state.user = user

        if user is not None:
            return user

        raise HTTPException(status_code=401, detail="Not authorized")

    async def _get_user(self, request: Request) -> User | None:
        creds = await super().__call__(request)

        if creds and creds.scheme.lower() == "bearer" and (user := get_user_by_api_key(creds.credentials)):
            return user

        if (api_key := request.cookies.get("api_key")) and (user := get_user_by_api_key(api_key)):
            return user

        return None


security = CustomAuthorizer(description="Add your Reportobello API key below. It should start with `rpbl_`")

CurrentUser = Annotated[User, Depends(security)]


# TODO: move to generic utils
def json_prettify(j: str) -> str:
    return json.dumps(json.loads(j), indent=2, ensure_ascii=False)


# TODO: use built in mimetype library?
def mimetype_strip_encoding(mime_type: str | None) -> str | None:
    if mime_type is None:
        return None

    return mime_type.split(";", maxsplit=1)[0].strip()
