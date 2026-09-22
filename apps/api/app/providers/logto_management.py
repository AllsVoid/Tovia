import base64
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.config import Settings
from app.errors import DomainError


def _request_json(request: Request) -> dict[str, object]:
    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read())
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise DomainError(
            "ACCOUNT_PROVIDER_UNAVAILABLE", "Account provider is unavailable", 503
        ) from exc
    if not isinstance(result, dict):
        raise DomainError("ACCOUNT_PROVIDER_UNAVAILABLE", "Account provider is unavailable", 503)
    return result


def delete_logto_user(settings: Settings, subject: str) -> None:
    """Delete one Logto account through a server-only M2M application."""
    endpoint = settings.logto_management_token_endpoint
    api_url = settings.logto_management_api_url
    resource = settings.logto_management_api_resource
    client_id = settings.logto_management_client_id
    client_secret = settings.logto_management_client_secret
    if not all((endpoint, api_url, resource, client_id, client_secret)):
        raise DomainError(
            "ACCOUNT_DELETION_UNAVAILABLE",
            "Account deletion is not configured",
            503,
        )

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode("ascii")
    token_request = Request(
        str(endpoint),
        data=(
            "grant_type=client_credentials&resource=" + quote(str(resource), safe="") + "&scope=all"
        ).encode("ascii"),
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    token_response = _request_json(token_request)
    access_token = token_response.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise DomainError("ACCOUNT_PROVIDER_UNAVAILABLE", "Account provider is unavailable", 503)

    delete_request = Request(
        f"{str(api_url).rstrip('/')}/users/{quote(subject, safe='')}",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        method="DELETE",
    )
    try:
        with urlopen(delete_request, timeout=10):
            pass
    except HTTPError as exc:
        # A missing identity is already deleted and is safe to complete locally.
        if exc.code == 404:
            return
        raise DomainError(
            "ACCOUNT_PROVIDER_UNAVAILABLE", "Account provider is unavailable", 503
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise DomainError(
            "ACCOUNT_PROVIDER_UNAVAILABLE", "Account provider is unavailable", 503
        ) from exc
