from fastapi import APIRouter

import reportobello.api.api
import reportobello.api.jaeger
import reportobello.api.legal
import reportobello.api.page.router
from reportobello.config import IS_LIVE_SITE

router = APIRouter()

router.include_router(reportobello.api.page.router.router)
router.include_router(reportobello.api.api.router)
router.include_router(reportobello.api.jaeger.router)

if IS_LIVE_SITE:
    router.include_router(reportobello.api.legal.router)
