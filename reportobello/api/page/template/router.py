import math
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from reportobello.api.common import CurrentUser, json_prettify
from reportobello.infra.db import (
    get_env_vars_for_user,
    get_files_for_template,
    get_recent_report_builds_for_user,
    get_template_for_user,
)

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/template/{name}")
async def get(request: Request, user: CurrentUser, name: str) -> HTMLResponse:
    now = datetime.now(tz=UTC)
    template = get_template_for_user(user.id, name)

    ctx = {
        "name": name,
        "time": time.time(),
        "before": now.isoformat(),
        "template": {},
        "env_vars": [],
        "last_json_value": "",
        "last_file_name": None,
    }

    if template:
        ctx["template"] = {
            "name": template.name,
            "version": template.version,
            "template": template.template,
        }

        ctx["env_vars"] = get_env_vars_for_user(user.id)

        reports = get_recent_report_builds_for_user(user.id, name, before=now, limit=1)

        if reports:
            ctx["last_json_value"] = json_prettify(reports[0].data or "{}")
            ctx["last_file_name"] = reports[0].filename or ""

    return templates.TemplateResponse(request, "template/index.html", context=ctx)


@router.get("/template/{name}/builds")
async def get_builds(request: Request, user: CurrentUser, name: str, before: datetime | None = None) -> HTMLResponse:
    limit = 20
    reports = get_recent_report_builds_for_user(user.id, name, before=before, limit=limit) or []

    ctx = {
        "limit": limit,
        "reports": [
            {
                "was_successful": bool(report.was_successful),
                "requested_version": report.requested_version,
                "actual_version": report.actual_version,
                "finished_at": report.finished_at.isoformat(),
                "started_at": report.started_at.isoformat(),
                "data_type": report.data_type.title(),
                "json": json_prettify(report.data or "{}"),
                "error_message": report.error_message,
                "filename": report.filename,
                "template_name": report.template_name,
            }
            for report in reports
        ],
        "name": name,
        "before": before.isoformat() if before else None,
        "last_report_started_at": reports[-1].started_at.isoformat() if reports else None,
    }
    return templates.TemplateResponse(request, "template/build_history_list.html", context=ctx)


@router.get("/template/{name}/files")
async def get_files(request: Request, user: CurrentUser, name: str) -> HTMLResponse:
    ctx = {
        "template_name": name,
        "files": [
            {
                "filename": file.filename,
                "size_full": f"{file.size:,}",
                "size_pretty": prettify_byte_size(file.size),
            }
            for file in get_files_for_template(user.id, name)
        ],
    }

    return templates.TemplateResponse(request, name="template/files_list.html", context=ctx)


# https://stackoverflow.com/a/14822210
def prettify_byte_size(size: int) -> str:
    if size == 0:
        return "0B"

    sizes = ("B", "K", "M", "G", "T", "P", "E", "Z", "Y")

    i = math.floor(math.log(size, 1000))
    p = math.pow(1000, i)
    s = round(size / p, 1)

    return f"{s}{sizes[i]}"
