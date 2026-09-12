import os
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_session
from app.main import app
from app.models import User, Visit
from app.routers.deps import current_user

pytestmark = pytest.mark.integration


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

            def post(path: str, payload: dict[str, object]) -> dict:
                response = client.post(f"/api/v1{path}", json=payload)
                assert response.status_code == 201, response.text
                return response.json()["data"]

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
                client.patch(f"/api/v1/visits/{visit['id']}", json={"note": "no"}).status_code
                == 404
            )
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
        command.upgrade(config, "head")
        command.check(config)
        command.downgrade(config, "base")
        command.upgrade(config, "head")
        command.check(config)
    finally:
        get_settings.cache_clear()
