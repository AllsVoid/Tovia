from datetime import UTC, date, datetime
from typing import Any, TypeVar
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from pydantic import BaseModel
from sqlalchemy import cast, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.audit import audit_data_event
from app.config import get_settings
from app.errors import DomainError
from app.models import Activity, Base, Place, Trip, TripDay, User, UserIdentity, Visit, WishlistItem
from app.providers.auth import AuthPrincipal
from app.providers.logto_management import delete_logto_user
from app.repositories.core import Repository
from app.schemas.core import (
    ActivityCreate,
    ActivityRead,
    DayCreate,
    DayRead,
    PlaceCreate,
    PlaceRead,
    TripCreate,
    TripRead,
    UserRead,
    UserUpdate,
    VisitCreate,
    VisitRead,
)
from app.schemas.data_export import DataExport, ExportRecords, WishlistItemExport

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
        audit_data_event(
            "data.entity_deletion",
            "succeeded",
            entity="trip",
            entity_id=str(trip_id),
            user_id=str(self.user.id),
        )

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
        audit_data_event(
            "data.entity_deletion",
            "succeeded",
            entity="trip_day",
            entity_id=str(day_id),
            user_id=str(self.user.id),
        )

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

    def export_data(self) -> DataExport:
        trips = self.session.scalars(
            select(Trip).where(Trip.user_id == self.user.id).order_by(Trip.created_at, Trip.id)
        ).all()
        trip_ids = [trip.id for trip in trips]
        days = (
            self.session.scalars(
                select(TripDay)
                .where(TripDay.trip_id.in_(trip_ids))
                .order_by(TripDay.date, TripDay.id)
            ).all()
            if trip_ids
            else []
        )
        visits = self.session.scalars(
            select(Visit).where(Visit.user_id == self.user.id).order_by(Visit.visited_at, Visit.id)
        ).all()
        activities = (
            self.session.scalars(
                select(Activity)
                .where(Activity.trip_id.in_(trip_ids))
                .order_by(Activity.trip_id, Activity.trip_day_id, Activity.sort_order, Activity.id)
            ).all()
            if trip_ids
            else []
        )
        wishlist = self.session.scalars(
            select(WishlistItem)
            .where(WishlistItem.user_id == self.user.id)
            .order_by(WishlistItem.created_at, WishlistItem.id)
        ).all()
        place_ids = {visit.place_id for visit in visits}
        place_ids.update(
            activity.place_id for activity in activities if activity.place_id is not None
        )
        place_ids.update(item.place_id for item in wishlist)
        places = (
            self.session.scalars(
                select(Place).where(Place.id.in_(place_ids)).order_by(Place.id)
            ).all()
            if place_ids
            else []
        )
        exported = DataExport(
            schema_version="1.0",
            exported_at=datetime.now(UTC),
            data=ExportRecords(
                user=UserRead.model_validate(self.user),
                trips=[TripRead.model_validate(trip) for trip in trips],
                trip_days=[DayRead.model_validate(day) for day in days],
                visits=[VisitRead.model_validate(visit) for visit in visits],
                activities=[ActivityRead.model_validate(activity) for activity in activities],
                places=[self.place_read(place) for place in places],
                wishlist_items=[WishlistItemExport.model_validate(item) for item in wishlist],
            ),
        )
        audit_data_event(
            "data.export",
            "succeeded",
            user_id=str(self.user.id),
            trips=len(trips),
            trip_days=len(days),
            visits=len(visits),
            activities=len(activities),
            places=len(places),
            wishlist_items=len(wishlist),
        )
        return exported

    def delete_visit(self, visit_id: UUID) -> None:
        visit = self.visit(visit_id)
        self.repo.delete(visit)
        audit_data_event(
            "data.entity_deletion",
            "succeeded",
            entity="visit",
            entity_id=str(visit_id),
            user_id=str(self.user.id),
        )

    def delete_activity(self, activity_id: UUID) -> None:
        activity = self.activity(activity_id)
        self.repo.delete(activity)
        audit_data_event(
            "data.entity_deletion",
            "succeeded",
            entity="activity",
            entity_id=str(activity_id),
            user_id=str(self.user.id),
        )

    def delete_account(self, principal: AuthPrincipal) -> None:
        if principal.provider != "logto" or principal.user_id != self.user.id:
            raise DomainError(
                "ACCOUNT_DELETION_REQUIRES_OIDC",
                "Sign in with your Logto account before deleting this account",
                403,
            )
        identity = self.session.scalar(
            select(UserIdentity).where(
                UserIdentity.user_id == self.user.id,
                UserIdentity.provider == principal.provider,
                UserIdentity.provider_subject == principal.subject,
            )
        )
        if identity is None:
            raise DomainError("AUTH_REQUIRED", "Identity is not linked", 401)

        user_id = str(self.user.id)
        provider_name = identity.provider
        provider_subject = identity.provider_subject
        settings = get_settings()
        audit_data_event(
            "account.deletion",
            "requested",
            user_id=user_id,
            provider=provider_name,
        )
        delete_logto_user(settings, provider_subject)
        try:
            # Visits are independent facts, so detach the container references
            # before user/trip cascades while deleting the account's own rows.
            self.session.execute(
                update(Visit)
                .where(Visit.user_id == self.user.id)
                .values(trip_id=None, trip_day_id=None)
            )
            self.session.delete(self.user)
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            audit_data_event(
                "account.deletion",
                "local_failed_after_provider_deletion",
                user_id=user_id,
                provider=provider_name,
            )
            raise DomainError(
                "ACCOUNT_DELETION_INCOMPLETE",
                "Identity was removed but local data cleanup failed; contact support",
                503,
            ) from exc
        audit_data_event(
            "account.deletion",
            "succeeded",
            user_id=user_id,
            provider=provider_name,
        )

    def apply[M: Base](self, entity: M, values: dict[str, Any]) -> M:
        for name, value in values.items():
            setattr(entity, name, value)
        return self.repo.save(entity)
