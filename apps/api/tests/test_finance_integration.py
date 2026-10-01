import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_integration import database as database

from app.db import get_session
from app.errors import DomainError
from app.main import app
from app.models import Activity, Trip, TripDay, User
from app.models.finance import Expense
from app.providers.auth import AuthPrincipal
from app.routers.deps import current_user
from app.schemas.data_export import validate_export_document
from app.schemas.finance import ExpenseCreate, ExpensePatch
from app.services.core import TravelService
from app.services.finance import FinanceService

pytestmark = pytest.mark.integration


def test_database_enforces_owner_and_container_links(database: Session) -> None:
    owner, stranger = User(display_name="Owner"), User(display_name="Stranger")
    database.add_all([owner, stranger])
    database.flush()
    first = Trip(user_id=owner.id, title="First", slug="finance-first")
    second = Trip(user_id=stranger.id, title="Second", slug="finance-second")
    database.add_all([first, second])
    database.flush()
    day = TripDay(trip_id=second.id, date=date(2026, 10, 1))
    database.add(day)
    database.flush()
    activity = Activity(trip_id=second.id, trip_day_id=day.id, type="HOTEL", title="Check in")
    database.add(activity)
    database.flush()
    for links in (
        {"trip_id": second.id},
        {"trip_id": first.id, "trip_day_id": day.id},
        {"trip_id": first.id, "activity_id": activity.id},
    ):
        with pytest.raises(IntegrityError), database.begin_nested():
            database.add(
                Expense(
                    user_id=owner.id,
                    original_amount=Decimal("1"),
                    original_currency="CNY",
                    category="FOOD",
                    occurred_at="2026-10-01T00:00:00Z",
                    timezone="UTC",
                    **links,
                )
            )
            database.flush()


