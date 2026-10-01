from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.models.finance import Booking, Expense
from app.routers.core import Limit, Offset
from app.routers.deps import CurrentUser, Db
from app.schemas.common import Envelope
from app.schemas.finance import (
    BookingCreate,
    BookingPatch,
    BookingRead,
    ExpenseCreate,
    ExpensePatch,
    ExpenseRead,
    TripSummary,
)
from app.services.finance import FinanceService

router = APIRouter(prefix="/api/v1", tags=["finance"])


def finance_service(session: Db, user: CurrentUser) -> FinanceService:
    return FinanceService(session, user)


Service = Annotated[FinanceService, Depends(finance_service)]
Revision = Annotated[int, Query(ge=1)]


@router.get("/bookings")
def bookings(
    service: Service, trip_id: UUID | None = None, limit: Limit = 50, offset: Offset = 0
) -> Envelope[list[BookingRead]]:
    rows, total = service.page(Booking, trip_id, limit, offset)
    return Envelope(
        data=[BookingRead.model_validate(row) for row in rows],
        meta={"limit": limit, "offset": offset, "total": total},
    )


@router.get("/trips/{trip_id}/bookings")
def trip_bookings(
    trip_id: UUID, service: Service, limit: Limit = 50, offset: Offset = 0
) -> Envelope[list[BookingRead]]:
    return bookings(service, trip_id, limit, offset)


@router.post("/bookings", status_code=201)
def create_booking(payload: BookingCreate, service: Service) -> Envelope[BookingRead]:
    return Envelope(data=BookingRead.model_validate(service.create_booking(payload)))


@router.get("/bookings/{booking_id}")
def booking(booking_id: UUID, service: Service) -> Envelope[BookingRead]:
    return Envelope(data=BookingRead.model_validate(service.entity(Booking, booking_id)))


@router.patch("/bookings/{booking_id}")
def patch_booking(
    booking_id: UUID, payload: BookingPatch, service: Service
) -> Envelope[BookingRead]:
    return Envelope(data=BookingRead.model_validate(service.patch(Booking, booking_id, payload)))


@router.delete("/bookings/{booking_id}")
def delete_booking(booking_id: UUID, service: Service, version: Revision) -> Envelope[None]:
    service.delete(Booking, booking_id, version)
    return Envelope()


@router.get("/expenses")
def expenses(
    service: Service, trip_id: UUID | None = None, limit: Limit = 50, offset: Offset = 0
) -> Envelope[list[ExpenseRead]]:
    rows, total = service.page(Expense, trip_id, limit, offset)
    return Envelope(
        data=[ExpenseRead.model_validate(row) for row in rows],
        meta={"limit": limit, "offset": offset, "total": total},
    )


@router.get("/trips/{trip_id}/expenses")
def trip_expenses(
    trip_id: UUID, service: Service, limit: Limit = 50, offset: Offset = 0
) -> Envelope[list[ExpenseRead]]:
    return expenses(service, trip_id, limit, offset)


@router.post("/expenses", status_code=201)
def create_expense(payload: ExpenseCreate, service: Service) -> Envelope[ExpenseRead]:
    return Envelope(data=ExpenseRead.model_validate(service.create_expense(payload)))


@router.get("/expenses/{expense_id}")
def expense(expense_id: UUID, service: Service) -> Envelope[ExpenseRead]:
    return Envelope(data=ExpenseRead.model_validate(service.entity(Expense, expense_id)))


@router.patch("/expenses/{expense_id}")
def patch_expense(
    expense_id: UUID, payload: ExpensePatch, service: Service
) -> Envelope[ExpenseRead]:
    return Envelope(data=ExpenseRead.model_validate(service.patch(Expense, expense_id, payload)))


@router.delete("/expenses/{expense_id}")
def delete_expense(expense_id: UUID, service: Service, version: Revision) -> Envelope[None]:
    service.delete(Expense, expense_id, version)
    return Envelope()


@router.get("/trips/{trip_id}/summary")
@router.get("/trips/{trip_id}/expenses/summary")
def summary(trip_id: UUID, service: Service) -> Envelope[TripSummary]:
    return Envelope(data=service.summary(trip_id))
