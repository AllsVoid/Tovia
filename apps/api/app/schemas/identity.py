from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.schemas.core import Input, Output

ProviderName = Annotated[
    str,
    Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9._-]*$"),
]
ProviderSubject = Annotated[str, Field(min_length=1, max_length=255)]


class UserIdentityBind(Input):
    user_id: UUID
    provider: ProviderName
    provider_subject: ProviderSubject


class UserIdentityRead(Output):
    id: UUID
    user_id: UUID
    provider: str
    provider_subject: str
    created_at: datetime
