from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import DomainError
from app.models import User


@dataclass(frozen=True, slots=True)
class AuthCredential:
    """Provider-neutral credential extracted at the HTTP boundary."""

    scheme: str
    token: str


@dataclass(frozen=True, slots=True)
class AuthPrincipal:
    """Authenticated identity resolved to Tovia's stable local user ID."""

    user_id: UUID
    provider: str
    subject: str


class AuthProvider(Protocol):
    def authenticate(self, credential: AuthCredential | None) -> AuthPrincipal: ...


class DevelopmentAuthProvider:
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id

    def authenticate(self, credential: AuthCredential | None = None) -> AuthPrincipal:
        return AuthPrincipal(
            user_id=self.user_id,
            provider="development",
            subject=str(self.user_id),
        )


def resolve_user(session: Session) -> User:
    settings = get_settings()
    if settings.auth_mode != "development" or settings.app_env == "production":
        raise DomainError("AUTH_REQUIRED", "Authentication provider is not configured", 401)
    provider: AuthProvider = DevelopmentAuthProvider(settings.dev_user_id)
    principal = provider.authenticate(None)
    session.execute(
        insert(User)
        .values(id=principal.user_id, display_name="旅行者")
        .on_conflict_do_nothing(index_elements=[User.id])
    )
    session.commit()
    user = session.get(User, principal.user_id)
    assert user is not None
    return user
