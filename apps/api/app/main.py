import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException

from app.config import get_settings
from app.db import engine
from app.errors import DomainError
from app.routers import core, explore, health
from app.schemas.common import Envelope, ErrorDetail

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    engine.dispose()


app = FastAPI(
    title="Tovia 所至 API",
    version="0.1.0",
    lifespan=lifespan,
    responses={
        401: {"model": Envelope[None]},
        404: {"model": Envelope[None]},
        409: {"model": Envelope[None]},
        422: {"model": Envelope[None]},
    },
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)
app.include_router(health.router)
app.include_router(core.router)
app.include_router(explore.router)


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=Envelope[None](error=ErrorDetail(code=code, message=message)).model_dump(),
    )


@app.exception_handler(DomainError)
async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
async def validation_error(request: Request, exc: Exception) -> JSONResponse:
    return error_response(422, "VALIDATION_ERROR", "Invalid request fields or date/time range")


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
    return error_response(
        409, "DATA_CONFLICT", "Duplicate value or conflicting entity relationship"
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("Database operation failed: %s", type(exc).__name__)
    return error_response(503, "DATABASE_UNAVAILABLE", "Database is unavailable")


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    return error_response(exc.status_code, f"HTTP_{exc.status_code}", str(exc.detail))
