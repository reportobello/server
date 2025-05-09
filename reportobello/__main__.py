import asyncio
import warnings
from contextlib import asynccontextmanager

# See https://github.com/encode/starlette/pull/2733
warnings.simplefilter(action="ignore", category=FutureWarning)

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# This must be imported above the rest of the routes to ensure that sqlite is patched properly
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor

SQLite3Instrumentor().instrument()

load_dotenv()

from reportobello.api.limiter import add_ratelimiter
from reportobello.config import IS_LIVE_SITE
from reportobello.infra.docker import pull_pdf_converter_in_background
from reportobello.infra.logging import get_uvicorn_logging_config, setup_logging
from reportobello.infra.otel import setup_otel_tracing
from reportobello.infra.retention import periodically_remove_expired_data
from reportobello.infra.seed.user import create_admin_user_if_not_exists, create_demo_user_if_not_exists

setup_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):  # type: ignore  # noqa: RUF029, ANN201
    periodically_remove_expired_data()

    task = asyncio.create_task(pull_pdf_converter_in_background())

    yield

    task.cancel()


app = FastAPI(
    title="Reportobello API",
    version="v1",
    docs_url="/swagger",
    openapi_tags=[
        {
            "name": "report",
            "description": "Everything you need for configuring and building reports",
        },
    ],
    lifespan=lifespan,
)

import reportobello.api.router
from reportobello.api.middleware import add_middleware

app.include_router(reportobello.api.router.router)
add_middleware(app)
setup_otel_tracing(app)
add_ratelimiter(app)


app.mount("/docs", StaticFiles(directory="./www/docs", html=True), "docs")
app.mount("/www", StaticFiles(directory="./www", html=True), "www")


for method_item in app.openapi().get("paths", {}).values():
    for param in method_item.values():
        param.get("responses", {}).pop("422", None)


if __name__ == "__main__":
    create_admin_user_if_not_exists()

    if IS_LIVE_SITE:
        create_demo_user_if_not_exists()

    uvicorn.run(app, host="0.0.0.0", log_config=get_uvicorn_logging_config(), forwarded_allow_ips="*")
