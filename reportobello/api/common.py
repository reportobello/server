import json
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer

from reportobello.domain.user import User
from reportobello.infra.db import get_user_by_api_key


class CustomAuthorizer(HTTPBearer):
    def __init__(self, **kwargs) -> None:  # type: ignore  # noqa: ANN003
        kwargs["auto_error"] = False

        super().__init__(**kwargs)

    async def __call__(self, request: Request) -> User:  # type: ignore
        # check if we have already called this function for the given request
        user = getattr(request.state, "user", ...)

        if user is ...:
            user = await self._get_user(request)

            request.state.user = user

        if user is not None:
            return user

        raise HTTPException(status_code=401, detail="Not authorized")

    async def _get_user(self, request: Request) -> User | None:
        creds = await super().__call__(request)

        if creds and creds.scheme.lower() == "bearer" and (user := get_user_by_api_key(creds.credentials)):
            return user

        if (api_key := request.cookies.get("api_key")) and (user := get_user_by_api_key(api_key)):
            return user

        return None


security = CustomAuthorizer(description="Add your Reportobello API key below. It should start with `rpbl_`")

CurrentUser = Annotated[User, Depends(security)]


# TODO: move to generic utils
def json_prettify(j: str) -> str:
    return json.dumps(json.loads(j), indent=2, ensure_ascii=False)


# TODO: use built in mimetype library?
def mimetype_strip_encoding(mime_type: str | None) -> str | None:
    if mime_type is None:
        return None

    return mime_type.split(";", maxsplit=1)[0].strip()
