import type {
  Feature,
  FeatureCollection,
  MultiPolygon,
  Polygon,
} from "geojson";
import type { MapPlace, PlaceStatus, Region } from "./types";

export type RegionFeature = Feature<
  Polygon | MultiPolygon,
  { id: string; name: string; level: number }
>;
type Boundaries = FeatureCollection<
  Polygon | MultiPolygon,
  RegionFeature["properties"]
>;
const files = new Map<string, Promise<Boundaries>>();
let index: Promise<Region[]> | undefined;

async function read<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) throw new Error("行政区边界加载失败");
  return response.json() as Promise<T>;
}
export function regionIndex(): Promise<Region[]> {
  index ??= read<Region[]>("/maps/regions/index.json").catch((error) => {
    index = undefined;
    throw error;
  });
  return index;
}
function boundaries(url: string): Promise<Boundaries> {
  if (!files.has(url))
    files.set(
      url,
      read<Boundaries>(url).catch((error) => {
        files.delete(url);
        throw error;
      }),
    );
  return files.get(url)!;
}
function inRing(point: number[], ring: number[][]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [x, y] = ring[i],
      [xj, yj] = ring[j];
    if (
      y > point[1] !== yj > point[1] &&
      point[0] < ((xj - x) * (point[1] - y)) / (yj - y) + x
    )
      inside = !inside;
  }
  return inside;
}
export function contains(feature: RegionFeature, point: number[]): boolean {
  const polygons =
    feature.geometry.type === "Polygon"
      ? [feature.geometry.coordinates]
      : feature.geometry.coordinates;
  return polygons.some(
    ([outer, ...holes]) =>
      inRing(point, outer) && !holes.some((h) => inRing(point, h)),
  );
}

export async function placeRegion(
  place: MapPlace,
  regions: Region[],
): Promise<Region | undefined> {
  if (place.region_id) return regions.find((r) => r.id === place.region_id);
  // Old POI records retain their original data. Project their coordinates onto city boundaries.
  const domestic = ["CN", "HK", "MO", "TW"].includes(place.country_code ?? "");
  if (domestic) {
    const cities = await boundaries("/maps/regions/cities.geojson");
    const match = cities.features.find((f) =>
      contains(f, [place.longitude, place.latitude]),
    );
    return regions.find((r) => r.id === match?.properties.id);
  }
  return regions.find((r) => r.id === `country:${place.country_code}`);
}

export async function highlightedRegions(
  places: MapPlace[],
  status: PlaceStatus | "all",
  selectedId: string | null,
) {
  const regions = await regionIndex();
  const matches = await Promise.all(
    places.map(async (place) => ({
      place,
      region: await placeRegion(place, regions),
    })),
  );
  const grouped = new Map<string, { region: Region; places: MapPlace[] }>();
  for (const { place, region } of matches) {
    if (!region) continue;
    const group = grouped.get(region.id) ?? { region, places: [] };
    group.places.push(place);
    grouped.set(region.id, group);
  }
  const features = await Promise.all(
    [...grouped.values()].map(async ({ region, places: members }) => {
      const data = await boundaries(region.boundary_file);
      const feature = data.features.find((f) => f.properties.id === region.id);
      if (!feature) throw new Error("行政区边界缺失");
      const selected = members.find((p) => p.id === selectedId);
      return {
        ...feature,
        properties: {
          ...feature.properties,
          place_id: selected?.id ?? members[0].id,
          selected: Boolean(selected),
          status:
            status !== "all"
              ? status
              : members.some((p) => p.visit_count)
                ? "visited"
                : members.some((p) => p.upcoming_count)
                  ? "upcoming"
                  : "wishlist",
        },
      };
    }),
  );
  // Large regions first, so smaller overlapping districts remain clickable.
  features.sort((a, b) => a.properties.level - b.properties.level);
  return {
    data: { type: "FeatureCollection" as const, features },
    missing: matches.filter((m) => !m.region).length,
  };
}
