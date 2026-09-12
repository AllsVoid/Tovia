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


def test_development_auth_forbidden_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", auth_mode="development", _env_file=None)


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
