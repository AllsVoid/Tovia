from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.schemas.common import Health

SCHEMA_HEAD = "0002_core"


def check_health(session: Session) -> Health:
    result = Health(
        status="degraded", database="unavailable", postgis="unavailable", migration="unavailable"
    )
    try:
        session.execute(text("SELECT 1"))
        result.database = "ok"
        session.execute(text("SELECT PostGIS_Version()"))
        result.postgis = "ok"
        revision = session.scalar(text("SELECT version_num FROM alembic_version"))
        result.migration = "ok" if revision == SCHEMA_HEAD else "outdated"
        if result.migration == "ok":
            result.status = "ok"
    except SQLAlchemyError:
        session.rollback()
    return result
