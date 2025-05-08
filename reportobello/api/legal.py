from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(include_in_schema=False)


@router.get("/privacy")
async def privacy() -> FileResponse:
    return FileResponse("www/privacy.html")


@router.get("/tos")
@router.get("/terms")
async def terms() -> FileResponse:
    return FileResponse("www/terms.html")


@router.get("/cookies")
async def cookies() -> FileResponse:
    return FileResponse("www/cookies.html")
