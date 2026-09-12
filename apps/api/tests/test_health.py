from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db import get_session
from app.main import app
from app.services.health import SCHEMA_HEAD


def test_health_and_openapi() -> None:
    session = MagicMock()
    session.scalar.return_value = SCHEMA_HEAD
    app.dependency_overrides[get_session] = lambda: session
    try:
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json()["data"]["postgis"] == "ok"
            schema = client.get("/openapi.json").json()
            assert "/api/v1/trips" in schema["paths"]
            assert not any("imports" in path or "/ai/" in path for path in schema["paths"])
            assert client.get("/missing").json()["error"]["code"] == "HTTP_404"
    finally:
        app.dependency_overrides.clear()


def test_health_reports_database_failure_without_credentials() -> None:
    session = MagicMock()
    session.execute.side_effect = OperationalError("secret", {}, Exception("secret"))
    app.dependency_overrides[get_session] = lambda: session
    try:
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 503
            assert response.json()["data"]["database"] == "unavailable"
            assert "secret" not in response.text
    finally:
        app.dependency_overrides.clear()
