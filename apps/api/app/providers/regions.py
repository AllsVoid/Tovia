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
    matches = [
        r
        for r in catalog().values()
        if query in r.path.lower() or query.replace(" ", "") in r.pinyin.replace(" ", "").lower()
    ]
    return sorted(
        matches, key=lambda r: (r.name != query and r.short_name != query, r.level, r.path)
    )[:limit]
