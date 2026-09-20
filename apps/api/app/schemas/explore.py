from datetime import date as Date
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.core import ActivityRead, Input, Output, VisitRead

Scope = Literal["domestic", "international", "all"]
PlaceStatus = Literal["visited", "upcoming", "wishlist"]


class WishlistCreate(Input):
    place_id: UUID
    note: str | None = Field(default=None, max_length=2000)


class WishlistRead(Output):
    id: UUID
    place_id: UUID
    note: str | None
    created_at: datetime


class MapPlace(BaseModel):
    id: UUID
    name: str
    country_code: str | None
    admin1: str | None
    city: str | None
    timezone: str
    latitude: float
    longitude: float
    region_id: str | None = None
    visit_count: int
    upcoming_count: int
    wishlist: bool
    last_visited_at: datetime | None
    next_visit_at: datetime | None


class MapPage(BaseModel):
    places: list[MapPlace]
    total: int
    limit: int
    offset: int


class MapSummary(BaseModel):
    places_count: int
    visited_places: int
    upcoming_places: int
    wishlist_places: int
    visit_count: int
    countries_count: int
    unknown_country_places: int


class MapDetail(BaseModel):
    place: MapPlace
    visits: list[VisitRead]
    visits_total: int
    wishlist_note: str | None


class CalendarTrip(Output):
    id: UUID
    title: str
    status: str
    start_date: Date | None
    end_date: Date | None
    timezone: str


class CalendarCell(BaseModel):
    date: Date
    trip_ids: list[UUID]
    places_count: int
    visits_count: int
    activities_count: int
    has_memory: bool


class CalendarMonth(BaseModel):
    year: int
    month: int
    trips: list[CalendarTrip]
    days: list[CalendarCell]


class CalendarVisit(VisitRead):
    place_name: str
    timezone: str


class CalendarActivity(ActivityRead):
    place_name: str | None
    timezone: str


class CalendarDay(BaseModel):
    date: Date
    trips: list[CalendarTrip]
    visits: list[CalendarVisit]
    activities: list[CalendarActivity]
