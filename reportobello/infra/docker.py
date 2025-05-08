import asyncio


async def pull_pdf_converter_in_background() -> None:
    process = await asyncio.subprocess.create_subprocess_exec(
        "docker",
        "pull",
        "ghcr.io/reportobello/x2typst",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )

    await process.wait()
