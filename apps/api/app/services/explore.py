from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.errors import DomainError
from app.models import Place, Trip, User, Visit, WishlistItem
from app.repositories.explore import CalendarRepository, map_query
from app.schemas.core import VisitRead
from app.schemas.explore import (
    CalendarActivity,
    CalendarCell,
    CalendarDay,
    CalendarMonth,
    CalendarTrip,
    CalendarVisit,
    MapDetail,
    MapPage,
    MapPlace,
    MapSummary,
    PlaceStatus,
    Scope,
    WishlistCreate,
    WishlistRead,
)
from app.services.core import TravelService


class ExploreService:
    def __init__(self, session: Session, user: User) -> None:
        self.session = session
        self.user = user

    def map_places(
        self, scope: Scope, status: PlaceStatus | None, limit: int, offset: int
    ) -> MapPage:
        query = map_query(self.user.id, datetime.now(UTC), scope, status)
        total = self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = self.session.execute(
            query.order_by("name", "id").limit(limit).offset(offset)
        ).mappings()
        return MapPage(
            places=[MapPlace.model_validate(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    def map_summary(self, scope: Scope) -> MapSummary:
        q = map_query(self.user.id, datetime.now(UTC), scope, None).subquery()
        row = (
            self.session.execute(
                select(
                    func.count().label("places_count"),
                    func.count().filter(q.c.visit_count > 0).label("visited_places"),
                    func.count().filter(q.c.upcoming_count > 0).label("upcoming_places"),
                    func.count().filter(q.c.wishlist).label("wishlist_places"),
                    func.coalesce(func.sum(q.c.visit_count), 0).label("visit_count"),
                    func.count(func.distinct(q.c.country_code)).label("countries_count"),
                    func.count().filter(q.c.country_code.is_(None)).label("unknown_country_places"),
                )
            )
            .mappings()
            .one()
        )
        return MapSummary.model_validate(row)

    def map_detail(self, place_id: UUID) -> MapDetail:
        match = (
            self.session.execute(
                map_query(self.user.id, datetime.now(UTC), "all", None).where(Place.id == place_id)
            )
            .mappings()
            .one_or_none()
        )
        if match is None:
            raise DomainError("MAP_PLACE_NOT_FOUND", "Place not found in your world", 404)
        visits = select(Visit).where(Visit.user_id == self.user.id, Visit.place_id == place_id)
        total = self.session.scalar(select(func.count()).select_from(visits.subquery())) or 0
        records = self.session.scalars(visits.order_by(Visit.visited_at.desc(), Visit.id).limit(20))
        note = self.session.scalar(
            select(WishlistItem.note).where(
                WishlistItem.user_id == self.user.id, WishlistItem.place_id == place_id
            )
        )
        return MapDetail(
            place=MapPlace.model_validate(match),
            visits=[VisitRead.model_validate(r) for r in records],
            visits_total=total,
            wishlist_note=note,
        )

    def add_wishlist(self, payload: WishlistCreate) -> WishlistRead:
        TravelService(self.session, self.user).place(payload.place_id)
        self.session.execute(
            insert(WishlistItem)
            .values(user_id=self.user.id, **payload.model_dump())
            .on_conflict_do_nothing(index_elements=["user_id", "place_id"])
        )
        self.session.commit()
        row = self.session.scalar(
            select(WishlistItem).where(
                WishlistItem.user_id == self.user.id, WishlistItem.place_id == payload.place_id
            )
        )
        return WishlistRead.model_validate(row)

    def remove_wishlist(self, place_id: UUID) -> None:
        self.session.execute(
            delete(WishlistItem).where(
                WishlistItem.user_id == self.user.id, WishlistItem.place_id == place_id
            )
        )
        self.session.commit()

    def calendar_month(self, year: int, month: int) -> CalendarMonth:
        first, last = date(year, month, 1), date(year, month, monthrange(year, month)[1])
        trips, visits, activities, trip_days = CalendarRepository(
            self.session, self.user.id
        ).records(first, last)
        cells = []
        now = datetime.now(UTC)
        for n in range(last.day):
            current = first + timedelta(days=n)
            ids = {t.id for t in trips if trip_contains(t, current)}
            ids.update(row[0] for row in trip_days if row[1] == current)
            present = [r for r in visits if r[3] <= current <= r[4]]
            planned = [r for r in activities if r[1] == current]
            ids.update(r[0].trip_id for r in present if r[0].trip_id)
            ids.update(r[0].trip_id for r in planned)
            places = {r[0].place_id for r in present}
            places.update(r[0].place_id for r in planned if r[0].place_id)
            cells.append(
                CalendarCell(
                    date=current,
                    trip_ids=sorted(ids, key=str),
                    places_count=len(places),
                    visits_count=len(present),
                    activities_count=len(planned),
                    has_memory=any(
                        r[0].visited_at <= now and current <= now.astimezone(ZoneInfo(r[2])).date()
                        for r in present
                    ),
                )
            )
        return CalendarMonth(
            year=year,
            month=month,
            trips=[CalendarTrip.model_validate(t) for t in trips],
            days=cells,
        )

    def calendar_day(self, day: date) -> CalendarDay:
        trips, visits, activities, _ = CalendarRepository(self.session, self.user.id).records(
            day, day
        )
        return CalendarDay(
            date=day,
            trips=[CalendarTrip.model_validate(t) for t in trips],
            visits=[
                CalendarVisit(
                    **VisitRead.model_validate(r[0]).model_dump(), place_name=r[1], timezone=r[2]
                )
                for r in visits
            ],
            activities=[
                CalendarActivity.model_validate(
                    {
                        **{
                            name: getattr(r[0], name)
                            for name in CalendarActivity.model_fields
                            if name not in {"place_name", "timezone"}
                        },
                        "place_name": r[2],
                        "timezone": r[3],
                    }
                )
                for r in activities
            ],
        )


def trip_contains(trip: Trip, day: date) -> bool:
    first, last = trip.start_date or trip.end_date, trip.end_date or trip.start_date
    return first is not None and last is not None and first <= day <= last
