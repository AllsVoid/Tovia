from datetime import date
from typing import Any, TypeVar
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from pydantic import BaseModel
from sqlalchemy import cast, func, select, update
from sqlalchemy.orm import Session

from app.errors import DomainError
from app.models import Activity, Base, Place, Trip, TripDay, User, Visit
from app.repositories.core import Repository
from app.schemas.core import (
    ActivityCreate,
    DayCreate,
    PlaceCreate,
    PlaceRead,
    TripCreate,
    UserUpdate,
    VisitCreate,
)

S = TypeVar("S", bound=BaseModel)


def merge_payload[S: BaseModel](schema: type[S], entity: Base, patch: BaseModel) -> S:
    values = {name: getattr(entity, name) for name in schema.model_fields}
    values.update(patch.model_dump(exclude_unset=True))
    return schema.model_validate(values)


class TravelService:
    def __init__(self, session: Session, user: User) -> None:
        self.session = session
        self.repo = Repository(session)
        self.user = user

    def trip(self, trip_id: UUID) -> Trip:
        trip = self.repo.get(Trip, trip_id)
        if trip is None or trip.user_id != self.user.id:
            raise DomainError("TRIP_NOT_FOUND", "Trip not found", 404)
        return trip

    def day(self, day_id: UUID, trip_id: UUID | None = None) -> TripDay:
        day = self.repo.get(TripDay, day_id)
        if day is None:
            raise DomainError("DAY_NOT_FOUND", "Day not found", 404)
        self.trip(day.trip_id)
        if trip_id is not None and day.trip_id != trip_id:
            raise DomainError("DAY_TRIP_MISMATCH", "Day does not belong to this trip", 422)
        return day

    def place(self, place_id: UUID) -> Place:
        place = self.repo.get(Place, place_id)
        if place is None:
            raise DomainError("PLACE_NOT_FOUND", "Place not found", 404)
        return place

    def visit(self, visit_id: UUID) -> Visit:
        visit = self.repo.get(Visit, visit_id)
        if visit is None or visit.user_id != self.user.id:
            raise DomainError("VISIT_NOT_FOUND", "Visit not found", 404)
        return visit

    def activity(self, activity_id: UUID) -> Activity:
        activity = self.repo.get(Activity, activity_id)
        if activity is None:
            raise DomainError("ACTIVITY_NOT_FOUND", "Activity not found", 404)
        self.trip(activity.trip_id)
        return activity

    def create_trip(self, payload: TripCreate) -> Trip:
        values = payload.model_dump()
        values["slug"] = payload.slug or f"trip-{uuid4().hex}"
        return self.repo.save(Trip(user_id=self.user.id, **values))

    def patch_trip(self, trip_id: UUID, patch: BaseModel) -> Trip:
        trip = self.trip(trip_id)
        payload = merge_payload(TripCreate, trip, patch)
        if payload.slug is None:
            raise DomainError("INVALID_SLUG", "An existing slug cannot be null", 422)
        for day in self.session.scalars(select(TripDay).where(TripDay.trip_id == trip_id)):
            self.validate_day_date(payload, day.date)
        return self.apply(trip, payload.model_dump())

    def delete_trip(self, trip_id: UUID) -> None:
        trip = self.trip(trip_id)
        # Visits are independent travel facts and survive container deletion.
        self.session.execute(
            update(Visit).where(Visit.trip_id == trip_id).values(trip_id=None, trip_day_id=None)
        )
        self.repo.delete(trip)

    @staticmethod
    def validate_day_date(trip: Trip | TripCreate, day_date: date) -> None:
        if (trip.start_date and day_date < trip.start_date) or (
            trip.end_date and day_date > trip.end_date
        ):
            raise DomainError("DAY_OUTSIDE_TRIP", "Day must lie within the trip date range", 422)

    def create_day(self, trip_id: UUID, payload: DayCreate) -> TripDay:
        self.validate_day_date(self.trip(trip_id), payload.date)
        return self.repo.save(TripDay(trip_id=trip_id, **payload.model_dump()))

    def patch_day(self, day_id: UUID, patch: BaseModel) -> TripDay:
        day = self.day(day_id)
        payload = merge_payload(DayCreate, day, patch)
        self.validate_day_date(self.trip(day.trip_id), payload.date)
        return self.apply(day, payload.model_dump())

    def delete_day(self, day_id: UUID) -> None:
        day = self.day(day_id)
        self.session.execute(
            update(Visit).where(Visit.trip_day_id == day_id).values(trip_day_id=None)
        )
        self.repo.delete(day)

    def create_place(self, payload: PlaceCreate) -> Place:
        values = payload.model_dump(exclude={"latitude", "longitude", "metadata"})
        return self.repo.save(
            Place(
                **values,
                metadata_=payload.metadata,
                location=WKTElement(f"POINT({payload.longitude} {payload.latitude})", srid=4326),
            )
        )

    def place_read(self, place: Place) -> PlaceRead:
        point = cast(Place.location, Geometry("POINT", srid=4326))
        row = self.session.execute(
            select(func.ST_Y(point), func.ST_X(point)).where(Place.id == place.id)
        ).one()
        values = {
            name: getattr(place, name)
            for name in PlaceCreate.model_fields
            if name not in {"latitude", "longitude", "metadata"}
        }
        return PlaceRead(
            **values,
            latitude=row[0],
            longitude=row[1],
            metadata=place.metadata_,
            id=place.id,
            created_at=place.created_at,
        )

    def validate_visit(self, payload: VisitCreate) -> None:
        self.place(payload.place_id)
        if payload.trip_id:
            self.trip(payload.trip_id)
        if payload.trip_day_id:
            self.day(payload.trip_day_id, payload.trip_id)

    def create_visit(self, payload: VisitCreate) -> Visit:
        self.validate_visit(payload)
        return self.repo.save(Visit(user_id=self.user.id, **payload.model_dump()))

    def patch_visit(self, visit_id: UUID, patch: BaseModel) -> Visit:
        visit = self.visit(visit_id)
        payload = merge_payload(VisitCreate, visit, patch)
        self.validate_visit(payload)
        return self.apply(visit, payload.model_dump())

    def create_activity(self, trip_id: UUID, payload: ActivityCreate) -> Activity:
        self.trip(trip_id)
        self.day(payload.trip_day_id, trip_id)
        if payload.place_id:
            self.place(payload.place_id)
        return self.repo.save(Activity(trip_id=trip_id, **payload.model_dump()))

    def patch_activity(self, activity_id: UUID, patch: BaseModel) -> Activity:
        activity = self.activity(activity_id)
        payload = merge_payload(ActivityCreate, activity, patch)
        self.day(payload.trip_day_id, activity.trip_id)
        if payload.place_id:
            self.place(payload.place_id)
        return self.apply(activity, payload.model_dump())

    def patch_user(self, patch: BaseModel) -> User:
        payload = merge_payload(UserUpdate, self.user, patch)
        return self.apply(self.user, payload.model_dump())

    def apply[M: Base](self, entity: M, values: dict[str, Any]) -> M:
        for name, value in values.items():
            setattr(entity, name, value)
        return self.repo.save(entity)
