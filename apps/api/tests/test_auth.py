from collections.abc import Iterator
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session
from app.main import app
from app.models import User
from app.providers.auth import AuthPrincipal, DevelopmentAuthProvider, resolve_user
from app.routers import core, explore
from app.routers.deps import current_user


def dependency_calls(route: APIRoute) -> Iterator[object]:
    pending = list(route.dependant.dependencies)
    while pending:
        dependency = pending.pop()
        yield dependency.call
        pending.extend(dependency.dependencies)


def test_every_business_route_requires_current_user() -> None:
    business_routes = [
        route
        for route in [*core.router.routes, *explore.router.routes]
        if isinstance(route, APIRoute) and route.path.startswith("/api/v1")
    ]
    assert business_routes
    missing = [
        route.path for route in business_routes if current_user not in dependency_calls(route)
    ]
    assert missing == []


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1/me"),
        ("GET", "/api/v1/trips"),
        ("GET", "/api/v1/regions/search?q=南京"),
        ("GET", "/api/v1/map/summary"),
        ("GET", "/api/v1/calendar/month?year=2026&month=9"),
    ],
)
def test_disabled_auth_returns_standard_401(
    monkeypatch: pytest.MonkeyPatch, method: str, path: str
) -> None:
    monkeypatch.setenv("AUTH_MODE", "disabled")
    get_settings.cache_clear()
    app.dependency_overrides[get_session] = lambda: MagicMock()
    try:
        with TestClient(app) as client:
            response = client.request(method, path)
        assert response.status_code == 401
        assert response.json() == {
            "data": None,
            "meta": {},
            "error": {
                "code": "AUTH_REQUIRED",
                "message": "Authentication provider is not configured",
            },
        }
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_development_provider_returns_stable_local_principal() -> None:
    user_id = UUID("00000000-0000-4000-8000-000000000001")
    provider = DevelopmentAuthProvider(user_id)

    assert provider.authenticate(None) == AuthPrincipal(
        user_id=user_id,
        provider="development",
        subject=str(user_id),
    )


def test_development_resolver_preserves_fixed_local_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = UUID("00000000-0000-4000-8000-000000000001")
    user = User(id=user_id, display_name="旅行者")
    session = MagicMock()
    session.get.return_value = user
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_MODE", "development")
    monkeypatch.setenv("DEV_USER_ID", str(user_id))
    get_settings.cache_clear()
    try:
        assert resolve_user(session) is user
        session.execute.assert_called_once()
        session.commit.assert_called_once()
        session.get.assert_called_once_with(User, user_id)
    finally:
        get_settings.cache_clear()
