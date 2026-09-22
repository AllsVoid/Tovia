import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.commands.validate_export import load_export
from app.schemas.data_export import validate_export_document


def empty_export() -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "schema_version": "1.0",
        "exported_at": now,
        "data": {
            "user": {
                "id": str(uuid4()),
                "display_name": "Export owner",
                "avatar_url": None,
                "timezone": "UTC",
                "locale": "zh-CN",
                "created_at": now,
                "updated_at": now,
            },
            "trips": [],
            "trip_days": [],
            "visits": [],
            "activities": [],
            "places": [],
            "wishlist_items": [],
        },
    }


def test_validate_export_accepts_downloaded_document_and_api_envelope(tmp_path: Path) -> None:
    document = empty_export()
    export_file = tmp_path / "tovia-export.json"
    export_file.write_text(json.dumps(document), encoding="utf-8")

    loaded = load_export(export_file)
    enveloped = validate_export_document({"data": document, "meta": {}, "error": None})

    assert loaded.schema_version == "1.0"
    assert enveloped.data.user.id == loaded.data.user.id


def test_validate_export_rejects_missing_relationship() -> None:
    document = empty_export()
    records = document["data"]
    assert isinstance(records, dict)
    records["trip_days"] = [
        {
            "id": str(uuid4()),
            "trip_id": str(uuid4()),
            "date": "2026-09-22",
            "title": None,
            "note": None,
            "sort_order": 0,
        }
    ]

    with pytest.raises(ValidationError, match="references a missing Trip"):
        validate_export_document(document)


def test_validate_export_rejects_naive_export_timestamp() -> None:
    document = empty_export()
    document["exported_at"] = "2026-09-22T12:00:00"

    with pytest.raises(ValidationError, match="timezone_aware"):
        validate_export_document(document)
