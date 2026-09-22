from sqlalchemy.exc import IntegrityError

from app.audit import audit_auth_event
from app.errors import DomainError
from app.models import UserIdentity
from app.repositories.identity import IdentityRepository
from app.schemas.identity import UserIdentityBind


class IdentityService:
    def __init__(self, repository: IdentityRepository) -> None:
        self.repository = repository

    def bind(self, payload: UserIdentityBind) -> UserIdentity:
        if self.repository.get_user(payload.user_id) is None:
            raise DomainError("USER_NOT_FOUND", "User not found", 404)

        existing = self.repository.find(payload.provider, payload.provider_subject)
        if existing is not None:
            return self._resolve_existing(existing, payload)

        identity = UserIdentity(
            user_id=payload.user_id,
            provider=payload.provider,
            provider_subject=payload.provider_subject,
        )
        try:
            return self.repository.save(identity)
        except IntegrityError:
            # Another operator/process may have created the same identity after
            # our lookup. Re-read it and preserve the same idempotency/conflict rules.
            self.repository.rollback()
            existing = self.repository.find(payload.provider, payload.provider_subject)
            if existing is None:
                raise
            return self._resolve_existing(existing, payload)

    @staticmethod
    def _resolve_existing(existing: UserIdentity, payload: UserIdentityBind) -> UserIdentity:
        if existing.user_id != payload.user_id:
            audit_auth_event(
                "auth.identity_binding",
                "conflict",
                provider=payload.provider,
                requested_user_id=str(payload.user_id),
                existing_user_id=str(existing.user_id),
                reason="subject_already_bound",
            )
            raise DomainError(
                "IDENTITY_CONFLICT",
                "Identity is already bound to another user",
                409,
            )
        return existing
