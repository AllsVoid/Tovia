from collections.abc import Sequence
from typing import Literal, Protocol, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.schemas.core import (
    ActivityRead,
    DayRead,
    PlaceRead,
    TripRead,
    UserRead,
    VisitRead,
)
from app.schemas.finance import BookingRead, ExpenseRead


class WishlistItemExport(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    user_id: UUID
    place_id: UUID
    priority: int
    note: str | None
    created_at: AwareDatetime


class ExportRecords(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: UserRead
    trips: list[TripRead]
    trip_days: list[DayRead]
    visits: list[VisitRead]
    activities: list[ActivityRead]
    places: list[PlaceRead]
    wishlist_items: list[WishlistItemExport]
    bookings: list[BookingRead] = Field(default_factory=list)
    expenses: list[ExpenseRead] = Field(default_factory=list)


class EntityWithId(Protocol):
    id: UUID


def _ids(rows: Sequence[EntityWithId]) -> set[UUID]:
    values = [row.id for row in rows]
    if len(values) != len(set(values)):
        raise ValueError("Export contains duplicate entity IDs")
    return set(values)


class DataExport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0", "1.1"]
    exported_at: AwareDatetime
    data: ExportRecords

    @model_validator(mode="after")
    def references_are_complete(self) -> Self:
        records = self.data
        trip_ids = _ids(records.trips)
        _ids(records.trip_days)
        _ids(records.visits)
        _ids(records.activities)
        place_ids = _ids(records.places)
        _ids(records.wishlist_items)
        _ids(records.bookings)
        _ids(records.expenses)
        if self.schema_version == "1.0" and (records.bookings or records.expenses):
            raise ValueError("Booking and Expense require schema_version 1.1")
        if self.schema_version == "1.1" and not {"bookings", "expenses"}.issubset(
            records.model_fields_set
        ):
            raise ValueError("Version 1.1 requires bookings and expenses")

        trip_days = {day.id: day for day in records.trip_days}
        owner_id = records.user.id

        for trip in records.trips:
            if trip.user_id != owner_id:
                raise ValueError(f"Trip {trip.id} is not owned by the exported user")

        for day in records.trip_days:
            if day.trip_id not in trip_ids:
                raise ValueError(f"TripDay {day.id} references a missing Trip")

        for visit in records.visits:
            if visit.user_id != owner_id:
                raise ValueError(f"Visit {visit.id} is not owned by the exported user")
            if visit.place_id not in place_ids:
                raise ValueError(f"Visit {visit.id} references a missing Place")
            if visit.trip_id is not None and visit.trip_id not in trip_ids:
                raise ValueError(f"Visit {visit.id} references a missing Trip")
            if visit.trip_day_id is not None:
                referenced_day = trip_days.get(visit.trip_day_id)
                if referenced_day is None:
                    raise ValueError(f"Visit {visit.id} references a missing TripDay")
                if visit.trip_id != referenced_day.trip_id:
                    raise ValueError(
                        f"Visit {visit.id} has inconsistent Trip and TripDay references"
                    )

        for activity in records.activities:
            referenced_day = trip_days.get(activity.trip_day_id)
            if activity.trip_id not in trip_ids:
                raise ValueError(f"Activity {activity.id} references a missing Trip")
            if referenced_day is None:
                raise ValueError(f"Activity {activity.id} references a missing TripDay")
            if activity.trip_id != referenced_day.trip_id:
                raise ValueError(
                    f"Activity {activity.id} has inconsistent Trip and TripDay references"
                )
            if activity.place_id is not None and activity.place_id not in place_ids:
                raise ValueError(f"Activity {activity.id} references a missing Place")

        for item in records.wishlist_items:
            if item.user_id != owner_id:
                raise ValueError(f"WishlistItem {item.id} is not owned by the exported user")
            if item.place_id not in place_ids:
                raise ValueError(f"WishlistItem {item.id} references a missing Place")

        activity_trips = {activity.id: activity.trip_id for activity in records.activities}
        financial_records: list[BookingRead | ExpenseRead] = [*records.bookings, *records.expenses]
        for entity in financial_records:
            if entity.user_id != owner_id:
                raise ValueError("Financial record is not owned by the exported user")
            if entity.trip_id is not None and entity.trip_id not in trip_ids:
                raise ValueError("Financial record references a missing Trip")
            if entity.activity_id is not None and (
                entity.activity_id not in activity_trips
                or activity_trips[entity.activity_id] != entity.trip_id
            ):
                raise ValueError("Financial record has inconsistent Activity reference")
        for booking in records.bookings:
            for place_id in (booking.origin_place_id, booking.destination_place_id):
                if place_id is not None and place_id not in place_ids:
                    raise ValueError("Booking references a missing Place")
        for expense in records.expenses:
            if expense.place_id is not None and expense.place_id not in place_ids:
                raise ValueError("Expense references a missing Place")
            if expense.trip_day_id is not None:
                expense_day = trip_days.get(expense.trip_day_id)
                if expense_day is None or expense_day.trip_id != expense.trip_id:
                    raise ValueError("Expense has inconsistent TripDay reference")

        return self


def validate_export_document(document: object) -> DataExport:
    if not isinstance(document, dict):
        raise ValueError("Export document must be a JSON object")

    payload = document
    envelope_data = document.get("data")
    if "schema_version" not in document and isinstance(envelope_data, dict):
        payload = envelope_data

    return DataExport.model_validate(payload)
