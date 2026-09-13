import { readFile, writeFile } from "node:fs/promises";

// Usage: node apps/web/scripts/build-map-data.mjs <admin0-50m.json> <admin1-50m.json>
// Both inputs are Natural Earth 1:50m GeoJSON; see docs/ARCHITECTURE.md.
const [countriesPath, provincesPath] = process.argv.slice(2);
if (!countriesPath || !provincesPath)
  throw new Error("Provide both 50m GeoJSON inputs.");
const countries = JSON.parse(await readFile(countriesPath, "utf8"));
const provinces = JSON.parse(
  await readFile(provincesPath, "utf8"),
).features.filter((feature) => feature.properties.admin === "China");
const edges = new Map();
for (const [province, feature] of provinces.entries()) {
  const polygons =
    feature.geometry.type === "Polygon"
      ? [feature.geometry.coordinates]
      : feature.geometry.coordinates;
  for (const polygon of polygons)
    for (const ring of polygon) {
      for (let i = 1; i < ring.length; i++) {
        const ends = [
          JSON.stringify(ring[i - 1]),
          JSON.stringify(ring[i]),
        ].sort();
        const key = ends.join("|");
        if (!edges.has(key)) edges.set(key, { ends, owners: new Set() });
        edges.get(key).owners.add(province);
      }
    }
}
// Only edges shared by distinct provinces are internal boundaries. Coastlines and
// national boundaries come exclusively from the country fill geometry.
const neighbors = new Map();
const remaining = new Set();
for (const [
  key,
  {
    ends: [a, b],
    owners,
  },
] of edges) {
  if (owners.size < 2) continue;
  remaining.add(key);
  for (const [from, to] of [
    [a, b],
    [b, a],
  ]) {
    if (!neighbors.has(from)) neighbors.set(from, []);
    neighbors.get(from).push(to);
  }
}
const lines = [];
function walk(start, next) {
  const line = [JSON.parse(start)];
  let current = start;
  while (next) {
    const key = [current, next].sort().join("|");
    if (!remaining.delete(key)) break;
    line.push(JSON.parse(next));
    current = next;
    const adjacent = neighbors.get(current);
    if (adjacent.length !== 2) break;
    next = adjacent.find((point) =>
      remaining.has([current, point].sort().join("|")),
    );
  }
  if (line.length > 1) lines.push(line);
}
for (const [point, adjacent] of neighbors) {
  if (adjacent.length !== 2) for (const next of adjacent) walk(point, next);
}
while (remaining.size) {
  const [start, next] = remaining.values().next().value.split("|");
  walk(start, next);
}
const collection = (features) => ({ type: "FeatureCollection", features });
await writeFile(
  new URL("../public/maps/countries.geojson", import.meta.url),
  JSON.stringify(
    collection(
      countries.features.map((f) => ({
        type: "Feature",
        properties: { name: f.properties.NAME, code: f.properties.ADM0_A3 },
        geometry: f.geometry,
      })),
    ),
  ),
);
await writeFile(
  new URL("../public/maps/provinces.geojson", import.meta.url),
  JSON.stringify(
    collection([
      {
        type: "Feature",
        properties: {},
        geometry: { type: "MultiLineString", coordinates: lines },
      },
    ]),
  ),
);
console.log(
  `${countries.features.length} countries; ${provinces.length} provinces → ${lines.length} internal boundary lines.`,
);
