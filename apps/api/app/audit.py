import json
import logging
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("tovia.audit")
_request_id: ContextVar[str | None] = ContextVar("tovia_request_id", default=None)


def set_request_id(request_id: str) -> Token[str | None]:
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id.reset(token)


def audit_auth_event(event: str, outcome: str, **fields: Any) -> None:
    """Emit one machine-readable auth audit record without credential material."""
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": event,
        "outcome": outcome,
        "request_id": _request_id.get(),
        **fields,
    }
    logger.info(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
