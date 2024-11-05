from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from secrets import token_urlsafe
from tempfile import TemporaryDirectory
from typing import Annotated, Any
from urllib.parse import quote
import asyncio
import hashlib
import logging
import shutil

from fastapi import APIRouter, Body, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse
from opentelemetry import trace

from reportobello.api.common import CurrentUser, mimetype_strip_encoding
from reportobello.application.build_pdf import ReportobelloBuildFailed, ReportobelloTemplateNotFound, build_report, typst_compile
from reportobello.application.convert import convert_file_in_memory
from reportobello.config import DOMAIN, IS_LIVE_SITE, PDF_ARTIFACT_DIR, get_file_artifact_path_from_hash
from reportobello.domain.file import File
from reportobello.domain.report import Report
from reportobello.domain.template import Template
from reportobello.api.limiter import limiter
from reportobello.infra.db import (
    check_template_exists_for_user,
    create_or_update_template_for_user,
    delete_env_vars_for_user,
    delete_file_for_template,
    get_all_template_versions_for_user,
    get_all_templates_for_user,
    get_env_vars_for_user,
    get_file_for_template,
    get_recent_report_builds_for_user,
    get_template_for_user,
    save_file_metadata,
    delete_template_for_user,
    update_env_vars_for_user,
)


tracer = trace.get_tracer("reportobello")
logger = logging.getLogger("reportobello")

router = APIRouter()


@router.get(
    "/api/v1/templates",
    tags=["report"],
    responses={
        200: {"model": list[Template]},
    }
)
@limiter.limit("5/second")
async def get_templates(user: CurrentUser, request: Request):
    """
    Get a list of all uploaded templates.
    """

    templates = [asdict(t) for t in get_all_templates_for_user(user.id)]

    return JSONResponse(templates)


@router.get(
    "/api/v1/template/{name}",
    tags=["report"],
    responses={
        200: {"model": list[Template]},
        404: {
            "model": str,
            "content": {
                "text/plain": {
                    "example":" Template not found",
                }
            }
        },
    }
)
@limiter.limit("5/second")
async def get_template(user: CurrentUser, name: str, request: Request):
    """
    Get the current (and previous) versions of a given template based on **name**.
    """

    if templates := get_all_template_versions_for_user(user.id, name):
        templates = list(asdict(t) for t in sorted(templates, key=lambda x: x.version, reverse=True))

        return JSONResponse(templates)

    return PlainTextResponse("Template not found", status_code=404)


@router.post(
    "/api/v1/template/{name}",
    tags=["report"],
    response_model=Template,
    responses={
        200: {"model": Template},
        400: {
            "model": str,
            "content": {
                "text/plain": {
                    "example": "Content type is invalid",
                }
            }
        },
    }
)
@limiter.limit("5/second")
async def add_or_update_template(
    user: CurrentUser,
    request: Request,
    name: str,
    body: str = Body(media_type="application/x-typst", example="Hello world"),
):
    """
    Create a new template called **name**, or if it already exists, make a new revision.
    If the uploaded template matches the most recent template contents, nothing happens (ie, the version number stays the same).

    The `Content-Type` header *must* be set to `application/x-typst` for this endpoint to work.
    """

    # TODO: is this needed anymore?
    if mimetype_strip_encoding(request.headers.get("Content-Type")) != "application/x-typst":
        return PlainTextResponse("Content type is invalid", status_code=400)

    logger.info("template created", extra={"user": user.id})

    if (most_recent_template := get_template_for_user(user.id, name)) and most_recent_template.template == body:
        return JSONResponse(asdict(most_recent_template), status_code=200)

    template = create_or_update_template_for_user(user.id, name=name, content=body)

    return JSONResponse(asdict(template))


@router.delete(
    "/api/v1/template/{name}",
    status_code=200,
    responses={
        200: {
            "model": str,
            "content": {
                "text/plain": {
                    "example": "OK",
                },
            },
        },
    },
    tags=["report"],
)
@limiter.limit("5/second")
async def delete_template(user: CurrentUser, name: str, request: Request):
    """
    Delete the template **name** if it exists. If the template does not exist,
    no error status is returned.

    Direct links to a existing reports might still work for a short period until they expire.
    This behavior might change in the future.
    """

    delete_template_for_user(user.id, name)

    logger.info("template deleted", extra={"user": user.id})

    return PlainTextResponse("OK", headers={"HX-Redirect": "/"})


@dataclass
class BuildTemplatePayload:
    data: Any
    content_type: str = "application/json"
    template_raw: str | None = None


