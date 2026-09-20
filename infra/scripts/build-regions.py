"""Build offline region assets. Run with uv --with shapely --with pycountry.

Inputs: ok_data_level3.csv, matching ok_geo.csv (AreaCity 2025.251231.260403).
Original GCJ-02 coordinates are converted to WGS84 before simplification.
"""

import csv
import gettext
import json
import math
import sys
from pathlib import Path

import pycountry
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "apps/web/public/maps/regions"
CATALOG = ROOT / "apps/api/app/data/regions.json"


def delta(lng: float, lat: float) -> tuple[float, float]:
    x, y = lng - 105, lat - 35
    a = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    b = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    common = (20 * math.sin(6 * x * math.pi) + 20 * math.sin(2 * x * math.pi)) * 2 / 3
    a += common + (20 * math.sin(y * math.pi) + 40 * math.sin(y / 3 * math.pi)) * 2 / 3
    a += (160 * math.sin(y / 12 * math.pi) + 320 * math.sin(y * math.pi / 30)) * 2 / 3
    b += common + (20 * math.sin(x * math.pi) + 40 * math.sin(x / 3 * math.pi)) * 2 / 3
    b += (150 * math.sin(x / 12 * math.pi) + 300 * math.sin(x / 30 * math.pi)) * 2 / 3
    rad = lat / 180 * math.pi
    magic = 1 - 0.00669342162296594323 * math.sin(rad) ** 2
    return (
        b * 180 / (6378245 / math.sqrt(magic) * math.cos(rad) * math.pi),
        a * 180 / (6378245 * (1 - 0.00669342162296594323) / (magic**1.5) * math.pi),
    )


def wgs84(point: str) -> tuple[float, float]:
    lng, lat = map(float, point.split())
    if not (72.004 <= lng <= 137.8347 and 0.8293 <= lat <= 55.8271):
        return lng, lat
    x, y = lng, lat
    for _ in range(4):
        dx, dy = delta(x, y)
        x, y = lng - dx, lat - dy
    return round(x, 6), round(y, 6)


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )


def rounded(value: object) -> object:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, (list, tuple)):
        return [rounded(v) for v in value]
    if isinstance(value, dict):
        return {k: rounded(v) for k, v in value.items()}
    return value


def main() -> None:
    csv.field_size_limit(100_000_000)
    with open(sys.argv[1], encoding="utf-8-sig", newline="") as file:
        names = {r["id"]: r for r in csv.DictReader(file)}
    catalog, groups, cities = [], {}, []
    with open(sys.argv[2], encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            code = row["id"]
            if code not in names or row["polygon"] == "EMPTY" or row["geo"] == "EMPTY":
                continue
            polygons = []
            for part in row["polygon"].split(";"):
                rings = [
                    [wgs84(p) for p in ring.split(",")] for ring in part.split("~")
                ]
                polygons.append(Polygon(rings[0], rings[1:]))
            geom = make_valid(MultiPolygon(polygons))
            if geom.geom_type == "GeometryCollection":
                parts = []
                for part in geom.geoms:
                    if part.geom_type == "Polygon":
                        parts.append(part)
                    elif part.geom_type == "MultiPolygon":
                        parts.extend(part.geoms)
                geom = MultiPolygon(parts)
            geom = geom.simplify(0.002, preserve_topology=True)
            if geom.geom_type not in ("Polygon", "MultiPolygon"):
                raise ValueError(f"Non polygon geometry: {code}")
            parent = names.get(row["pid"])
            province = names[code[:2]]["ext_name"]
            name = names[code]
            country = {"71": "TW", "81": "HK", "82": "MO"}.get(code[:2], "CN")
            timezone = {
                "TW": "Asia/Taipei",
                "HK": "Asia/Hong_Kong",
                "MO": "Asia/Macau",
            }.get(country, "Asia/Shanghai")
            region_id = f"cn:{code}"
            lng, lat = wgs84(row["geo"])
            entry = {
                "id": region_id,
                "parent_id": f"cn:{row['pid']}" if row["pid"] != "0" else None,
                "name": name["ext_name"],
                "short_name": name["name"],
                "path": row["ext_path"],
                "pinyin": name["pinyin"],
                "level": int(row["deep"]),
                "country_code": country,
                "admin1": province,
                "city": parent["ext_name"]
                if int(row["deep"]) == 2 and parent
                else name["ext_name"],
                "timezone": timezone,
                "longitude": lng,
                "latitude": lat,
                "bbox": list(geom.bounds),
                "boundary_file": f"/maps/regions/{code[:2]}.geojson",
            }
            feature = {
                "type": "Feature",
                "properties": {
                    "id": region_id,
                    "name": entry["name"],
                    "level": entry["level"],
                },
                "geometry": rounded(mapping(geom)),
            }
            catalog.append(entry)
            groups.setdefault(code[:2], []).append(feature)
            if entry["level"] == 1:
                cities.append(feature)
    countries = json.loads(
        (ROOT / "apps/web/public/maps/countries.geojson").read_text()
    )
    translate = gettext.translation(
        "iso3166-1", pycountry.LOCALES_DIR, languages=["zh_CN"], fallback=True
    ).gettext
    world = []
    for feature in countries["features"]:
        props = feature["properties"]
        country = pycountry.countries.get(alpha_3=props["code"])
        if not country or country.alpha_2 in ("CN", "HK", "MO", "TW"):
            continue
        geom = shape(feature["geometry"])
        center = geom.representative_point()
        region_id = f"country:{country.alpha_2}"
        name = translate(country.name)
        catalog.append(
            {
                "id": region_id,
                "parent_id": None,
                "name": name,
                "short_name": name,
                "path": name,
                "pinyin": country.name,
                "level": 0,
                "country_code": country.alpha_2,
                "admin1": None,
                "city": None,
                "timezone": "UTC",
                "longitude": center.x,
                "latitude": center.y,
                "bbox": list(geom.bounds),
                "boundary_file": "/maps/regions/world.geojson",
            }
        )
        world.append(
            {
                "type": "Feature",
                "properties": {"id": region_id, "name": name, "level": 0},
                "geometry": feature["geometry"],
            }
        )
    for key, features in {**groups, "cities": cities, "world": world}.items():
        dump(
            OUT / f"{key}.geojson", {"type": "FeatureCollection", "features": features}
        )
    dump(CATALOG, catalog)
    dump(OUT / "index.json", catalog)
    print(f"Built {len(catalog)} searchable regions, {len(cities)} city outlines.")


if __name__ == "__main__":
    main()
