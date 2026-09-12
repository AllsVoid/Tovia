from datetime import date as Date
from datetime import datetime as Datetime
from decimal import Decimal
from typing import Annotated, Any, Literal, Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.models.core import ActivityStatus, ActivityType, TripStatus, VisitSource


def valid_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("Use an IANA timezone name") from exc
    return value


Timezone = Annotated[str, AfterValidator(valid_timezone)]
Title = Annotated[str, Field(min_length=1, max_length=200)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, from_attributes=True)


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(Input):
    display_name: Annotated[str, Field(min_length=1, max_length=100)]
    timezone: Timezone = "UTC"
    locale: Annotated[str, Field(min_length=2, max_length=35)] = "zh-CN"


class UserRead(Output):
    id: UUID
    display_name: str
    avatar_url: str | None
    timezone: str
    locale: str
    created_at: Datetime
    updated_at: Datetime


class TripCreate(Input):
    title: Title
    slug: (
        Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
        | None
    ) = None
    status: TripStatus = TripStatus.IDEA
    start_date: Date | None = None
    end_date: Date | None = None
    timezone: Timezone = "UTC"
    summary: str | None = None
    visibility: Literal["PRIVATE"] = "PRIVATE"

    @model_validator(mode="after")
    def date_range(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class TripRead(Output):
    id: UUID
    user_id: UUID
    title: str
    slug: str
    status: TripStatus
    start_date: Date | None
    end_date: Date | None
    timezone: str
    summary: str | None
    visibility: str
    created_at: Datetime
    updated_at: Datetime


class DayCreate(Input):
    date: Date
    title: Title | None = None
    note: str | None = None
    sort_order: int = 0


class DayRead(Output):
    id: UUID
    trip_id: UUID
    date: Date
    title: str | None
    note: str | None
    sort_order: int


class PlaceCreate(Input):
    canonical_name: Annotated[str, Field(min_length=1, max_length=300)]
    local_name: Annotated[str, Field(max_length=300)] | None = None
    country_code: Annotated[str, Field(pattern=r"^[A-Z]{2}$")] | None = None
    admin1: Annotated[str, Field(max_length=200)] | None = None
    admin2: Annotated[str, Field(max_length=200)] | None = None
    city: Annotated[str, Field(max_length=200)] | None = None
    timezone: Timezone
    latitude: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
    longitude: Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]
    osm_id: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    google_place_id: Annotated[str, Field(min_length=1, max_length=300)] | None = None
    amap_id: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlaceRead(PlaceCreate):
    id: UUID
    created_at: Datetime


class VisitCreate(Input):
    trip_id: UUID | None = None
    trip_day_id: UUID | None = None
    place_id: UUID
    visited_at: AwareDatetime
    ended_at: AwareDatetime | None = None
    source: Literal[VisitSource.MANUAL] = VisitSource.MANUAL
    note: str | None = None

    @model_validator(mode="after")
    def visit_range(self) -> Self:
        if self.ended_at and self.ended_at < self.visited_at:
            raise ValueError("ended_at must be on or after visited_at")
        if self.trip_day_id and not self.trip_id:
            raise ValueError("trip_day_id requires trip_id")
        return self


class VisitRead(Output):
    id: UUID
    user_id: UUID
    trip_id: UUID | None
    trip_day_id: UUID | None
    place_id: UUID
    visited_at: Datetime
    ended_at: Datetime | None
    source: VisitSource
    confidence: Decimal | None
    note: str | None
    created_at: Datetime


class ActivityCreate(Input):
    trip_day_id: UUID
    place_id: UUID | None = None
    type: ActivityType = ActivityType.VISIT
    title: Title
    start_at: AwareDatetime | None = None
    end_at: AwareDatetime | None = None
    status: ActivityStatus = ActivityStatus.PLANNED
    sort_order: int = 0
    note: str | None = None
    source: Literal[VisitSource.MANUAL] = VisitSource.MANUAL

    @model_validator(mode="after")
    def activity_range(self) -> Self:
        if self.start_at and self.end_at and self.end_at < self.start_at:
            raise ValueError("end_at must be on or after start_at")
        return self


class ActivityRead(Output):
    id: UUID
    trip_id: UUID
    trip_day_id: UUID
    place_id: UUID | None
    type: ActivityType
    title: str
    start_at: Datetime | None
    end_at: Datetime | None
    status: ActivityStatus
    sort_order: int
    note: str | None
    source: VisitSource
    created_at: Datetime
    updated_at: Datetime


# PATCH fields default to None only to permit omission. The service merges provided
# fields into the existing object and revalidates the complete create schema.
class TripPatch(Input):
    title: Title | None = None
    slug: str | None = None
    status: TripStatus | None = None
    start_date: Date | None = None
    end_date: Date | None = None
    timezone: Timezone | None = None
    summary: str | None = None
    visibility: Literal["PRIVATE"] | None = None


class DayPatch(Input):
    date: Date | None = None
    title: Title | None = None
    note: str | None = None
    sort_order: int | None = None


class VisitPatch(Input):
    trip_id: UUID | None = None
    trip_day_id: UUID | None = None
    place_id: UUID | None = None
    visited_at: AwareDatetime | None = None
    ended_at: AwareDatetime | None = None
    note: str | None = None


class ActivityPatch(Input):
    trip_day_id: UUID | None = None
    place_id: UUID | None = None
    type: ActivityType | None = None
    title: Title | None = None
    start_at: AwareDatetime | None = None
    end_at: AwareDatetime | None = None
    status: ActivityStatus | None = None
    sort_order: int | None = None
    note: str | None = None


class UserPatch(Input):
    display_name: str | None = None
    timezone: Timezone | None = None
    locale: str | None = None
