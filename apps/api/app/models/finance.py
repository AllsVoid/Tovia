import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core import Base, Created, Entity, Updated


class BookingType(enum.StrEnum):
    FLIGHT = "FLIGHT"
    TRAIN = "TRAIN"
    BUS = "BUS"
    HOTEL = "HOTEL"
    TICKET = "TICKET"
    RESTAURANT = "RESTAURANT"
    OTHER = "OTHER"


class BookingStatus(enum.StrEnum):
    PLANNED = "PLANNED"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Booking(Entity, Created, Updated, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["activity_id", "trip_id"],
            ["activities.id", "activities.trip_id"],
            ondelete="RESTRICT",
            name="fk_bookings_activity_trip",
        ),
        ForeignKeyConstraint(
            ["trip_id", "user_id"],
            ["trips.id", "trips.user_id"],
            ondelete="RESTRICT",
            name="fk_bookings_trip_owner",
        ),
        CheckConstraint(
            "type IN ('FLIGHT','TRAIN','BUS','HOTEL','TICKET','RESTAURANT','OTHER')", name="type"
        ),
        CheckConstraint("status IN ('PLANNED','CONFIRMED','COMPLETED','CANCELLED')", name="status"),
        CheckConstraint("end_at IS NULL OR end_at >= start_at", name="time_range"),
        CheckConstraint("(amount IS NULL) = (currency IS NULL)", name="money_pair"),
        CheckConstraint("amount IS NULL OR amount >= 0", name="amount"),
        CheckConstraint("version > 0", name="version"),
        CheckConstraint(
            "activity_id IS NULL OR trip_id IS NOT NULL", name="activity_requires_trip"
        ),
        Index("ix_bookings_user_time", "user_id", "start_at"),
        Index("ix_bookings_trip", "trip_id"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    trip_id: Mapped[uuid.UUID | None]
    activity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("activities.id", ondelete="SET NULL")
    )
    type: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="CONFIRMED", server_default="CONFIRMED")
    title: Mapped[str] = mapped_column(String(200))
    provider_name: Mapped[str | None] = mapped_column(String(200))
    reference_no: Mapped[str | None] = mapped_column(String(200))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(64))
    end_timezone: Mapped[str] = mapped_column(String(64))
    origin_place_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("places.id", ondelete="RESTRICT")
    )
    destination_place_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("places.id", ondelete="RESTRICT")
    )
    address: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str | None] = mapped_column(String(3))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    note: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class Expense(Entity, Created, Updated, Base):
    __tablename__ = "expenses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["activity_id", "trip_id"],
            ["activities.id", "activities.trip_id"],
            ondelete="RESTRICT",
            name="fk_expenses_activity_trip",
        ),
        ForeignKeyConstraint(
            ["trip_day_id", "trip_id"],
            ["trip_days.id", "trip_days.trip_id"],
            ondelete="RESTRICT",
            name="fk_expenses_day_trip",
        ),
        ForeignKeyConstraint(
            ["trip_id", "user_id"],
            ["trips.id", "trips.user_id"],
            ondelete="RESTRICT",
            name="fk_expenses_trip_owner",
        ),
        CheckConstraint("original_amount >= 0", name="amount"),
        CheckConstraint(
            "(settled_amount IS NULL) = (settled_currency IS NULL)", name="settlement_pair"
        ),
        CheckConstraint("settled_amount IS NULL OR settled_amount >= 0", name="settled_amount"),
        CheckConstraint(
            "exchange_rate IS NULL OR (exchange_rate > 0 AND settled_amount IS NOT NULL)",
            name="exchange_rate",
        ),
        CheckConstraint("version > 0", name="version"),
        CheckConstraint(
            "(activity_id IS NULL AND trip_day_id IS NULL) OR trip_id IS NOT NULL",
            name="links_require_trip",
        ),
        Index("ix_expenses_user_time", "user_id", "occurred_at"),
        Index("ix_expenses_trip", "trip_id"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    trip_id: Mapped[uuid.UUID | None]
    trip_day_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trip_days.id", ondelete="SET NULL")
    )
    activity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("activities.id", ondelete="SET NULL")
    )
    place_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("places.id", ondelete="RESTRICT"))
    merchant: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(64))
    original_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    original_currency: Mapped[str] = mapped_column(String(3))
    settled_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    settled_currency: Mapped[str | None] = mapped_column(String(3))
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    payment_method: Mapped[str | None] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
