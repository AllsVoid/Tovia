from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str


class Envelope[T](BaseModel):
    data: T | None = None
    meta: dict[str, object] = Field(default_factory=dict)
    error: ErrorDetail | None = None


class Health(BaseModel):
    status: str
    database: str
    postgis: str
    migration: str
