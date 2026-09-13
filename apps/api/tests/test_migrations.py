import io

from alembic import command
from alembic.config import Config


def test_offline_migration_upgrade_and_downgrade() -> None:
    output = io.StringIO()
    config = Config("alembic.ini", output_buffer=output)
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in sql
    assert "geography(POINT,4326)" in sql
    assert sql.count("CREATE TYPE visit_source") == 1
    assert sql.count("CREATE INDEX idx_places_location") == 1
    assert "fk_visits_trip_owner" in sql
    assert "fk_activities_day_trip" in sql
    assert "CREATE TABLE wishlist_items" in sql
    output.seek(0)
    output.truncate()
    command.downgrade(config, "0003_wishlist:base", sql=True)
    sql = output.getvalue()
    assert "DROP TABLE visits" in sql
    assert "DROP TYPE visit_source" in sql
    assert "DROP EXTENSION" not in sql
