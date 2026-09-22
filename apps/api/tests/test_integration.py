import os
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_session
from app.main import app
from app.models import Activity, Place, Trip, TripDay, User, UserIdentity, Visit, WishlistItem
from app.providers.auth import AuthPrincipal
from app.routers.deps import current_user, recent_oidc_principal

pytestmark = pytest.mark.integration


def test_region_selection_reuses_place_and_projects_trip_visit(database: Session) -> None:
    user = User(display_name="region explorer")
    database.add(user)
    database.commit()
    app.dependency_overrides[get_session] = lambda: database
    app.dependency_overrides[current_user] = lambda: user
    try:
        with TestClient(app) as client:
            search = client.get("/api/v1/regions/search", params={"q": "南京"})
            assert search.status_code == 200
            assert search.json()["data"][0]["id"] == "cn:3201"
            first = client.post("/api/v1/regions/cn:3201/place")
            second = client.post("/api/v1/regions/cn:3201/place")
            assert first.status_code == second.status_code == 200
            place = first.json()["data"]
            assert place["id"] == second.json()["data"]["id"]
            assert place["metadata"]["region_id"] == "cn:3201"
            assert client.get("/api/v1/map/places").json()["data"]["total"] == 0
            trip = client.post("/api/v1/trips", json={"title": "南京回忆"}).json()["data"]
            visit = client.post(
                "/api/v1/visits",
                json={
                    "place_id": place["id"],
                    "trip_id": trip["id"],
                    "visited_at": "2024-10-01T09:00:00+08:00",
                },
            )
            assert visit.status_code == 201
            marker = client.get("/api/v1/map/places").json()["data"]["places"][0]
            assert marker["region_id"] == "cn:3201"
            assert marker["visit_count"] == 1
            assert client.post("/api/v1/regions/cn:invalid/place").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_profile_export_includes_linked_records_and_is_audited(
    database: Session, caplog: pytest.LogCaptureFixture
) -> None:
    user = User(display_name="export owner")
    place = Place(
        canonical_name="Kyoto",
        country_code="JP",
        timezone="Asia/Tokyo",
        location=WKTElement("POINT(135.7681 35.0116)", srid=4326),
    )
    database.add_all([user, place])
    database.flush()
    trip = Trip(user_id=user.id, title="Kyoto", slug="kyoto", timezone="Asia/Tokyo")
    database.add(trip)
    database.flush()
    trip_day = TripDay(trip_id=trip.id, date=datetime(2026, 10, 2).date(), title="Old town")
    database.add(trip_day)
    database.flush()
    visit = Visit(
        user_id=user.id,
        trip_id=trip.id,
        trip_day_id=trip_day.id,
        place_id=place.id,
        visited_at=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    activity = Activity(
        trip_id=trip.id,
        trip_day_id=trip_day.id,
        place_id=place.id,
        type="VISIT",
        title="Temple walk",
    )
    wishlist = WishlistItem(user_id=user.id, place_id=place.id, note="Return in spring")
    database.add_all([visit, activity, wishlist])
    database.commit()
    app.dependency_overrides[get_session] = lambda: database
    app.dependency_overrides[current_user] = lambda: user
    try:
        with caplog.at_level("INFO", logger="tovia.audit"), TestClient(app) as client:
            response = client.get("/api/v1/me/export")
        assert response.status_code == 200
        exported = response.json()["data"]
        assert exported["schema_version"] == "1.0"
        records = exported["data"]
        assert records["user"]["id"] == str(user.id)
        assert records["trips"][0]["id"] == str(trip.id)
        assert records["trip_days"][0]["trip_id"] == str(trip.id)
        assert records["visits"][0]["trip_day_id"] == str(trip_day.id)
        assert records["activities"][0]["place_id"] == str(place.id)
        assert records["places"][0]["id"] == str(place.id)
        assert records["wishlist_items"][0]["place_id"] == str(place.id)
        assert any('"event":"data.export"' in record.message for record in caplog.records)
    finally:
        app.dependency_overrides.clear()


def test_account_deletion_removes_logto_and_local_user_data(
    database: Session, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from app.services import core as core_service

    user = User(display_name="delete owner")
    place = Place(
        canonical_name="Osaka",
        country_code="JP",
        timezone="Asia/Tokyo",
        location=WKTElement("POINT(135.5 34.7)", srid=4326),
    )
    database.add_all([user, place])
    database.flush()
    trip = Trip(user_id=user.id, title="Osaka", slug="osaka", timezone="Asia/Tokyo")
    database.add(trip)
    database.flush()
    trip_day = TripDay(trip_id=trip.id, date=datetime(2026, 10, 2).date())
    database.add(trip_day)
    database.flush()
    database.add_all(
        [
            UserIdentity(user_id=user.id, provider="logto", provider_subject="logto-user-1"),
            Visit(
                user_id=user.id,
                trip_id=trip.id,
                trip_day_id=trip_day.id,
                place_id=place.id,
                visited_at=datetime(2026, 10, 2, 0, tzinfo=UTC),
            ),
            WishlistItem(user_id=user.id, place_id=place.id),
        ]
    )
    database.commit()
    provider_deletions: list[str] = []
    monkeypatch.setattr(
        core_service,
        "delete_logto_user",
        lambda _settings, subject: provider_deletions.append(subject),
    )
    app.dependency_overrides[get_session] = lambda: database
    app.dependency_overrides[current_user] = lambda: user
    app.dependency_overrides[recent_oidc_principal] = lambda: AuthPrincipal(
        user_id=user.id, provider="logto", subject="logto-user-1", issued_at=1
    )
    try:
        with caplog.at_level("INFO", logger="tovia.audit"), TestClient(app) as client:
            response = client.post("/api/v1/me/delete", json={"confirmation": "DELETE"})
        assert response.status_code == 200
        assert provider_deletions == ["logto-user-1"]
        assert database.scalar(select(User.id).where(User.id == user.id)) is None
        assert (
            database.scalar(select(UserIdentity.id).where(UserIdentity.user_id == user.id)) is None
        )
        assert database.scalar(select(Visit.id).where(Visit.user_id == user.id)) is None
        assert (
            database.scalar(select(WishlistItem.id).where(WishlistItem.user_id == user.id)) is None
        )
        assert any('"event":"account.deletion"' in record.message for record in caplog.records)
    finally:
        app.dependency_overrides.clear()


def test_map_counts_wishlist_and_calendar_boundaries(database: Session) -> None:
    user = User(display_name="explorer")
    other = User(display_name="private")
    database.add_all([user, other])
    database.commit()
    app.dependency_overrides[get_session] = lambda: database
    app.dependency_overrides[current_user] = lambda: user
    try:
        with TestClient(app) as client:

            def post(path: str, payload: dict[str, object]) -> dict[str, Any]:
                response = client.post(f"/api/v1{path}", json=payload)
                assert response.status_code in (200, 201), response.text
                return cast(dict[str, Any], response.json()["data"])

            def get(path: str) -> dict[str, Any]:
                response = client.get(f"/api/v1{path}")
                assert response.status_code == 200, response.text
                return cast(dict[str, Any], response.json()["data"])

            place = post(
                "/places",
                {
                    "canonical_name": "Tokyo",
                    "country_code": "JP",
                    "timezone": "Asia/Tokyo",
                    "latitude": 35.68,
                    "longitude": 139.69,
                },
            )
            domestic = post(
                "/places",
                {
                    "canonical_name": "Shanghai",
                    "country_code": "CN",
                    "timezone": "Asia/Shanghai",
                    "latitude": 31.23,
                    "longitude": 121.47,
                },
            )
            unknown = post(
                "/places",
                {"canonical_name": "Unknown", "latitude": 0, "longitude": 0, "timezone": "UTC"},
            )
            trip = post(
                "/trips", {"title": "跨月", "start_date": "2024-02-28", "end_date": "2024-03-02"}
            )
            first = post(
                "/visits",
                {
                    "place_id": place["id"],
                    "trip_id": trip["id"],
                    "visited_at": "2024-02-28T15:30:00Z",
                    "ended_at": "2024-03-01T15:00:00Z",
                },
            )
            post("/visits", {"place_id": place["id"], "visited_at": "2024-02-29T03:00:00Z"})
            post("/visits", {"place_id": place["id"], "visited_at": "2099-01-01T00:00:00Z"})
            wish = post("/wishlist", {"place_id": place["id"], "note": "again"})
            assert post("/wishlist", {"place_id": place["id"]})["id"] == wish["id"]
            post("/wishlist", {"place_id": domestic["id"]})
            post("/wishlist", {"place_id": unknown["id"]})
            summary = get("/map/summary")
            assert summary == {
                "places_count": 3,
                "visited_places": 1,
                "upcoming_places": 1,
                "wishlist_places": 3,
                "visit_count": 2,
                "countries_count": 2,
                "unknown_country_places": 1,
            }
            page = get("/map/places?limit=1")
            assert len(page["places"]) == 1 and page["total"] == 3
            assert get("/map/places?scope=domestic")["total"] == 1
            assert get("/map/places?scope=international")["total"] == 1
            assert get("/map/places?status=upcoming")["places"][0]["id"] == place["id"]
            detail = get(f"/map/places/{place['id']}")
            assert detail["visits_total"] == 3 and detail["wishlist_note"] == "again"
            assert detail["place"]["longitude"] == pytest.approx(139.69)
            feb = get("/calendar/month?year=2024&month=2")
            assert len(feb["days"]) == 29
            assert feb["days"][27]["visits_count"] == 0
            assert feb["days"][28]["visits_count"] == 2
            assert feb["days"][28]["places_count"] == 1
            march = get("/calendar/month?year=2024&month=3")
            assert march["days"][0]["visits_count"] == 1
            assert march["days"][1]["visits_count"] == 0  # midnight end is exclusive
            assert march["days"][1]["trip_ids"] == [trip["id"]]
            assert get("/calendar/day?date=2024-03-01")["visits"][0]["id"] == first["id"]
            undated = post("/trips", {"title": "未定日期"})
            day = post(f"/trips/{undated['id']}/days", {"date": "2024-02-29"})
            post(f"/trips/{undated['id']}/activities", {"trip_day_id": day["id"], "title": "散步"})
            daily = get("/calendar/day?date=2024-02-29")
            assert len(daily["activities"]) == 1 and len(daily["trips"]) == 2
            app.dependency_overrides[current_user] = lambda: other
            assert get("/map/summary")["places_count"] == 0
            assert client.get(f"/api/v1/map/places/{place['id']}").status_code == 404
            assert get("/calendar/day?date=2024-02-29")["visits"] == []
            assert get("/calendar/month?year=2024&month=2")["trips"] == []
            assert client.delete(f"/api/v1/wishlist/{place['id']}").status_code == 200
            app.dependency_overrides[current_user] = lambda: user
            assert get("/map/summary")["wishlist_places"] == 3
            assert client.delete(f"/api/v1/wishlist/{place['id']}").status_code == 200
            assert get("/map/summary")["visit_count"] == 2
            assert client.delete(f"/api/v1/trips/{trip['id']}").status_code == 200
            assert get("/calendar/day?date=2024-03-01")["visits"][0]["trip_id"] is None
            assert client.get("/api/v1/calendar/month?year=2024&month=13").status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def database() -> Iterator[Session]:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set; requires a dedicated migrated PostGIS database")
    engine = create_engine(url)
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()
    engine.dispose()


def test_postgis_crud_ownership_and_preserved_visits(database: Session) -> None:
    user = User(display_name="test", timezone="Asia/Tokyo")
    stranger = User(display_name="other")
    database.add_all([user, stranger])
    database.commit()
    app.dependency_overrides[get_session] = lambda: database
    app.dependency_overrides[current_user] = lambda: user
    try:
        with TestClient(app) as client:

            def post(path: str, payload: dict[str, object]) -> dict[str, Any]:
                response = client.post(f"/api/v1{path}", json=payload)
                assert response.status_code == 201, response.text
                return cast(dict[str, Any], response.json()["data"])

            assert client.get("/health").status_code == 200
            trip = post(
                "/trips",
                {
                    "title": "京都",
                    "start_date": "2026-10-01",
                    "end_date": "2026-10-05",
                    "timezone": "Asia/Tokyo",
                },
            )
            day = post(f"/trips/{trip['id']}/days", {"date": "2026-10-02"})
            place = post(
                "/places",
                {
                    "canonical_name": "京都",
                    "latitude": 35.0116,
                    "longitude": 135.7681,
                    "timezone": "Asia/Tokyo",
                },
            )
            assert place["latitude"] == pytest.approx(35.0116)
            assert place["longitude"] == pytest.approx(135.7681)
            visit = post(
                "/visits",
                {
                    "place_id": place["id"],
                    "trip_id": trip["id"],
                    "trip_day_id": day["id"],
                    "visited_at": "2026-10-02T09:00:00+09:00",
                },
            )
            second = post(
                "/visits", {"place_id": place["id"], "visited_at": "2025-10-02T09:00:00+09:00"}
            )
            assert second["id"] != visit["id"]
            activity = post(
                f"/trips/{trip['id']}/activities",
                {"trip_day_id": day["id"], "place_id": place["id"], "title": "散步"},
            )
            assert (
                client.patch(
                    f"/api/v1/trips/{trip['id']}", json={"start_date": "2026-10-04"}
                ).status_code
                == 422
            )
            assert (
                client.patch(
                    f"/api/v1/activities/{activity['id']}", json={"title": "清晨散步"}
                ).status_code
                == 200
            )
            assert (
                client.post(
                    f"/api/v1/trips/{trip['id']}/days", json={"date": "2026-10-02"}
                ).status_code
                == 409
            )
            database.rollback()
            app.dependency_overrides[current_user] = lambda: stranger
            assert client.get(f"/api/v1/trips/{trip['id']}").status_code == 404
            assert client.get("/api/v1/visits").json()["data"] == []
            assert (
                client.patch(f"/api/v1/trips/{trip['id']}", json={"title": "越权修改"}).status_code
                == 404
            )
            assert client.delete(f"/api/v1/trips/{trip['id']}").status_code == 404
            assert (
                client.patch(f"/api/v1/visits/{visit['id']}", json={"note": "no"}).status_code
                == 404
            )
            assert client.delete(f"/api/v1/visits/{visit['id']}").status_code == 404
            assert client.delete(f"/api/v1/activities/{activity['id']}").status_code == 404
            assert (
                client.post(
                    "/api/v1/visits",
                    json={
                        "place_id": place["id"],
                        "trip_id": trip["id"],
                        "visited_at": "2026-10-02T09:00:00Z",
                    },
                ).status_code
                == 404
            )
            app.dependency_overrides[current_user] = lambda: user
            assert client.get(f"/api/v1/trips/{trip['id']}").status_code == 200
            owner_visits = client.get("/api/v1/visits").json()["data"]
            assert {row["id"] for row in owner_visits} == {visit["id"], second["id"]}
            assert client.delete(f"/api/v1/trips/{trip['id']}").status_code == 200
            visits = client.get("/api/v1/visits").json()["data"]
            assert len(visits) == 2
            assert all(row["trip_id"] is None and row["trip_day_id"] is None for row in visits)
            assert client.get(f"/api/v1/places/{place['id']}").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_schema_constraints_and_spatial_index(database: Session) -> None:
    indexes = (
        database.execute(text("SELECT indexdef FROM pg_indexes WHERE tablename='places'"))
        .scalars()
        .all()
    )
    assert any("USING gist (location)" in value for value in indexes)
    assert database.scalar(text("SELECT PostGIS_Version()"))
    with pytest.raises(IntegrityError), database.begin_nested():
        database.add(Visit(user_id=uuid4(), place_id=uuid4(), visited_at=datetime.now(UTC)))
        database.flush()
    assert database.scalar(select(text("1"))) == 1


def test_user_identity_database_constraints(database: Session) -> None:
    owner = User(display_name="identity owner")
    other = User(display_name="identity other")
    database.add_all([owner, other])
    database.commit()
    database.add(
        UserIdentity(user_id=owner.id, provider="logto", provider_subject="stable-subject")
    )
    database.commit()

    with pytest.raises(IntegrityError), database.begin_nested():
        database.add(
            UserIdentity(user_id=other.id, provider="logto", provider_subject="stable-subject")
        )
        database.flush()

    assert (
        database.scalar(
            select(UserIdentity.user_id).where(
                UserIdentity.provider == "logto",
                UserIdentity.provider_subject == "stable-subject",
            )
        )
        == owner.id
    )


def test_migration_roundtrip_on_disposable_database(monkeypatch: pytest.MonkeyPatch) -> None:
    # Explicit opt-in: never downgrade a developer's normal database.
    url = os.environ.get("MIGRATION_TEST_DATABASE_URL")
    if not url:
        pytest.skip("MIGRATION_TEST_DATABASE_URL not set (must be disposable)")
    from app.config import get_settings

    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    try:
        config = Config("alembic.ini")
        command.upgrade(config, "0003_wishlist")
        engine = create_engine(url)
        user_id = uuid4()
        trip_id = uuid4()
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO users (id, display_name) VALUES (:user_id, 'migration owner')"),
                {"user_id": user_id},
            )
            connection.execute(
                text(
                    "INSERT INTO trips (id, user_id, title, slug) "
                    "VALUES (:trip_id, :user_id, 'existing trip', 'existing-trip')"
                ),
                {"trip_id": trip_id, "user_id": user_id},
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert (
                connection.scalar(
                    text("SELECT id FROM users WHERE id = :user_id"), {"user_id": user_id}
                )
                == user_id
            )
            assert (
                connection.scalar(
                    text("SELECT id FROM trips WHERE id = :trip_id"), {"trip_id": trip_id}
                )
                == trip_id
            )
            assert connection.scalar(text("SELECT count(*) FROM user_identities")) == 0
        engine.dispose()
        command.check(config)
        command.downgrade(config, "base")
        command.upgrade(config, "head")
        command.check(config)
    finally:
        get_settings.cache_clear()
