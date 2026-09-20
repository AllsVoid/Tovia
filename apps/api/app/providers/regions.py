"""Offline administrative catalog, replaceable independently of domain services."""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel


class Region(BaseModel):
    id: str
    parent_id: str | None
    name: str
    short_name: str
    path: str
    pinyin: str
    level: int
    country_code: str
    admin1: str | None
    city: str | None
    timezone: str
    longitude: float
    latitude: float
    bbox: list[float]
    boundary_file: str


@lru_cache(maxsize=1)
def catalog() -> dict[str, Region]:
    path = Path(__file__).resolve().parents[1] / "data" / "regions.json"
    return {
        r.id: r
        for row in json.loads(path.read_text(encoding="utf-8"))
        if (r := Region.model_validate(row))
    }


def search_regions(query: str, limit: int = 30) -> list[Region]:
    query = query.strip().lower()
    if not query:
        return []
    source = catalog()
    matches = [
        r
        for r in source.values()
        if query in r.path.lower() or query.replace(" ", "") in r.pinyin.replace(" ", "").lower()
    ]
    # A trip footprint is city-level. District names remain useful search terms,
    # but resolve to their parent city instead of creating overly precise map data.
    promoted: dict[str, Region] = {}
    for region in matches:
        if region.id.startswith("cn:"):
            city = region if region.level == 1 else source.get(region.parent_id or "")
            if city is None or city.level != 1:
                continue
            promoted[city.id] = city
        else:
            promoted[region.id] = region
    return sorted(
        promoted.values(),
        key=lambda r: (r.name != query and r.short_name != query, r.path),
    )[:limit]
