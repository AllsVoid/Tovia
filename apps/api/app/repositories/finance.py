from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.finance import Booking, Expense
from app.repositories.core import Repository


class FinanceRepository(Repository):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def owned[M: Booking | Expense](
        self, model: type[M], entity_id: UUID, user_id: UUID, *, lock: bool = False
    ) -> M | None:
        query = select(model).where(model.id == entity_id, model.user_id == user_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(query)

    def page[M: Booking | Expense](
        self, model: type[M], user_id: UUID, trip_id: UUID | None, limit: int, offset: int
    ) -> tuple[Sequence[M], int]:
        filters = [model.user_id == user_id]
        if trip_id is not None:
            filters.append(model.trip_id == trip_id)
        time = Booking.start_at if model is Booking else Expense.occurred_at
        rows = self.list(model, *filters, limit=limit, offset=offset, order_by=time.desc())
        total = self.session.scalar(select(func.count()).select_from(model).where(*filters)) or 0
        return rows, total

    def summary_rows(self, trip_id: UUID, user_id: UUID) -> tuple[int, Sequence[Expense]]:
        count = (
            self.session.scalar(
                select(func.count())
                .select_from(Booking)
                .where(Booking.trip_id == trip_id, Booking.user_id == user_id)
            )
            or 0
        )
        expenses = self.session.scalars(
            select(Expense).where(Expense.trip_id == trip_id, Expense.user_id == user_id)
        ).all()
        return count, expenses
