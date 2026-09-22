import time
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.errors import DomainError
from app.models import User
from app.providers.auth import (
    AuthCredential,
    AuthPrincipal,
    OidcAuthProvider,
    get_oidc_signing_keys,
    resolve_user,
)
from app.repositories.identity import IdentityRepository

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


def recent_oidc_principal(
    session: Db,
    user: CurrentUser,
    authorization: Annotated[str | None, Header()] = None,
) -> AuthPrincipal:
    settings = get_settings()
    if settings.auth_mode != "oidc" or settings.oidc_jwks_url is None:
        raise DomainError(
            "ACCOUNT_DELETION_REQUIRES_OIDC",
            "Sign in with your Logto account before deleting this account",
            403,
        )
    scheme, separator, token = (authorization or "").partition(" ")
    provider = OidcAuthProvider(
        settings,
        IdentityRepository(session),
        get_oidc_signing_keys(str(settings.oidc_jwks_url)),
    )
    principal = provider.authenticate(
        AuthCredential(scheme=scheme, token=token if separator else "")
    )
    if principal.user_id != user.id:
        raise DomainError("AUTH_REQUIRED", "Invalid or expired access token", 401)
    if principal.issued_at is None or not 0 <= time.time() - principal.issued_at <= 300:
        raise DomainError(
            "RECENT_AUTH_REQUIRED",
            "Sign in again before deleting your account",
            403,
        )
    return principal


RecentOidcPrincipal = Annotated[AuthPrincipal, Depends(recent_oidc_principal)]
