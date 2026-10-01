from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit import audit_data_event
from app.errors import DomainError
from app.models import User
from app.models.finance import Booking, Expense
from app.repositories.finance import FinanceRepository
from app.schemas.finance import (
    BookingCreate,
    BookingPatch,
    CategoryTotal,
    ExpenseCreate,
    ExpensePatch,
    MoneyTotal,
    TripSummary,
)
from app.services.core import TravelService


def expense_summary(booking_count: int, expenses: Sequence[Expense]) -> TripSummary:
    originals: dict[str, Decimal] = defaultdict(Decimal)
    paid: dict[str, Decimal] = defaultdict(Decimal)
    categories: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for expense in expenses:
        originals[expense.original_currency] += expense.original_amount
        currency = expense.settled_currency or expense.original_currency
        amount = (
            expense.settled_amount
            if expense.settled_amount is not None
            else expense.original_amount
        )
        paid[currency] += amount
        categories[(expense.category, currency)] += amount
    return TripSummary(
        booking_count=booking_count,
        expense_count=len(expenses),
        original_totals=[
            MoneyTotal(currency=currency, amount=amount)
            for currency, amount in sorted(originals.items())
        ],
        paid_totals=[
            MoneyTotal(currency=currency, amount=amount)
            for currency, amount in sorted(paid.items())
        ],
        categories=[
            CategoryTotal(category=category, currency=currency, amount=amount)
            for (category, currency), amount in sorted(categories.items())
        ],
    )


class FinanceService:
    def __init__(self, session: Session, user: User) -> None:
        self.repo = FinanceRepository(session)
        self.travel = TravelService(session, user)
        self.user = user

    def entity[M: Booking | Expense](
        self, model: type[M], entity_id: UUID, *, lock: bool = False
    ) -> M:
        entity = self.repo.owned(model, entity_id, self.user.id, lock=lock)
        if entity is None:
            raise DomainError(
                f"{model.__name__.upper()}_NOT_FOUND", f"{model.__name__} not found", 404
            )
        return entity

    def validate_links(self, payload: BookingCreate | ExpenseCreate) -> None:
        if payload.trip_id:
            self.travel.trip(payload.trip_id)
        if payload.activity_id:
            activity = self.travel.activity(payload.activity_id)
            if activity.trip_id != payload.trip_id:
                raise DomainError(
                    "ACTIVITY_TRIP_MISMATCH", "Activity does not belong to this trip", 422
                )
        if isinstance(payload, ExpenseCreate):
            if payload.trip_day_id:
                self.travel.day(payload.trip_day_id, payload.trip_id)
            places = [payload.place_id]
        else:
            places = [payload.origin_place_id, payload.destination_place_id]
        for place_id in places:
            if place_id:
                self.travel.place(place_id)

    def create_booking(self, payload: BookingCreate) -> Booking:
        self.validate_links(payload)
        return self.repo.save(Booking(user_id=self.user.id, **payload.model_dump()))

    def create_expense(self, payload: ExpenseCreate) -> Expense:
        self.validate_links(payload)
        return self.repo.save(Expense(user_id=self.user.id, **payload.model_dump()))

    @staticmethod
    def check_version(entity: Booking | Expense, version: int) -> None:
        if entity.version != version:
            raise DomainError(
                "VERSION_CONFLICT", "Record changed; reload before saving or deleting", 409
            )

    def patch[M: Booking | Expense](
        self, model: type[M], entity_id: UUID, patch: BookingPatch | ExpensePatch
    ) -> M:
        entity = self.entity(model, entity_id, lock=True)
        self.check_version(entity, patch.version)
        # version is a concurrency precondition, never a mutable business field.
        values = patch.model_dump(exclude_unset=True, exclude={"version"})
        schema = BookingCreate if isinstance(entity, Booking) else ExpenseCreate
        merged = {name: getattr(entity, name) for name in schema.model_fields}
        merged.update(values)
        payload = schema.model_validate(merged)
        self.validate_links(payload)
        for name, value in payload.model_dump().items():
            setattr(entity, name, value)
        entity.version += 1
        return self.repo.save(entity)

    def delete(self, model: type[Booking] | type[Expense], entity_id: UUID, version: int) -> None:
        entity = self.entity(model, entity_id, lock=True)
        self.check_version(entity, version)
        self.repo.delete(entity)
        audit_data_event(
            "data.entity_deletion",
            "succeeded",
            entity=model.__name__.lower(),
            entity_id=str(entity_id),
            user_id=str(self.user.id),
        )

    def page[M: Booking | Expense](
        self, model: type[M], trip_id: UUID | None, limit: int, offset: int
    ) -> tuple[Sequence[M], int]:
        if trip_id:
            self.travel.trip(trip_id)
        return self.repo.page(model, self.user.id, trip_id, limit, offset)

    def summary(self, trip_id: UUID) -> TripSummary:
        self.travel.trip(trip_id)
        count, rows = self.repo.summary_rows(trip_id, self.user.id)
        return expense_summary(count, rows)