@router.post(
    "/api/v1/template/{name}/build",
    status_code=303,
    responses={
        303: {},
        400: {
            "model": str,
            "content": {
                "text/plain": {
                    "example": "Version 1 does not exist for template\nContent type is invalid\nFailed to build report",
                }
            }
        },
        404: {
            "model": str,
            "content": {
                "text/plain": {
                    "example": "Template not found",
                }
            }
        },
    },
    tags=["report"],
)
@limiter.limit("2/second")
async def template_build(
    user: CurrentUser,
    request: Request,
    name: str,
    body: BuildTemplatePayload,
    version: int = -1,
    just_url: str | None = Query(None, alias="justUrl"),
    is_pure: str | None = Query(None, alias="isPure"),
):
    """
    Build a new report from the template **name**.

    Rate limit: 2 requests per second.

    The `Content-Type` header *must* be set to `application/json` for this endpoint to work.

    The optional query parameter **version** can be used to specify what version of the template to use. By default, the latest is used.

    The optional query parameter **just_url** can be set to return the URL directly instead of a PDF blob.
    This is useful for JavaScript libraries since fetch does not provide a good way to intercept headers for 3xx redirect requests.

    > Note: when writing your template, use `data.json` as the input filename for the `json()`, that way your data is properly imported.

    The optional query parameter **is_pure** can be set to return a cached (already built) report based on the hash of the JSON data.
    By default, a new report is built every time regardless of whether the JSON data matches an existing report.
    This is due to the fact that Typst templates can be non-deterministic, meaning the same input might yield different outputs.
    For example, using `#datetime.today()` will be different depending on which day the report is generated.
    If your report only depends on the JSON data does not have side effects, and does not rely on environment variables, consider using **is_pure**.

    > Note that **is_pure** applies to a template version and not the template itself, meaning if you make a new version of a template, the template will need to be rebuilt.
    """

    try:
        report = await build_report(
            user=user,
            template_name=name,
            template_version=version,
            template_raw=body.template_raw,
            content_type=body.content_type,
            data=body.data,
            is_pure=is_pure is not None,
        )

    except ReportobelloTemplateNotFound as ex:
        return PlainTextResponse("Template not found", status_code=404)

    except ReportobelloBuildFailed as ex:
        return PlainTextResponse(str(ex), status_code=400)

    if just_url is not None:
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)

        return PlainTextResponse(f"{scheme}://{DOMAIN}/api/v1/files/{report.filename}", status_code=200)

    assert report.filename

    return FileResponse(PDF_ARTIFACT_DIR / report.filename, status_code=200)


# TODO: add query parameters to control success status, count, since, etc.
@router.get(
    "/api/v1/template/{name}/recent",
    tags=["report"],
    response_model=list[Report],
    responses={
        404: {
            "model": str,
            "content": {
                "text/plain": {
                    "example": "Template not found",
                }
            }
        },
    },
)
@limiter.limit("5/second")
async def get_recently_built_reports(
    request: Request,
    user: CurrentUser,
    name: str,
    before: datetime | None = None,
):
    """
    Get recently built reports for template **name**.

    By default, only the top 20 most recent reports are returned. The page size cannot be set (yet).

    To get reports built before a given timestamp, set the **before** query parameter to an ISO 8601 timestamp.
    """

    recent = get_recent_report_builds_for_user(user.id, name, before=before)

    if recent is None:
        return PlainTextResponse("Template not found", status_code=404)

    return JSONResponse([r.as_json() for r in recent])


@router.post(
    "/api/v1/template/{name}/files",
    tags=["report"],
    responses={
        400: {
            "model": str,
            "content": {
                "text/plain": {
                    "example": "One or more files are too large",
                }
            }
        },
        404: {
            "model": str,
            "content": {
                "text/plain": {
                    "example": "Template not found",
                }
            }
        },
    },
)
@limiter.limit("5/second")
async def upload_files_for_template(
    request: Request,
    user: CurrentUser,
    name: str,
):
    """
    Upload one or more data files to template **name**.
    Uploading files to templates allows you to use in from within the report.

    Files are uploaded as a multipart form submission. For each file, the following occurs:

    * Get filename: Uses the `filename` field, or if that is unset, the `name` field.
    * Get content type (optional): Get the `Content-Type` field, if it exists.
    * Hash and store the file contents
    * Attach file metadata to template **name**.

    The underlying file content is shared, meaning if you upload the same file
    twice, the file only gets stored once ("the same" here means the file contents
    have the same hash).
    """

    # TODO: allow this to be configurable
    MAX_FILESIZE = 10 * 1000 * 1000  # 10 MB

    if not check_template_exists_for_user(user.id, name):
        return PlainTextResponse("Template not found", status_code=404)

    async with request.form(max_files=100, max_fields=0) as form:
        for filename, file in form.multi_items():
            if isinstance(file, str):
                return PlainTextResponse("Only files can be uploaded", status_code=400)

            if file.size is None or file.size > MAX_FILESIZE:
                return PlainTextResponse("One or more files are too large", status_code=413)

            content = await file.read()
            file_hash = hashlib.sha3_512(content).hexdigest().lower()

            raw_filename = get_file_artifact_path_from_hash(file_hash)

            if not raw_filename.exists():
                raw_filename.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                raw_filename.write_bytes(content)

            file = File(
                filename=file.filename or filename,
                hash=file_hash,
                content_type=file.content_type,
                size=file.size,
            )

            save_file_metadata(user_id=user.id, template_name=name, file=file)


