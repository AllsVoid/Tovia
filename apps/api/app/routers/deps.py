from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User
from app.providers.auth import resolve_user

Db = Annotated[Session, Depends(get_session)]


def current_user(session: Db) -> User:
    return resolve_user(session)


CurrentUser = Annotated[User, Depends(current_user)]
