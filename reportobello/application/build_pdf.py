from hashlib import sha256
import json
import logging
import re
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from itertools import chain
from pathlib import Path
from secrets import token_urlsafe
from tempfile import TemporaryDirectory
from typing import Any

from opentelemetry import trace

from reportobello.api.common import mimetype_strip_encoding
from reportobello.config import IS_LIVE_SITE, PDF_ARTIFACT_DIR, get_file_artifact_path_from_hash
from reportobello.domain.report import Report
from reportobello.domain.template import Template
from reportobello.domain.user import User
from reportobello.infra.db import (
    check_template_exists_for_user,
    get_cached_report_by_hash,
    get_env_vars_for_user,
    get_files_for_template,
    get_template_for_user,
    save_recent_report_build_for_user,
)
from reportobello.infra.job_queue import JobQueue

tracer = trace.get_tracer("reportobello")
logger = logging.getLogger("reportobello")


# TODO: move to common location
class ReportobelloException(Exception):
    pass


class ReportobelloTemplateNotFound(ReportobelloException):
    pass


class ReportobelloInvalidContentType(ReportobelloException):
    pass


class ReportobelloTemplateVersionNotFound(ReportobelloException):
    def __init__(self, version: int) -> None:
        self.version = version


class ReportobelloBuildFailed(ReportobelloException):
    def __init__(self, error_msg: str) -> None:
        self.error_msg = error_msg

    def __str__(self) -> str:
        return f"Failed to build report:\n\n{self.error_msg}"


async def build_report(  # noqa: PLR0913
    *,
    user: User,
    template_name: str,
    template_version: int,
    content_type: str,
    data: Any,
    template_raw: str | None = None,
    is_pure: bool = False,
) -> Report:
    started_at = datetime.now(tz=UTC)

    if not check_template_exists_for_user(user.id, template_name):
        raise ReportobelloTemplateNotFound()

    if mimetype_strip_encoding(content_type) != "application/json":
        raise ReportobelloInvalidContentType(f'Invalid content type "{content_type}"')

    data = json.dumps(data, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    data_hash = sha256(data.encode()).hexdigest().lower()

    if template_raw is not None:
        template = Template(name=template_name, template=template_raw, version=-1)

    elif template := get_template_for_user(user.id, template_name, template_version):
        if is_pure:
            cached_report = get_cached_report_by_hash(
                user_id=user.id,
                template_name=template.name,
                template_version=template.version,
                hash=data_hash
            )

            if cached_report:
                return cached_report

    else:
        raise ReportobelloTemplateVersionNotFound(template_version)


    report = await build_template(
        user=user,
        requested_version=template_version,
        started_at=started_at,
        template=template,
        extension="json",
        data=data,
    )

    report.hash = data_hash

    save_recent_report_build_for_user(user.id, report)

    return report


STRIP_ERROR_MSG = re.compile(r"(\s)┌─\ (.*\/)report.typ(st)?(.*)")


POOL = JobQueue()


async def typst_compile(file: Path, inputs: list[tuple[str, str]]) -> tuple[int, str]:
    with tracer.start_as_current_span("typst compile"):
        return await POOL.run(_typst_compile, str(file), inputs)


def _typst_compile(file: str, inputs: list[tuple[str, str]]) -> tuple[int, str]:
    process = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "typst",
            "compile",
            file,
            *chain.from_iterable(inputs),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=False,
    )

    return process.returncode, process.stdout.decode()


async def build_template(  # noqa: PLR0913, PLR0914
    *,
    user: User,
    requested_version: int,
    started_at: datetime,
    template: Template,
    extension: str,
    data: str,
) -> Report:
    with TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        files = get_files_for_template(user.id, template.name)

        for file in files:
            raw_file = get_file_artifact_path_from_hash(file.hash)

            expanded_path = (tmp_dir / file.filename).absolute()
            assert expanded_path.is_relative_to(tmp_dir)

            expanded_path.symlink_to(raw_file)

        data_file = tmp_dir / f"data.{extension}"
        data_file.write_text(data)

        typst_file = tmp_dir / "report.typ"
        typst_file.write_text(template.template)

        env_vars = get_env_vars_for_user(user.id)

        inputs: list[tuple[str, str]] = [
            ("--input", f"{k}={v}") for k, v in env_vars.items()
        ]

        inputs.append(("--input", f"__RPBL_JSON_PAYLOAD={data}"))

        returncode, stdout = await typst_compile(typst_file, inputs)

        # TODO: how do we differentiate between user error vs server error?
        if returncode != 0:
            logger.info("build failed", extra={"user": user.id})

            finished_at = datetime.now(tz=UTC)

            stdout = STRIP_ERROR_MSG.sub(r"\1┌─ report.typ\3", stdout)

            report = Report(
                filename=None,
                requested_version=requested_version,
                actual_version=template.version,
                template_name=template.name,
                started_at=started_at,
                finished_at=finished_at,
                expires_at=finished_at,
                error_message=stdout,
                data=data,
                data_type=extension,
            )

            save_recent_report_build_for_user(user.id, report)

            raise ReportobelloBuildFailed(stdout)

        final_pdf = typst_file.with_suffix(".pdf")
        output_file = PDF_ARTIFACT_DIR / f"{token_urlsafe(32)}.pdf"

        with tracer.start_as_current_span("copy file"):
            # TODO: upload to S3 bucket
            shutil.move(final_pdf, output_file)

    # TODO: allow this to be configurable
    offset = timedelta(hours=1) if IS_LIVE_SITE else timedelta(days=7)

    finished_at = datetime.now(tz=UTC)
    expires_at = finished_at + offset

    return Report(
        filename=output_file.name,
        requested_version=requested_version,
        actual_version=template.version,
        template_name=template.name,
        started_at=started_at,
        finished_at=finished_at,
        expires_at=expires_at,
        data=data,
        data_type=extension,
    )
