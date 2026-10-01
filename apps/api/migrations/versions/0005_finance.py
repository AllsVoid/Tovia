"""Manual bookings and expenses, exact money and optimistic versions."""

import sqlalchemy as sa
from alembic import op

revision = "0005_finance"
down_revision = "0004_user_identity"
branch_labels = None
depends_on = None


def common_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("trip_id", sa.Uuid()),
        sa.Column("activity_id", sa.Uuid(), sa.ForeignKey("activities.id", ondelete="SET NULL")),
        sa.Column("note", sa.Text()),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_unique_constraint("uq_activities_id", "activities", ["id", "trip_id"])
    op.create_table(
        "bookings",
        *common_columns(),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), server_default="CONFIRMED", nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("provider_name", sa.String(200)),
        sa.Column("reference_no", sa.String(200)),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True)),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("end_timezone", sa.String(64), nullable=False),
        sa.Column("origin_place_id", sa.Uuid(), sa.ForeignKey("places.id", ondelete="RESTRICT")),
        sa.Column(
            "destination_place_id", sa.Uuid(), sa.ForeignKey("places.id", ondelete="RESTRICT")
        ),
        sa.Column("address", sa.Text()),
        sa.Column("currency", sa.String(3)),
        sa.Column("amount", sa.Numeric(18, 4)),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["activity_id", "trip_id"],
            ["activities.id", "activities.trip_id"],
            ondelete="RESTRICT",
            name="fk_bookings_activity_trip",
        ),
        sa.ForeignKeyConstraint(
            ["trip_id", "user_id"],
            ["trips.id", "trips.user_id"],
            ondelete="RESTRICT",
            name="fk_bookings_trip_owner",
        ),
        sa.CheckConstraint(
            "type IN ('FLIGHT','TRAIN','BUS','HOTEL','TICKET','RESTAURANT','OTHER')", name="type"
        ),
        sa.CheckConstraint(
            "status IN ('PLANNED','CONFIRMED','COMPLETED','CANCELLED')", name="status"
        ),
        sa.CheckConstraint("end_at IS NULL OR end_at >= start_at", name="time_range"),
        sa.CheckConstraint("(amount IS NULL) = (currency IS NULL)", name="money_pair"),
        sa.CheckConstraint("amount IS NULL OR amount >= 0", name="amount"),
        sa.CheckConstraint("version > 0", name="version"),
        sa.CheckConstraint(
            "activity_id IS NULL OR trip_id IS NOT NULL", name="activity_requires_trip"
        ),
    )
    op.create_index("ix_bookings_user_time", "bookings", ["user_id", "start_at"])
    op.create_index("ix_bookings_trip", "bookings", ["trip_id"])
    op.create_table(
        "expenses",
        *common_columns(),
        sa.Column("trip_day_id", sa.Uuid(), sa.ForeignKey("trip_days.id", ondelete="SET NULL")),
        sa.Column("place_id", sa.Uuid(), sa.ForeignKey("places.id", ondelete="RESTRICT")),
        sa.Column("merchant", sa.String(200)),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("original_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("original_currency", sa.String(3), nullable=False),
        sa.Column("settled_amount", sa.Numeric(18, 4)),
        sa.Column("settled_currency", sa.String(3)),
        sa.Column("exchange_rate", sa.Numeric(18, 8)),
        sa.Column("payment_method", sa.String(64)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["trip_id", "user_id"],
            ["trips.id", "trips.user_id"],
            ondelete="RESTRICT",
            name="fk_expenses_trip_owner",
        ),
        sa.CheckConstraint("original_amount >= 0", name="amount"),
        sa.ForeignKeyConstraint(
            ["activity_id", "trip_id"],
            ["activities.id", "activities.trip_id"],
            ondelete="RESTRICT",
            name="fk_expenses_activity_trip",
        ),
        sa.ForeignKeyConstraint(
            ["trip_day_id", "trip_id"],
            ["trip_days.id", "trip_days.trip_id"],
            ondelete="RESTRICT",
            name="fk_expenses_day_trip",
        ),
        sa.CheckConstraint(
            "(settled_amount IS NULL) = (settled_currency IS NULL)", name="settlement_pair"
        ),
        sa.CheckConstraint("settled_amount IS NULL OR settled_amount >= 0", name="settled_amount"),
        sa.CheckConstraint(
            "exchange_rate IS NULL OR (exchange_rate > 0 AND settled_amount IS NOT NULL)",
            name="exchange_rate",
        ),
        sa.CheckConstraint("version > 0", name="version"),
        sa.CheckConstraint(
            "(activity_id IS NULL AND trip_day_id IS NULL) OR trip_id IS NOT NULL",
            name="links_require_trip",
        ),
    )
    op.create_index("ix_expenses_user_time", "expenses", ["user_id", "occurred_at"])
    op.create_index("ix_expenses_trip", "expenses", ["trip_id"])


def downgrade() -> None:
    op.drop_table("expenses")
    op.drop_table("bookings")
    op.drop_constraint("uq_activities_id", "activities", type_="unique")
