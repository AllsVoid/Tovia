import base64
from urllib.parse import parse_qs, unquote
from urllib.request import Request

import pytest

from app.config import Settings
from app.errors import DomainError
from app.providers import logto_management


class JsonResponse:
    def __init__(self, payload: bytes = b"") -> None:
        self.payload = payload

    def __enter__(self) -> "JsonResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def configured_settings() -> Settings:
    return Settings(
        logto_management_token_endpoint="https://logto.example/oidc/token",
        logto_management_api_url="https://logto.example/api",
        logto_management_api_resource="https://logto.example/api",
        logto_management_client_id="server-app",
        logto_management_client_secret="secret-value",
        _env_file=None,
    )


def test_management_client_requests_scoped_token_and_deletes_encoded_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[Request] = []

    def fake_urlopen(request: Request, timeout: int) -> JsonResponse:
        assert timeout == 10
        requests.append(request)
        if request.method == "POST":
            return JsonResponse(b'{"access_token":"temporary-token"}')
        return JsonResponse()

    monkeypatch.setattr(logto_management, "urlopen", fake_urlopen)
    logto_management.delete_logto_user(configured_settings(), "subject/with space")

    token_request, delete_request = requests
    assert token_request.full_url == "https://logto.example/oidc/token"
    basic = token_request.get_header("Authorization").removeprefix("Basic ")
    assert base64.b64decode(basic).decode() == "server-app:secret-value"
    token_form = parse_qs(token_request.data.decode())
    assert token_form == {
        "grant_type": ["client_credentials"],
        "resource": ["https://logto.example/api"],
        "scope": ["all"],
    }
    assert unquote(delete_request.full_url.rsplit("/", 1)[-1]) == "subject/with space"
    assert delete_request.get_header("Authorization") == "Bearer temporary-token"


def test_management_client_fails_closed_when_not_configured() -> None:
    with pytest.raises(DomainError) as error:
        logto_management.delete_logto_user(Settings(_env_file=None), "user-1")
    assert error.value.code == "ACCOUNT_DELETION_UNAVAILABLE"
    assert error.value.status_code == 503
