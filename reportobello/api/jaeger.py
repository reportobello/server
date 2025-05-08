import os
from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse, StreamingResponse

import httpx
from starlette.background import BackgroundTask

from reportobello.api.common import CurrentUser


JAEGER_URL = os.getenv("REPORTOBELLO_JAEGER_URL", "http://localhost:16686/jaeger")
jaeger_client = httpx.AsyncClient(base_url=JAEGER_URL)


router = APIRouter(include_in_schema=False)


@router.get("/jaeger/{path:path}")
async def jaeger_reverse_proxy(user: CurrentUser, path: str, request: Request) -> Response:
    if not user.is_admin:
        return PlainTextResponse(status_code=403)

    jaeger_url = httpx.URL(path, params=request.query_params)

    proxy_req = jaeger_client.build_request(
        request.method,
        jaeger_url,
        # TODO: remove sensitive headers
        headers=request.headers.raw,
        content=await request.body(),
    )

    try:
        jaeger_resp = await jaeger_client.send(proxy_req, stream=True)

    except Exception:  # noqa: BLE001
        return PlainTextResponse("Could not load traces, is Jaeger running?", status_code=404)

    return StreamingResponse(
        jaeger_resp.aiter_raw(),
        status_code=jaeger_resp.status_code,
        headers=jaeger_resp.headers,
        background=BackgroundTask(jaeger_resp.aclose),
        # TODO: figure out why content type is wrong here
    )
