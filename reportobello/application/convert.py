import asyncio
import json
from pathlib import Path

from opentelemetry import trace


tracer = trace.get_tracer("reportobello")

async def convert_file_in_memory(dir: Path, file: Path):
    with tracer.start_as_current_span("x2typst") as span:
        tmp = str(dir)

        process = await asyncio.subprocess.create_subprocess_exec(
            "docker",
            "run",
            "--rm",
            "--cpus",
            "1",
            "--network",
            "none",
            "--mount",
            f"type=bind,src={tmp},dst={tmp}",
            "ghcr.io/reportobello/x2typst",
            str(file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=tmp,
        )

        await process.wait()

        if process.returncode != 0:
            assert process.stdout

            stdout = (await process.stdout.read()).decode()

            span.add_event("failure", {"error": stdout})
            span.set_status(trace.StatusCode.ERROR)

            typst = "= Could not convert template"
            (dir / "report.typ").write_text(typst)

            return typst, {}

        typst = (dir / "report.typ").read_text()
        data = json.loads((dir / "data.json").read_text())

        return typst, data
