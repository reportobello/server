import asyncio
import json
from pathlib import Path
from typing import Any

from opentelemetry import trace


tracer = trace.get_tracer("reportobello")

async def convert_file_in_memory(mount: Path, file: Path) -> tuple[str, Any]:
    with tracer.start_as_current_span("x2typst") as span:
        cwd = str(mount)

        process = await asyncio.subprocess.create_subprocess_exec(
            "docker",
            "run",
            "--rm",
            "--cpus",
            "1",
            "--network",
            "none",
            "--mount",
            f"type=bind,src={cwd},dst={cwd}",
            "ghcr.io/reportobello/x2typst",
            str(file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )

        await process.wait()

        if process.returncode != 0:
            assert process.stdout

            stdout = (await process.stdout.read()).decode()

            span.add_event("failure", {"error": stdout})
            span.set_status(trace.StatusCode.ERROR)

            typst = "= Could not convert template"
            (mount / "report.typ").write_text(typst)

            return typst, {}

        typst = (mount / "report.typ").read_text()
        data = json.loads((mount / "data.json").read_text())

        return typst, data
