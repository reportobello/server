import logging
import os

from fastapi import APIRouter

import reportobello.api.page.homepage
import reportobello.api.page.login
import reportobello.api.page.logout
import reportobello.api.page.settings
import reportobello.api.page.template.router
from reportobello.config import IS_LIVE_SITE

router = APIRouter(include_in_schema=False)

router.include_router(reportobello.api.page.template.router.router)
router.include_router(reportobello.api.page.homepage.router)
router.include_router(reportobello.api.page.settings.router)
router.include_router(reportobello.api.page.login.router)
router.include_router(reportobello.api.page.logout.router)


logger = logging.getLogger("reportobello")


if os.getenv("REPORTOBELLO_GITHUB_OAUTH_CLIENT_ID"):
    import reportobello.api.page.provider.github.router

    router.include_router(reportobello.api.page.provider.github.router.router)

else:
    logger.warning("Could not find REPORTOBELLO_GITHUB_OAUTH_CLIENT_ID env var, GitHub SSO will be disabled")


if IS_LIVE_SITE:
    import reportobello.api.page.survey

    router.include_router(reportobello.api.page.survey.router)
