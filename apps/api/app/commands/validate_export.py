import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.schemas.data_export import DataExport, validate_export_document


def load_export(path: Path) -> DataExport:
    with path.open(encoding="utf-8") as source:
        document: Any = json.load(source)
    return validate_export_document(document)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a Tovia profile JSON export and all entity references."
    )
    parser.add_argument("path", type=Path, help="Path to the downloaded JSON export")
    args = parser.parse_args()

    try:
        exported = load_export(args.path)
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        print(f"INVALID: {exc}")
        return 1

    records = exported.data
    print(
        "VALID: "
        f"schema={exported.schema_version} "
        f"trips={len(records.trips)} "
        f"trip_days={len(records.trip_days)} "
        f"visits={len(records.visits)} "
        f"activities={len(records.activities)} "
        f"places={len(records.places)} "
        f"wishlist_items={len(records.wishlist_items)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
