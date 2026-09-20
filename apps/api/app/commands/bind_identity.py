import argparse
import sys
from collections.abc import Sequence

from pydantic import ValidationError

from app.db import SessionLocal
from app.errors import DomainError
from app.repositories.identity import IdentityRepository
from app.schemas.identity import UserIdentityBind, UserIdentityRead
from app.services.identity import IdentityService


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Bind an external provider subject to an existing Tovia user."
    )
    command.add_argument("--provider", required=True, help="Provider key, for example: logto")
    command.add_argument("--subject", required=True, help="Stable subject from the provider")
    command.add_argument("--user-id", required=True, help="Existing Tovia User UUID")
    return command


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        payload = UserIdentityBind(
            user_id=args.user_id,
            provider=args.provider,
            provider_subject=args.subject,
        )
        with SessionLocal() as session:
            identity = IdentityService(IdentityRepository(session)).bind(payload)
        result = UserIdentityRead.model_validate(identity)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except DomainError as exc:
        print(f"{exc.code}: {exc.message}", file=sys.stderr)
        return 1

    print(result.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
