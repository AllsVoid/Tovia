from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol
from uuid import UUID

import jwt
from jwt import PyJWK, PyJWKClient, PyJWKClientConnectionError, PyJWTError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.audit import audit_auth_event
from app.config import Settings, get_settings
from app.errors import DomainError
from app.models import User
from app.repositories.identity import IdentityRepository

OIDC_PROVIDER = "logto"
OIDC_ALGORITHMS = ("ES384", "RS256")


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
    issued_at: int | None = None


class AuthProvider(Protocol):
    def authenticate(self, credential: AuthCredential | None) -> AuthPrincipal: ...


class SigningKeyResolver(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> PyJWK: ...


class DevelopmentAuthProvider:
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id

    def authenticate(self, credential: AuthCredential | None = None) -> AuthPrincipal:
        return AuthPrincipal(
            user_id=self.user_id,
            provider="development",
            subject=str(self.user_id),
        )


class OidcAuthProvider:
    def __init__(
        self,
        settings: Settings,
        repository: IdentityRepository,
        signing_keys: SigningKeyResolver,
    ) -> None:
        if settings.oidc_issuer is None or settings.oidc_audience is None:
            raise ValueError("OIDC authentication is not fully configured")
        self.issuer = str(settings.oidc_issuer)
        self.audience = settings.oidc_audience
        self.clock_skew_seconds = settings.oidc_clock_skew_seconds
        self.repository = repository
        self.signing_keys = signing_keys

    def authenticate(self, credential: AuthCredential | None) -> AuthPrincipal:
        if credential is None or credential.scheme.lower() != "bearer" or not credential.token:
            audit_auth_event(
                "auth.authentication", "denied", provider=OIDC_PROVIDER, reason="missing_bearer"
            )
            raise DomainError("AUTH_REQUIRED", "Bearer access token is required", 401)

        try:
            signing_key = self.signing_keys.get_signing_key_from_jwt(credential.token)
            claims: dict[str, Any] = jwt.decode(
                credential.token,
                signing_key,
                algorithms=OIDC_ALGORITHMS,
                audience=self.audience,
                issuer=self.issuer,
                leeway=self.clock_skew_seconds,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except PyJWKClientConnectionError as exc:
            audit_auth_event(
                "auth.authentication",
                "unavailable",
                provider=OIDC_PROVIDER,
                reason="jwks_unavailable",
            )
            raise DomainError(
                "AUTH_PROVIDER_UNAVAILABLE", "Authentication provider is unavailable", 503
            ) from exc
        except (PyJWTError, ValueError) as exc:
            audit_auth_event(
                "auth.authentication", "denied", provider=OIDC_PROVIDER, reason="invalid_token"
            )
            raise DomainError("AUTH_REQUIRED", "Invalid or expired access token", 401) from exc

        subject = claims["sub"]
        if not isinstance(subject, str) or not subject:
            audit_auth_event(
                "auth.authentication", "denied", provider=OIDC_PROVIDER, reason="invalid_subject"
            )
            raise DomainError("AUTH_REQUIRED", "Invalid or expired access token", 401)
        identity = self.repository.find(OIDC_PROVIDER, subject)
        if identity is None:
            audit_auth_event(
                "auth.authentication",
                "denied",
                provider=OIDC_PROVIDER,
                reason="identity_unlinked",
            )
            raise DomainError("AUTH_REQUIRED", "Identity is not linked", 401)
        issued_at = claims.get("iat")
        return AuthPrincipal(
            user_id=identity.user_id,
            provider=OIDC_PROVIDER,
            subject=subject,
            issued_at=issued_at if isinstance(issued_at, int) else None,
        )


@lru_cache
def get_oidc_signing_keys(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(
        jwks_url,
        cache_jwk_set=True,
        lifespan=300,
        timeout=5,
    )


def resolve_user(session: Session, credential: AuthCredential | None = None) -> User:
    settings = get_settings()
    if settings.auth_mode == "development" and settings.app_env != "production":
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
    if settings.auth_mode == "oidc":
        if settings.oidc_jwks_url is None:
            raise DomainError("AUTH_REQUIRED", "Authentication provider is not configured", 401)
        provider = OidcAuthProvider(
            settings,
            IdentityRepository(session),
            get_oidc_signing_keys(str(settings.oidc_jwks_url)),
        )
        principal = provider.authenticate(credential)
        user = session.get(User, principal.user_id)
        if user is None:
            audit_auth_event(
                "auth.authentication",
                "denied",
                provider=principal.provider,
                reason="local_user_missing",
                user_id=str(principal.user_id),
            )
            raise DomainError("AUTH_REQUIRED", "Identity is not linked", 401)
        audit_auth_event(
            "auth.authentication",
            "succeeded",
            provider=principal.provider,
            user_id=str(principal.user_id),
        )
        return user
    raise DomainError("AUTH_REQUIRED", "Authentication provider is not configured", 401)
