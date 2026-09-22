import json
import logging
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi.testclient import TestClient
from jwt import PyJWK, PyJWKClientConnectionError
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

from app.config import Settings, get_settings
from app.db import get_session
from app.errors import DomainError
from app.main import app
from app.models import User, UserIdentity
from app.providers.auth import (
    AuthCredential,
    OidcAuthProvider,
    SigningKeyResolver,
    get_oidc_signing_keys,
)
from app.repositories.identity import IdentityRepository

ISSUER = "https://auth.example.com/oidc"
AUDIENCE = "https://api.example.com"
SUBJECT = "logto-user-123"


class StaticSigningKeys:
    def __init__(self, signing_key: PyJWK) -> None:
        self.signing_key = signing_key

    def get_signing_key_from_jwt(self, token: str) -> PyJWK:
        return self.signing_key


@pytest.fixture(scope="module")
def local_signing_keys() -> tuple[rsa.RSAPrivateKey, SigningKeyResolver]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    jwk.update({"kid": "local-test-key", "alg": "RS256", "use": "sig"})
    return private_key, StaticSigningKeys(PyJWK.from_dict(jwk))


@pytest.fixture(scope="module")
def logto_signing_keys() -> tuple[ec.EllipticCurvePrivateKey, SigningKeyResolver]:
    private_key = ec.generate_private_key(ec.SECP384R1())
    jwk = ECAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    jwk.update({"kid": "logto-test-key", "alg": "ES384", "use": "sig"})
    return private_key, StaticSigningKeys(PyJWK.from_dict(jwk))


def oidc_settings() -> Settings:
    return Settings(
        app_env="test",
        auth_mode="oidc",
        oidc_issuer=ISSUER,
        oidc_audience=AUDIENCE,
        oidc_jwks_url=f"{ISSUER}/jwks",
        oidc_clock_skew_seconds=0,
        _env_file=None,
    )


def access_token(private_key: rsa.RSAPrivateKey, **claims: Any) -> str:
    payload: dict[str, Any] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": SUBJECT,
        "exp": 4_102_444_800,
        "iat": 1_700_000_000,
    }
    payload.update(claims)
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "local-test-key"})


def logto_access_token(private_key: ec.EllipticCurvePrivateKey, **claims: Any) -> str:
    payload: dict[str, Any] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": SUBJECT,
        "exp": 4_102_444_800,
        "iat": 1_700_000_000,
    }
    payload.update(claims)
    return jwt.encode(payload, private_key, algorithm="ES384", headers={"kid": "logto-test-key"})


@pytest.fixture(scope="module")
def valid_access_token(
    local_signing_keys: tuple[rsa.RSAPrivateKey, SigningKeyResolver],
) -> str:
    private_key, _ = local_signing_keys
    return access_token(private_key)


def provider(
    signing_keys: SigningKeyResolver,
    *,
    identity: UserIdentity | None,
) -> OidcAuthProvider:
    repository = MagicMock(spec=IdentityRepository)
    repository.find.return_value = identity
    return OidcAuthProvider(oidc_settings(), repository, signing_keys)


def assert_auth_required(callable_auth: Any) -> None:
    with pytest.raises(DomainError) as error:
        callable_auth()
    assert error.value.code == "AUTH_REQUIRED"
    assert error.value.status_code == 401


def test_valid_token_resolves_linked_local_user(
    local_signing_keys: tuple[rsa.RSAPrivateKey, SigningKeyResolver],
    valid_access_token: str,
) -> None:
    _, signing_keys = local_signing_keys
    user = User(id=uuid4(), display_name="OIDC user")
    identity = UserIdentity(id=uuid4(), user_id=user.id, provider="logto", provider_subject=SUBJECT)

    principal = provider(signing_keys, identity=identity).authenticate(
        AuthCredential("Bearer", valid_access_token)
    )

    assert principal.user_id == user.id
    assert principal.provider == "logto"
    assert principal.subject == SUBJECT


def test_default_logto_es384_token_resolves_linked_local_user(
    logto_signing_keys: tuple[ec.EllipticCurvePrivateKey, SigningKeyResolver],
) -> None:
    private_key, signing_keys = logto_signing_keys
    user = User(id=uuid4(), display_name="Logto user")
    identity = UserIdentity(id=uuid4(), user_id=user.id, provider="logto", provider_subject=SUBJECT)

    principal = provider(signing_keys, identity=identity).authenticate(
        AuthCredential("Bearer", logto_access_token(private_key))
    )

    assert principal.user_id == user.id
    assert principal.provider == "logto"
    assert principal.subject == SUBJECT


