from datetime import date, datetime
from typing import Any
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import Date, Select, and_, case, cast, func, or_, select, text
from sqlalchemy.orm import Session

from app.models import Activity, Place, Trip, TripDay, Visit, WishlistItem
from app.schemas.explore import PlaceStatus, Scope

DOMESTIC_CODES = ("CN", "HK", "MO", "TW")


def map_query(
    user_id: UUID, now: datetime, scope: Scope, status: PlaceStatus | None
) -> Select[Any]:
    visits = (
        select(
            Visit.place_id,
            func.count().filter(Visit.visited_at <= now).label("visit_count"),
            func.count().filter(Visit.visited_at > now).label("upcoming_count"),
            func.max(Visit.visited_at).filter(Visit.visited_at <= now).label("last_visited_at"),
            func.min(Visit.visited_at).filter(Visit.visited_at > now).label("next_visit_at"),
        )
        .where(Visit.user_id == user_id)
        .group_by(Visit.place_id)
        .subquery()
    )
    point = cast(Place.location, Geometry("POINT", srid=4326))
    past = func.coalesce(visits.c.visit_count, 0)
    future = func.coalesce(visits.c.upcoming_count, 0)
    wished = WishlistItem.id.is_not(None)
    query = (
        select(
            Place.id,
            Place.canonical_name.label("name"),
            Place.country_code,
            Place.admin1,
            Place.city,
            Place.timezone,
            func.ST_Y(point).label("latitude"),
            func.ST_X(point).label("longitude"),
            past.label("visit_count"),
            future.label("upcoming_count"),
            wished.label("wishlist"),
            visits.c.last_visited_at,
            visits.c.next_visit_at,
        )
        .outerjoin(visits, visits.c.place_id == Place.id)
        .outerjoin(
            WishlistItem, and_(WishlistItem.place_id == Place.id, WishlistItem.user_id == user_id)
        )
        .where(or_(visits.c.place_id.is_not(None), wished))
    )
    if scope == "domestic":
        query = query.where(Place.country_code.in_(DOMESTIC_CODES))
    elif scope == "international":
        query = query.where(Place.country_code.not_in(DOMESTIC_CODES))
    if status:
        query = query.where(
            {"visited": past > 0, "upcoming": future > 0, "wishlist": wished}[status]
        )
    return query


def visit_local_dates() -> tuple[Any, Any]:
    start = cast(func.timezone(Place.timezone, Visit.visited_at), Date)
    # A stay ending exactly at midnight does not occupy the following day.
    end_instant = case(
        (Visit.ended_at > Visit.visited_at, Visit.ended_at - text("interval '1 microsecond'")),
        else_=Visit.visited_at,
    )
    return start, cast(func.timezone(Place.timezone, end_instant), Date)


class CalendarRepository:
    def __init__(self, session: Session, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id

    def records(
        self, first: date, last: date
    ) -> tuple[list[Trip], list[Any], list[Any], list[Any]]:
        start, end = visit_local_dates()
        visits = list(
            self.session.execute(
                select(
                    Visit,
                    Place.canonical_name,
                    Place.timezone,
                    start.label("local_start"),
                    end.label("local_end"),
                )
                .join(Place, Place.id == Visit.place_id)
                .where(
                    Visit.user_id == self.user_id,
                    start <= last,
                    end >= first,
                )
                .order_by(Visit.visited_at, Visit.id)
            ).all()
        )
        activities = list(
            self.session.execute(
                select(
                    Activity,
                    TripDay.date,
                    Place.canonical_name,
                    Trip.timezone,
                )
                .join(Trip, Trip.id == Activity.trip_id)
                .join(TripDay, TripDay.id == Activity.trip_day_id)
                .outerjoin(Place, Place.id == Activity.place_id)
                .where(
                    Trip.user_id == self.user_id,
                    TripDay.date >= first,
                    TripDay.date <= last,
                )
                .order_by(TripDay.date, Activity.sort_order, Activity.id)
            ).all()
        )
        days = list(
            self.session.execute(
                select(TripDay.trip_id, TripDay.date)
                .join(Trip)
                .where(
                    Trip.user_id == self.user_id,
                    TripDay.date >= first,
                    TripDay.date <= last,
                )
            ).all()
        )
        # Dates remain useful even when the container is archived, or has no range.
        related_ids = {row[0].trip_id for row in visits if row[0].trip_id}
        related_ids.update(row[0].trip_id for row in activities)
        related_ids.update(row[0] for row in days)
        trips = list(
            self.session.scalars(
                select(Trip)
                .where(
                    Trip.user_id == self.user_id,
                    or_(
                        and_(
                            func.coalesce(Trip.start_date, Trip.end_date) <= last,
                            func.coalesce(Trip.end_date, Trip.start_date) >= first,
                        ),
                        Trip.id.in_(related_ids),
                    ),
                )
                .order_by(Trip.start_date, Trip.id)
            )
        )
        return trips, visits, activities, days