@router.get(
    "/api/v1/template/{name}/file/{filename}",
    tags=["report"],
    responses={
        404: {
            "model": str,
            "content": {
                "text/plain": {
                    "example": "File not found",
                }
            }
        },
    },
)
@limiter.limit("5/second")
async def get_files_for_template(
    request: Request,
    user: CurrentUser,
    name: str,
    filename: str,
):
    """
    Return the data file **filename** attached to a given template **name**, or `404` if it doesn't exist.
    """

    if file := get_file_for_template(user.id, name, filename):
        raw_file = get_file_artifact_path_from_hash(file.hash)

        return FileResponse(raw_file, media_type=file.content_type)

    return PlainTextResponse("File not found", status_code=404)


@router.delete(
    "/api/v1/template/{name}/file/{filename}",
    tags=["report"],
)
@limiter.limit("5/second")
async def delete_files_for_template(
    request: Request,
    user: CurrentUser,
    name: str,
    filename: str,
):
    """
    Delete a data file **filename** for a given template **name**.
    If the filename doesn't exist, no error is returned.
    """

    delete_file_for_template(user.id, name, filename)


class PdfFileResponse(FileResponse):
    media_type = "application/pdf"


@router.get(
    "/api/v1/files/{filename}",
    summary="Get PDF",
    tags=["report"],
    response_class=PdfFileResponse,
    responses={
        200: {
            "content": {
                "application/pdf": {"example": ""},
            }
        },
        404: {
            "model": str,
            "content": {
                "text/plain": {
                    "example": "File not found",
                }
            }
        },
    },
)
async def get_pdf(
    filename: str,
    download_as: str | None = Query(None, alias="downloadAs"),
    download: str | None = None,
):
    """
    Get a previously generated PDF file by it's **filename**.

    The **downloadAs** query parameter can be set to change the file name of the file once downloaded (on the client).

    The **download** query parameter can be set to automatically download the file when viewed in a browser.
    This is only used if **downloadAs** is set.
    """

    file = (PDF_ARTIFACT_DIR / filename).absolute()

    if file.is_relative_to(PDF_ARTIFACT_DIR) and file.name.endswith(".pdf") and file.exists():
        headers = {"Content-Disposition": f'attachment; filename="{quote(download_as)}"'} if download_as is not None else {}

        if download_as is not None:
            prefix = "attachment; " if download is not None else ""

            headers = {"Content-Disposition": f'{prefix}filename="{quote(download_as)}"'}

        headers["Cache-Control"] = "max-age=31536000, immutable"

        return PdfFileResponse(file, headers=headers)

    return PlainTextResponse("File not found", status_code=404)


@router.get(
    "/api/v1/env",
    tags=["report"],
    summary="Get Environment Variables",
    responses={
        200: {
            "model": dict[str, str],
            "content": {
                "text/plain": {
                    "example": "Content type is invalid",
                }
            }
        },
    },
)
@limiter.limit("5/second")
async def get_env_vars(user: CurrentUser, request: Request):
    """
    Get environment variables set for the current user.
    """

    logger.info("get env vars", extra={"user": user.id})

    return get_env_vars_for_user(user.id)


@router.post(
    "/api/v1/env",
    tags=["report"],
    summary="Update Environment Variables",
    responses={
        400: {
            "model": str,
            "content": {
                "text/plain": {
                    "example": "Content type is invalid",
                }
            }
        },
    },
)
@limiter.limit("5/second")
async def update_env_vars(
    user: CurrentUser,
    request: Request,
    body: dict[str, str] = Body(example='{"KEY": "value"}'),
):
    """
    Post a JSON blob of key-value pairs that will be injected and usable with *all* reports.
    The `Content-Type` header *must* be set to `application/json` for this endpoint to work.
    """

    # TODO: is this needed?
    if mimetype_strip_encoding(request.headers.get("Content-Type")) != "application/json":
        return PlainTextResponse("Content type is invalid", status_code=400)

    update_env_vars_for_user(user.id, body)

    logger.info("update env var", extra={"user": user.id})


