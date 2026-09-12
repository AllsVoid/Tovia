from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.common import Envelope, Health
from app.services.health import check_health

router = APIRouter(tags=["health"])


@router.get(
    "/health", response_model=Envelope[Health], responses={503: {"model": Envelope[Health]}}
)
def health(
    response: Response, session: Annotated[Session, Depends(get_session)]
) -> Envelope[Health]:
    state = check_health(session)
    if state.status != "ok":
        response.status_code = 503
    return Envelope(data=state)
