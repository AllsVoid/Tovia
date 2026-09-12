from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.models import Activity, Place, Trip, TripDay, Visit
from app.routers.deps import CurrentUser, Db
from app.schemas.common import Envelope
from app.schemas.core import (
    ActivityCreate,
    ActivityPatch,
    ActivityRead,
    DayCreate,
    DayPatch,
    DayRead,
    PlaceCreate,
    PlaceRead,
    TripCreate,
    TripPatch,
    TripRead,
    UserPatch,
    UserRead,
    VisitCreate,
    VisitPatch,
    VisitRead,
)
from app.services.core import TravelService

router = APIRouter(prefix="/api/v1")


def travel_service(session: Db, user: CurrentUser) -> TravelService:
    return TravelService(session, user)


Service = Annotated[TravelService, Depends(travel_service)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/me", tags=["users"])
def me(user: CurrentUser) -> Envelope[UserRead]:
    return Envelope(data=UserRead.model_validate(user))


@router.patch("/me", tags=["users"])
def update_me(payload: UserPatch, service: Service) -> Envelope[UserRead]:
    return Envelope(data=UserRead.model_validate(service.patch_user(payload)))


@router.get("/trips", tags=["trips"])
def trips(service: Service, limit: Limit = 50, offset: Offset = 0) -> Envelope[list[TripRead]]:
    rows = service.repo.list(
        Trip,
        Trip.user_id == service.user.id,
        limit=limit,
        offset=offset,
        order_by=Trip.created_at.desc(),
    )
    return Envelope(
        data=[TripRead.model_validate(row) for row in rows], meta={"limit": limit, "offset": offset}
    )


@router.post("/trips", status_code=201, tags=["trips"])
def create_trip(payload: TripCreate, service: Service) -> Envelope[TripRead]:
    return Envelope(data=TripRead.model_validate(service.create_trip(payload)))


@router.get("/trips/{trip_id}", tags=["trips"])
def trip(trip_id: UUID, service: Service) -> Envelope[TripRead]:
    return Envelope(data=TripRead.model_validate(service.trip(trip_id)))


@router.patch("/trips/{trip_id}", tags=["trips"])
def patch_trip(trip_id: UUID, payload: TripPatch, service: Service) -> Envelope[TripRead]:
    return Envelope(data=TripRead.model_validate(service.patch_trip(trip_id, payload)))


@router.delete("/trips/{trip_id}", tags=["trips"])
def delete_trip(trip_id: UUID, service: Service) -> Envelope[None]:
    service.delete_trip(trip_id)
    return Envelope()


@router.get("/trips/{trip_id}/days", tags=["days"])
def days(
    trip_id: UUID, service: Service, limit: Limit = 50, offset: Offset = 0
) -> Envelope[list[DayRead]]:
    service.trip(trip_id)
    rows = service.repo.list(
        TripDay, TripDay.trip_id == trip_id, limit=limit, offset=offset, order_by=TripDay.date.asc()
    )
    return Envelope(
        data=[DayRead.model_validate(row) for row in rows], meta={"limit": limit, "offset": offset}
    )


@router.post("/trips/{trip_id}/days", status_code=201, tags=["days"])
def create_day(trip_id: UUID, payload: DayCreate, service: Service) -> Envelope[DayRead]:
    return Envelope(data=DayRead.model_validate(service.create_day(trip_id, payload)))


@router.patch("/days/{day_id}", tags=["days"])
def patch_day(day_id: UUID, payload: DayPatch, service: Service) -> Envelope[DayRead]:
    return Envelope(data=DayRead.model_validate(service.patch_day(day_id, payload)))


@router.delete("/days/{day_id}", tags=["days"])
def delete_day(day_id: UUID, service: Service) -> Envelope[None]:
    service.delete_day(day_id)
    return Envelope()


@router.get("/places/search", tags=["places"])
def search_places(
    service: Service,
    q: Annotated[str, Query(max_length=200)] = "",
    limit: Limit = 50,
    offset: Offset = 0,
) -> Envelope[list[PlaceRead]]:
    rows = service.repo.list(
        Place, Place.canonical_name.icontains(q, autoescape=True), limit=limit, offset=offset
    )
    return Envelope(
        data=[service.place_read(row) for row in rows], meta={"limit": limit, "offset": offset}
    )


@router.post("/places", status_code=201, tags=["places"])
def create_place(payload: PlaceCreate, service: Service) -> Envelope[PlaceRead]:
    return Envelope(data=service.place_read(service.create_place(payload)))


@router.get("/places/{place_id}", tags=["places"])
def place(place_id: UUID, service: Service) -> Envelope[PlaceRead]:
    return Envelope(data=service.place_read(service.place(place_id)))


@router.get("/visits", tags=["visits"])
def visits(
    service: Service, trip_id: UUID | None = None, limit: Limit = 50, offset: Offset = 0
) -> Envelope[list[VisitRead]]:
    filters = [Visit.user_id == service.user.id]
    if trip_id:
        service.trip(trip_id)
        filters.append(Visit.trip_id == trip_id)
    rows = service.repo.list(
        Visit, *filters, limit=limit, offset=offset, order_by=Visit.visited_at.desc()
    )
    return Envelope(
        data=[VisitRead.model_validate(row) for row in rows],
        meta={"limit": limit, "offset": offset},
    )


@router.post("/visits", status_code=201, tags=["visits"])
def create_visit(payload: VisitCreate, service: Service) -> Envelope[VisitRead]:
    return Envelope(data=VisitRead.model_validate(service.create_visit(payload)))


@router.patch("/visits/{visit_id}", tags=["visits"])
def patch_visit(visit_id: UUID, payload: VisitPatch, service: Service) -> Envelope[VisitRead]:
    return Envelope(data=VisitRead.model_validate(service.patch_visit(visit_id, payload)))


@router.delete("/visits/{visit_id}", tags=["visits"])
def delete_visit(visit_id: UUID, service: Service) -> Envelope[None]:
    service.repo.delete(service.visit(visit_id))
    return Envelope()


@router.get("/trips/{trip_id}/activities", tags=["activities"])
def activities(
    trip_id: UUID, service: Service, limit: Limit = 50, offset: Offset = 0
) -> Envelope[list[ActivityRead]]:
    service.trip(trip_id)
    rows = service.repo.list(
        Activity,
        Activity.trip_id == trip_id,
        limit=limit,
        offset=offset,
        order_by=Activity.sort_order.asc(),
    )
    return Envelope(
        data=[ActivityRead.model_validate(row) for row in rows],
        meta={"limit": limit, "offset": offset},
    )


@router.post("/trips/{trip_id}/activities", status_code=201, tags=["activities"])
def create_activity(
    trip_id: UUID, payload: ActivityCreate, service: Service
) -> Envelope[ActivityRead]:
    return Envelope(data=ActivityRead.model_validate(service.create_activity(trip_id, payload)))


@router.patch("/activities/{activity_id}", tags=["activities"])
def patch_activity(
    activity_id: UUID, payload: ActivityPatch, service: Service
) -> Envelope[ActivityRead]:
    return Envelope(data=ActivityRead.model_validate(service.patch_activity(activity_id, payload)))


@router.delete("/activities/{activity_id}", tags=["activities"])
def delete_activity(activity_id: UUID, service: Service) -> Envelope[None]:
    service.repo.delete(service.activity(activity_id))
    return Envelope()
