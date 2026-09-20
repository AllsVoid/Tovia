from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User
from app.providers.auth import AuthCredential, resolve_user

Db = Annotated[Session, Depends(get_session)]


def current_user(
    session: Db,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    credential = None
    if authorization is not None:
        scheme, separator, token = authorization.partition(" ")
        credential = AuthCredential(scheme=scheme, token=token if separator else "")
    return resolve_user(session, credential)


CurrentUser = Annotated[User, Depends(current_user)]
