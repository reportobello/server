import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from requests_oauthlib import OAuth2Session

from reportobello.api.limiter import limiter
from reportobello.domain.user import User
from reportobello.infra.db import (
    create_or_update_user,
    create_random_api_key,
    get_user_by_provider_id,
)

router = APIRouter()

GITHUB_OAUTH_LOGIN_URL = "https://github.com/login/oauth/authorize"
GITHUB_OAUTH_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"  # noqa: S105

logger = logging.getLogger("reportobello")


class GitHubProvider:
    client_id: str
    client_secret: str

    def __init__(self) -> None:
        self.config_dir = Path("data")

        assert self.config_dir.exists()

        load_dotenv(self.config_dir / ".env", override=True)

        client_id = os.getenv("REPORTOBELLO_GITHUB_OAUTH_CLIENT_ID")
        assert client_id

        client_secret = os.getenv("REPORTOBELLO_GITHUB_OAUTH_CLIENT_SECRET")
        assert client_secret

        self.client_id = client_id
        self.client_secret = client_secret

        self.oauth_csrf_tokens = dict[str, str]()

    async def oauth_create_login_url(self) -> str:
        oauth_session = OAuth2Session(self.client_id)
        url, state = oauth_session.authorization_url(GITHUB_OAUTH_LOGIN_URL, state="")
        assert isinstance(state, str)
        assert isinstance(url, str)

        self.oauth_csrf_tokens[state] = url

        return url

    async def oauth_post_login_handler(
        self,
        state: str | None,
        oauth_url: str,
    ) -> User:
        # TODO: handle token not existing
        if state:
            self.oauth_csrf_tokens.pop(state)

        oauth_session = OAuth2Session(self.client_id, state=state)

        oauth_session.fetch_token(
            GITHUB_OAUTH_ACCESS_TOKEN_URL,
            client_secret=self.client_secret,
            authorization_response=str(oauth_url),
        )

        github_user = oauth_session.get("https://api.github.com/user").json()

        provider = "github"
        provider_user_id = str(github_user["id"])

        if user := get_user_by_provider_id(provider=provider, provider_user_id=provider_user_id):
            return user

        new_user = User(
            id=-1,
            provider=provider,
            provider_user_id=provider_user_id,
            username=github_user["login"],
            api_key=create_random_api_key(),
            email=github_user.get("email"),
        )

        return create_or_update_user(new_user)


GitHubOAuth = GitHubProvider()


@router.get("/provider/github/authorize")
@limiter.limit("5/minute")
async def github_sso(request: Request) -> RedirectResponse:
    url = await GitHubOAuth.oauth_create_login_url()

    return RedirectResponse(url)


@router.get("/provider/github/sso")
@limiter.limit("5/minute")
async def handle_github_sso(state: str, request: Request, error: str | None = None) -> RedirectResponse:
    if error:
        return get_login_error_response("GitHub login failed")

    request_url = request.url.replace(scheme="https")

    user = await GitHubOAuth.oauth_post_login_handler(state, str(request_url))

    logger.info("github login", extra={"user": user.id})

    response = RedirectResponse("/survey" if user.is_setting_up_account else "/?refresh")

    response.set_cookie(
        key="api_key",
        value=user.api_key,
        secure=True,
        httponly=False,
        samesite="strict",
    )

    return response


# TODO: deduplicate
def get_login_error_response(err: str) -> RedirectResponse:
    response = RedirectResponse("/login", status_code=302)

    response.set_cookie(
        key="login_error_msg",
        value=err,
        expires=2,
        secure=True,
        httponly=True,
        samesite="strict",
        path="/login",
    )

    return response
