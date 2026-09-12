from typing import Protocol
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import DomainError
from app.models import User


class AuthProvider(Protocol):
    def current_user_id(self) -> UUID: ...


class DevelopmentAuthProvider:
    def current_user_id(self) -> UUID:
        return get_settings().dev_user_id


def resolve_user(session: Session) -> User:
    settings = get_settings()
    if settings.auth_mode != "development" or settings.app_env == "production":
        raise DomainError("AUTH_REQUIRED", "Authentication provider is not configured", 401)
    provider: AuthProvider = DevelopmentAuthProvider()
    user_id = provider.current_user_id()
    session.execute(
        insert(User)
        .values(id=user_id, display_name="旅行者")
        .on_conflict_do_nothing(index_elements=[User.id])
    )
    session.commit()
    user = session.get(User, user_id)
    assert user is not None
    return user
