from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.errors import DomainError
from app.models import User, UserIdentity
from app.repositories.identity import IdentityRepository
from app.schemas.identity import UserIdentityBind
from app.services.identity import IdentityService


def payload(user_id: UUID | None = None) -> UserIdentityBind:
    return UserIdentityBind(
        user_id=user_id or uuid4(),
        provider="logto",
        provider_subject="subject-123",
    )


def test_bind_identity_to_existing_user() -> None:
    binding = payload()
    repository = MagicMock(spec=IdentityRepository)
    repository.get_user.return_value = User(id=binding.user_id, display_name="owner")
    repository.find.return_value = None
    repository.save.side_effect = lambda identity: identity

    identity = IdentityService(repository).bind(binding)

    assert identity.user_id == binding.user_id
    assert identity.provider == "logto"
    assert identity.provider_subject == "subject-123"
    repository.save.assert_called_once_with(identity)


def test_rebinding_same_identity_to_same_user_is_idempotent() -> None:
    binding = payload()
    existing = UserIdentity(
        id=uuid4(),
        user_id=binding.user_id,
        provider=binding.provider,
        provider_subject=binding.provider_subject,
    )
    repository = MagicMock(spec=IdentityRepository)
    repository.get_user.return_value = User(id=binding.user_id, display_name="owner")
    repository.find.return_value = existing

    assert IdentityService(repository).bind(binding) is existing
    repository.save.assert_not_called()


def test_identity_cannot_be_rebound_to_another_user() -> None:
    binding = payload()
    repository = MagicMock(spec=IdentityRepository)
    repository.get_user.return_value = User(id=binding.user_id, display_name="other")
    repository.find.return_value = UserIdentity(
        id=uuid4(),
        user_id=uuid4(),
        provider=binding.provider,
        provider_subject=binding.provider_subject,
    )

    with pytest.raises(DomainError) as error:
        IdentityService(repository).bind(binding)
    assert error.value.code == "IDENTITY_CONFLICT"
    assert error.value.status_code == 409


def test_binding_does_not_create_unknown_user() -> None:
    repository = MagicMock(spec=IdentityRepository)
    repository.get_user.return_value = None

    with pytest.raises(DomainError) as error:
        IdentityService(repository).bind(payload())
    assert error.value.code == "USER_NOT_FOUND"
    repository.save.assert_not_called()


def test_concurrent_duplicate_uses_same_conflict_rules() -> None:
    binding = payload()
    existing = UserIdentity(
        id=uuid4(),
        user_id=binding.user_id,
        provider=binding.provider,
        provider_subject=binding.provider_subject,
    )
    repository = MagicMock(spec=IdentityRepository)
    repository.get_user.return_value = User(id=binding.user_id, display_name="owner")
    repository.find.side_effect = [None, existing]
    repository.save.side_effect = IntegrityError("insert", {}, Exception("duplicate"))

    assert IdentityService(repository).bind(binding) is existing
    repository.rollback.assert_called_once()


@pytest.mark.parametrize("provider", ["Logto", "log to", "@logto", ""])
def test_provider_key_must_be_normalized(provider: str) -> None:
    with pytest.raises(ValidationError):
        UserIdentityBind(user_id=uuid4(), provider=provider, provider_subject="subject")
