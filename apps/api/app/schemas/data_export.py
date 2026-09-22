from collections.abc import Sequence
from typing import Literal, Protocol, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator

from app.schemas.core import (
    ActivityRead,
    DayRead,
    PlaceRead,
    TripRead,
    UserRead,
    VisitRead,
)


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


class EntityWithId(Protocol):
    id: UUID


def _ids(rows: Sequence[EntityWithId]) -> set[UUID]:
    values = [row.id for row in rows]
    if len(values) != len(set(values)):
        raise ValueError("Export contains duplicate entity IDs")
    return set(values)


class DataExport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
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

        return self


def validate_export_document(document: object) -> DataExport:
    if not isinstance(document, dict):
        raise ValueError("Export document must be a JSON object")

    payload = document
    envelope_data = document.get("data")
    if "schema_version" not in document and isinstance(envelope_data, dict):
        payload = envelope_data

    return DataExport.model_validate(payload)
