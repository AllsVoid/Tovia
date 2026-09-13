import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from geoalchemy2 import Geography, Geometry
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class TripStatus(enum.StrEnum):
    IDEA = "IDEA"
    PLANNING = "PLANNING"
    BOOKED = "BOOKED"
    TRAVELING = "TRAVELING"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class VisitSource(enum.StrEnum):
    MANUAL = "MANUAL"
    PHOTO = "PHOTO"
    BOOKING = "BOOKING"
    IMPORT = "IMPORT"
    GPS = "GPS"
    AI = "AI"


class ActivityType(enum.StrEnum):
    VISIT = "VISIT"
    TRANSPORT = "TRANSPORT"
    FOOD = "FOOD"
    HOTEL = "HOTEL"
    EVENT = "EVENT"
    FREE_TIME = "FREE_TIME"
    OTHER = "OTHER"


class ActivityStatus(enum.StrEnum):
    CANDIDATE = "CANDIDATE"
    PLANNED = "PLANNED"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"


class Entity:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class Created:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Updated:
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(Entity, Created, Updated, Base):
    __tablename__ = "users"
    display_name: Mapped[str] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", server_default="UTC")
    locale: Mapped[str] = mapped_column(String(35), default="zh-CN", server_default="zh-CN")


class Trip(Entity, Created, Updated, Base):
    __tablename__ = "trips"
    __table_args__ = (
        UniqueConstraint("id", "user_id"),
        UniqueConstraint("user_id", "slug"),
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date", name="date_range"
        ),
        CheckConstraint("visibility = 'PRIVATE'", name="private_visibility"),
        Index("ix_trips_user_start", "user_id", "start_date"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200))
    status: Mapped[TripStatus] = mapped_column(
        Enum(TripStatus, name="trip_status"), default=TripStatus.IDEA, server_default="IDEA"
    )
    start_date: Mapped[date | None]
    end_date: Mapped[date | None]
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", server_default="UTC")
    summary: Mapped[str | None] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(16), default="PRIVATE", server_default="PRIVATE")


class TripDay(Entity, Base):
    __tablename__ = "trip_days"
    __table_args__ = (UniqueConstraint("trip_id", "date"), UniqueConstraint("id", "trip_id"))
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    date: Mapped[date]
    title: Mapped[str | None] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Place(Entity, Created, Base):
    __tablename__ = "places"
    canonical_name: Mapped[str] = mapped_column(String(300))
    local_name: Mapped[str | None] = mapped_column(String(300))
    country_code: Mapped[str | None] = mapped_column(String(2))
    admin1: Mapped[str | None] = mapped_column(String(200))
    admin2: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(64))
    location: Mapped[WKBElement] = mapped_column(Geography("POINT", srid=4326, spatial_index=True))
    geometry: Mapped[WKBElement | None] = mapped_column(
        Geometry("GEOMETRY", srid=4326, spatial_index=False)
    )
    osm_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    google_place_id: Mapped[str | None] = mapped_column(String(300), unique=True)
    amap_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'::jsonb")
    )


class Visit(Entity, Created, Base):
    __tablename__ = "visits"
    __table_args__ = (
        ForeignKeyConstraint(
            ["trip_id", "user_id"],
            ["trips.id", "trips.user_id"],
            ondelete="RESTRICT",
            name="fk_visits_trip_owner",
        ),
        ForeignKeyConstraint(
            ["trip_day_id", "trip_id"],
            ["trip_days.id", "trip_days.trip_id"],
            ondelete="RESTRICT",
            name="fk_visits_day_trip",
        ),
        CheckConstraint("trip_day_id IS NULL OR trip_id IS NOT NULL", name="day_requires_trip"),
        CheckConstraint("ended_at IS NULL OR ended_at >= visited_at", name="time_range"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="confidence_range"
        ),
        Index("ix_visits_user_time", "user_id", "visited_at"),
        Index("ix_visits_place", "place_id"),
        Index("ix_visits_trip", "trip_id"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    trip_id: Mapped[uuid.UUID | None]
    trip_day_id: Mapped[uuid.UUID | None]
    place_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("places.id", ondelete="RESTRICT"))
    visited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[VisitSource] = mapped_column(
        Enum(VisitSource, name="visit_source"), default=VisitSource.MANUAL, server_default="MANUAL"
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    note: Mapped[str | None] = mapped_column(Text)


class Activity(Entity, Created, Updated, Base):
    __tablename__ = "activities"
    __table_args__ = (
        ForeignKeyConstraint(
            ["trip_day_id", "trip_id"],
            ["trip_days.id", "trip_days.trip_id"],
            ondelete="CASCADE",
            name="fk_activities_day_trip",
        ),
        CheckConstraint(
            "end_at IS NULL OR start_at IS NULL OR end_at >= start_at", name="time_range"
        ),
        Index("ix_activities_trip", "trip_id", "sort_order"),
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    trip_day_id: Mapped[uuid.UUID]
    place_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("places.id", ondelete="RESTRICT"))
    type: Mapped[ActivityType] = mapped_column(Enum(ActivityType, name="activity_type"))
    title: Mapped[str] = mapped_column(String(200))
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[ActivityStatus] = mapped_column(
        Enum(ActivityStatus, name="activity_status"),
        default=ActivityStatus.PLANNED,
        server_default="PLANNED",
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    note: Mapped[str | None] = mapped_column(Text)
    source: Mapped[VisitSource] = mapped_column(
        Enum(VisitSource, name="visit_source"), default=VisitSource.MANUAL, server_default="MANUAL"
    )


class WishlistItem(Entity, Created, Base):
    __tablename__ = "wishlist_items"
    __table_args__ = (UniqueConstraint("user_id", "place_id"),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    place_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("places.id", ondelete="RESTRICT"))
    priority: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    note: Mapped[str | None] = mapped_column(Text)
