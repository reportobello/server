from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse, RedirectResponse

router = APIRouter()


@router.get("/logout")
async def handle_logout(request: Request) -> Response:
    if request.headers.get("HX-Request"):
        # We need to have a separate flow for HTMX since it won't do a full page reload
        response = PlainTextResponse(status_code=200, headers={"HX-Redirect": "/"})

    else:
        response = RedirectResponse("/", status_code=302)

    response.delete_cookie(
        key="api_key",
        secure=True,
        httponly=True,
        samesite="lax",
    )

    return response