@router.delete(
    "/api/v1/env",
    tags=["report"],
    summary="Delete Environment Variables",
    responses={
        400: {
            "model": str,
            "content": {
                "text/plain": {
                    "example": "Content type is invalid",
                }
            }
        },
    },
)
@limiter.limit("5/second")
async def delete_env_vars(
    user: CurrentUser,
    request: Request,
    body: list[str] | None = Body(None, example='["KEY1", "KEY2", "KEY3"]'),
    keys: str | None = Query(None),
):
    """
    Delete a list of environment variables based on key name.
    If the key does not exist, nothing happens.

    The `Content-Type` header *must* be set to `application/json` for this endpoint to work.

    For clients that do not support request bodies when using DELETE,
    you can set the query parameter **keys** to a comma-separated list of keys to delete.
    In this case, the `Content-Type` header is not checked, since there is no request body.
    """

    if body is keys is None:
        # TODO: handle this
        assert False

    if keys:
        delete_env_vars_for_user(user.id, [k.strip() for k in keys.split(",")])
        return

    if not body or mimetype_strip_encoding(request.headers.get("Content-Type")) != "application/json":
        return PlainTextResponse("Content type is invalid", status_code=404)

    delete_env_vars_for_user(user.id, body)

    logger.info("delete env var", extra={"user": user.id})


@router.post(
    "/api/v1/convert/pdf",
    tags=["report"],
    response_model=Template,
    responses={
        200: {"model": Template},
        303: {},
    }
)
@limiter.limit("10/minute")
async def create_template_from_existing_document(
    user: CurrentUser,
    pdf: UploadFile,
    template_name: Annotated[str, Form()],
    request: Request,
):
    """
    Convert an existing document to a Typst template named **name**.
    The uploaded file can be either a PDF, DOC/DOCX, or Markdown file.

    This endpoint will build an initial PDF for the converted document
    based off the template and data extracted from the template.
    """

    logger.info("convert pdf", extra={"user": user.id})

    with (
        TemporaryDirectory() as tmp_dir,
        tracer.start_as_current_span("convert PDF to typst"),
    ):
        file = (Path(tmp_dir) / "report").with_suffix(Path(pdf.filename or ".pdf").suffix)

        file.write_bytes(await pdf.read())

        typst, data = await convert_file_in_memory(Path(tmp_dir), file)

        template = create_or_update_template_for_user(user.id, name=template_name, content=typst)

        await build_report(
            user=user,
            template_name=template_name,
            template_version=template.version,
            content_type="application/json",
            data=data,
        )

    # TODO: use HX-Redirect?
    if request.headers.get("HX-Request"):
        return RedirectResponse(f"/template/{template_name}", 303)

    return template


if IS_LIVE_SITE:
    tasks = set()

    @router.post("/api/convert/pdf/demo", include_in_schema=False)
    @limiter.limit("10/minute")
    async def anonymous_convert(pdf: UploadFile, request: Request):
        logger.info("convert pdf demo")

        with (
            TemporaryDirectory() as tmp_dir,
            tracer.start_as_current_span("convert PDF to typst"),
        ):
            file = (Path(tmp_dir) / "report").with_suffix(Path(pdf.filename or ".pdf").suffix)

            with tracer.start_as_current_span("write files"):
                file.write_bytes(await pdf.read())

            typst_template, data = await convert_file_in_memory(Path(tmp_dir), file)

            typst_file = Path(tmp_dir) / "report.typ"

            returncode, stdout = await typst_compile(typst_file, [])

            if returncode != 0:
                return PlainTextResponse(f"Failed to build report:\n\n{stdout}", status_code=400)

            final_pdf = typst_file.with_suffix(".pdf")

            output_file = PDF_ARTIFACT_DIR / f"{token_urlsafe(32)}.pdf"

            shutil.move(final_pdf, output_file)

        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)

        pdf_url = f"{scheme}://{DOMAIN}/api/v1/files/{output_file.name}"

        task = asyncio.create_task(delete_file_after_timeout(output_file))
        tasks.add(task)
        task.add_done_callback(tasks.discard)

        return {
            "url": pdf_url,
            "typst_file": typst_template,
            "data": data,
        }

    async def delete_file_after_timeout(file: Path):
        await asyncio.sleep(60)

        file.unlink(missing_ok=True)
