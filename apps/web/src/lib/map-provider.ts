import type { StyleSpecification } from "maplibre-gl";
import type { Scope } from "./types";
export interface MapProvider {
  style(): StyleSpecification;
  camera(scope: Scope): { center: [number, number]; zoom: number };
}
// Published WGS84 administrative geometry, served locally without API keys.
export const outlineMapProvider: MapProvider = {
  camera: (scope) =>
    scope === "domestic"
      ? { center: [104, 35], zoom: 2.8 }
      : { center: [30, 20], zoom: 1.2 },
  style: () => ({
    version: 8,
    sources: {
      countries: {
        type: "geojson",
        data: "/maps/countries.geojson",
        attribution:
          '© <a href="https://www.naturalearthdata.com/">Natural Earth</a>',
      },
      provinces: { type: "geojson", data: "/maps/provinces.geojson" },
      visits: {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      },
    },
    layers: [
      {
        id: "background",
        type: "background",
        paint: { "background-color": "#eef0e8" },
      },
      {
        id: "land",
        type: "fill",
        source: "countries",
        paint: { "fill-color": "#dbe3d4" },
      },
      {
        id: "borders",
        type: "line",
        source: "countries",
        paint: { "line-color": "#fbfcf7", "line-width": 1 },
      },
      {
        id: "provinces",
        type: "line",
        source: "provinces",
        minzoom: 2,
        paint: { "line-color": "#fbfcf7", "line-width": 0.8 },
      },
      {
        id: "places",
        type: "circle",
        source: "visits",
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["get", "visit_count"],
            0,
            6,
            10,
            13,
          ],
          "circle-color": [
            "match",
            ["get", "status"],
            "visited",
            "#3f6849",
            "upcoming",
            "#a8743c",
            "#f8f7f3",
          ],
          "circle-stroke-color": [
            "match",
            ["get", "status"],
            "wishlist",
            "#778471",
            "#fffefa",
          ],
          "circle-stroke-width": 2,
        },
      },
    ],
  }),
};
