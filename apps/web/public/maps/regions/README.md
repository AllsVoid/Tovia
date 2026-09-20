# Administrative regions

China region names and hierarchy: user-provided `ok_data_level3.csv`, AreaCity
release `2025.251231.260403`. Matching boundaries: `ok_geo.csv.7z` from
https://github.com/xiangyuecn/AreaCity-JsSpider-StatsGov/releases/tag/2025.251231.260403.
Project license is included as `LICENSE-AreaCity.txt`.

Input SHA256:

- `ok_data_level3.csv`: `dd5a1594565b65fa3fea5ce4b9935e0b28908226949ae44f07ebfd533428e8ff`
- `ok_geo.csv.7z`: `675c3e9b8dec6444994d3ef53259a145304f6a957db8a5e601e55c0b9e61e21a`

Build: `uv run --project apps/api --with shapely==2.1.2 --with pycountry==26.2.16 python infra/scripts/build-regions.py <ok_data_level3.csv> <ok_geo.csv>`.
The build joins by administrative ID, converts GCJ-02 to WGS84 using iterative
inverse conversion, repairs invalid polygon geometry, simplifies with topology
preservation at 0.002 degrees, and rounds coordinates to six decimal places.
Non-area remnants from geometry repair are discarded. These are overview
boundaries, not navigation or surveying geometry. Independent simplification
can leave tiny differences between adjacent edges.

`index.json` is the searchable catalog (also bundled in the API); numbered
GeoJSON files contain province/city/district boundaries grouped by province.
`cities.geojson` provides overview city outlines and legacy coordinate lookup.
Only entries with an available boundary and center are selectable. The source
has incomplete Taiwan city/district geometry; unsupported entries are omitted,
not substituted with a larger region. Overseas entries use existing Natural
Earth 1:50m country boundaries (public domain), with ISO names from pycountry.
Overseas country records use UTC because a country may have multiple timezones.

The map highlights the explicitly selected area, never all its parents. A
historical POI is displayed within its containing city without changing the
stored record. Repeated visits are aggregated for display, not deleted.