def test_account_cleanup_includes_financial_records(
    database: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.models import UserIdentity
    from app.schemas.core import ActivityCreate, DayCreate, TripCreate
    from app.schemas.finance import BookingCreate
    from app.services import core as core_module

    owner = User(display_name="Financial account")
    database.add(owner)
    database.commit()
    owner_id = owner.id
    database.add(
        UserIdentity(user_id=owner_id, provider="logto", provider_subject="finance-cleanup-subject")
    )
    database.commit()
    travel = TravelService(database, owner)
    trip = travel.create_trip(TripCreate(title="Cleanup"))
    day = travel.create_day(trip.id, DayCreate(date=date(2026, 10, 1)))
    activity = travel.create_activity(trip.id, ActivityCreate(title="Stay", trip_day_id=day.id))
    finance = FinanceService(database, owner)
    finance.create_booking(
        BookingCreate(
            trip_id=trip.id,
            activity_id=activity.id,
            type="HOTEL",
            title="Stay",
            start_at="2026-10-01T00:00:00Z",
        )
    )
    finance.create_expense(
        ExpenseCreate(
            trip_id=trip.id,
            trip_day_id=day.id,
            activity_id=activity.id,
            original_amount=Decimal("10"),
            original_currency="CNY",
            occurred_at="2026-10-01T00:00:00Z",
        )
    )
    monkeypatch.setattr(core_module, "delete_logto_user", lambda settings, subject: None)
    travel.delete_account(
        AuthPrincipal(user_id=owner_id, provider="logto", subject="finance-cleanup-subject")
    )
    assert database.get(User, owner_id) is None
    assert FinanceService(database, owner).repo.page(Expense, owner_id, None, 50, 0)[1] == 0


def test_finance_crud_permissions_paging_links_export_and_deletion(database: Session) -> None:
    owner = User(display_name="Finance owner")
    stranger = User(display_name="Stranger")
    database.add_all([owner, stranger])
    database.commit()
    app.dependency_overrides[get_session] = lambda: database
    app.dependency_overrides[current_user] = lambda: owner
    try:
        with TestClient(app) as client:
            trip = client.post("/api/v1/trips", json={"title": "Return journey"}).json()["data"]
            trip_id = trip["id"]
            day = client.post(f"/api/v1/trips/{trip_id}/days", json={"date": "2026-10-01"}).json()[
                "data"
            ]
            activity = client.post(
                f"/api/v1/trips/{trip_id}/activities",
                json={"trip_day_id": day["id"], "title": "Check in"},
            ).json()["data"]
            place = client.post("/api/v1/regions/cn:3201/place").json()["data"]
            bookings = []
            for kind, title in [("FLIGHT", "Outbound"), ("TRAIN", "Return"), ("HOTEL", "Hotel")]:
                response = client.post(
                    "/api/v1/bookings",
                    json={
                        "trip_id": trip_id,
                        "activity_id": activity["id"],
                        "type": kind,
                        "title": title,
                        "start_at": "2026-10-01T09:00:00+08:00",
                        "origin_place_id": place["id"],
                        "amount": "100.1234",
                        "currency": "CNY",
                    },
                )
                assert response.status_code == 201, response.text
                bookings.append(response.json()["data"])
            base = {
                "trip_id": trip_id,
                "trip_day_id": day["id"],
                "activity_id": activity["id"],
                "place_id": place["id"],
                "original_currency": "USD",
                "occurred_at": "2026-10-01T10:00:00+08:00",
                "category": "FOOD",
            }
            expenses = []
            for amount in ["0.1", "0.2"]:
                response = client.post("/api/v1/expenses", json={**base, "original_amount": amount})
                assert response.status_code == 201, response.text
                expenses.append(response.json()["data"])
            settled = client.post(
                "/api/v1/expenses",
                json={
                    **base,
                    "original_amount": "1000",
                    "original_currency": "JPY",
                    "settled_amount": "50.4321",
                    "settled_currency": "CNY",
                    "exchange_rate": "0.0504321",
                },
            )
            assert settled.status_code == 201
            expenses.append(settled.json()["data"])
            for path in ("bookings", "expenses"):
                page = client.get(f"/api/v1/trips/{trip_id}/{path}?limit=1&offset=1")
                assert len(page.json()["data"]) == 1
                assert page.json()["meta"]["total"] == 3
                assert client.get(f"/api/v1/{path}?limit=101").status_code == 422
                assert client.get(f"/api/v1/{path}?offset=-1").status_code == 422
            summary = client.get(f"/api/v1/trips/{trip_id}/summary").json()["data"]
            assert summary["booking_count"] == 3
            assert {m["currency"]: Decimal(m["amount"]) for m in summary["paid_totals"]} == {
                "USD": Decimal("0.3"),
                "CNY": Decimal("50.4321"),
            }
            for path, record in [("bookings", bookings[0]), ("expenses", expenses[0])]:
                assert (
                    client.patch(
                        f"/api/v1/{path}/{record['id']}", json={"version": 1, "note": "edited"}
                    ).status_code
                    == 200
                )
                conflict = client.patch(
                    f"/api/v1/{path}/{record['id']}", json={"version": 1, "note": "stale"}
                )
                assert conflict.status_code == 409
                assert conflict.json()["error"]["code"] == "VERSION_CONFLICT"
                assert client.delete(f"/api/v1/{path}/{record['id']}?version=1").status_code == 409
                assert client.delete(f"/api/v1/{path}/{record['id']}").status_code == 422
                assert (
                    client.patch(
                        f"/api/v1/{path}/{record['id']}", json={"version": 2, "trip_id": None}
                    ).status_code
                    == 422
                )
            assert (
                client.patch(
                    f"/api/v1/expenses/{expenses[0]['id']}",
                    json={"version": 2, "original_amount": None},
                ).status_code
                == 422
            )
            other_trip = client.post("/api/v1/trips", json={"title": "Another trip"}).json()["data"]
            assert (
                client.patch(
                    f"/api/v1/bookings/{bookings[0]['id']}",
                    json={"version": 2, "trip_id": other_trip["id"]},
                ).status_code
                == 422
            )
            exported = validate_export_document(client.get("/api/v1/me/export").json())
            assert exported.schema_version == "1.1"
            assert len(exported.data.bookings) == len(exported.data.expenses) == 3
            assert len(exported.data.places) == 1
            app.dependency_overrides[current_user] = lambda: stranger
            for path, record in [("bookings", bookings[0]), ("expenses", expenses[0])]:
                assert client.get(f"/api/v1/{path}").json()["data"] == []
                for method in ["GET", "PATCH", "DELETE"]:
                    response = client.request(
                        method,
                        f"/api/v1/{path}/{record['id']}?version=2"
                        if method == "DELETE"
                        else f"/api/v1/{path}/{record['id']}",
                        json={"version": 2} if method == "PATCH" else None,
                    )
                    assert response.status_code == 404
            assert client.get(f"/api/v1/trips/{trip_id}/summary").status_code == 404
            assert (
                client.post("/api/v1/expenses", json={**base, "original_amount": "1"}).status_code
                == 404
            )
            app.dependency_overrides[current_user] = lambda: owner
            assert client.delete(f"/api/v1/activities/{activity['id']}").status_code == 200
            assert (
                client.get(f"/api/v1/bookings/{bookings[0]['id']}").json()["data"]["activity_id"]
                is None
            )
            assert client.delete(f"/api/v1/days/{day['id']}").status_code == 200
            assert (
                client.get(f"/api/v1/expenses/{expenses[0]['id']}").json()["data"]["trip_day_id"]
                is None
            )
            assert client.delete(f"/api/v1/trips/{trip_id}").status_code == 200
            for path, record in [("bookings", bookings[0]), ("expenses", expenses[0])]:
                retained = client.get(f"/api/v1/{path}/{record['id']}").json()["data"]
                assert retained["trip_id"] is None
                assert retained["version"] > 2
                assert (
                    client.delete(
                        f"/api/v1/{path}/{record['id']}?version={retained['version']}"
                    ).status_code
                    == 200
                )
            validate_export_document(client.get("/api/v1/me/export").json())
    finally:
        app.dependency_overrides.clear()


def test_simultaneous_edits_only_one_wins() -> None:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL requires a dedicated PostGIS database")
    engine = create_engine(url)
    user_id = uuid4()
    barrier = Barrier(2)
    with Session(engine) as session:
        user = User(id=user_id, display_name="Concurrent owner")
        session.add(user)
        session.commit()
        record = FinanceService(session, user).create_expense(
            ExpenseCreate(
                original_amount=Decimal("1"),
                original_currency="CNY",
                occurred_at="2026-10-01T00:00:00Z",
            )
        )
        record_id = record.id

    def edit(note: str) -> str:
        with Session(engine) as session:
            user = session.get(User, user_id)
            assert user is not None
            service = FinanceService(session, user)
            barrier.wait(timeout=10)
            try:
                service.patch(Expense, record_id, ExpensePatch(version=1, note=note))
                return "saved"
            except DomainError as exc:
                return exc.code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(edit, ["first", "second"]))
        assert sorted(results) == ["VERSION_CONFLICT", "saved"]
        with Session(engine) as session:
            saved = session.get(Expense, record_id)
            assert saved is not None and saved.version == 2
    finally:
        with engine.begin() as connection:
            connection.execute(delete(User).where(User.id == user_id))
        engine.dispose()