def test_bearer_header_authenticates_api_request(
    monkeypatch: pytest.MonkeyPatch,
    local_signing_keys: tuple[rsa.RSAPrivateKey, SigningKeyResolver],
    valid_access_token: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _, signing_keys = local_signing_keys
    timestamp = datetime.now(UTC)
    user = User(
        id=uuid4(),
        display_name="OIDC user",
        timezone="UTC",
        locale="zh-CN",
        created_at=timestamp,
        updated_at=timestamp,
    )
    identity = UserIdentity(id=uuid4(), user_id=user.id, provider="logto", provider_subject=SUBJECT)
    session = MagicMock()
    session.scalar.return_value = identity
    session.get.return_value = user
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_MODE", "oidc")
    monkeypatch.setenv("OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("OIDC_AUDIENCE", AUDIENCE)
    monkeypatch.setenv("OIDC_JWKS_URL", f"{ISSUER}/jwks")
    monkeypatch.setenv("OIDC_CLOCK_SKEW_SECONDS", "0")
    monkeypatch.setattr("app.providers.auth.get_oidc_signing_keys", lambda _: signing_keys)
    get_settings.cache_clear()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with caplog.at_level(logging.INFO, logger="tovia.audit"), TestClient(app) as client:
            response = client.get(
                "/api/v1/me",
                headers={"Authorization": f"Bearer {valid_access_token}"},
            )
        assert response.status_code == 200
        assert response.json()["data"]["id"] == str(user.id)
        assert response.headers["x-request-id"]
        event = next(
            json.loads(record.message)
            for record in caplog.records
            if record.name == "tovia.audit" and '"event":"auth.authentication"' in record.message
        )
        assert event["outcome"] == "succeeded"
        assert event["provider"] == "logto"
        assert event["user_id"] == str(user.id)
        assert event["request_id"] == response.headers["x-request-id"]
        assert valid_access_token not in caplog.text
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_jwks_outage_fails_closed_as_service_unavailable(
    valid_access_token: str,
) -> None:
    class UnavailableSigningKeys:
        def get_signing_key_from_jwt(self, token: str) -> PyJWK:
            raise PyJWKClientConnectionError("upstream details must not escape")

    auth = provider(UnavailableSigningKeys(), identity=None)
    with pytest.raises(DomainError) as error:
        auth.authenticate(AuthCredential("Bearer", valid_access_token))
    assert error.value.code == "AUTH_PROVIDER_UNAVAILABLE"
    assert error.value.status_code == 503
    assert "upstream details" not in error.value.message


@pytest.mark.parametrize(
    "claim_overrides",
    [
        {"exp": 1},
        {"aud": "https://wrong.example.com"},
        {"iss": "https://wrong.example.com/oidc"},
    ],
    ids=["expired", "wrong-audience", "wrong-issuer"],
)
def test_invalid_standard_claims_are_rejected(
    local_signing_keys: tuple[rsa.RSAPrivateKey, SigningKeyResolver],
    claim_overrides: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    private_key, signing_keys = local_signing_keys
    auth = provider(signing_keys, identity=None)

    token = access_token(private_key, **claim_overrides)
    with caplog.at_level(logging.INFO, logger="tovia.audit"):
        assert_auth_required(lambda: auth.authenticate(AuthCredential("Bearer", token)))
    event = json.loads(caplog.records[-1].message)
    assert event["event"] == "auth.authentication"
    assert event["outcome"] == "denied"
    assert event["reason"] == "invalid_token"
    assert token not in caplog.text


def test_unknown_identity_is_not_registered(
    local_signing_keys: tuple[rsa.RSAPrivateKey, SigningKeyResolver],
) -> None:
    private_key, signing_keys = local_signing_keys
    auth = provider(signing_keys, identity=None)

    assert_auth_required(
        lambda: auth.authenticate(AuthCredential("Bearer", access_token(private_key)))
    )


def test_missing_subject_and_non_bearer_credentials_are_rejected(
    local_signing_keys: tuple[rsa.RSAPrivateKey, SigningKeyResolver],
) -> None:
    private_key, signing_keys = local_signing_keys
    auth = provider(signing_keys, identity=None)
    token_without_subject = access_token(private_key)
    claims = jwt.decode(token_without_subject, options={"verify_signature": False})
    del claims["sub"]
    token_without_subject = jwt.encode(
        claims, private_key, algorithm="RS256", headers={"kid": "local-test-key"}
    )

    assert_auth_required(lambda: auth.authenticate(AuthCredential("Bearer", token_without_subject)))
    assert_auth_required(lambda: auth.authenticate(AuthCredential("Basic", "credentials")))
    assert_auth_required(lambda: auth.authenticate(None))


def test_token_signed_by_another_key_is_rejected(
    local_signing_keys: tuple[rsa.RSAPrivateKey, SigningKeyResolver],
) -> None:
    _, signing_keys = local_signing_keys
    untrusted_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    auth = provider(signing_keys, identity=None)

    assert_auth_required(
        lambda: auth.authenticate(AuthCredential("Bearer", access_token(untrusted_key)))
    )


def test_token_algorithm_is_not_selected_from_header(
    local_signing_keys: tuple[rsa.RSAPrivateKey, SigningKeyResolver],
) -> None:
    _, signing_keys = local_signing_keys
    token = jwt.encode(
        {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": SUBJECT,
            "exp": 4_102_444_800,
        },
        "local-test-secret-with-32-bytes!!",
        algorithm="HS256",
        headers={"kid": "local-test-key"},
    )
    auth = provider(signing_keys, identity=None)

    assert_auth_required(lambda: auth.authenticate(AuthCredential("Bearer", token)))


def test_jwks_client_is_reused_for_same_endpoint() -> None:
    get_oidc_signing_keys.cache_clear()
    try:
        first = get_oidc_signing_keys(f"{ISSUER}/jwks")
        second = get_oidc_signing_keys(f"{ISSUER}/jwks")
        assert first is second
    finally:
        get_oidc_signing_keys.cache_clear()
