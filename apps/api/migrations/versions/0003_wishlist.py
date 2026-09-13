"""Phase 2: independent user wishlist, without inventing visits."""

import sqlalchemy as sa
from alembic import op

revision = "0003_wishlist"
down_revision = "0002_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wishlist_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("place_id", sa.Uuid(), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_wishlist_items"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_wishlist_items_user_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["place_id"],
            ["places.id"],
            ondelete="RESTRICT",
            name="fk_wishlist_items_place_id_places",
        ),
        sa.UniqueConstraint("user_id", "place_id", name="uq_wishlist_items_user_id"),
    )


def downgrade() -> None:
    op.drop_table("wishlist_items")
