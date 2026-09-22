from datetime import UTC, date, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.errors import DomainError
from app.models import Trip, TripDay, User, Visit
from app.schemas.core import PlaceCreate, TripCreate, TripPatch, VisitCreate
from app.services.core import TravelService, merge_payload


def test_date_range_and_partial_patch() -> None:
    trip = Trip(
        title="京都",
        slug="kyoto",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 5),
        status="IDEA",
        timezone="Asia/Tokyo",
        visibility="PRIVATE",
    )
    assert merge_payload(TripCreate, trip, TripPatch(title="秋日京都")).end_date == trip.end_date
    with pytest.raises(ValidationError):
        merge_payload(TripCreate, trip, TripPatch(start_date=date(2026, 10, 6)))
    with pytest.raises(ValidationError):
        merge_payload(TripCreate, trip, TripPatch(title=None))


def test_visit_requires_aware_time_and_trip_for_day() -> None:
    with pytest.raises(ValidationError):
        VisitCreate(place_id=uuid4(), visited_at=datetime(2026, 10, 1))
    with pytest.raises(ValidationError):
        VisitCreate(place_id=uuid4(), visited_at=datetime.now(UTC), trip_day_id=uuid4())
    with pytest.raises(ValidationError):
        VisitCreate.model_validate(
            {"place_id": uuid4(), "visited_at": datetime.now(UTC), "source": "AI"}
        )


@pytest.mark.parametrize(
    "changes", [{"latitude": 91}, {"longitude": 181}, {"timezone": "Not/AZone"}]
)
def test_place_rejects_invalid_geography(changes: dict[str, object]) -> None:
    payload = {"canonical_name": "京都", "latitude": 35, "longitude": 135, "timezone": "Asia/Tokyo"}
    with pytest.raises(ValidationError):
        PlaceCreate.model_validate(payload | changes)


@pytest.mark.parametrize("auth_mode", ["disabled", "development"])
def test_non_oidc_auth_forbidden_in_production(auth_mode: str) -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", auth_mode=auth_mode, _env_file=None)


def test_production_oidc_requires_https_issuer() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            auth_mode="oidc",
            oidc_issuer="http://auth.example.com/oidc",
            oidc_audience="https://api.example.com",
            oidc_jwks_url="http://logto:3001/oidc/jwks",
            database_url="postgresql+psycopg://tovia:production-secret@db:5432/tovia",
            _env_file=None,
        )


def test_production_oidc_requires_complete_configuration() -> None:
    with pytest.raises(ValidationError, match="OIDC authentication requires issuer"):
        Settings(app_env="production", auth_mode="oidc", _env_file=None)


def test_production_oidc_accepts_internal_http_jwks_endpoint() -> None:
    settings = Settings(
        app_env="production",
        auth_mode="oidc",
        oidc_issuer="https://auth.example.com/oidc",
        oidc_audience="https://api.example.com",
        oidc_jwks_url="http://logto:3001/oidc/jwks",
        database_url="postgresql+psycopg://tovia:production-secret@db:5432/tovia",
        logto_management_token_endpoint="http://logto:3001/oidc/token",
        logto_management_api_url="http://logto:3001/api",
        logto_management_api_resource="https://default.logto.app/api",
        logto_management_client_id="management-client",
        logto_management_client_secret="management-secret",
        _env_file=None,
    )
    assert settings.auth_mode == "oidc"


def test_production_rejects_sample_database_password() -> None:
    with pytest.raises(ValidationError, match="replace the sample database password"):
        Settings(
            app_env="production",
            auth_mode="oidc",
            oidc_issuer="https://auth.example.com/oidc",
            oidc_audience="https://api.example.com",
            oidc_jwks_url="http://logto:3001/oidc/jwks",
            _env_file=None,
        )


def test_oidc_configuration_requires_all_endpoints() -> None:
    settings = Settings(
        auth_mode="oidc",
        oidc_issuer="https://auth.example.com/oidc",
        oidc_audience="https://api.example.com",
        oidc_jwks_url="https://auth.example.com/oidc/jwks",
        oidc_clock_skew_seconds=60,
        _env_file=None,
    )
    assert str(settings.oidc_issuer) == "https://auth.example.com/oidc"
    assert settings.oidc_audience == "https://api.example.com"
    assert settings.oidc_clock_skew_seconds == 60
    assert settings.auth_mode == "oidc"
    with pytest.raises(ValidationError):
        Settings(
            auth_mode="oidc",
            oidc_issuer="https://auth.example.com/oidc",
            _env_file=None,
        )
    with pytest.raises(ValidationError):
        Settings(oidc_clock_skew_seconds=301, _env_file=None)


def test_service_hides_other_users_trip_and_visit() -> None:
    service = TravelService(MagicMock(), User(id=uuid4(), display_name="one"))
    service.repo = MagicMock()
    service.repo.get.return_value = Trip(id=uuid4(), user_id=uuid4())
    with pytest.raises(DomainError, match="Trip not found"):
        service.trip(uuid4())
    service.repo.get.return_value = Visit(id=uuid4(), user_id=uuid4())
    with pytest.raises(DomainError, match="Visit not found"):
        service.visit(uuid4())


def test_service_rejects_day_from_another_trip() -> None:
    user = User(id=uuid4(), display_name="one")
    trip = Trip(id=uuid4(), user_id=user.id)
    service = TravelService(MagicMock(), user)
    service.repo = MagicMock()
    service.repo.get.side_effect = [TripDay(id=uuid4(), trip_id=trip.id), trip]
    with pytest.raises(DomainError, match="does not belong"):
        service.day(uuid4(), uuid4())
