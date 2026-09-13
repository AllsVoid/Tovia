from datetime import date as Date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.routers.deps import CurrentUser, Db
from app.schemas.common import Envelope
from app.schemas.explore import (
    CalendarDay,
    CalendarMonth,
    MapDetail,
    MapPage,
    MapSummary,
    PlaceStatus,
    Scope,
    WishlistCreate,
    WishlistRead,
)
from app.services.explore import ExploreService

router = APIRouter(prefix="/api/v1")


def explore_service(session: Db, user: CurrentUser) -> ExploreService:
    return ExploreService(session, user)


Service = Annotated[ExploreService, Depends(explore_service)]


@router.get("/map/summary", tags=["map"])
def summary(service: Service, scope: Scope = "all") -> Envelope[MapSummary]:
    return Envelope(data=service.map_summary(scope))


@router.get("/map/places", tags=["map"])
def map_places(
    service: Service,
    scope: Scope = "all",
    status: PlaceStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Envelope[MapPage]:
    return Envelope(data=service.map_places(scope, status, limit, offset))


@router.get("/map/places/{place_id}", tags=["map"])
def detail(place_id: UUID, service: Service) -> Envelope[MapDetail]:
    return Envelope(data=service.map_detail(place_id))


@router.post("/wishlist", tags=["wishlist"])
def wishlist(payload: WishlistCreate, service: Service) -> Envelope[WishlistRead]:
    return Envelope(data=service.add_wishlist(payload))


@router.delete("/wishlist/{place_id}", tags=["wishlist"])
def remove_wishlist(place_id: UUID, service: Service) -> Envelope[None]:
    service.remove_wishlist(place_id)
    return Envelope()


@router.get("/calendar/month", tags=["calendar"])
def month(
    service: Service,
    year: Annotated[int, Query(ge=1900, le=2100)],
    month: Annotated[int, Query(ge=1, le=12)],
) -> Envelope[CalendarMonth]:
    return Envelope(data=service.calendar_month(year, month))


@router.get("/calendar/day", tags=["calendar"])
def day(service: Service, date: Date) -> Envelope[CalendarDay]:
    return Envelope(data=service.calendar_day(date))
