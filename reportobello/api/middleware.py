import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse

from reportobello.api.common import security


STATIC_CONTENT = re.compile(r"^\/docs\/.*\.(css|js)$")


def add_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=512)

    DEMO_USER_ALLOWED_ENDPOINTS = frozenset(
        (
            "/api/v1/template/demo/build",
            "/favicon.ico",
            "/terms",
            "/privacy",
            "/cookies",
        )
    )

    @app.middleware("http")
    async def restrict_demo_user(request: Request, call_next):
        url = request.url.path.rstrip("/")

        # fast path to allow static content and demo API path
        if url in DEMO_USER_ALLOWED_ENDPOINTS or url.startswith("/www"):
            return await call_next(request)

        try:
            user = await security(request)

            if user.is_demo_user:
                return PlainTextResponse("Cannot access this resource using demo account", status_code=403)

        except HTTPException:
            pass

        return await call_next(request)

    @app.middleware("http")
    async def cache_static_content(request: Request, call_next):
        url = request.url.path.rstrip("/")

        response = await call_next(request)

        if STATIC_CONTENT.match(url):
            response.headers["Cache-Control"] = "max-age=2592000"  # 30 days

        return response

    @app.middleware("http")
    async def redirect_docs_html(request: Request, call_next):
        url = request.url.path.rstrip("/")

        if url.startswith("/docs/"):
            path = Path(url.split("?", maxsplit=1)[0])

            if not path.is_dir() and not path.suffix:
                return RedirectResponse(f"{request.url}.html", status_code=302)

        return await call_next(request)
