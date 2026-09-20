from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserIdentity


class IdentityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_user(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def find(self, provider: str, provider_subject: str) -> UserIdentity | None:
        return self.session.scalar(
            select(UserIdentity).where(
                UserIdentity.provider == provider,
                UserIdentity.provider_subject == provider_subject,
            )
        )

    def save(self, identity: UserIdentity) -> UserIdentity:
        self.session.add(identity)
        self.session.commit()
        self.session.refresh(identity)
        return identity

    def rollback(self) -> None:
        self.session.rollback()
