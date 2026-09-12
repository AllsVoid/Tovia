from collections.abc import Sequence
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models import Base

M = TypeVar("M", bound=Base)


class Repository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, model: type[M], entity_id: UUID) -> M | None:
        return self.session.get(model, entity_id)

    def list(
        self,
        model: type[M],
        *filters: ColumnElement[bool],
        limit: int = 50,
        offset: int = 0,
        order_by: ColumnElement[Any] | None = None,
    ) -> Sequence[M]:
        return self.session.scalars(
            select(model)
            .where(*filters)
            .order_by(
                order_by if order_by is not None else model.__table__.c.id,
                model.__table__.c.id,
            )
            .limit(limit)
            .offset(offset)
        ).all()

    def save(self, entity: M) -> M:
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def delete(self, entity: Base) -> None:
        self.session.delete(entity)
        self.session.commit()
